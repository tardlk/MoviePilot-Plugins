"""
光鸭云盘存储操作层。

对外提供与 MoviePilot V3 存储契约一致的方法集合，供插件主类与存储链调用：
`list / detail / get_item / get_item_strict / get_parent / create_folder / get_folder /
delete / rename / copy / move / upload / upload_folder / download / usage /
support_transtype / exists / snapshot / clear_cache`。

设计要点：
- 列表分页取全；``get_item`` 容忍查询失败返回 None，``get_item_strict`` 失败抛
  ``StorageQueryError``——两者语义必须区分（查询失败 ≠ 文件不存在）；
- 缓存为实例级并带容量上限（``clear_cache()`` 只清自身）；列举失败不写入缓存；
- 删除/移动/复制走任务并等待完成；
- 上传：取票据 → 156/秒传探测 → OSS 断点续传 → 任务轮询确认（145 等视为进行中）。
"""

from __future__ import annotations

import ast
import shutil
import time
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from app import schemas
from app.modules.filemanager.storages import transfer_process
from app.sdk.config import global_vars, settings
from app.sdk.logging import logger
from app.sdk.network import RequestUtils

from .guangya_client import GuangYaApiError, GuangYaAuthError, GuangYaClient

try:
    from app.schemas.exception import StorageQueryError
except ImportError:  # pragma: no cover - 兼容旧版 MoviePilot
    class StorageQueryError(Exception):
        """无法确认存储查询结果时抛出。"""


class GuangYaApi:
    """
    光鸭云盘基础操作类。
    """

    # 实例缓存上限
    _CACHE_LIMIT = 5000
    # 列举分页的最大页数保护
    _MAX_PAGES = 1000
    # MD5 计算的分块大小
    _HASH_CHUNK = 4 * 1024 * 1024
    # 上传任务轮询：视为「进行中」的业务码
    _UPLOAD_PENDING_CODES = {
        0, 1, 3, 145, 146, 147, 155, 163,
        "0", "1", "3", "145", "146", "147", "155", "163",
    }
    # 任务状态：已完成 / 已失败
    _TASK_DONE = (2, "2", "success", "done", "finished")
    _TASK_FAILED = (3, -1, "3", "-1", "fail", "failed")

    def __init__(
        self,
        client: GuangYaClient,
        disk_name: str,
        page_size: int = 100,
        order_by: int = 3,
        sort_type: int = 1,
        permanently_delete: bool = False,
        resume_store_dir: Optional[str] = None,
    ):
        """初始化存储操作层。"""
        self.client = client
        self._disk_name = disk_name
        self._page_size = max(int(page_size or 100), 10)
        self._order_by = order_by
        self._sort_type = sort_type
        self._permanently_delete = permanently_delete
        self._resume_store_dir = resume_store_dir
        self.transtype = {"move": "移动", "copy": "复制"}
        # 实例级缓存
        self._id_cache: Dict[str, str] = {"/": ""}
        self._item_cache: Dict[str, Dict[str, Any]] = {}
        # 目录直接子项缓存（按父目录路径），避免同一目录内多次 get_item / 新建文件重复列举
        self._dir_cache: Dict[str, List[schemas.FileItem]] = {}

    # ── 路径 / 缓存工具 ──

    @staticmethod
    def _normalize_path(path: str) -> str:
        """规整为绝对路径形式（前导 /、无尾随 /）。"""
        normalized = str(path or "/").replace("\\", "/")
        if normalized in ("", "."):
            return "/"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized.rstrip("/") or "/"

    @staticmethod
    def _normalize_fileid(fileid: Optional[str], path: Optional[str] = None) -> str:
        """规整文件 ID：根目录统一为空串。"""
        normalized_fileid = str(fileid or "")
        normalized_path = str(path or "").replace("\\", "/")
        if normalized_fileid == "root" and normalized_path in ("", "/"):
            return ""
        return normalized_fileid

    def _cache_item(self, item: schemas.FileItem) -> None:
        """把条目写入路径缓存（超限时重置）。"""
        normalized_path = self._normalize_path(item.path)
        normalized_fileid = self._normalize_fileid(item.fileid, normalized_path)
        if normalized_path != "/" and normalized_fileid:
            self._id_cache[normalized_path] = normalized_fileid
        if len(self._id_cache) > self._CACHE_LIMIT:
            self._id_cache = {"/": ""}
        self._item_cache[normalized_path] = {
            "storage": item.storage,
            "fileid": normalized_fileid,
            "parent_fileid": str(item.parent_fileid or ""),
            "name": item.name,
            "basename": item.basename,
            "extension": item.extension,
            "type": item.type,
            "path": item.path,
            "size": item.size,
            "modify_time": item.modify_time,
            "thumbnail": getattr(item, "thumbnail", None),
            "pickcode": item.pickcode,
            "drive_id": getattr(item, "drive_id", None),
        }
        if len(self._item_cache) > self._CACHE_LIMIT:
            self._item_cache.clear()

    def _invalidate_path_cache(self, path: str) -> None:
        """失效指定路径的 ID/条目缓存及其所在目录的子项缓存。"""
        normalized_path = self._normalize_path(path)
        for key in (normalized_path, normalized_path.rstrip("/") or "/", f"{normalized_path.rstrip('/')}/"):
            self._id_cache.pop(key, None)
            self._item_cache.pop(key, None)
        self._invalidate_dir_cache(normalized_path)

    def _invalidate_dir_cache(self, path: str) -> None:
        """失效指定路径所在目录及其自身的子项缓存（增删改后调用）。"""
        normalized_path = self._normalize_path(path)
        parent_path = self._normalize_path(str(Path(normalized_path).parent))
        self._dir_cache.pop(parent_path, None)
        self._dir_cache.pop(normalized_path, None)

    def clear_cache(self) -> None:
        """清空实例级路径/文件项缓存。"""
        self._id_cache = {"/": ""}
        self._item_cache = {}
        self._dir_cache = {}

    # ── 响应解析 ──

    @staticmethod
    def _first_value(data: Any, keys: List[str], default: Any = None) -> Any:
        """按候选键顺序取第一个非 None 值。"""
        for key in keys:
            if isinstance(data, dict) and data.get(key) is not None:
                return data.get(key)
        return default

    @staticmethod
    def _parse_time(value: Any) -> Optional[float]:
        """把毫秒/秒时间戳或 ISO 字符串统一解析为 Unix 秒。"""
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return value / 1000 if value > 9999999999 else value
        if isinstance(value, str):
            try:
                if value.isdigit():
                    num = int(value)
                    return num / 1000 if num > 9999999999 else num
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except Exception:  # noqa: BLE001
                return None
        return None

    @staticmethod
    def _extract_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从多种响应结构中提取列表字段。"""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("list", "files", "items", "records", "fileList", "infoList", "InfoList"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []

    def _find_number(self, data: Any, keys: List[str]) -> Optional[float]:
        """递归查找第一个匹配候选键的数值（用于空间统计字段名不确定的场景）。"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in keys and value not in (None, ""):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        pass
            for value in data.values():
                found = self._find_number(value, keys)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for value in data:
                found = self._find_number(value, keys)
                if found is not None:
                    return found
        return None

    def _to_file_item(self, item: Dict[str, Any], parent_path: str = "/") -> schemas.FileItem:
        """把原始响应条目转换为 MoviePilot FileItem。"""
        file_id = str(self._first_value(item, ["fileId", "id", "fid", "resId"], ""))
        parent_id = str(self._first_value(item, ["parentId", "parent_file_id", "parentFileId"], ""))
        name = self._first_value(item, ["fileName", "name", "filename"], "") or ""
        raw_type = self._first_value(item, ["type", "resType", "fileType", "dirType"])
        is_dir = bool(
            item.get("isDir")
            or item.get("is_dir")
            or item.get("dir")
            or raw_type in ("dir", "folder")
            or raw_type == 2
        )
        if raw_type in (0, 1, "file"):
            is_dir = False
        path = f"{parent_path.rstrip('/')}/{name}" if parent_path != "/" else f"/{name}"
        file_path = path + ("/" if is_dir else "")
        size = self._first_value(item, ["fileSize", "size", "Size"], None)
        modify_time = self._parse_time(
            self._first_value(item, ["utime", "updateTime", "updatedAt", "UpdateAt", "modifyTime", "mtime"])
        )
        file_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=parent_id,
            name=name,
            basename=Path(name).stem,
            extension=Path(name).suffix[1:] if not is_dir and Path(name).suffix else None,
            type="dir" if is_dir else "file",
            path=file_path,
            size=int(size) if size not in (None, "") and not is_dir else None,
            modify_time=modify_time,
            thumbnail=self._first_value(item, ["thumbnail", "thumb", "cover"], None),
            pickcode=str(item),
            drive_id=str(self._first_value(item, ["gcid", "GCID", "md5"], "")) or None,
        )
        self._cache_item(file_item)
        return file_item

    def _path_to_id(self, path: str, strict: bool = False) -> str:
        """
        按路径逐级解析文件 ID。

        :param strict: True 时查询失败抛 GuangYaApiError；否则统一抛 FileNotFoundError
            （调用方按「不存在」处理）。确认不存在始终抛 FileNotFoundError。
        """
        normalized_path = self._normalize_path(path)
        if normalized_path == "/":
            return ""
        if normalized_path in self._id_cache:
            return self._id_cache[normalized_path]
        current_id = ""
        current_path = "/"
        for part in Path(normalized_path).parts[1:]:
            parent_item = schemas.FileItem(
                storage=self._disk_name, fileid=current_id, path=current_path, type="dir"
            )
            found = None
            for item in self._list_children(parent_item, strict=strict):
                if item.name == part:
                    found = item
                    break
            if not found:
                raise FileNotFoundError(f"【光鸭云盘】{normalized_path} 不存在")
            current_id = found.fileid or ""
            current_path = found.path if found.type == "dir" else str(Path(found.path).parent)
        self._id_cache[normalized_path] = current_id
        return current_id

    def _list_children(
        self,
        parent_item: schemas.FileItem,
        strict: bool = False,
        refresh: bool = False,
    ) -> List[schemas.FileItem]:
        """
        列出一个目录的全部直接子项（分页取全）。

        :param strict: True 时查询失败抛 GuangYaApiError；否则记录日志并返回 []。
        :param refresh: True 时绕过目录子项缓存，强制重新列举（写入后确认等场景）。

        仅成功的列举结果才会进入缓存，避免把查询失败/目录缺失缓存为「空目录」。
        """
        if parent_item.type == "file":
            item = self.detail(parent_item)
            return [item] if item else []

        cache_key = self._normalize_path(parent_item.path or "/")
        if not refresh and cache_key in self._dir_cache:
            return list(self._dir_cache[cache_key])

        try:
            if parent_item.path == "/":
                file_id = ""
            else:
                file_id = parent_item.fileid or self._path_to_id(parent_item.path, strict=strict)
        except FileNotFoundError:
            return []
        except GuangYaApiError:
            if strict:
                raise
            logger.debug(f"【光鸭云盘】解析目录失败: {parent_item.path}")
            return []

        items: List[schemas.FileItem] = []
        page = 0
        page_size = self._page_size
        while page < self._MAX_PAGES:
            try:
                data = self.client.get_file_list(
                    parent_id=file_id or "",
                    page_size=page_size,
                    order_by=self._order_by,
                    sort_type=self._sort_type,
                    file_types=[],
                    page=page,
                )
            except (GuangYaApiError, GuangYaAuthError) as err:
                if strict:
                    raise GuangYaApiError(f"获取目录列表失败: {err}")
                logger.debug(f"【光鸭云盘】获取目录列表失败 file_id={file_id!r}: {err}")
                # 查询失败不写入缓存，避免把临时故障固化成空目录
                return items
            raw_list = self._extract_list(data)
            if not raw_list:
                break
            for raw in raw_list:
                items.append(self._to_file_item(raw, parent_item.path or "/"))
            total = int(data.get("total") or 0) if isinstance(data, dict) else 0
            if len(raw_list) < page_size or (total and len(items) >= total):
                break
            page += 1
        if len(self._dir_cache) >= self._CACHE_LIMIT:
            self._dir_cache.clear()
        self._dir_cache[cache_key] = list(items)
        return items

    # ── 对外：列表 / 详情 / 查询 ──

    def list(self, fileitem: schemas.FileItem, page: int = 0, page_size: int = 100) -> List[schemas.FileItem]:
        """
        获取目录下的文件列表（分页取全；失败返回已获取部分）。

        对外列举始终重新拉取（refresh=True），保证快照/文件浏览能反映云端最新状态；
        目录子项缓存只用于 get_item 等按名查询，避免同一目录内重复列举。
        """
        if page_size and page_size > self._page_size:
            self._page_size = page_size
        return self._list_children(fileitem, strict=False, refresh=True)

    def detail(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """获取条目详情，按路径重新解析以保证信息最新。"""
        if fileitem.path:
            item = self.get_item(Path(fileitem.path))
            if item:
                return item
        return fileitem if fileitem.fileid else None

    def get_item(self, path: Path) -> Optional[schemas.FileItem]:
        """
        按路径获取文件或目录。

        容忍模式：不存在或查询失败一律返回 None。调用方若需区分「确认不存在」与
        「无法确认状态」，应改用 :meth:`get_item_strict`。
        """
        normalized = self._normalize_path(str(path))
        if normalized == "/":
            root_item = schemas.FileItem(
                storage=self._disk_name, path="/", fileid="", name=self._disk_name,
                basename=self._disk_name, type="dir",
            )
            self._cache_item(root_item)
            return root_item
        cached = self._item_cache.get(normalized)
        if cached:
            return schemas.FileItem(**cached)
        path_obj = Path(normalized)
        parent_path = path_obj.parent if path_obj.parent.as_posix() not in ("", ".") else Path("/")
        try:
            parent_id = self._path_to_id(parent_path.as_posix(), strict=False)
        except FileNotFoundError:
            return None
        parent = schemas.FileItem(
            storage=self._disk_name,
            path=parent_path.as_posix() if parent_path.as_posix() != "." else "/",
            fileid=parent_id,
            type="dir",
        )
        target_name = path_obj.name
        for item in self._list_children(parent, strict=False):
            if item.name == target_name:
                return item
        return None

    def get_item_strict(self, path: Path) -> Optional[schemas.FileItem]:
        """严格获取：确认不存在返回 None；无法确认状态时抛 StorageQueryError。"""
        normalized = self._normalize_path(str(path))
        if normalized == "/":
            return self.get_item(path)
        cached = self._item_cache.get(normalized)
        if cached:
            return schemas.FileItem(**cached)
        path_obj = Path(normalized)
        parent_path = path_obj.parent if path_obj.parent.as_posix() not in ("", ".") else Path("/")
        try:
            parent_id = self._path_to_id(parent_path.as_posix(), strict=True)
        except FileNotFoundError:
            return None
        except GuangYaApiError as err:
            raise StorageQueryError(f"无法确认父目录 {parent_path} 状态: {err}") from err
        parent = schemas.FileItem(
            storage=self._disk_name,
            path=parent_path.as_posix(),
            fileid=parent_id,
            type="dir",
        )
        try:
            children = self._list_children(parent, strict=True)
        except GuangYaApiError as err:
            raise StorageQueryError(f"查询目标目录失败，无法确认 {normalized}: {err}") from err
        for item in children:
            if item.name == path_obj.name:
                return item
        return None

    def get_parent(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """获取条目的父目录。"""
        return self.get_item(Path(fileitem.path).parent)

    # ── 目录创建 ──

    def create_folder(self, fileitem: schemas.FileItem, name: str) -> Optional[schemas.FileItem]:
        """在指定目录下创建子目录，成功返回新目录条目。"""
        try:
            new_path = Path(fileitem.path) / name
            parent_id = fileitem.fileid or self._path_to_id(fileitem.path)
            data = self.client.create_dir(parent_id=parent_id or "", dir_name=name)
        except (GuangYaApiError, GuangYaAuthError, FileNotFoundError) as err:
            logger.debug(f"【光鸭云盘】创建目录失败: {err}")
            return None
        raw = data.get("info") or data.get("Info") or data
        file_id = str(self._first_value(raw if isinstance(raw, dict) else {}, ["fileId", "id", "FileId"], ""))
        folder_item = schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=parent_id,
            path=str(new_path).replace("\\", "/") + "/",
            name=name,
            basename=name,
            type="dir",
            modify_time=int(datetime.now().timestamp()),
            pickcode=str(raw),
        )
        self._invalidate_dir_cache(str(new_path))
        self._cache_item(folder_item)
        return folder_item

    def get_folder(self, path: Path) -> Optional[schemas.FileItem]:
        """获取目录，不存在时逐级创建。"""
        folder = self.get_item(path)
        if folder:
            return folder
        current = schemas.FileItem(storage=self._disk_name, path="/", fileid="", type="dir")
        for part in Path(self._normalize_path(str(path))).parts[1:]:
            next_folder = None
            for sub_folder in self._list_children(current):
                if sub_folder.type == "dir" and sub_folder.name == part:
                    next_folder = sub_folder
                    break
            if not next_folder:
                next_folder = self.create_folder(current, part)
            if not next_folder:
                logger.warning(f"【光鸭云盘】创建目录 {current.path}{part} 失败！")
                return None
            current = next_folder
        return current

    # ── 删除 / 重命名 / 移动 / 复制 ──

    def _wait_task(self, task_id: str, max_try: int = 40, interval: float = 0.3) -> bool:
        """
        等待任务完成。

        仅在明确失败时返回 False，超时/查询异常按已受理处理（与原行为一致）。
        """
        task_id = str(task_id or "").strip()
        if not task_id:
            return True
        for index in range(max_try):
            try:
                data = self.client.get_task_status(task_id)
            except (GuangYaApiError, GuangYaAuthError):
                data = {}
            status = data.get("status", data.get("taskStatus"))
            if status in self._TASK_DONE:
                return True
            if status in self._TASK_FAILED:
                logger.error(f"【光鸭云盘】任务失败 task_id={task_id} status={status}")
                return False
            if index < max_try - 1:
                time.sleep(interval)
        logger.warning(f"【光鸭云盘】任务状态未确认（按已受理处理） task_id={task_id}")
        return True

    def delete(self, fileitem: schemas.FileItem) -> bool:
        """删除文件/目录（任务型）；配置了彻底删除时再从回收站清除。"""
        try:
            file_id = fileitem.fileid or self._path_to_id(str(fileitem.path))
            data = self.client.delete_file([file_id])
            self._wait_task(data.get("taskId") or "")
            self._invalidate_path_cache(fileitem.path)
            if self._permanently_delete:
                return self._delete_permanently_from_recycle(fileitem)
            return True
        except (GuangYaApiError, GuangYaAuthError, FileNotFoundError) as err:
            logger.debug(f"【光鸭云盘】删除文件失败: {err}")
            return False

    def rename(self, fileitem: schemas.FileItem, name: str) -> bool:
        """重命名文件/目录。"""
        try:
            file_id = fileitem.fileid or self._path_to_id(str(fileitem.path))
            self.client.rename(file_id=file_id, new_name=name)
            self._invalidate_path_cache(fileitem.path)
            return True
        except (GuangYaApiError, GuangYaAuthError, FileNotFoundError) as err:
            logger.debug(f"【光鸭云盘】重命名失败: {err}")
            return False

    def copy(self, fileitem: schemas.FileItem, path: Path, new_name: str = None) -> bool:
        """复制文件/目录到目标目录（任务型），可选重命名。"""
        try:
            target_parent = Path(path)
            target_id = self._path_to_id(target_parent.as_posix())
            file_id = fileitem.fileid or self._path_to_id(str(fileitem.path))
            data = self.client.copy_file([file_id], target_parent_id=target_id or "")
            self._wait_task(data.get("taskId") or "")
            copied = self._wait_item_visible(target_parent, fileitem.name or Path(fileitem.path).name)
            if not copied:
                return False
            if new_name and new_name != copied.name:
                return self.rename(copied, new_name)
            return True
        except (GuangYaApiError, GuangYaAuthError, FileNotFoundError) as err:
            logger.debug(f"【光鸭云盘】复制文件异常: {err}")
            return False

    def move(self, fileitem: schemas.FileItem, path: Path, new_name: str = None) -> bool:
        """移动文件/目录到目标目录（任务型），可选重命名。"""
        try:
            target_parent = Path(path)
            source_path = Path(fileitem.path)
            current_name = fileitem.name or source_path.name
            target_name = new_name or current_name
            if target_parent.as_posix() == source_path.parent.as_posix():
                if target_name == current_name:
                    return True
                return self.rename(fileitem, target_name)
            target_id = self._path_to_id(target_parent.as_posix())
            file_id = fileitem.fileid or self._path_to_id(str(fileitem.path))
            data = self.client.move_file([file_id], target_parent_id=target_id or "")
            self._wait_task(data.get("taskId") or "")
            self._invalidate_path_cache(fileitem.path)
            moved = self._wait_item_visible(target_parent, current_name)
            if not moved:
                return False
            if target_name != moved.name:
                return self.rename(moved, target_name)
            return True
        except (GuangYaApiError, GuangYaAuthError, FileNotFoundError) as err:
            logger.debug(f"【光鸭云盘】移动文件异常: {err}")
            return False

    def _wait_item_visible(
        self, parent_path: Path, name: str, retry: int = 10, interval: float = 0.5
    ) -> Optional[schemas.FileItem]:
        """轮询等待条目在目标目录可见（写入后索引延迟）。"""
        target_path = Path(parent_path) / name
        for index in range(retry):
            self._invalidate_path_cache(str(target_path))
            item = self.get_item(target_path)
            if item:
                return item
            if index < retry - 1:
                time.sleep(interval)
        return None

    # ── 下载 ──

    @staticmethod
    def _parse_pickcode(value: Any) -> Dict[str, Any]:
        """解析 pickcode（可能是 dict 或其字面量字符串）。"""
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def _normalize_download_fileitem(self, fileitem: schemas.FileItem) -> schemas.FileItem:
        """下载前规整条目：从 pickcode 中补全 fileId/name 等信息。"""
        pickcode = self._parse_pickcode(fileitem.pickcode)
        raw = pickcode.get("fileInfo") if isinstance(pickcode.get("fileInfo"), dict) else pickcode
        if not isinstance(raw, dict):
            raw = {}
        if not raw and fileitem.path and (not fileitem.fileid or not fileitem.name):
            item = self.get_item(Path(fileitem.path))
            if item:
                return item
        raw_file_id = str(self._first_value(raw, ["fileId", "id", "fid", "resId"], ""))
        raw_name = self._first_value(raw, ["fileName", "name", "filename"], "") or ""
        if not raw_file_id or not raw_name:
            return fileitem
        if fileitem.fileid == raw_file_id and fileitem.name:
            return fileitem
        location = pickcode.get("location") if isinstance(pickcode, dict) else None
        normalized_path = (
            f"/{str(location).lstrip('/')}" if location
            else str(Path(fileitem.path) / raw_name).replace("\\", "/")
        )
        return schemas.FileItem(
            storage=fileitem.storage,
            fileid=raw_file_id,
            parent_fileid=str(self._first_value(
                raw, ["parentId", "parent_file_id", "parentFileId"], fileitem.parent_fileid or ""
            )),
            name=raw_name,
            basename=Path(raw_name).stem,
            extension=Path(raw_name).suffix[1:] if Path(raw_name).suffix else None,
            type="file",
            path=normalized_path,
            size=int(raw.get("fileSize")) if raw.get("fileSize") not in (None, "") else fileitem.size,
            modify_time=self._parse_time(
                self._first_value(raw, ["utime", "updateTime", "updatedAt", "modifyTime"], fileitem.modify_time)
            ),
            thumbnail=self._first_value(raw, ["thumbnail", "thumb", "cover"], getattr(fileitem, "thumbnail", None)),
            pickcode=str(raw),
            drive_id=str(self._first_value(raw, ["gcid", "GCID", "md5"], getattr(fileitem, "drive_id", "") or "")) or None,
        )

    def _get_download_url(self, fileitem: schemas.FileItem) -> Optional[str]:
        """获取下载直链，直链失败时按 gcid 回退 VOD 链接。"""
        file_id = fileitem.fileid or self._path_to_id(str(fileitem.path))
        try:
            data = self.client.get_download_url(file_id)
        except (GuangYaApiError, GuangYaAuthError):
            data = None
        if isinstance(data, dict):
            download_url = self._first_value(data, ["signedURL", "downloadUrl", "download_url", "url"])
            if download_url:
                return download_url
        if not getattr(fileitem, "drive_id", None):
            logger.error(f"【光鸭云盘】获取下载链接失败: {file_id}")
            return None
        try:
            vod = self.client.get_vod_download_url(file_id, str(fileitem.drive_id))
        except (GuangYaApiError, GuangYaAuthError) as err:
            logger.error(f"【光鸭云盘】获取下载链接失败: {err}")
            return None
        download_url = self._first_value(
            vod if isinstance(vod, dict) else {}, ["signedURL", "downloadUrl", "download_url", "url"]
        )
        if not download_url:
            logger.error("【光鸭云盘】获取下载链接失败: 无URL")
            return None
        return download_url

    def download(self, fileitem: schemas.FileItem, path: Path = None) -> Optional[Path]:
        """下载文件到本地路径（默认宿主临时目录），支持传输中断。"""
        try:
            fileitem = self._normalize_download_fileitem(fileitem)
            download_url = self._get_download_url(fileitem)
            if not download_url:
                return None
            local_path = (path or settings.TEMP_PATH) / (
                fileitem.name or Path(fileitem.path).name or fileitem.fileid
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【光鸭云盘】获取下载链接失败: {fileitem.name} - {err}")
            return None

        file_size = fileitem.size
        progress_callback = transfer_process(Path(fileitem.path).as_posix())
        try:
            http = RequestUtils(verify=True, timeout=300)
            with http.response_manager("get", download_url, stream=True) as response_obj:
                if response_obj is None:
                    logger.error(f"【光鸭云盘】下载失败: {fileitem.name} - 网络请求失败")
                    return None
                response_obj.raise_for_status()
                downloaded_size = 0
                with open(local_path, "wb") as file_obj:
                    for chunk in response_obj.iter_content(chunk_size=10 * 1024 * 1024):
                        if global_vars.is_transfer_stopped(fileitem.path):
                            self._safe_unlink(local_path)
                            return None
                        if not chunk:
                            continue
                        file_obj.write(chunk)
                        downloaded_size += len(chunk)
                        if file_size:
                            progress_callback((downloaded_size * 100) / file_size)
            progress_callback(100)
            return local_path
        except Exception as err:  # noqa: BLE001
            logger.error(f"【光鸭云盘】下载失败: {fileitem.name} - {err}")
            self._safe_unlink(local_path)
            return None

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        """尽力删除本地文件，失败不影响主流程。"""
        try:
            if path.exists():
                path.unlink()
        except Exception:  # noqa: BLE001
            pass

    # ── 上传 ──

    @staticmethod
    def _extract_file_info(resp: Dict[str, Any]) -> Dict[str, Any]:
        """从上传响应中提取文件信息对象。"""
        data = resp.get("data") if isinstance(resp, dict) else None
        if not isinstance(data, dict):
            return data if isinstance(data, dict) else {}
        for key in ("fileInfo", "info", "Info", "detail"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return data

    def _has_uploaded_file(self, resp: Any) -> bool:
        """判断响应中是否含有效 fileId（表示文件已落库）。"""
        raw = self._extract_file_info(resp) if isinstance(resp, dict) else {}
        return bool(self._first_value(raw, ["fileId", "id", "fid", "resId", "FileId"], ""))

    def _confirm_uploaded_item(
        self,
        target_path: Path,
        retry: int = 20,
        interval: float = 0.5,
        file_size: Optional[int] = None,
    ) -> Optional[schemas.FileItem]:
        """按「路径 + 文件名 + 大小」轮询回查已上传文件。"""
        target_path = Path(target_path)
        for index in range(retry):
            self._invalidate_path_cache(str(target_path))
            parent_path = target_path.parent if target_path.parent.as_posix() else Path("/")
            parent_id = self._path_to_id(parent_path.as_posix(), strict=False)
            parent = schemas.FileItem(
                storage=self._disk_name,
                path=parent_path.as_posix() if parent_path.as_posix() != "." else "/",
                fileid=parent_id,
                type="dir",
            )
            for item in self._list_children(parent):
                if item.name != target_path.name:
                    continue
                if file_size and item.size and int(item.size) != int(file_size):
                    continue
                return item
            if index < retry - 1 and interval > 0:
                time.sleep(interval)
        return None

    def _wait_upload_done(
        self,
        task_id: str,
        *,
        target_path: Optional[Path] = None,
        file_size: Optional[int] = None,
        max_try: int = 120,
        interval: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """轮询上传任务；返回含 fileId 的文件信息，或 None。"""
        task_id = str(task_id or "").strip()
        if not task_id:
            return None
        last: Optional[Dict[str, Any]] = None
        for index in range(max_try):
            try:
                info = self.client.get_file_info_by_task_id(task_id)
            except (GuangYaApiError, GuangYaAuthError):
                info = None
            if isinstance(info, dict):
                last = info
                if self._has_uploaded_file(info):
                    return info
            if target_path is not None and index > 0 and index % 5 == 0:
                item = self._confirm_uploaded_item(target_path, retry=1, interval=0, file_size=file_size)
                if item:
                    return {"fileId": item.fileid, "parentId": item.parent_fileid}
            if index < max_try - 1:
                time.sleep(interval)
        return last

    def _build_uploaded_item(
        self, target_path: Path, target_name: str, parent_id: str, file_size: int, raw: Dict[str, Any] = None
    ) -> schemas.FileItem:
        """在无法从云端确认时，按已知信息构造 FileItem。"""
        raw = raw or {}
        # 未确认到实际文件时，父目录列表缓存可能仍是旧的，先失效以便后续列举能取到新文件
        self._invalidate_dir_cache(Path(target_path).as_posix())
        file_id = str(self._first_value(raw, ["fileId", "id", "FileId", "fid", "resId"], ""))
        return schemas.FileItem(
            storage=self._disk_name,
            fileid=file_id,
            parent_fileid=parent_id,
            path=Path(target_path).as_posix(),
            type="file",
            name=target_name,
            basename=Path(target_name).stem,
            extension=Path(target_name).suffix[1:] if Path(target_name).suffix else None,
            size=file_size,
            modify_time=int(datetime.now().timestamp()),
            pickcode=str(raw),
            thumbnail=self._first_value(raw, ["thumbnail", "thumb", "cover"], None),
            drive_id=str(self._first_value(raw, ["gcid", "GCID", "md5"], "")) or None,
        )

    def _resolve_uploaded_item(
        self, task_id: str, target_path: Path, target_name: str, parent_id: str, file_size: int
    ) -> Optional[schemas.FileItem]:
        """秒传/完成场景：按 taskId 取回已上传条目。"""
        if task_id:
            info = self._wait_upload_done(task_id, target_path=target_path, file_size=file_size, max_try=120)
            if isinstance(info, dict) and self._has_uploaded_file(info):
                raw = self._extract_file_info(info)
                item = self._confirm_uploaded_item(target_path, retry=6, interval=0.5, file_size=file_size)
                return item or self._build_uploaded_item(target_path, target_name, parent_id, file_size, raw)
        return self._confirm_uploaded_item(target_path, retry=10, interval=0.5, file_size=file_size)

    def upload(
        self,
        target_dir: schemas.FileItem,
        local_path: Path,
        new_name: Optional[str] = None,
        on_progress: Optional[Callable[[int], None]] = None,
        on_phase: Optional[Callable[[str], None]] = None,
        result_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[schemas.FileItem]:
        """
        上传本地文件到目标目录。

        :param on_progress: 0-100 的字节传输进度回调。
        :param on_phase: 阶段回调，用于告知调用方当前处于「哈希计算/传输/确认」等阶段，
            避免大文件计算 MD5 期间进度条长时间无反馈。
        :param result_meta: 命中秒传时写入 ``flash=True``。
        """
        if result_meta is not None:
            result_meta["flash"] = False
        if local_path.is_dir():
            return self.upload_folder(target_dir, local_path, new_name)

        target_name = new_name or local_path.name
        target_path = Path(target_dir.path) / target_name
        try:
            parent_id = target_dir.fileid or self._path_to_id(target_dir.path)
        except FileNotFoundError:
            return None

        try:
            transfer_callback = transfer_process(local_path.as_posix())

            def progress_callback(value):
                """同时驱动宿主传输进度与调用方回调。"""
                transfer_callback(value)
                if on_progress:
                    try:
                        on_progress(value)
                    except Exception:  # noqa: BLE001
                        pass

            def phase_callback(phase: str) -> None:
                """透传阶段变化，异常不影响上传。"""
                if on_phase:
                    try:
                        on_phase(phase)
                    except Exception:  # noqa: BLE001
                        pass

            file_size = local_path.stat().st_size
            phase_callback("hashing")
            file_md5 = self._calc_md5(local_path)
            phase_callback("uploading")

            # 1) 取上传票据；156 表示云端已完成（秒传）
            try:
                data = self.client.get_upload_token(
                    file_name=target_name,
                    file_size=file_size,
                    file_md5=file_md5,
                    parent_id=parent_id or "",
                    capacity=2,
                )
            except GuangYaApiError as err:
                # client 允许 156，其余非成功码在此抛出
                logger.error(f"【光鸭云盘】上传失败：get_res_center_token {target_name} - {err}")
                return None
            except GuangYaAuthError:
                return None
            data = data if isinstance(data, dict) else {}
            task_id = str(self._first_value(data, ["taskId", "task_id"], ""))
            # 156（云端已完成）时 data 只带 taskId、无 objectPath
            object_path = data.get("objectPath", "")
            if task_id and not object_path:
                phase_callback("confirming")
                item = self._resolve_uploaded_item(task_id, target_path, target_name, parent_id, file_size)
                if item:
                    if result_meta is not None:
                        result_meta["flash"] = True
                    progress_callback(100)
                    return item
                logger.warning(f"【光鸭云盘】上传诊断[{target_name}] 云端已完成但未取回文件")
                return None

            # 2) OSS 分片上传
            # 说明：秒传由上传票据返回码 156 识别（见上），不额外调用秒传探测接口，
            # 避免误判后空等任务；未命中 156 即走真实上传。
            bucket_name = data.get("bucketName", "")
            endpoint = data.get("endPoint", "") or data.get("fullEndPoint", "")
            creds = data.get("creds", {}) or {}
            access_key_id = creds.get("accessKeyID", "")
            secret_access_key = creds.get("secretAccessKey", "")
            session_token = creds.get("sessionToken", "")

            oss_result = None
            if endpoint and bucket_name and object_path and access_key_id and secret_access_key and session_token:
                host = self._resolve_oss_host(endpoint, bucket_name)
                try:
                    oss_result = self.client.upload_file_multipart(
                        endpoint=f"https://{host}",
                        bucket_name=bucket_name,
                        object_path=object_path,
                        file_path=str(local_path),
                        oss_access_key_id=access_key_id,
                        oss_access_key_secret=secret_access_key,
                        security_token=session_token,
                        progress_callback=lambda consumed, total: (
                            progress_callback((consumed * 100) / total) if total else None
                        ),
                        store_root=self._resume_store_dir,
                    )
                except GuangYaApiError as err:
                    logger.error(f"【光鸭云盘】上传诊断[{target_name}] {err}")
                    return None
            else:
                logger.error(f"【光鸭云盘】上传诊断[{target_name}] 缺少 OSS 凭证字段")

            # 3) 任务确认 + 按「路径+大小」回查
            # 光鸭列表对刚上传文件有分钟级延迟，OSS 已成功时只做短等待，
            # 未确认到则按「已上传」处理，后续同步会自然收敛。
            phase_callback("confirming")
            result = (
                self._wait_upload_done(task_id, target_path=target_path, file_size=file_size, max_try=20)
                if task_id
                else None
            )
            item = self._confirm_uploaded_item(target_path, retry=8, interval=0.5, file_size=file_size)
            if item:
                progress_callback(100)
                return item

            if isinstance(result, dict) and self._has_uploaded_file(result):
                raw = self._extract_file_info(result)
                progress_callback(100)
                return self._build_uploaded_item(target_path, target_name, parent_id, file_size, raw)

            if oss_result:
                logger.warning(f"【光鸭云盘】上传诊断[{target_name}] OSS 上传成功但云端暂未确认，按已上传处理")
                progress_callback(100)
                return self._build_uploaded_item(target_path, target_name, parent_id, file_size)

            logger.error(f"【光鸭云盘】上传失败：{target_name}")
            return None
        except Exception as err:  # noqa: BLE001
            logger.error(f"【光鸭云盘】上传失败: {target_name} - {err}")
            return None

    def _calc_md5(self, local_path: Path) -> str:
        """分块计算文件 MD5（大写十六进制）。"""
        hash_md5 = md5()
        with open(local_path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(self._HASH_CHUNK), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest().upper()

    @staticmethod
    def _resolve_oss_host(endpoint: str, bucket_name: str) -> str:
        """从 endpoint 中解析 OSS 主机名（去掉 bucket 前缀重复）。"""
        parsed = urlparse(endpoint if endpoint.startswith("http") else f"https://{endpoint}")
        host = parsed.netloc or parsed.path
        if bucket_name and host.startswith(bucket_name + "."):
            host = host[len(bucket_name) + 1:]
        return host

    def upload_folder(
        self, target_dir: schemas.FileItem, local_path: Path, new_name: Optional[str] = None
    ) -> Optional[schemas.FileItem]:
        """递归上传本地目录到目标目录，保留相对结构。"""
        folder_name = new_name or local_path.name
        cloud_folder = self.create_folder(target_dir, folder_name)
        if not cloud_folder:
            return None
        for child in local_path.iterdir():
            if global_vars.is_transfer_stopped(child.as_posix()):
                return None
            if child.is_dir():
                if not self.upload_folder(cloud_folder, child):
                    return None
            else:
                if not self.upload(cloud_folder, child):
                    return None
        return cloud_folder

    # ── 回收站 / 空间 / 快照 ──

    def _list_recycle_items(self, page: int = 0, page_size: int = 100) -> List[Dict[str, Any]]:
        """列举回收站条目（dirType=4）。"""
        try:
            data = self.client.get_file_list(
                parent_id="", page_size=page_size, order_by=10, sort_type=0,
                file_types=[], page=page, dir_type=4,
            )
        except (GuangYaApiError, GuangYaAuthError):
            return []
        return self._extract_list(data)

    def _find_recycle_item(
        self, fileitem: schemas.FileItem, retry: int = 10, interval: float = 0.5
    ) -> Dict[str, Any]:
        """在回收站中按名称与路径定位条目。"""
        target_name = fileitem.name or Path(fileitem.path).name
        target_path = str(fileitem.path or "").rstrip("/")
        for index in range(retry):
            for page in range(3):
                for raw in self._list_recycle_items(page=page, page_size=100):
                    raw_name = self._first_value(raw, ["fileName", "name", "filename"], "") or ""
                    if raw_name != target_name:
                        continue
                    raw_path = str(
                        self._first_value(raw, ["location", "path", "filePath", "parentPath"], "") or ""
                    ).rstrip("/")
                    if raw_path and target_path and target_path not in raw_path and raw_path not in target_path:
                        continue
                    return raw
            if index < retry - 1:
                time.sleep(interval)
        return {}

    def _delete_permanently_from_recycle(self, fileitem: schemas.FileItem) -> bool:
        """从回收站彻底删除条目。"""
        recycle_item = self._find_recycle_item(fileitem)
        recycle_file_id = str(self._first_value(recycle_item, ["fileId", "id", "fid", "resId"], ""))
        if not recycle_file_id:
            return True
        try:
            data = self.client.delete_file([recycle_file_id])
            self._wait_task(data.get("taskId") or "")
        except (GuangYaApiError, GuangYaAuthError) as err:
            logger.warning(f"【光鸭云盘】永久删除失败，文件可能仍在回收站: {err}")
        return True

    def usage(self) -> Optional[schemas.StorageUsage]:
        """获取空间用量，字段缺失时按 total-used 兜底。"""
        try:
            envelope = self.client.get_assets()
            data = envelope.get("data") if isinstance(envelope, dict) else None
            if not isinstance(data, dict):
                data = envelope if isinstance(envelope, dict) else {}
            total = self._find_number(data, [
                "totalSpaceSize", "total_space", "totalSpace", "total", "totalSize", "total_size",
                "capacity", "spaceTotal", "quota", "quotaSize",
            ])
            used = self._find_number(data, [
                "usedSpaceSize", "used_space", "usedSpace", "used", "usedSize", "used_size",
                "spaceUsed", "useSize", "fileSize",
            ])
            available = self._find_number(data, [
                "freeSpaceSize", "free_space", "freeSpace", "free", "available", "freeSize",
                "free_size", "availableSpace", "spaceAvailable", "remain", "remainSize", "remainingSize",
            ])
            total = float(total or 0)
            if available is None:
                available = max(total - float(used or 0), 0) if total else 0
            return schemas.StorageUsage(total=total, available=float(available or 0))
        except Exception as err:  # noqa: BLE001
            logger.debug(f"【光鸭云盘】获取空间使用情况失败: {err}")
            return schemas.StorageUsage(total=0, available=0)

    def support_transtype(self) -> dict:
        """返回支持的整理方式。"""
        return self.transtype

    def is_support_transtype(self, transtype: str) -> bool:
        """判断是否支持指定整理方式。"""
        return transtype in self.transtype

    def exists(self, fileitem: schemas.FileItem) -> bool:
        """判断条目是否存在。"""
        return bool(self.get_item(Path(fileitem.path)))

    def snapshot(self, fileitem: schemas.FileItem) -> List[schemas.FileItem]:
        """递归列出目录下的所有文件条目。"""
        result: List[schemas.FileItem] = []

        def _walk(_item: schemas.FileItem):
            """深度优先遍历，仅收集文件。"""
            for child in self._list_children(_item):
                if child.type == "dir":
                    _walk(child)
                else:
                    result.append(child)

        _walk(fileitem)
        return result

    @staticmethod
    def copy_local(src: Path, dst: Path) -> bool:
        """本地复制（文件或目录）。"""
        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            return True
        except Exception:  # noqa: BLE001
            return False

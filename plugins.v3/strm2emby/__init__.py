"""
Strm2Emby —— 让 MoviePilot 把「光鸭云盘」当作存储使用，并提供目录同步、
手动上传、上传记录与 LitePan 联动。

文件结构：
- 本文件：插件主类，负责生命周期、配置、API、存储契约转发、目录同步与联动；
- ``guangya_client.py``：传输层，只提供原子 HTTP 能力；
- ``guangya_api.py``：存储语义层，把云盘 API 翻译为 MoviePilot 的 FileItem 语义；
- ``models.py``：API 请求/响应数据模型。

关于 `get_module()` 返回值的约定（重要）：
存储族模块方法的聚合策略并非单一（见宿主
``app/runtime/extensions/module/contracts.py`` 的 ``ModuleResultAggregation``）：

- ``list_files``（及 ``media_files``）使用 ``ORDERED_LIST_MERGE``：各 provider 的列表
  结果按序合并，空列表不参与合并；
- 其余方法（``any_files`` / ``create_folder`` / ``upload_file`` / ``storage_manage`` 等）
  使用 ``FIRST_NON_EMPTY``：返回非空即停止分派。

两者的共同约定是：返回 ``None`` 表示「不是本存储，请继续找下一个 provider」。
因此本插件中：

- ``None`` 仅用于表达「该条目不属于本存储」（即 ``fileitem.storage`` 不匹配）；
- 属于本存储但无法处理时，必须返回该方法的失败语义（列表返回 ``[]``、布尔返回
  ``False``、对象返回 ``None``）并记录错误日志，不能返回 ``None``。

否则真实故障会被分派器误判为「该存储不具备此能力」，进而落到宿主的
``FileManagerModule`` 并报出「不支持的存储类型」，掩盖真实原因。
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends

from app import schemas
from app.api.dependencies.auth import get_current_active_superuser
from app.schemas import FileItem, StorageOperSelectionEventData
from app.schemas.types import ChainEventType, StorageAction
from app.sdk.events import Event, eventmanager
from app.sdk.logging import logger
from app.sdk.network import RequestUtils
from app.sdk.plugin import _PluginBase
from app.sdk.services import StorageHelper

from .guangya_api import GuangYaApi
from .guangya_client import GuangYaClient
from .models import (
    FsEntry,
    FsListData,
    LitePanNotifyData,
    LoginPollData,
    PluginConfigData,
    PluginConfigPayload,
    QrCodeData,
    UploadHistoryData,
    UploadPayload,
    UploadProgressData,
    UploadRecord,
    UploadStatsData,
)

# 同名文件处理策略
CONFLICT_SKIP = "skip"
CONFLICT_OVERWRITE = "overwrite"
CONFLICT_RENAME = "rename"
CONFLICT_CHOICES = (CONFLICT_SKIP, CONFLICT_OVERWRITE, CONFLICT_RENAME)

# 上传/同步触发来源
TRIGGER_MANUAL = "manual"
TRIGGER_SYNC = "sync"
TRIGGER_WATCH = "watch"

# 上传阶段标识（用于把「计算哈希」等阶段透传给前端）
PHASE_HASHING = "hashing"
PHASE_UPLOADING = "uploading"
PHASE_CONFIRMING = "confirming"

# 不应上传的临时文件后缀
_TEMP_SUFFIXES = (
    ".part", ".tmp", ".temp", ".crdownload", ".download", ".downloading",
    ".!ut", ".!qb", ".aria2", ".opdownload", ".partial",
)


class Strm2Emby(_PluginBase):
    """
    Strm2Emby 插件主类。
    """

    # ── 插件元信息 ──
    plugin_name = "Strm2Emby"
    plugin_desc = "使 MoviePilot 存储支持光鸭云盘，内置目录同步、手动上传与 LitePan 联动。"
    plugin_icon = "https://raw.githubusercontent.com/tardlk/MoviePilot-Plugins/main/icons/Strm2Emby.png"
    plugin_version = "1.0.2"
    plugin_author = "tardlk"
    author_url = "https://github.com/tardlk"
    plugin_config_prefix = "strm2emby_"
    plugin_order = 99
    auth_level = 1

    # 存储展示名（用于 StorageHelper 注册与 FileItem.storage）
    _disk_name = "Strm2Emby"
    # 快照时是否按目录修改时间做增量跳过（对齐 MoviePilot V3 StorageBase）
    snapshot_check_folder_modtime: bool = True

    # 存储整理方式的兜底声明（存储层未就绪时使用）
    _TRANSTYPE_FALLBACK = {"move": "移动", "copy": "复制"}

    # 记录与进度的容量上限
    _upload_history_max: int = 500
    _progress_items_max: int = 200

    # 默认配置值（供 _full_config / _merge_config 复用，避免散落字面量）
    _DEFAULT_POLL_INTERVAL = 5
    _DEFAULT_PAGE_SIZE = 100
    _DEFAULT_ORDER_BY = 3
    _DEFAULT_SORT_TYPE = 1
    _DEFAULT_MIN_INTERVAL = 0.0
    _DEFAULT_DEBOUNCE = 30

    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)

    # ── 生命周期 ──

    def __init__(self):
        """初始化插件实例状态（全部为实例属性，不使用类属性承载可变状态）。"""
        super().__init__()
        # 运行态对象
        self._client: Optional[GuangYaClient] = None
        self._guangya_api: Optional[GuangYaApi] = None

        # 配置项
        self._enabled = False
        self._access_token = ""
        self._refresh_token = ""
        self._client_id = GuangYaClient.DEFAULT_CLIENT_ID
        self._device_id = ""
        self._poll_interval = self._DEFAULT_POLL_INTERVAL
        self._page_size = self._DEFAULT_PAGE_SIZE
        self._order_by = self._DEFAULT_ORDER_BY
        self._sort_type = self._DEFAULT_SORT_TYPE
        self._min_interval = self._DEFAULT_MIN_INTERVAL
        self._permanently_delete = False

        # 目录同步
        self._sync_enabled = False
        self._sync_source_dir = ""
        self._sync_remote_dir = "/"
        self._sync_watch = False
        self._sync_cron = ""
        self._sync_conflict = CONFLICT_SKIP
        self._sync_delete_source = False
        self._sync_extensions = ""

        # 允许浏览/手动上传的本地根目录（逗号分隔，空表示不额外限制）
        self._fs_allowed_roots = ""

        # LitePan 联动
        self._litepan_enabled = False
        self._litepan_base_url = ""
        self._litepan_api_key = ""
        self._litepan_event = "MP"
        self._litepan_source = ""
        self._litepan_path = ""
        self._litepan_message = ""
        self._litepan_debounce = self._DEFAULT_DEBOUNCE
        self._last_litepan_notify: Optional[Dict[str, Any]] = None

        # 扫码登录临时态
        self._device_code = ""
        self._user_code = ""
        self._verification_uri = ""
        self._qr_expires_at = 0

        # 并发控制
        self._sync_lock = threading.Lock()
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_stop: Optional[threading.Event] = None
        self._litepan_lock = threading.Lock()
        self._litepan_timer: Optional[threading.Timer] = None
        self._progress_lock = threading.Lock()

        # 记录与进度
        self._upload_history: List[Dict[str, Any]] = []
        self._progress: Dict[str, Any] = {}
        self._reset_progress()

    def init_plugin(self, config: dict = None):
        """
        初始化插件：注册存储、读取配置、重建客户端与监控线程。
        """
        if not config:
            return

        self._ensure_storage_registered()
        self._load_config(config)

        logger.info(
            "【Strm2Emby】初始化插件: enabled=%s, device_id=%s, has_access_token=%s",
            self._enabled,
            self._device_id,
            bool(self._access_token),
        )

        self._build_client()
        self._load_upload_history()
        self._reset_progress()
        self._cancel_litepan_notify()
        self._restart_watch()

    def _load_config(self, config: dict) -> None:
        """从配置字典读取全部字段到实例属性。"""

        def _as_int(key: str, default: int) -> int:
            """读取整型配置，非法值回退默认。"""
            try:
                return int(config.get(key) or default)
            except (TypeError, ValueError):
                return default

        def _as_float(key: str, default: float) -> float:
            """读取浮点配置，非法值回退默认。"""
            try:
                return float(config.get(key) or default)
            except (TypeError, ValueError):
                return default

        self._enabled = bool(config.get("enabled"))
        self._access_token = (config.get("access_token") or "").strip()
        self._refresh_token = (config.get("refresh_token") or "").strip()
        self._client_id = (
            (config.get("client_id") or GuangYaClient.DEFAULT_CLIENT_ID).strip()
            or GuangYaClient.DEFAULT_CLIENT_ID
        )
        self._device_id = (config.get("device_id") or "").strip()
        self._poll_interval = _as_int("poll_interval", self._DEFAULT_POLL_INTERVAL)
        self._page_size = _as_int("page_size", self._DEFAULT_PAGE_SIZE)
        self._order_by = _as_int("order_by", self._DEFAULT_ORDER_BY)
        self._sort_type = _as_int("sort_type", self._DEFAULT_SORT_TYPE)
        self._min_interval = max(_as_float("min_interval", self._DEFAULT_MIN_INTERVAL), 0.0)
        self._permanently_delete = bool(config.get("permanently_delete"))

        self._sync_enabled = bool(config.get("sync_enabled"))
        self._sync_source_dir = (config.get("sync_source_dir") or "").strip()
        self._sync_remote_dir = (config.get("sync_remote_dir") or "").strip() or "/"
        self._sync_watch = bool(config.get("sync_watch"))
        self._sync_cron = (config.get("sync_cron") or "").strip()
        self._sync_conflict = self._normalize_conflict(config.get("sync_conflict"))
        self._sync_delete_source = bool(config.get("sync_delete_source"))
        self._sync_extensions = (config.get("sync_extensions") or "").strip()

        self._fs_allowed_roots = (config.get("fs_allowed_roots") or "").strip()

        self._litepan_enabled = bool(config.get("litepan_enabled"))
        self._litepan_base_url = (config.get("litepan_base_url") or "").strip().rstrip("/")
        self._litepan_api_key = (config.get("litepan_api_key") or "").strip()
        self._litepan_event = (config.get("litepan_event") or "").strip() or "MP"
        self._litepan_source = (config.get("litepan_source") or "").strip()
        self._litepan_path = (config.get("litepan_path") or "").strip()
        self._litepan_message = (config.get("litepan_message") or "").strip()
        self._litepan_debounce = max(
            _as_int("litepan_debounce", self._DEFAULT_DEBOUNCE), 1
        )

    @staticmethod
    def _normalize_conflict(value: Any) -> str:
        """规整同名文件策略，非法值回退 skip。"""
        conflict = str(value or "").strip() or CONFLICT_SKIP
        return conflict if conflict in CONFLICT_CHOICES else CONFLICT_SKIP

    def _ensure_storage_registered(self) -> None:
        """
        确保本存储已在宿主登记。

        ``StorageHelper.add_storage()`` 是 append 语义而非 upsert，重复调用会累积
        重复条目，因此必须先查重。
        """
        storage_helper = StorageHelper()
        storages = storage_helper.get_storagies()
        if any(s.type == self._disk_name and s.name == self._disk_name for s in storages):
            return
        storage_helper.add_storage(
            storage=self._disk_name,
            name=self._disk_name,
            conf={},
        )

    def _build_client(self) -> None:
        """按当前配置创建传输层与存储层实例。"""

        def on_token_refresh(access_token: str, refresh_token: str):
            """token 刷新后自动持久化，避免重启后失效。"""
            logger.info("【Strm2Emby】收到 Token 刷新回调，准备保存配置")
            self._access_token = access_token
            self._refresh_token = refresh_token
            self.update_config(self._full_config())
            logger.info("【Strm2Emby】Token 已自动保存")

        try:
            self._client = GuangYaClient(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                client_id=self._client_id,
                device_id=self._device_id,
                on_token_refresh=on_token_refresh,
                min_interval=self._min_interval,
            )
            self._device_id = self._client.device_id
            try:
                resume_store_dir = str(self.get_data_path() / "upload_resume")
            except Exception:  # noqa: BLE001
                resume_store_dir = None
            self._guangya_api = GuangYaApi(
                client=self._client,
                disk_name=self._disk_name,
                page_size=self._page_size,
                order_by=self._order_by,
                sort_type=self._sort_type,
                permanently_delete=self._permanently_delete,
                resume_store_dir=resume_store_dir,
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】客户端创建失败: {err}")
            self._client = None
            self._guangya_api = None

    def _load_upload_history(self) -> None:
        """读取持久化的历史记录。"""
        try:
            history = self.get_data("upload_history")
            self._upload_history = history if isinstance(history, list) else []
        except Exception as err:  # noqa: BLE001
            logger.debug(f"【Strm2Emby】读取上传记录失败: {err}")
            self._upload_history = []

    def get_state(self) -> bool:
        """返回插件当前是否启用。"""
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回插件远程命令列表（当前未注册）。"""
        return []

    @staticmethod
    def get_render_mode() -> Tuple[str, str]:
        """返回 Vue 渲染模式与构建产物目录（与官方示例一致声明为静态方法）。"""
        return "vue", "dist/assets"

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """
        在左侧「整理」分组注册全页入口。

        前端会加载 dist 暴露的 AppPage 组件，路由为
        ``#/plugin-app/<PluginID>/<nav_key>``。未启用时不注册入口
        （与官方同代实现一致，避免禁用状态下仍出现菜单项）。
        """
        if not self.get_state():
            return []
        return [
            {
                "nav_key": "main",
                "title": "Strm2Emby",
                "icon": "mdi-duck",
                "section": "organize",
                "permission": "manage",
                "order": 10,
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        Vue 模式下返回空表单与默认配置模型。

        配置页由 Vue 组件自行渲染，这里只提供首次安装时的默认模型；
        字段与 ``_full_config()`` 一一对应，但**不含任何令牌**。
        """
        return [], self._default_config()

    @classmethod
    def _default_config(cls) -> Dict[str, Any]:
        """构造不含令牌的完整默认配置（字段与 `_full_config()` 对齐）。"""
        return {
            "enabled": False,
            "client_id": GuangYaClient.DEFAULT_CLIENT_ID,
            "device_id": "",
            "poll_interval": cls._DEFAULT_POLL_INTERVAL,
            "page_size": cls._DEFAULT_PAGE_SIZE,
            "order_by": cls._DEFAULT_ORDER_BY,
            "sort_type": cls._DEFAULT_SORT_TYPE,
            "min_interval": cls._DEFAULT_MIN_INTERVAL,
            "permanently_delete": False,
            "sync_enabled": False,
            "sync_source_dir": "",
            "sync_remote_dir": "/",
            "sync_watch": False,
            "sync_cron": "",
            "sync_conflict": CONFLICT_SKIP,
            "sync_delete_source": False,
            "sync_extensions": "",
            "fs_allowed_roots": "",
            "litepan_enabled": False,
            "litepan_base_url": "",
            "litepan_api_key_set": False,
            "litepan_event": "MP",
            "litepan_source": "",
            "litepan_path": "",
            "litepan_message": "",
            "litepan_debounce": cls._DEFAULT_DEBOUNCE,
            "logged_in": False,
        }

    def get_page(self) -> List[dict]:
        """Vue 模式下返回空页面。"""
        return []

    def stop_service(self):
        """退出插件：停止目录监控线程与待发送的联动通知。"""
        self._stop_watch()
        self._cancel_litepan_notify()
        self._reset_progress()

    # ── 配置读写 ──

    def _full_config(self) -> Dict[str, Any]:
        """
        汇总当前内存中的全部配置字段。

        MoviePilot V3 的 ``update_config()`` 是整份替换而非按字段合并，
        因此任何一次持久化都必须提交完整字段，否则会把未提交的配置
        （例如目录同步、token）清空。
        """
        return {
            "enabled": self._enabled,
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "device_id": self._device_id,
            "poll_interval": self._poll_interval,
            "page_size": self._page_size,
            "order_by": self._order_by,
            "sort_type": self._sort_type,
            "min_interval": self._min_interval,
            "permanently_delete": self._permanently_delete,
            "sync_enabled": self._sync_enabled,
            "sync_source_dir": self._sync_source_dir,
            "sync_remote_dir": self._sync_remote_dir,
            "sync_watch": self._sync_watch,
            "sync_cron": self._sync_cron,
            "sync_conflict": self._sync_conflict,
            "sync_delete_source": self._sync_delete_source,
            "sync_extensions": self._sync_extensions,
            "fs_allowed_roots": self._fs_allowed_roots,
            "litepan_enabled": self._litepan_enabled,
            "litepan_base_url": self._litepan_base_url,
            "litepan_api_key": self._litepan_api_key,
            "litepan_event": self._litepan_event,
            "litepan_source": self._litepan_source,
            "litepan_path": self._litepan_path,
            "litepan_message": self._litepan_message,
            "litepan_debounce": self._litepan_debounce,
        }

    def _merge_config(self, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        以当前内存配置为基线，叠加本次提交的字段，返回完整配置。

        支持前端只提交部分字段（例如登录成功后仅提交 enabled），未提交的字段
        保持原值，避免误清 token、目录同步等设置。
        """
        payload = payload or {}
        base = self._full_config()

        def _as_bool(key: str) -> bool:
            """布尔字段：提交了就用提交值，否则沿用基线。"""
            return bool(payload[key]) if key in payload else bool(base[key])

        def _as_str(key: str, default: str = "") -> str:
            """字符串字段：提交了就规整后使用，否则沿用基线。"""
            if key in payload:
                return str(payload.get(key) or default).strip()
            return str(base.get(key) or default).strip()

        def _as_int(key: str, default: int) -> int:
            """整型字段：非法值回退默认。"""
            if key in payload:
                try:
                    return int(payload.get(key))
                except (TypeError, ValueError):
                    return default
            try:
                return int(base.get(key, default))
            except (TypeError, ValueError):
                return default

        return {
            "enabled": _as_bool("enabled"),
            # 令牌只由扫码登录流程写入，忽略客户端提交，避免被清空或篡改
            "access_token": str(base.get("access_token") or ""),
            "refresh_token": str(base.get("refresh_token") or ""),
            "client_id": _as_str("client_id", GuangYaClient.DEFAULT_CLIENT_ID)
            or GuangYaClient.DEFAULT_CLIENT_ID,
            "device_id": _as_str("device_id"),
            "poll_interval": _as_int("poll_interval", self._DEFAULT_POLL_INTERVAL),
            "page_size": _as_int("page_size", self._DEFAULT_PAGE_SIZE),
            "order_by": _as_int("order_by", self._DEFAULT_ORDER_BY),
            "sort_type": _as_int("sort_type", self._DEFAULT_SORT_TYPE),
            "min_interval": max(
                float(payload.get("min_interval", base.get("min_interval", 0.0)) or 0.0), 0.0
            ),
            "permanently_delete": _as_bool("permanently_delete"),
            "sync_enabled": _as_bool("sync_enabled"),
            "sync_source_dir": _as_str("sync_source_dir"),
            "sync_remote_dir": _as_str("sync_remote_dir", "/") or "/",
            "sync_watch": _as_bool("sync_watch"),
            "sync_cron": _as_str("sync_cron"),
            "sync_conflict": self._normalize_conflict(
                payload["sync_conflict"] if "sync_conflict" in payload else base.get("sync_conflict")
            ),
            "sync_delete_source": _as_bool("sync_delete_source"),
            "sync_extensions": _as_str("sync_extensions"),
            "fs_allowed_roots": _as_str("fs_allowed_roots"),
            "litepan_enabled": _as_bool("litepan_enabled"),
            "litepan_base_url": _as_str("litepan_base_url").rstrip("/"),
            # API Key 只写不读：提交非空才更新，否则保留原值
            "litepan_api_key": (
                str(payload.get("litepan_api_key")).strip()
                if payload.get("litepan_api_key")
                else str(base.get("litepan_api_key") or "")
            ),
            "litepan_event": _as_str("litepan_event", "MP") or "MP",
            "litepan_source": _as_str("litepan_source"),
            "litepan_path": _as_str("litepan_path"),
            "litepan_message": _as_str("litepan_message"),
            "litepan_debounce": max(_as_int("litepan_debounce", self._DEFAULT_DEBOUNCE), 1),
        }

    def _persist_config(self) -> None:
        """把当前完整配置写回宿主。"""
        self.update_config(self._full_config())

    def _clear_auth_state(self, reason: str = "") -> None:
        """清理认证状态并持久化。"""
        if reason:
            logger.warning(f"【Strm2Emby】清理登录状态: {reason}")
        self._access_token = ""
        self._refresh_token = ""
        self._device_code = ""
        self._user_code = ""
        self._verification_uri = ""
        self._qr_expires_at = 0
        if self._client:
            self._client._access_token = ""
            self._client._refresh_token = ""
        self._persist_config()

    def _config_dict(self) -> Dict[str, Any]:
        """构造配置/登录态/空间统计字典（不含任何令牌）。"""
        config: Dict[str, Any] = {
            "enabled": self._enabled,
            "client_id": self._client_id or GuangYaClient.DEFAULT_CLIENT_ID,
            "device_id": self._device_id,
            "poll_interval": self._poll_interval,
            "page_size": self._page_size,
            "order_by": self._order_by,
            "sort_type": self._sort_type,
            "min_interval": self._min_interval,
            "permanently_delete": self._permanently_delete,
            "sync_enabled": self._sync_enabled,
            "sync_source_dir": self._sync_source_dir,
            "sync_remote_dir": self._sync_remote_dir,
            "sync_watch": self._sync_watch,
            "sync_cron": self._sync_cron,
            "sync_conflict": self._sync_conflict,
            "sync_delete_source": self._sync_delete_source,
            "sync_extensions": self._sync_extensions,
            "fs_allowed_roots": self._fs_allowed_roots,
            "litepan_enabled": self._litepan_enabled,
            "litepan_base_url": self._litepan_base_url,
            "litepan_api_key_set": bool(self._litepan_api_key),
            "litepan_event": self._litepan_event,
            "litepan_source": self._litepan_source,
            "litepan_path": self._litepan_path,
            "litepan_message": self._litepan_message,
            "litepan_debounce": self._litepan_debounce,
            "last_litepan_notify": self._last_litepan_notify,
            "logged_in": False,
            "user_code": self._user_code,
            "verification_uri": self._verification_uri,
            "qr_expires_in": (
                max(int(self._qr_expires_at - time.time()), 0) if self._qr_expires_at else 0
            ),
        }

        if not (self._access_token and self._client):
            config.update(self._empty_account_stats())
            return config

        config.update(self._fetch_account_stats())
        return config

    @staticmethod
    def _empty_account_stats() -> Dict[str, Any]:
        """未登录时的账户统计占位。"""
        return {
            "logged_in": False,
            "user_name": "",
            "user_id": "",
            "vip_level": "",
            "member_expire_time": 0,
            "total_space": 0,
            "used_space": 0,
            "free_space": 0,
            "file_count": 0,
        }

    def _fetch_account_stats(self) -> Dict[str, Any]:
        """
        拉取用户信息与空间统计。

        认证判定分两级：只有「刷新确实尝试过且确实失效」才清空登录态；
        仅仅是接口返回认证异常（可能是网络抖动或单接口故障）时只记警告，
        避免把用户踢下线。
        """
        stats = self._empty_account_stats()
        try:
            user_info = self._client.get_user_info() or {}
            if self._should_clear_auth(user_info):
                self._clear_auth_state(
                    f"access_token/refresh_token 已失效，需要重新扫码登录: {self._client.last_refresh_result}"
                )
                return stats
            if self._is_auth_invalid(user_info):
                logger.warning(
                    f"【Strm2Emby】用户信息接口认证异常，但未确认 refresh_token 失效，暂不清空登录态: {user_info}"
                )
                return stats

            user_data = user_info.get("data") if isinstance(user_info.get("data"), dict) else user_info
            user_name = self._pick_first(
                user_data,
                "name", "user_name", "username", "nickname", "nickName",
                "phone", "mobile", "display_name", "preferred_username",
            )
            user_id = self._pick_first(user_data, "user_id", "userId", "id", "sub", "uid", "openId")
            vip_level = self._pick_first(
                user_data, "vip_level", "vipLevel", "vip", "level", "memberLevel", "vipName", "memberType"
            )
            if user_name is None and user_id is not None:
                user_name = user_id
            if user_name is None and user_id is None:
                logger.warning(f"【Strm2Emby】用户信息无有效身份字段，视为未登录: {user_info}")
                return stats

            stats["user_name"] = "" if user_name is None else str(user_name)
            stats["user_id"] = "" if user_id is None else str(user_id)
            stats["vip_level"] = "" if vip_level is None else str(vip_level)
            stats["logged_in"] = True

            assets_info = self._client.get_assets() or {}
            if self._should_clear_auth(assets_info):
                self._clear_auth_state(
                    f"空间信息接口返回未认证，且 refresh_token 已失效，需要重新扫码登录: "
                    f"{self._client.last_refresh_result}"
                )
                stats["logged_in"] = False
                return stats
            if self._is_auth_invalid(assets_info):
                logger.warning(
                    f"【Strm2Emby】空间信息接口认证异常，但未确认 refresh_token 失效，暂不清空登录态: {assets_info}"
                )
                return stats

            assets_data = assets_info.get("data") if isinstance(assets_info.get("data"), dict) else assets_info
            total_space = self._to_int(self._pick_first(
                assets_data, "totalSpaceSize", "total_space", "totalSpace", "total"
            ))
            used_raw = self._pick_first(assets_data, "usedSpaceSize", "used_space", "usedSpace", "used")
            used_space = self._to_int(used_raw)
            free_raw = self._pick_first(
                assets_data, "freeSpaceSize", "free_space", "freeSpace", "free", "available"
            )
            free_space = self._to_int(free_raw)
            if free_space == 0 and total_space and used_raw not in (None, ""):
                free_space = max(total_space - used_space, 0)

            stats["total_space"] = total_space
            stats["used_space"] = used_space
            stats["free_space"] = free_space
            stats["file_count"] = self._to_int(
                self._pick_first(assets_data, "file_count", "fileCount", "totalFileCount")
            )
            stats["member_expire_time"] = self._to_int(
                self._pick_first(assets_data, "vipExpireTime", "vip_expire_time", "expireTime")
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】获取用户信息失败: {err}")
            return self._empty_account_stats()
        return stats

    @staticmethod
    def _pick_first(data: Dict[str, Any], *keys: str) -> Any:
        """按候选键顺序取第一个非空值。"""
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _to_int(value: Any) -> int:
        """尽力把值转为整数。"""
        if value in (None, ""):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0

    @staticmethod
    def _is_auth_invalid(result: Dict[str, Any]) -> bool:
        """
        判断响应是否表示认证失效。

        直接复用传输层的关键词表，避免插件与客户端各维护一份、判定口径漂移。
        """
        return GuangYaClient._is_auth_invalid_result(result)  # noqa: SLF001

    def _should_clear_auth(self, result: Dict[str, Any]) -> bool:
        """
        判断是否应当清空登录态。

        必须同时满足「响应表明认证失效」与「本次确实尝试刷新且刷新失败」，
        否则网络抖动会导致登录态被误清。
        """
        if not self._should_clear_auth_by_result(result):
            return False
        if not self._client:
            return False
        return bool(self._client.last_refresh_attempted and self._client.last_refresh_invalid)

    def _should_clear_auth_by_result(self, result: Dict[str, Any]) -> bool:
        """响应本身是否表明认证失效（供文件级操作与刷新流程共用）。"""
        return self._is_auth_invalid(result)


    # ── 进度管理 ──

    def _reset_progress(self) -> None:
        """重置实时进度状态。"""
        with self._progress_lock:
            self._progress = {
                "active": False,
                "trigger": "",
                "total": 0,
                "done": 0,
                "uploaded": 0,
                "skipped": 0,
                "failed": 0,
                "current": "",
                "current_percent": 0,
                "percent": 0,
                "message": "",
                "started_at": 0,
                "updated_at": 0,
                "items": [],
            }

    def _begin_progress(self, trigger: str, total: int, message: str = "") -> None:
        """开始一轮上传/同步的进度统计。"""
        with self._progress_lock:
            self._progress = {
                "active": True,
                "trigger": trigger,
                "total": max(int(total or 0), 0),
                "done": 0,
                "uploaded": 0,
                "skipped": 0,
                "failed": 0,
                "current": "",
                "current_percent": 0,
                "percent": 0,
                "message": message or "进行中",
                "started_at": time.time(),
                "updated_at": time.time(),
                "items": [],
            }

    def _start_progress_item(self, name: str, local: str, size: int) -> Optional[Dict[str, Any]]:
        """为当前开始处理的文件新增一行进度（仅保留最近 N 行）。"""
        with self._progress_lock:
            progress = self._progress
            if not progress:
                return None
            item = {
                "name": name,
                "local": local,
                "size": int(size or 0),
                "status": "running",
                "percent": 0,
                "remote": "",
                "error": "",
                "flash": False,
                "phase": "",
            }
            items = progress.setdefault("items", [])
            items.append(item)
            if len(items) > self._progress_items_max:
                del items[: len(items) - self._progress_items_max]
            progress["current"] = name
            progress["current_percent"] = 0
            progress["updated_at"] = time.time()
            return item

    def _update_progress_item(
        self,
        item: Optional[Dict[str, Any]],
        *,
        percent: Optional[int] = None,
        status: Optional[str] = None,
        remote: Optional[str] = None,
        error: Optional[str] = None,
        flash: Optional[bool] = None,
        phase: Optional[str] = None,
    ) -> None:
        """
        更新单个文件的进度行。

        只有 running 状态的字节进度计入整体百分比；phase 用于区分「计算哈希」
        与「传输中」，避免大文件算哈希时进度条看起来卡死。
        """
        if item is None:
            return
        with self._progress_lock:
            if percent is not None:
                item["percent"] = max(0, min(int(percent), 100))
            if status is not None:
                item["status"] = status
            if remote is not None:
                item["remote"] = remote
            if error is not None:
                item["error"] = error
            if flash is not None:
                item["flash"] = bool(flash)
            if phase is not None:
                item["phase"] = phase
            progress = self._progress
            if progress:
                progress["current"] = item.get("name", "")
                progress["current_percent"] = (
                    item.get("percent", 0) if item.get("status") == "running" else 0
                )
        self._recalc_progress()

    def _update_progress(
        self,
        *,
        uploaded: Optional[int] = None,
        skipped: Optional[int] = None,
        failed: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """更新已处理文件计数。"""
        with self._progress_lock:
            progress = self._progress
            if not progress:
                return
            if uploaded is not None:
                progress["uploaded"] = int(uploaded)
            if skipped is not None:
                progress["skipped"] = int(skipped)
            if failed is not None:
                progress["failed"] = int(failed)
            if message is not None:
                progress["message"] = message
        self._recalc_progress()

    def _recalc_progress(self) -> None:
        """依据已处理计数与当前文件字节进度重算整体百分比。"""
        with self._progress_lock:
            progress = self._progress
            if not progress:
                return
            done = (
                int(progress.get("uploaded", 0))
                + int(progress.get("skipped", 0))
                + int(progress.get("failed", 0))
            )
            progress["done"] = done
            total = int(progress.get("total", 0))
            if total > 0:
                overall = done + int(progress.get("current_percent", 0)) / 100.0
                progress["percent"] = int(min(overall / total, 1) * 100)
            else:
                progress["percent"] = 100 if done else 0
            progress["updated_at"] = time.time()

    def _finish_progress(self, stats: Dict[str, int], trigger: str, message: str = "") -> None:
        """结束一轮上传/同步的进度统计。"""
        with self._progress_lock:
            progress = self._progress
            if not progress:
                return
            progress["active"] = False
            progress["trigger"] = trigger or progress.get("trigger", "")
            progress["uploaded"] = int(stats.get("uploaded", 0))
            progress["skipped"] = int(stats.get("skipped", 0))
            progress["failed"] = int(stats.get("failed", 0))
            progress["done"] = sum(int(stats.get(key, 0)) for key in ("uploaded", "skipped", "failed"))
            progress["current"] = ""
            progress["current_percent"] = 0
            progress["percent"] = 100
            progress["message"] = message or "完成"
            progress["updated_at"] = time.time()

    # ── 上传记录 ──

    @staticmethod
    def _build_record(trigger: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """把单文件处理结果转换为一条上传记录。"""
        return {
            "time": int(time.time()),
            "trigger": trigger,
            "action": result.get("status", "failed"),
            "name": result.get("name", ""),
            "local": result.get("local", ""),
            "remote": result.get("remote", ""),
            "size": int(result.get("size", 0) or 0),
            "error": result.get("error", ""),
            "flash": bool(result.get("flash", False)),
        }

    def _record_upload(self, records: List[Dict[str, Any]]) -> None:
        """批量写入上传记录（新的在前，超过上限截断）。"""
        if not records:
            return
        history = list(self._upload_history)
        history[0:0] = records
        if len(history) > self._upload_history_max:
            del history[self._upload_history_max:]
        self._upload_history = history
        try:
            self.save_data("upload_history", self._upload_history)
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】保存上传记录失败: {err}")

    # ── API 注册 ──

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件 API 端点。

        所有普通 JSON 端点统一使用宿主 ``schemas.Response`` 响应 envelope，
        并用 Pydantic 模型声明请求体与业务数据。
        """
        return [
            {
                "path": "/config",
                "endpoint": self.api_get_config,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "获取配置",
                "response_model": schemas.Response[PluginConfigData],
            },
            {
                "path": "/config",
                "endpoint": self.api_save_config,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "保存配置",
                "response_model": schemas.Response[PluginConfigData],
            },
            {
                "path": "/login/qrcode",
                "endpoint": self.get_qrcode,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "获取扫码登录二维码",
                "response_model": schemas.Response[QrCodeData],
            },
            {
                "path": "/login/poll",
                "endpoint": self.poll_login,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "轮询扫码登录状态",
                "response_model": schemas.Response[LoginPollData],
            },
            {
                "path": "/login/logout",
                "endpoint": self.logout,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "退出登录",
                "response_model": schemas.Response[dict],
            },
            {
                "path": "/sync",
                "endpoint": self.api_sync,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "立即执行一次目录同步",
                "response_model": schemas.Response[dict],
            },
            {
                "path": "/fs/list",
                "endpoint": self.list_local_dir,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "浏览 MoviePilot 主机目录（仅超级管理员）",
                "response_model": schemas.Response[FsListData],
            },
            {
                "path": "/upload",
                "endpoint": self.manual_upload,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "手动上传服务器文件/目录到光鸭云盘（仅超级管理员，后台执行）",
                "response_model": schemas.Response[UploadStatsData],
            },
            {
                "path": "/progress",
                "endpoint": self.get_upload_progress,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "查询当前上传/同步进度",
                "response_model": schemas.Response[UploadProgressData],
            },
            {
                "path": "/history",
                "endpoint": self.get_upload_history,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "查询上传/同步记录",
                "response_model": schemas.Response[UploadHistoryData],
            },
            {
                "path": "/history/clear",
                "endpoint": self.clear_upload_history,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "清空上传/同步记录",
                "response_model": schemas.Response[dict],
            },
            {
                "path": "/litepan/status",
                "endpoint": self.get_litepan_status,
                "auth": "bear",
                "methods": ["GET"],
                "summary": "最近一次 LitePan 联动结果",
                "response_model": schemas.Response[LitePanNotifyData],
            },
            {
                "path": "/litepan/test",
                "endpoint": self.test_litepan,
                "auth": "bear",
                "methods": ["POST"],
                "summary": "立即发送一次 LitePan 测试事件",
                "response_model": schemas.Response[LitePanNotifyData],
            },
        ]

    def api_get_config(self) -> schemas.Response[PluginConfigData]:
        """GET /config：返回配置、登录态与空间统计（不含令牌）。"""
        return schemas.Response(
            success=True,
            data=PluginConfigData(**self._config_dict()),
        )

    def api_save_config(self, payload: PluginConfigPayload) -> schemas.Response[PluginConfigData]:
        """
        保存插件配置（仅接受可编辑字段，令牌不参与保存）。
        """
        try:
            new_config = self._merge_config(payload.model_dump(exclude_unset=True))
            self.update_config(new_config)
            self.init_plugin(new_config)
            if self._enabled:
                eventmanager.enable_event_handler(type(self))
            else:
                eventmanager.disable_event_handler(type(self))
            return schemas.Response(
                success=True,
                message="配置保存成功",
                data=PluginConfigData(**self._config_dict()),
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】保存配置失败: {err}")
            return schemas.Response(success=False, message=f"保存配置失败: {err}")

    # ── 存储契约：模块方法 ──

    def get_module(self) -> Dict[str, Any]:
        """
        获取插件模块声明。

        返回的方法名与签名必须匹配 MoviePilot V3 的模块方法契约
        （``app/runtime/extensions/module/contracts.py`` 的 ``required_parameters``）。
        """
        return {
            "list_files": self.list_files,
            "any_files": self.any_files,
            "download_file": self.download_file,
            "upload_file": self.upload_file,
            "delete_file": self.delete_file,
            "rename_file": self.rename_file,
            "get_file_item": self.get_file_item,
            "get_parent_item": self.get_parent_item,
            "snapshot_storage": self.snapshot_storage,
            "storage_usage": self.storage_usage,
            "support_transtype": self.support_transtype,
            "storage_manage": self.storage_manage,
            "create_folder": self.create_folder,
            "get_folder": self.get_folder,
            "exists": self.exists,
            "get_item": self.get_item,
        }

    def storage_manage(self, storage: str, action: str, **params) -> Optional[Dict[str, Any]]:
        """
        存储统一管理入口（MoviePilot V3 storage_manage 模块契约）。

        返回 ``None`` 表示「不是本存储」，让宿主继续分派给其它 provider；
        是本存储时自行处理 save_config / reset_config / usage / support_transtype /
        generate_qrcode / check_login 等动作，避免系统文件整理模块把自定义存储判为
        「不支持的存储类型」。

        注意校验顺序：先验 action 合法性、再验 storage 归属。若顺序颠倒，遇到非法
        action 时会提前返回 dict 而终止分派，可能跳过后继 provider。
        """
        # 先验证动作合法性，非法动作直接拒绝
        try:
            act = StorageAction(action)
        except ValueError:
            return {"success": False, "message": f"不支持的存储管理动作：{action}"}

        # 再验证存储归属，非本存储返回 None 让路
        if storage != self._disk_name:
            return None

        if act == StorageAction.SAVE_CONFIG:
            StorageHelper().set_storage(self._disk_name, params.get("conf") or {})
            return {"success": True}

        if act == StorageAction.RESET_CONFIG:
            StorageHelper().reset_storage(self._disk_name)
            return {"success": True}

        if act == StorageAction.SUPPORT_TRANSTYPE:
            transtype = (
                self._guangya_api.support_transtype() if self._guangya_api else dict(self._TRANSTYPE_FALLBACK)
            )
            return {"success": True, "data": {"transtype": transtype or {}}}

        if act == StorageAction.USAGE:
            usage = self._guangya_api.usage() if self._guangya_api else None
            return {"success": True, "data": usage.model_dump() if usage else {}}

        if act == StorageAction.CHECK_LOGIN:
            if self._access_token:
                return {"success": True, "message": "光鸭云盘已登录"}
            return {"success": False, "message": "光鸭云盘未登录"}

        if act == StorageAction.GENERATE_QRCODE:
            return self.get_qrcode().model_dump()

        if act == StorageAction.GENERATE_AUTH_URL:
            return {"success": False, "message": "光鸭云盘不支持 OAuth2 授权"}

        return {"success": False, "message": f"光鸭云盘不支持 {action}"}

    @eventmanager.register(ChainEventType.StorageOperSelection)
    def storage_oper_selection(self, event: Event):
        """监听存储选择事件，把存储操作对象注入事件数据。"""
        if not self._enabled or not self._guangya_api:
            return
        event_data: StorageOperSelectionEventData = event.event_data
        if event_data.storage == self._disk_name:
            event_data.storage_oper = self._guangya_api  # noqa: SLF001

    def _own_storage(self, storage: Optional[str]) -> bool:
        """判断条目/存储是否属于本插件管理的存储。"""
        return storage == self._disk_name

    def list_files(
        self, fileitem: schemas.FileItem, recursion: bool = False
    ) -> Optional[List[schemas.FileItem]]:
        """
        查询目录下所有目录和文件。

        :return: 非本存储返回 ``None``（让路）；本存储但插件未就绪返回 ``[]``。
        """
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】list_files 失败：插件未初始化或未登录")
            return []

        result: List[schemas.FileItem] = []

        def _walk(_item: FileItem, _recursion: bool = False):
            """按需递归收集文件。"""
            items = self._guangya_api.list(_item)
            if not items:
                return
            if _recursion:
                for sub_item in items:
                    if sub_item.type == "dir":
                        _walk(sub_item, _recursion)
                    else:
                        result.append(sub_item)
            else:
                result.extend(items)

        _walk(fileitem, recursion)
        return result

    def any_files(
        self, fileitem: schemas.FileItem, extensions: list = None
    ) -> Optional[bool]:
        """查询目录下是否存在任意目标文件。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】any_files 失败：插件未初始化或未登录")
            return False

        def _any(_item: FileItem) -> bool:
            """递归判断是否存在匹配扩展名的文件。"""
            items = self._guangya_api.list(_item)
            if not items:
                return False
            if not extensions:
                return True
            for sub_item in items:
                if (
                    sub_item.type == "file"
                    and sub_item.extension
                    and f".{sub_item.extension.lower()}" in extensions
                ):
                    return True
                if sub_item.type == "dir" and _any(sub_item):
                    return True
            return False

        return _any(fileitem)

    def create_folder(
        self, fileitem: schemas.FileItem, name: str
    ) -> Optional[schemas.FileItem]:
        """在指定目录下新建子目录。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】create_folder 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.create_folder(fileitem=fileitem, name=name)

    def download_file(
        self, fileitem: schemas.FileItem, path: Path = None
    ) -> Optional[Path]:
        """下载文件到本地路径。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】download_file 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.download(fileitem, path)

    def upload_file(
        self, fileitem: schemas.FileItem, path: Path, new_name: Optional[str] = None
    ) -> Optional[schemas.FileItem]:
        """上传本地文件到指定目录。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】upload_file 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.upload(fileitem, path, new_name)

    def delete_file(self, fileitem: schemas.FileItem) -> Optional[bool]:
        """删除文件或目录。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】delete_file 失败：插件未初始化或未登录")
            return False
        return self._guangya_api.delete(fileitem)

    def rename_file(self, fileitem: schemas.FileItem, name: str) -> Optional[bool]:
        """重命名文件或目录。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】rename_file 失败：插件未初始化或未登录")
            return False
        return self._guangya_api.rename(fileitem, name)

    def exists(self, fileitem: schemas.FileItem) -> Optional[bool]:
        """判断文件或目录是否存在。"""
        if not self._own_storage(fileitem.storage):
            return None
        return True if self.get_item(fileitem) else False

    def get_item(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """按 FileItem 获取对应条目。"""
        if not self._own_storage(fileitem.storage):
            return None
        return self.get_file_item(storage=fileitem.storage, path=Path(fileitem.path))

    def get_file_item(self, storage: str, path: Path) -> Optional[schemas.FileItem]:
        """按存储与路径获取条目。"""
        if not self._own_storage(storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】get_file_item 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.get_item(path)

    def get_parent_item(self, fileitem: schemas.FileItem) -> Optional[schemas.FileItem]:
        """获取父目录条目。"""
        if not self._own_storage(fileitem.storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】get_parent_item 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.get_parent(fileitem)

    def get_folder(self, storage: str, path: Path) -> Optional[schemas.FileItem]:
        """
        获取目录，不存在时自动创建。

        供 StorageChain.get_folder() 等公共存储入口使用，使其它插件
        （如目录同步）能够定位/创建光鸭云盘上的目标目录。
        """
        if not self._own_storage(storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】get_folder 失败：插件未初始化或未登录")
            return None
        return self._guangya_api.get_folder(path)

    def storage_usage(self, storage: str) -> Optional[schemas.StorageUsage]:
        """
        返回存储空间用量。

        非本存储返回 ``None`` 让路；本存储但未就绪时返回零用量对象而非 ``None``，
        避免分派器把「未登录」误判为「该存储不具备用量能力」。
        """
        if not self._own_storage(storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】storage_usage 失败：插件未初始化或未登录")
            return schemas.StorageUsage(total=0, available=0)
        return self._guangya_api.usage()


    def support_transtype(self, storage: str) -> Optional[dict]:
        """
        声明支持的整理方式（移动/复制）。

        与 ``storage_manage(SUPPORT_TRANSTYPE)`` 共用同一取值来源：优先使用存储层
        声明，存储层未就绪时回退到内置兜底值，避免两处口径漂移。
        """
        if not self._own_storage(storage):
            return None
        if self._guangya_api:
            return dict(self._guangya_api.support_transtype() or self._TRANSTYPE_FALLBACK)
        return dict(self._TRANSTYPE_FALLBACK)

    def snapshot_storage(
        self,
        storage: str,
        path: Path,
        last_snapshot_time: float = None,
        max_depth: int = 5,
        previous_snapshot: Optional[Dict[str, Dict]] = None,
    ) -> Optional[Dict[str, Dict]]:
        """
        快照存储。

        :param storage: 存储类型
        :param path: 路径
        :param last_snapshot_time: 上次快照时间，用于增量跳过未变化目录
        :param max_depth: 最大递归深度
        :param previous_snapshot: 上次完整快照，用于保留未变化目录并清理已删除文件
        """
        if not self._own_storage(storage):
            return None
        if not self._guangya_api:
            logger.error("【Strm2Emby】snapshot_storage 失败：插件未初始化或未登录")
            return {}

        root_path = PurePosixPath(path.as_posix())
        files_info: Dict[str, Dict] = {
            file_path: file_info
            for file_path, file_info in (previous_snapshot or {}).items()
            if PurePosixPath(file_path).is_relative_to(root_path)
        }

        def _remove_deleted_children(
            _fileitem: schemas.FileItem, sub_files: List[schemas.FileItem]
        ) -> None:
            """
            清理已确认遍历目录中不再存在的直接子项。

            未变化的子目录仍保留旧基线，避免增量遍历将其误删。
            """
            directory_path = PurePosixPath(_fileitem.path)
            child_paths = {PurePosixPath(sub_file.path) for sub_file in sub_files}
            for old_file_path in list(files_info):
                try:
                    relative_path = PurePosixPath(old_file_path).relative_to(directory_path)
                except ValueError:
                    continue
                if not relative_path.parts:
                    continue
                direct_child_path = directory_path / relative_path.parts[0]
                if direct_child_path not in child_paths:
                    files_info.pop(old_file_path, None)

        def _snapshot(_fileitem: schemas.FileItem, current_depth: int = 0):
            """深度优先遍历并按需写入快照。"""
            try:
                if _fileitem.type == "dir":
                    if current_depth >= max_depth:
                        return
                    # 根目录每轮至少列举一次以清理已移走的子项；子目录按修改时间增量遍历
                    if (
                        current_depth > 0
                        and self.snapshot_check_folder_modtime
                        and last_snapshot_time
                        and _fileitem.modify_time
                        and _fileitem.modify_time <= last_snapshot_time
                    ):
                        return
                    # 只有目录列举成功后才清理旧基线，查询异常时保留待下轮重试
                    sub_files = self._guangya_api.list(_fileitem)
                    if sub_files is None:
                        return
                    sub_files = list(sub_files)
                    _remove_deleted_children(_fileitem, sub_files)
                    for sub_file in sub_files:
                        _snapshot(sub_file, current_depth + 1)
                else:
                    files_info[_fileitem.path] = {
                        "size": _fileitem.size or 0,
                        "modify_time": getattr(_fileitem, "modify_time", 0),
                        "fileid": getattr(_fileitem, "fileid", None),
                        "type": _fileitem.type,
                    }
            except Exception as err:  # noqa: BLE001
                logger.debug(f"【Strm2Emby】快照遍历 {_fileitem.path} 出错: {err}")

        root_item = self._guangya_api.get_item(path)
        if not root_item:
            return {}
        _snapshot(root_item)
        return files_info

    # ── 扫码登录 ──

    def get_qrcode(self) -> schemas.Response[QrCodeData]:
        """
        获取设备码与扫码二维码。

        每次重新生成 ``device_id`` 并立刻持久化：设备码按 device_id 绑定，
        若仅存在于内存，插件重载（保存配置、更新版本）会导致轮询失效。
        """
        try:
            self._device_id = uuid.uuid4().hex
            self._qr_expires_at = 0
            self._device_code = ""
            # device_id 与设备码同批写入配置，保证轮询阶段重载后仍可继续
            self._persist_config()

            temp_client = GuangYaClient(
                access_token=None,
                refresh_token=None,
                client_id=self._client_id,
                device_id=self._device_id,
                min_interval=self._min_interval,
            )
            result = temp_client.get_device_code()
            if not result:
                return schemas.Response(success=False, message="获取二维码失败")

            self._device_code = result.get("device_code") or ""
            self._poll_interval = int(result.get("interval") or self._poll_interval or 5)
            self._user_code = result.get("user_code") or ""
            self._verification_uri = result.get("verification_uri") or ""
            expires_in = int(result.get("expires_in") or 300)
            self._qr_expires_at = time.time() + expires_in

            return schemas.Response(
                success=True,
                data=QrCodeData(
                    user_code=self._user_code,
                    verification_uri=self._verification_uri,
                    verification_uri_complete=result.get("verification_uri_complete") or "",
                    expires_in=expires_in,
                    device_id=self._device_id,
                ),
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】获取二维码失败: {err}")
            return schemas.Response(success=False, message=f"获取二维码失败: {err}")

    def poll_login(self) -> schemas.Response[LoginPollData]:
        """轮询扫码登录状态，成功后持久化令牌。"""
        if not self._device_code:
            return schemas.Response(success=False, message="请先获取二维码")
        if self._qr_expires_at and time.time() > self._qr_expires_at:
            return schemas.Response(success=False, message="二维码已过期，请重新获取")

        try:
            temp_client = GuangYaClient(
                access_token=None,
                refresh_token=None,
                client_id=self._client_id,
                device_id=self._device_id,
                min_interval=self._min_interval,
            )
            result = temp_client.poll_device_code(self._device_code)
            if not result or result.get("waiting") or not result.get("access_token"):
                return schemas.Response(
                    success=False,
                    message=(result or {}).get("message") or "等待扫码中...",
                    data=LoginPollData(waiting=True),
                )

            self._access_token = result.get("access_token") or ""
            self._refresh_token = result.get("refresh_token") or ""
            # 提交完整配置，保留目录同步等未由登录流程修改的字段
            new_config = self._full_config()
            self.update_config(new_config)
            self.init_plugin(new_config)
            self._device_code = ""
            logger.info("【Strm2Emby】扫码登录成功")
            return schemas.Response(
                success=True,
                message="登录成功",
                data=LoginPollData(waiting=False),
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】轮询登录失败: {err}")
            return schemas.Response(success=False, message=f"轮询失败: {err}")

    def logout(self) -> schemas.Response[dict]:
        """退出登录：清空登录态但保留 device_id 与其它配置。"""
        self._access_token = ""
        self._refresh_token = ""
        self._device_code = ""
        self._user_code = ""
        self._verification_uri = ""
        self._qr_expires_at = 0
        if self._client:
            self._client._access_token = ""
            self._client._refresh_token = ""
        self._client = None
        self._guangya_api = None
        self._persist_config()
        return schemas.Response(success=True, message="已退出登录")

    # ── 目录同步：定时与手动触发 ──

    def get_service(self) -> List[Dict[str, Any]]:
        """注册目录同步定时服务（Cron）。"""
        if not (self._enabled and self._sync_enabled and self._sync_cron):
            return []
        try:
            trigger = CronTrigger.from_crontab(self._sync_cron)
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】目录同步 Cron 表达式无效：{self._sync_cron} - {err}")
            return []
        return [
            {
                # 使用类名作为服务 ID，避免虚拟分身之间服务 ID 冲突
                "id": f"{self.__class__.__name__}.Sync",
                "name": "Strm2Emby 目录同步",
                "trigger": trigger,
                "func": self.sync_directory,
                "kwargs": {},
            }
        ]

    def api_sync(self) -> schemas.Response[dict]:
        """立即执行一次目录同步（手动触发/调试）。"""
        if not self._sync_enabled:
            return schemas.Response(success=False, message="目录同步未启用")
        # 同步可能耗时较长，放到线程里执行，避免阻塞请求
        threading.Thread(
            target=self.sync_directory, name="Strm2EmbyManualSync", daemon=True
        ).start()
        return schemas.Response(success=True, message="同步任务已触发，请查看插件日志")

    # ── 本地目录浏览与手动上传 ──

    def list_local_dir(
        self,
        path: str = "",
        _: Any = Depends(get_current_active_superuser),
    ) -> schemas.Response[FsListData]:
        """
        浏览 MoviePilot 主机上的目录，供「手动上传」选择文件/文件夹。

        仅超级管理员可用；配置了「允许浏览的本地根目录」时，目标必须位于其中。
        仅列出目标目录的直接子项，不递归。
        """
        try:
            target = Path((path or "").strip() or "/").expanduser()
            if not target.is_absolute():
                return schemas.Response(success=False, message="请输入绝对路径")
            if not self._is_path_allowed(target):
                return schemas.Response(
                    success=False, message=f"路径不在允许浏览的根目录内：{target}"
                )
            if not target.exists():
                return schemas.Response(success=False, message=f"路径不存在：{target}")
            if not target.is_dir():
                return schemas.Response(success=False, message=f"不是目录：{target}")

            try:
                entries = sorted(
                    target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())
                )
            except PermissionError:
                return schemas.Response(success=False, message=f"没有权限访问：{target}")

            items: List[FsEntry] = []
            for entry in entries:
                try:
                    is_dir = entry.is_dir()
                    size = entry.stat().st_size if not is_dir else 0
                except OSError:
                    continue
                items.append(
                    FsEntry(
                        name=entry.name,
                        path=entry.as_posix(),
                        type="dir" if is_dir else "file",
                        size=size,
                    )
                )

            parent = target.parent.as_posix()
            return schemas.Response(
                success=True,
                data=FsListData(
                    path=target.as_posix(),
                    parent="" if parent == target.as_posix() else parent,
                    items=items,
                ),
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】浏览本地目录失败: {err}")
            return schemas.Response(success=False, message=f"浏览失败: {err}")

    def manual_upload(
        self,
        payload: UploadPayload,
        _: Any = Depends(get_current_active_superuser),
    ) -> schemas.Response[UploadStatsData]:
        """
        手动把 MoviePilot 主机上的文件/目录上传到光鸭云盘（仅超级管理员）。

        路径校验同步完成并立即返回（无效路径计入 ``missing``），实际上传转交后台线程：
        大批量或大文件上传不再占用 HTTP 请求线程，避免撞上网关超时造成「假失败」；
        进度与逐文件结果通过 ``/progress`` 与 ``/history`` 查询。
        配置了「允许浏览的本地根目录」时，所有源路径必须位于其中；
        复用目录同步的同名文件策略（sync_conflict），但恒不删除本地源文件。
        """
        if not self._guangya_api:
            return schemas.Response(success=False, message="插件未初始化，请先登录光鸭云盘")

        raw_paths = [str(item).strip() for item in (payload.paths or []) if str(item).strip()]
        if not raw_paths:
            return schemas.Response(success=False, message="请先选择要上传的文件或目录")

        remote_dir = (payload.remote_dir or self._sync_remote_dir or "/").strip() or "/"

        valid: List[Path] = []
        missing: List[str] = []
        for raw_path in raw_paths:
            local = Path(raw_path).expanduser()
            if not self._is_path_allowed(local) or not local.exists() or not (
                local.is_file() or local.is_dir()
            ):
                missing.append(raw_path)
                continue
            valid.append(local)

        if not valid:
            message = f"没有可上传的路径：{', '.join(missing)}"
            logger.warning(f"【Strm2Emby】手动上传未启动：{message}")
            return schemas.Response(
                success=False,
                message=message,
                data=UploadStatsData(uploaded=0, skipped=0, failed=0, missing=missing),
            )

        threading.Thread(
            target=self._run_manual_upload,
            args=(valid, remote_dir),
            name="Strm2EmbyManualUpload",
            daemon=True,
        ).start()
        message = f"已提交 {len(valid)} 个路径的后台上传任务，进度请查看「上传记录」"
        if missing:
            message += f"；已忽略无效路径：{', '.join(missing)}"
        logger.info(f"【Strm2Emby】手动上传任务已提交：{len(valid)} 个路径 → {remote_dir}")
        return schemas.Response(
            success=True,
            message=message,
            data=UploadStatsData(uploaded=0, skipped=0, failed=0, missing=missing),
        )

    def _run_manual_upload(self, paths: List[Path], remote_dir: str) -> None:
        """
        后台执行手动上传（由 :meth:`manual_upload` 启动的线程调用）。

        :param paths: 已通过存在性与路径白名单校验的本地文件/目录
        :param remote_dir: 光鸭云盘目标目录
        """
        if not self._guangya_api:
            logger.error("【Strm2Emby】手动上传失败：插件未初始化或未登录")
            return

        remote_root = Path(remote_dir)
        stats = {"uploaded": 0, "skipped": 0, "failed": 0}
        records: List[Dict[str, Any]] = []

        try:
            with self._sync_lock:
                # 清空缓存，避免云端被外部删除后误判为「已存在」而跳过上传
                self._guangya_api.clear_cache()
                if not self._guangya_api.get_folder(remote_root):
                    logger.error(f"【Strm2Emby】手动上传失败：无法创建光鸭目标目录 {remote_dir}")
                    return

                # 展开为文件级任务，先算总数用于进度
                file_jobs: List[Tuple[Path, Path, Path]] = []
                for local in paths:
                    if local.is_dir():
                        target_root = remote_root / local.name
                        if not self._guangya_api.get_folder(target_root):
                            logger.error(f"【Strm2Emby】手动上传：无法创建光鸭目录 {target_root}")
                            stats["failed"] += 1
                            records.append(
                                {
                                    "time": int(time.time()),
                                    "trigger": TRIGGER_MANUAL,
                                    "action": "failed",
                                    "name": local.name,
                                    "local": local.as_posix(),
                                    "remote": target_root.as_posix(),
                                    "size": 0,
                                    "error": "无法创建光鸭目录",
                                    "flash": False,
                                }
                            )
                            continue
                        for item in local.rglob("*"):
                            if item.is_file():
                                file_jobs.append((item, local, target_root))
                    else:
                        file_jobs.append((local, local.parent, remote_root))

                self._begin_progress(TRIGGER_MANUAL, len(file_jobs), "手动上传中")
                for local_file, src, target_root in file_jobs:
                    size = local_file.stat().st_size if local_file.is_file() else 0
                    row = self._start_progress_item(local_file.name, local_file.as_posix(), size)
                    result = self._sync_file(
                        local_file,
                        src,
                        target_root,
                        set(),
                        trigger=TRIGGER_MANUAL,
                        delete_source=False,
                        on_progress=lambda percent, _row=row: self._update_progress_item(
                            _row, percent=percent
                        ),
                        on_phase=lambda phase, _row=row: self._update_progress_item(
                            _row, phase=phase
                        ),
                    )
                    status = result.get("status", "failed")
                    stats[status] = stats.get(status, 0) + 1
                    self._update_progress_item(
                        row,
                        status=status,
                        percent=100 if status == "uploaded" else row.get("percent", 0),
                        remote=result.get("remote", ""),
                        error=result.get("error", ""),
                        flash=result.get("flash", False),
                    )
                    records.append(self._build_record(TRIGGER_MANUAL, result))
                    self._update_progress(
                        uploaded=stats["uploaded"],
                        skipped=stats["skipped"],
                        failed=stats["failed"],
                    )
                self._finish_progress(stats, TRIGGER_MANUAL)
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】手动上传后台任务异常：{err}")
        finally:
            self._record_upload(records)
            if stats["uploaded"] > 0:
                self._schedule_litepan_notify()
            logger.info(
                f"【Strm2Emby】手动上传完成：成功 {stats['uploaded']}，"
                f"跳过 {stats['skipped']}，失败 {stats['failed']}"
            )

    # ── 目录同步：内部实现 ──

    def _unique_remote_name(self, remote_path: Path) -> str:
        """同名文件选择「保留两者」时，生成一个不冲突的新文件名。"""
        stem, suffix = remote_path.stem, remote_path.suffix
        for index in range(1, 1000):
            candidate_name = f"{stem} ({index}){suffix}"
            if not self._guangya_api.get_item(remote_path.parent / candidate_name):
                return candidate_name
        return f"{stem} ({int(time.time())}){suffix}"

    def _sync_ext_set(self) -> set:
        """解析「仅同步扩展名」配置为小写后缀集合。"""
        if not self._sync_extensions:
            return set()
        return {e.strip().lower() for e in self._sync_extensions.split(",") if e.strip()}

    @staticmethod
    def _is_temp_name(name: str) -> bool:
        """
        判断是否为下载器/浏览器产生的临时文件，不应上传。

        覆盖隐藏文件、常见临时后缀，以及 `文件名.~#0`、`文件名~` 之类的中间态命名。
        """
        if not name:
            return True
        if name.startswith("."):
            return True
        if name.lower().endswith(_TEMP_SUFFIXES):
            return True
        if ".~#" in name or name.endswith("~"):
            return True
        return False

    def _allowed_browse_roots(self) -> List[Path]:
        """解析「允许浏览的本地根目录」配置，返回规范化的绝对路径列表。"""
        roots: List[Path] = []
        for raw in (self._fs_allowed_roots or "").split(","):
            item = raw.strip()
            if not item:
                continue
            try:
                roots.append(Path(item).expanduser().resolve())
            except OSError:
                continue
        return roots

    def _is_path_allowed(self, target: Path) -> bool:
        """
        校验目标路径是否位于允许的根目录内。

        未配置允许根目录时不额外限制（`/fs/list`、`/upload` 仍需超级管理员）。
        """
        roots = self._allowed_browse_roots()
        if not roots:
            return True
        try:
            resolved = target.expanduser().resolve()
        except OSError:
            return False
        return any(resolved == root or root in resolved.parents for root in roots)

    def _prepare_remote(self) -> Optional[Path]:
        """同步前准备：清空缓存并确保远端目标根目录存在，返回目标根路径。"""
        if not self._guangya_api:
            logger.error("【Strm2Emby】目录同步失败：插件未初始化或未登录")
            return None
        # 每轮同步前清空缓存：云端可能被外部修改，避免把已删除文件误判为存在而跳过上传
        self._guangya_api.clear_cache()
        remote_root = Path(self._sync_remote_dir or "/")
        if not self._guangya_api.get_folder(remote_root):
            logger.error("【Strm2Emby】目录同步失败：无法获取/创建光鸭目标目录")
            return None
        return remote_root

    def _sync_file(
        self,
        local: Path,
        source: Path,
        remote_root: Path,
        exts: set,
        trigger: str = TRIGGER_SYNC,
        delete_source: Optional[bool] = None,
        on_progress: Optional[Any] = None,
        on_phase: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        同步单个文件，返回 {status, name, local, remote, size, error, flash}。

        :param trigger: 触发来源（manual/sync/watch），用于进度与记录标记。
        :param delete_source: 上传成功后是否删除本地文件；默认沿用插件配置，
            手动上传等场景传 False 以免误删源文件。
        :param on_progress: 可选的字节进度回调，接收 0-100 的整数百分比。
        :param on_phase: 可选的阶段回调，接收 hashing/uploading/confirming，
            避免大文件计算 MD5 期间进度条长时间无反馈。
        """
        if delete_source is None:
            delete_source = self._sync_delete_source
        name = local.name
        size = local.stat().st_size if local.is_file() else 0
        base = {
            "name": name,
            "local": local.as_posix(),
            "remote": "",
            "size": size,
            "error": "",
            "flash": False,
        }

        if self._is_temp_name(name):
            return {**base, "status": "skipped"}
        if exts and local.suffix.lower() not in exts:
            return {**base, "status": "skipped"}
        if not local.is_file():
            return {**base, "status": "skipped"}

        try:
            remote_path = remote_root / local.relative_to(source)
            upload_name = name
            existing = self._guangya_api.get_item(remote_path)
            if existing:
                if self._sync_conflict == CONFLICT_SKIP:
                    return {**base, "status": "skipped", "remote": remote_path.as_posix()}
                if self._sync_conflict == CONFLICT_OVERWRITE:
                    if existing.type != "file":
                        logger.error(f"【Strm2Emby】上传：目标已存在同名目录，跳过：{remote_path}")
                        return {**base, "status": "failed", "remote": remote_path.as_posix()}
                    if existing.size and int(existing.size) == size:
                        return {**base, "status": "skipped", "remote": remote_path.as_posix()}
                    if not self._guangya_api.delete(existing):
                        logger.error(f"【Strm2Emby】上传：删除远端同名文件失败：{remote_path}")
                        return {**base, "status": "failed", "remote": remote_path.as_posix()}
                elif self._sync_conflict == CONFLICT_RENAME:
                    upload_name = self._unique_remote_name(remote_path)
                    remote_path = remote_path.parent / upload_name

            parent = self._guangya_api.get_folder(remote_path.parent)
            if not parent:
                logger.error(f"【Strm2Emby】上传目标目录创建失败：{remote_path.parent}")
                return {**base, "status": "failed", "remote": remote_path.as_posix()}

            meta: Dict[str, Any] = {}
            item = self._guangya_api.upload(
                parent,
                local,
                new_name=upload_name,
                on_progress=on_progress,
                on_phase=on_phase,
                result_meta=meta,
            )
            if not item:
                logger.error(f"【Strm2Emby】上传失败（详见 upload 诊断日志）：{local}")
                return {
                    **base,
                    "status": "failed",
                    "remote": remote_path.as_posix(),
                    "error": "上传失败，详见插件日志的上传诊断",
                }

            flash = bool(meta.get("flash"))
            logger.info(f"【Strm2Emby】已上传{'（秒传）' if flash else ''}：{local} -> {remote_path}")
            if delete_source:
                try:
                    local.unlink()
                except OSError as err:
                    logger.warning(f"【Strm2Emby】删除本地源文件失败：{local} - {err}")
            return {
                **base,
                "status": "uploaded",
                "remote": remote_path.as_posix(),
                "flash": flash,
            }
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】上传处理 {local} 出错：{err}")
            return {**base, "status": "failed", "error": str(err)}

    def sync_directory(self, trigger: str = TRIGGER_SYNC):
        """
        全量同步：把本地源目录同步（上传）到光鸭云盘目标目录。

        独立于 MoviePilot 整理链：按相对路径上传，已存在同名文件时按配置处理。
        """
        if not self._sync_enabled:
            return

        source = Path(self._sync_source_dir) if self._sync_source_dir else None
        if not source or not source.is_dir():
            logger.warning(f"【Strm2Emby】目录同步源目录无效：{self._sync_source_dir}")
            return

        stats = {"uploaded": 0, "skipped": 0, "failed": 0}
        records: List[Dict[str, Any]] = []
        # 全量与增量监控共用同一把锁，避免并发上传同名文件
        with self._sync_lock:
            remote_root = self._prepare_remote()
            if remote_root is None:
                return
            exts = self._sync_ext_set()
            files = [item for item in source.rglob("*") if item.is_file()]
            self._begin_progress(trigger, len(files), "目录同步中")
            for local in files:
                size = local.stat().st_size if local.is_file() else 0
                row = self._start_progress_item(local.name, local.as_posix(), size)
                result = self._sync_file(
                    local,
                    source,
                    remote_root,
                    exts,
                    trigger=trigger,
                    on_progress=lambda percent, _row=row: self._update_progress_item(
                        _row, percent=percent
                    ),
                    on_phase=lambda phase, _row=row: self._update_progress_item(
                        _row, phase=phase
                    ),
                )
                status = result.get("status", "failed")
                stats[status] = stats.get(status, 0) + 1
                self._update_progress_item(
                    row,
                    status=status,
                    percent=100 if status == "uploaded" else row.get("percent", 0),
                    remote=result.get("remote", ""),
                    error=result.get("error", ""),
                    flash=result.get("flash", False),
                )
                records.append(self._build_record(trigger, result))
                self._update_progress(
                    uploaded=stats["uploaded"],
                    skipped=stats["skipped"],
                    failed=stats["failed"],
                )
            self._finish_progress(stats, trigger)
            logger.info(
                f"【Strm2Emby】目录同步完成：上传 {stats['uploaded']}，"
                f"跳过 {stats['skipped']}，失败 {stats['failed']}"
            )
        self._record_upload(records)
        if stats["uploaded"] > 0:
            self._schedule_litepan_notify()

    # ── 目录监控 ──

    def _restart_watch(self) -> None:
        """根据配置重建或停止目录监控线程。"""
        self._stop_watch()
        if not (self._enabled and self._sync_enabled and self._sync_watch):
            return
        source = Path(self._sync_source_dir) if self._sync_source_dir else None
        if not source or not source.is_dir():
            logger.warning(f"【Strm2Emby】目录监控未启动，源目录无效：{self._sync_source_dir}")
            return
        self._watch_stop = threading.Event()
        self._watch_thread = threading.Thread(
            target=self._watch_loop, name="Strm2EmbyWatch", daemon=True
        )
        self._watch_thread.start()
        logger.info(f"【Strm2Emby】目录监控已启动：{source}")

    def _stop_watch(self) -> None:
        """停止目录监控线程。"""
        if self._watch_stop is not None:
            self._watch_stop.set()
        if self._watch_thread is not None and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5)
        self._watch_thread = None
        self._watch_stop = None

    def _watch_loop(self) -> None:
        """目录监控线程：监听本地源目录变化，去抖后增量上传。"""
        try:
            from watchfiles import Change, watch
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】目录监控不可用（缺少 watchfiles）：{err}")
            return

        source = Path(self._sync_source_dir)
        exts = self._sync_ext_set()
        logger.info(f"【Strm2Emby】目录监控线程开始，目录：{source}")
        try:
            for changes in watch(
                str(source),
                stop_event=self._watch_stop,
                recursive=True,
                debounce=10000,
                step=1000,
                raise_interrupt=False,
            ):
                if self._watch_stop is not None and self._watch_stop.is_set():
                    break
                targets = [
                    Path(path)
                    for change, path in changes
                    if change in (Change.added, Change.modified)
                ]
                targets = [p for p in targets if p.is_file()]
                if not targets:
                    continue
                stats = {"uploaded": 0, "skipped": 0, "failed": 0}
                records: List[Dict[str, Any]] = []
                with self._sync_lock:
                    remote_root = self._prepare_remote()
                    if remote_root is None:
                        continue
                    self._begin_progress(TRIGGER_WATCH, len(targets), "目录监控上传中")
                    for local in targets:
                        size = local.stat().st_size if local.is_file() else 0
                        row = self._start_progress_item(local.name, local.as_posix(), size)
                        result = self._sync_file(
                            local,
                            source,
                            remote_root,
                            exts,
                            trigger=TRIGGER_WATCH,
                            on_progress=lambda percent, _row=row: self._update_progress_item(
                                _row, percent=percent
                            ),
                            on_phase=lambda phase, _row=row: self._update_progress_item(
                                _row, phase=phase
                            ),
                        )
                        status = result.get("status", "failed")
                        stats[status] = stats.get(status, 0) + 1
                        self._update_progress_item(
                            row,
                            status=status,
                            percent=100 if status == "uploaded" else row.get("percent", 0),
                            remote=result.get("remote", ""),
                            error=result.get("error", ""),
                            flash=result.get("flash", False),
                        )
                        records.append(self._build_record(TRIGGER_WATCH, result))
                        self._update_progress(
                            uploaded=stats["uploaded"],
                            skipped=stats["skipped"],
                            failed=stats["failed"],
                        )
                    self._finish_progress(stats, TRIGGER_WATCH)
                    logger.info(
                        f"【Strm2Emby】目录监控触发：上传 {stats['uploaded']}，"
                        f"跳过 {stats['skipped']}，失败 {stats['failed']}"
                    )
                self._record_upload(records)
                if stats["uploaded"] > 0:
                    self._schedule_litepan_notify()
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】目录监控异常退出：{err}")
        finally:
            logger.info("【Strm2Emby】目录监控线程结束")

    # ── 记录 / 进度 / LitePan 查询 API ──

    def get_upload_history(self, limit: int = 200) -> schemas.Response[UploadHistoryData]:
        """查询上传/同步记录（新的在前）。"""
        try:
            limit = int(limit) if limit else 200
        except (TypeError, ValueError):
            limit = 200
        limit = max(1, min(limit, self._upload_history_max))
        items = [UploadRecord(**(record or {})) for record in list(self._upload_history)[:limit]]
        return schemas.Response(
            success=True,
            data=UploadHistoryData(items=items, total=len(self._upload_history)),
        )

    def clear_upload_history(self) -> schemas.Response[dict]:
        """清空上传/同步记录。"""
        self._upload_history = []
        try:
            self.save_data("upload_history", [])
        except Exception as err:  # noqa: BLE001
            logger.error(f"【Strm2Emby】清空上传记录失败: {err}")
        return schemas.Response(success=True, message="上传记录已清空")

    def get_upload_progress(self) -> schemas.Response[UploadProgressData]:
        """查询当前上传/同步进度。"""
        with self._progress_lock:
            data = UploadProgressData(**(self._progress or {}))
        return schemas.Response(success=True, data=data)

    def get_litepan_status(self) -> schemas.Response[LitePanNotifyData]:
        """返回最近一次 LitePan 联动结果。"""
        data = LitePanNotifyData(**(self._last_litepan_notify or {}))
        return schemas.Response(success=True, data=data)

    def test_litepan(self) -> schemas.Response[LitePanNotifyData]:
        """立即向 LitePan 发送一次测试事件。"""
        result = self._send_litepan_event(self._litepan_path)
        return schemas.Response(
            success=bool(result.get("ok")),
            message=str(result.get("message") or ""),
            data=LitePanNotifyData(**result),
        )

    # ── LitePan 联动：去抖与发送 ──

    def _cancel_litepan_notify(self) -> None:
        """取消待发送的 LitePan 去抖通知。"""
        with self._litepan_lock:
            if self._litepan_timer is not None:
                self._litepan_timer.cancel()
                self._litepan_timer = None

    def _schedule_litepan_notify(self) -> None:
        """
        安排一次去抖后的 LitePan 事件通知。

        多次上传会在 ``litepan_debounce`` 秒的静默期后合并为一次通知。
        """
        if not (
            self._enabled
            and self._litepan_enabled
            and self._litepan_base_url
            and self._litepan_api_key
        ):
            return
        with self._litepan_lock:
            if self._litepan_timer is not None:
                self._litepan_timer.cancel()
            delay = max(1, int(self._litepan_debounce or self._DEFAULT_DEBOUNCE))
            self._litepan_timer = threading.Timer(delay, self._flush_litepan_notify)
            self._litepan_timer.daemon = True
            self._litepan_timer.start()

    def _flush_litepan_notify(self) -> None:
        """去抖到期：向 LitePan 发送一次联动事件。"""
        with self._litepan_lock:
            self._litepan_timer = None
        self._send_litepan_event(self._litepan_path)

    def _send_litepan_event(self, path: str) -> Dict[str, Any]:
        """
        调用 LitePan 开放 webhook（``/api/open/automation/events``）触发自动联动。

        LitePan 侧规则会顺序执行 STRM 生成、刮削与媒体服务器刷新；本方法失败时
        只记录告警，不影响上传主流程。返回归一化的结果字典。
        """
        event = self._litepan_event or "MP"
        source = self._litepan_source or ""
        message = self._litepan_message or f"{event}，请执行联动"
        payload: Dict[str, Any] = {"event": event, "message": message}
        if source:
            payload["source"] = source
        if path:
            payload["path"] = path
        url = f"{self._litepan_base_url}/api/open/automation/events"
        result: Dict[str, Any] = {
            "time": int(time.time()),
            "event": event,
            "source": source,
            "path": path,
            "ok": False,
            "message": "",
            "matched": 0,
            "triggered": 0,
        }
        if not (self._litepan_enabled and self._litepan_base_url and self._litepan_api_key):
            result["message"] = "LitePan 联动未启用或未配置"
            self._last_litepan_notify = result
            return result
        try:
            response = RequestUtils(
                headers={"Authorization": f"Bearer {self._litepan_api_key}"},
                verify=True,
                timeout=15,
            ).post_res(url, json=payload)
            if response is None:
                raise RuntimeError("网络请求失败")
            result["message"] = f"HTTP {response.status_code}"
            try:
                body = response.json()
            except ValueError:
                body = {}
            if isinstance(body, dict):
                data = body.get("data") if isinstance(body.get("data"), dict) else body
                result["matched"] = int(data.get("matched") or 0)
                triggered = data.get("triggered") or []
                result["triggered"] = (
                    len(triggered) if isinstance(triggered, list) else int(triggered or 0)
                )
                result["ok"] = response.status_code == 200 and body.get("success", True) is not False
                if not result["ok"] and body.get("message"):
                    result["message"] = str(body.get("message"))
            else:
                result["ok"] = response.status_code == 200
            logger.info(
                f"【Strm2Emby】LitePan 联动已通知: event={event} path={path} "
                f"matched={result['matched']} triggered={result['triggered']}"
            )
        except Exception as err:  # noqa: BLE001
            result["message"] = str(err)
            logger.warning(f"【Strm2Emby】LitePan 联动通知失败: {err}")
        self._last_litepan_notify = result
        return result

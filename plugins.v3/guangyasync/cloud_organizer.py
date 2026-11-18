"""光鸭目录整理入口；识别、命名、队列、覆盖策略和历史均由宿主负责。"""

from pathlib import Path, PurePosixPath
from typing import Tuple


def organize_paths(source: str, target: str) -> Tuple[Path, Path]:
    """要求独立的绝对云盘目录，防止把产物再次作为待整理资源扫描。"""
    paths = []
    for label, raw in (("待整理目录", source), ("目标目录", target)):
        value = raw.strip()
        path = PurePosixPath(value)
        if not value.startswith("/") or value.startswith("//") or "\\" in value or "\x00" in value or ".." in path.parts:
            raise ValueError(f"{label}必须是有效的云盘绝对路径")
        paths.append(Path(path.as_posix()))
    source_path, target_path = paths
    if source_path == Path("/"):
        raise ValueError("请选择具体的待整理目录，不能整理整个云盘根目录")
    if source_path == target_path or source_path in target_path.parents or target_path in source_path.parents:
        raise ValueError("待整理目录与目标目录不能相同，也不能互相包含")
    return source_path, target_path


def organize_cloud_directory(api, payload, disk_name: str):
    """只读校验后调用宿主公开手动整理入口；预览不创建云端目录。"""
    source, target = organize_paths(payload.source_dir, payload.target_dir)
    folder = api.get_item_strict(source)
    if not folder or folder.type != "dir":
        raise ValueError(f"待整理目录不存在或不是目录：{source}")
    destination = api.get_item_strict(target)
    if destination and destination.type != "dir":
        raise ValueError(f"目标路径不是目录：{target}")

    # 整理链是宿主保留给插件的公开入口，不实现私有 plan/execute 模块能力。
    from app.chain.transfer import TransferChain
    from app.schemas.types import MediaType

    mtype = {"auto": None, "movie": MediaType.MOVIE, "tv": MediaType.TV}[payload.media_type]
    state, result = TransferChain().manual_transfer(
        fileitem=folder,
        target_storage=disk_name,
        target_path=target,
        transfer_type=payload.transfer_type,
        mtype=mtype,
        preview=payload.preview,
        background=not payload.preview,
        scrape=payload.scrape,
        library_type_folder=payload.library_type_folder,
        library_category_folder=payload.library_category_folder,
        sync_extra_files=True,
    )
    return state, result

"""Strm2Emby 插件 API 的数据模型与请求体模型。

MoviePilot V3 要求 `get_api()` 注册的普通 JSON endpoint 使用
`app.schemas.response.Response` 作为统一响应 envelope，并用 Pydantic 模型声明
请求体与业务数据。

本模块只定义业务数据与请求体，envelope 本体由宿主 `schemas.Response[T]` 提供。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LitePanNotifyData(BaseModel):
    """最近一次向 LitePan 发送联动事件的结果。"""

    time: int = 0
    event: str = ""
    source: str = ""
    path: str = ""
    ok: bool = False
    message: str = ""
    matched: int = 0
    triggered: int = 0


class PluginConfigData(BaseModel):
    """GET /config 返回的配置、登录态与空间统计。

    出于安全考虑不包含 access_token / refresh_token 与 LitePan API Key：
    令牌只保存在宿主配置中，LitePan Key 仅以 ``litepan_api_key_set`` 表示是否已配置。
    """

    enabled: bool = False
    client_id: str = ""
    device_id: str = ""
    poll_interval: int = 5
    page_size: int = 100
    order_by: int = 3
    sort_type: int = 1
    min_interval: float = 0.0
    permanently_delete: bool = False

    sync_enabled: bool = False
    sync_source_dir: str = ""
    sync_remote_dir: str = "/"
    sync_watch: bool = False
    sync_watch_polling: bool = False
    sync_poll_interval: int = 2
    sync_cron: str = ""
    sync_conflict: str = "skip"
    sync_delete_source: bool = False
    sync_extensions: str = ""

    fs_allowed_roots: str = ""

    litepan_enabled: bool = False
    litepan_base_url: str = ""
    litepan_api_key_set: bool = False
    litepan_event: str = "MP"
    litepan_source: str = ""
    litepan_path: str = ""
    litepan_message: str = ""
    litepan_debounce: int = 30
    last_litepan_notify: Optional[LitePanNotifyData] = None

    logged_in: bool = False
    user_code: str = ""
    verification_uri: str = ""
    qr_expires_in: int = 0
    user_name: str = ""
    user_id: str = ""
    vip_level: str = ""
    member_expire_time: int = 0
    total_space: int = 0
    used_space: int = 0
    free_space: int = 0
    file_count: int = 0


class PluginConfigPayload(BaseModel):
    """POST /config 的请求体，只接受客户端可编辑字段。

    未提交的字段由后端保留原值；access_token / refresh_token 不在此模型中，
    只能通过扫码登录流程更新。
    """

    enabled: Optional[bool] = None
    client_id: Optional[str] = None
    poll_interval: Optional[int] = None
    page_size: Optional[int] = None
    order_by: Optional[int] = None
    sort_type: Optional[int] = None
    min_interval: Optional[float] = None
    permanently_delete: Optional[bool] = None

    sync_enabled: Optional[bool] = None
    sync_source_dir: Optional[str] = None
    sync_remote_dir: Optional[str] = None
    sync_watch: Optional[bool] = None
    sync_watch_polling: Optional[bool] = None
    sync_poll_interval: Optional[int] = None
    sync_cron: Optional[str] = None
    sync_conflict: Optional[str] = None
    sync_delete_source: Optional[bool] = None
    sync_extensions: Optional[str] = None

    fs_allowed_roots: Optional[str] = None

    litepan_enabled: Optional[bool] = None
    litepan_base_url: Optional[str] = None
    litepan_api_key: Optional[str] = None
    litepan_event: Optional[str] = None
    litepan_source: Optional[str] = None
    litepan_path: Optional[str] = None
    litepan_message: Optional[str] = None
    litepan_debounce: Optional[int] = None


class QrCodeData(BaseModel):
    """GET /login/qrcode 的二维码数据。"""

    user_code: str = ""
    verification_uri: str = ""
    verification_uri_complete: str = ""
    expires_in: int = 0
    device_id: str = ""


class LoginPollData(BaseModel):
    """GET /login/poll 的轮询结果。"""

    waiting: bool = False


class FsEntry(BaseModel):
    """MoviePilot 主机上的一个文件或目录。"""

    name: str
    path: str
    type: str = "file"
    size: int = 0


class FsListData(BaseModel):
    """GET /fs/list 返回的目录内容。"""

    path: str = "/"
    parent: str = ""
    items: List[FsEntry] = Field(default_factory=list)


class UploadPayload(BaseModel):
    """POST /upload 的请求体。"""

    paths: List[str] = Field(default_factory=list)
    remote_dir: Optional[str] = None


class UploadStatsData(BaseModel):
    """POST /upload 的结果统计。"""

    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    missing: List[str] = Field(default_factory=list)


class UploadRecord(BaseModel):
    """一条上传/同步记录。"""

    time: int = 0
    trigger: str = "manual"
    action: str = "failed"
    name: str = ""
    local: str = ""
    remote: str = ""
    size: int = 0
    error: str = ""
    flash: bool = False


class UploadHistoryData(BaseModel):
    """GET /history 的业务数据。"""

    items: List[UploadRecord] = Field(default_factory=list)
    total: int = 0


class UploadProgressItem(BaseModel):
    """进度列表中的单个文件。"""

    name: str = ""
    local: str = ""
    size: int = 0
    status: str = "running"
    percent: int = 0
    remote: str = ""
    error: str = ""
    flash: bool = False
    phase: str = ""


class UploadProgressData(BaseModel):
    """GET /progress 的业务数据。"""

    active: bool = False
    trigger: str = ""
    total: int = 0
    done: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    current: str = ""
    current_percent: int = 0
    percent: int = 0
    message: str = ""
    started_at: float = 0
    updated_at: float = 0
    items: List[UploadProgressItem] = Field(default_factory=list)

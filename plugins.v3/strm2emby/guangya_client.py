"""
光鸭云盘 HTTP 客户端。

设计要点：
- 统一请求入口，严格区分「HTTP 错误」「业务错误码」与「认证失效」；
- 业务响应用白名单判定成功（不再用「msg 不是 error/fail」的宽松兜底），
  避免把上游的中文错误文案误判为成功；
- 401/403 触发带锁的 token 刷新后重试一次；429 / 业务 354 限流等待后重试一次；
- 支持最小请求间隔限流（``min_interval``），可由插件配置注入，避免全量同步触发上游限流；
- 提供设备码登录、token 刷新、列表/增删改、任务查询、上传票据、OSS 分片上传等原子能力。

对外仅暴露原子接口，业务编排在 GuangyaApi 中完成。
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import oss2

from app.sdk.logging import logger
from app.sdk.network import RequestUtils


class GuangYaAuthError(Exception):
    """认证失效，需要重新登录。"""


class GuangYaApiError(Exception):
    """光鸭接口 / 业务错误。"""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code


class GuangYaClient:
    """
    光鸭云盘 HTTP 客户端。
    """

    ACCOUNT_BASE_URL = "https://account.guangyapan.com"
    API_BASE_URL = "https://api.guangyapan.com"
    DEFAULT_CLIENT_ID = "aMe-8VSlkrbQXpUR"

    # 业务成功码（白名单）
    _SUCCESS_CODES = (0, 200, "0", "200")
    # 业务限流码
    _RATE_LIMIT_CODES = (354,)
    # 上传票据返回码：156 表示云端已完成（秒传）
    FLASH_DONE_CODE = 156
    # HTTP 限流状态码
    _HTTP_RATE_LIMIT = 429
    # 认证失效状态码
    _HTTP_AUTH_ERRORS = (401, 403)
    # 认证失效关键词（用于从响应体中识别）
    _AUTH_INVALID_KEYWORDS = (
        "unauthenticated",
        "无效token",
        "authorize failed",
        "认证失败",
        "invalid_grant",
        "invalid token",
        "invalid_token",
        "token expiry",
    )

    def __init__(
        self,
        access_token: str = None,
        refresh_token: str = None,
        client_id: str = None,
        device_id: str = None,
        on_token_refresh: Callable[[str, str], None] = None,
        min_interval: float = 0.0,
    ):
        """
        初始化客户端。

        :param min_interval: 两次 API/账户请求之间的最小间隔（秒），0 表示不限速。
        """
        self._access_token = (access_token or "").strip()
        self._refresh_token = (refresh_token or "").strip()
        self._client_id = (client_id or self.DEFAULT_CLIENT_ID).strip() or self.DEFAULT_CLIENT_ID
        self._device_id = self._normalize_device_id(device_id) or self._generate_device_id()
        self._on_token_refresh = on_token_refresh
        self._min_interval = max(float(min_interval or 0.0), 0.0)
        self._last_request_at = 0.0
        self._token_lock = threading.RLock()
        self._request_lock = threading.Lock()
        self._last_refresh_attempted = False
        self._last_refresh_invalid = False
        self._last_refresh_result: Dict[str, Any] = {}
        # 统一走宿主 RequestUtils（代理/超时/TLS/重试/关联头），verify=True 保持证书校验
        self._http = RequestUtils(
            headers=self._build_common_headers(), verify=True, timeout=30
        )

    # ── 对外只读属性 ──

    @property
    def device_id(self) -> str:
        """当前设备标识。"""
        return self._device_id

    @property
    def last_refresh_attempted(self) -> bool:
        """上一次是否尝试过刷新令牌。"""
        return self._last_refresh_attempted

    @property
    def last_refresh_invalid(self) -> bool:
        """上一次刷新是否确认令牌已失效（需重新登录）。"""
        return self._last_refresh_invalid

    @property
    def last_refresh_result(self) -> Dict[str, Any]:
        """上一次刷新的原始结果，供排错展示。"""
        return self._last_refresh_result

    # ── 设备标识 ──

    @staticmethod
    def _generate_device_id() -> str:
        """生成随机设备标识。"""
        return uuid.uuid4().hex

    @staticmethod
    def _normalize_device_id(device_id: Optional[str]) -> str:
        """规整设备标识（去除连字符与空白）。"""
        if not device_id:
            return ""
        return str(device_id).replace("-", "").strip()

    # ── 请求头 ──

    def _build_common_headers(self) -> Dict[str, str]:
        """构造公共请求头。"""
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://www.guangyupan.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN",
            "X-Client-Id": self._client_id,
            "X-Client-Version": "0.0.1",
            "X-Device-Id": self._device_id,
            "X-Device-Model": "chrome%2F147.0.0.0",
            "X-Device-Name": "PC-Chrome",
            "X-Device-Sign": f"wdi10.{self._device_id}xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "X-Net-Work-Type": "NONE",
            "X-Os-Version": "Win32",
            "X-Platform-Version": "1",
            "X-Protocol-Version": "301",
            "X-Provider-Name": "NONE",
            "X-Sdk-Version": "9.0.2",
        }

    def _auth_headers(self) -> Dict[str, str]:
        """构造鉴权请求头。"""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "accessToken": self._access_token,
            "Did": self._device_id,
            "Dt": "4",
            "did": self._device_id,
            "dt": "4",
        }

    def _throttle(self) -> None:
        """按 min_interval 控制两次请求的最小间隔。"""
        if self._min_interval <= 0:
            return
        with self._request_lock:
            wait = self._min_interval - (time.time() - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.time()

    # ── 核心请求 ──

    @classmethod
    def _is_auth_invalid_result(cls, result: Dict[str, Any]) -> bool:
        """判断响应体是否表示认证失效。"""
        if not isinstance(result, dict):
            return False
        combined = " ".join(
            [
                str(result.get("error") or ""),
                str(result.get("msg") or ""),
                str(result.get("error_description") or ""),
                str(result),
            ]
        ).lower()
        return any(keyword.lower() in combined for keyword in cls._AUTH_INVALID_KEYWORDS)

    def _execute(
        self,
        method: str,
        url: str,
        *,
        data: Optional[dict] = None,
        auth: bool = True,
    ) -> Any:
        """
        发送一次 HTTP 请求，返回响应对象（不解析业务码、不做重试）。

        走宿主 `RequestUtils`：统一代理、超时、TLS 校验与关联头；网络异常返回 None，
        由调用方按网络失败处理。
        """
        self._throttle()
        headers = dict(self._build_common_headers())
        if auth and self._access_token:
            headers.update(self._auth_headers())
        method_upper = method.upper()
        kwargs: Dict[str, Any] = {"headers": headers, "timeout": 30}
        if method_upper == "GET":
            kwargs["params"] = data
        elif method_upper == "PUT":
            kwargs["data"] = data
        else:
            kwargs["json"] = data
        response = self._http.request(method=method_upper, url=url, **kwargs)
        if response is None:
            raise GuangYaApiError(f"网络请求失败: {url}")
        return response

    def _request_raw(
        self,
        method: str,
        url: str,
        *,
        data: Optional[dict] = None,
        auth: bool = True,
        treat_http_error_as_response: bool = False,
        retry_auth: bool = True,
        retry_rate: bool = True,
    ) -> Dict[str, Any]:
        """
        发送请求并解析 JSON，返回原始 dict（不做业务码校验）。

        处理认证失效（刷新重试）与 HTTP 限流（等待重试）。
        """
        response = self._execute(method, url, data=data, auth=auth)
        status = response.status_code

        if status in self._HTTP_AUTH_ERRORS and auth and retry_auth:
            if self.refresh_access_token():
                return self._request_raw(
                    method, url, data=data, auth=auth,
                    treat_http_error_as_response=treat_http_error_as_response,
                    retry_auth=False, retry_rate=retry_rate,
                )
            raise GuangYaAuthError(f"认证失效: HTTP {status}")

        if status == self._HTTP_RATE_LIMIT and retry_rate:
            time.sleep(2.0)
            return self._request_raw(
                method, url, data=data, auth=auth,
                treat_http_error_as_response=treat_http_error_as_response,
                retry_auth=retry_auth, retry_rate=False,
            )

        if status != 200:
            if treat_http_error_as_response:
                try:
                    return response.json()
                except ValueError:
                    return {"code": status, "msg": response.text[:300]}
            raise GuangYaApiError(f"HTTP {status}: {response.text[:300]}", code=status)

        if not response.text:
            return {}
        try:
            parsed = response.json()
        except ValueError:
            raise GuangYaApiError("响应不是合法 JSON")
        if isinstance(parsed, dict):
            return parsed
        return {"code": 0, "data": parsed}

    @classmethod
    def _is_success_code(cls, envelope: Dict[str, Any]) -> bool:
        """
        白名单式判定业务响应是否成功。

        成功条件（满足其一）：
        - ``code`` 为约定的成功码（0 / 200 / "0" / "200"）；
        - ``code`` 缺失且 ``success`` 显式为 True（部分接口用该字段表达结果）。

        不再使用「msg 不是 error/fail 即成功」的黑名单兜底：上游返回
        ``{"msg": "文件不存在"}`` 这类中文错误文案时会被误判为成功。
        """
        code = envelope.get("code")
        if code in cls._SUCCESS_CODES:
            return True
        if code is None and envelope.get("success") is True:
            return True
        return False

    def _request_envelope(
        self,
        method: str,
        url: str,
        *,
        data: Optional[dict] = None,
        allow_codes: tuple = (),
        retry_rate: bool = True,
    ) -> Dict[str, Any]:
        """
        发送业务 API 请求，校验 `{code,msg,data}`：成功码返回 envelope，否则抛错。
        """
        envelope = self._request_raw(method, url, data=data, auth=True, retry_rate=retry_rate)
        code = envelope.get("code")
        if code in allow_codes:
            return envelope
        if code in self._RATE_LIMIT_CODES and retry_rate:
            time.sleep(1.5)
            return self._request_envelope(method, url, data=data, allow_codes=allow_codes, retry_rate=False)
        if self._is_success_code(envelope):
            return envelope
        message = str(envelope.get("msg") or envelope.get("message") or "业务错误")
        raise GuangYaApiError(f"{message} (code={code!r})", code=code)

    def _api(self, path: str, data: Optional[dict] = None, *, allow_codes: tuple = ()) -> Any:
        """调用业务 API 并返回 data 字段；失败抛错。"""
        envelope = self._request_envelope(
            "POST", f"{self.API_BASE_URL}{path}", data=data or {}, allow_codes=allow_codes
        )
        payload = envelope.get("data")
        if payload is None:
            payload = envelope.get("result")
        return payload

    def _account(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        *,
        auth: bool = True,
        allow_http_error: bool = False,
    ) -> Dict[str, Any]:
        """调用账户 API（account.guangyapan.com），返回原始 JSON（无业务 envelope）。"""
        return self._request_raw(
            method, f"{self.ACCOUNT_BASE_URL}{path}", data=data,
            auth=auth, treat_http_error_as_response=allow_http_error,
        )

    # ── 登录 / 令牌 ──

    def get_device_code(self) -> Optional[Dict[str, Any]]:
        """获取设备码与二维码；失败返回 None。"""
        try:
            result = self._account(
                "POST",
                "/v1/auth/device/code",
                {"scope": "user", "client_id": self._client_id},
                auth=False,
            )
        except (GuangYaApiError, GuangYaAuthError):
            return None
        if result.get("error"):
            return None
        return result

    def poll_device_code(self, device_code: str) -> Optional[Dict[str, Any]]:
        """
        轮询设备码状态。

        :return: 命中返回含 access_token 的结果；等待中返回 {"waiting": True}；失败返回 None。
        """
        try:
            result = self._account(
                "POST",
                "/v1/auth/token",
                {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": self._client_id,
                },
                auth=False,
                allow_http_error=True,
            )
        except (GuangYaApiError, GuangYaAuthError):
            return None
        if result.get("error") == "authorization_pending":
            return {"waiting": True, "message": "等待扫码中..."}
        if result.get("access_token"):
            self._access_token = result.get("access_token") or ""
            self._refresh_token = result.get("refresh_token") or ""
            return result
        return None

    def refresh_access_token(self) -> bool:
        """刷新访问令牌（加锁，避免并发重复刷新）。"""
        with self._token_lock:
            self._last_refresh_attempted = True
            self._last_refresh_invalid = False
            self._last_refresh_result = {}
            if not self._refresh_token:
                self._last_refresh_invalid = True
                self._last_refresh_result = {"error": "missing_refresh_token", "msg": "refresh_token 为空"}
                logger.warning("【光鸭云盘】Token 刷新跳过: refresh_token 缺失")
                return False
            old_access = self._access_token
            old_refresh = self._refresh_token
            logger.info(
                "【光鸭云盘】Token 失效，尝试刷新: device_id=%s, has_refresh_token=%s",
                self._device_id,
                bool(self._refresh_token),
            )
            try:
                result = self._request_raw(
                    "POST",
                    f"{self.ACCOUNT_BASE_URL}/v1/auth/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                        "client_id": self._client_id,
                    },
                    auth=False,
                    retry_auth=False,
                )
            except (GuangYaApiError, GuangYaAuthError) as err:
                result = {"error": "refresh_failed", "msg": str(err)}
            self._last_refresh_result = result if isinstance(result, dict) else {"result": result}
            if result.get("access_token"):
                self._access_token = result.get("access_token") or ""
                self._refresh_token = result.get("refresh_token") or self._refresh_token
                self._last_refresh_invalid = False
                logger.info(
                    "【光鸭云盘】Token 刷新成功: access_token_updated=%s, refresh_token_rotated=%s",
                    old_access != self._access_token,
                    old_refresh != self._refresh_token,
                )
                self._notify_token_refresh()
                return True
            self._last_refresh_invalid = self._is_auth_invalid_result(result)
            logger.warning(
                "【光鸭云盘】Token 刷新失败: auth_invalid=%s, code=%s, msg=%s",
                self._last_refresh_invalid,
                result.get("code"),
                result.get("msg") or result.get("error") or result.get("error_description"),
            )
            return False

    def _notify_token_refresh(self) -> None:
        """触发 token 刷新回调，异常不影响主流程。"""
        if not self._on_token_refresh:
            return
        try:
            self._on_token_refresh(self._access_token, self._refresh_token)
        except Exception as err:  # noqa: BLE001
            logger.error(f"【光鸭云盘】Token 刷新回调失败: {err}")

    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息（保留 envelope，供插件判定登录态）。"""
        try:
            return self._account("GET", "/v1/user/me")
        except (GuangYaApiError, GuangYaAuthError) as err:
            return {"error": "request_failed", "msg": str(err)}

    def get_assets(self) -> Dict[str, Any]:
        """获取空间信息（业务 envelope，保留 data 结构）。"""
        try:
            return self._request_envelope(
                "POST", f"{self.API_BASE_URL}/nd.bizassets.s/v1/get_assets", data={}
            )
        except (GuangYaApiError, GuangYaAuthError) as err:
            return {"error": "request_failed", "msg": str(err)}

    # ── 文件列表 / 详情 ──

    def get_file_list(
        self,
        parent_id: str = "",
        page_size: int = 50,
        order_by: int = 3,
        sort_type: int = 1,
        file_types: Optional[list] = None,
        page: int = 0,
        dir_type: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取指定目录下的文件列表（分页由调用方控制）。"""
        body: Dict[str, Any] = {
            "parentId": parent_id or "",
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "sortType": sort_type,
            "fileTypes": file_types or [],
        }
        if dir_type is not None:
            body["dirType"] = dir_type
        data = self._api("/nd.bizuserres.s/v1/file/get_file_list", body)
        return data if isinstance(data, dict) else {"list": data or [], "total": 0}

    def get_file_detail(self, file_id: str) -> Dict[str, Any]:
        """按文件 ID 获取详情（失败时回退 get_info_by_file_id）。"""
        try:
            data = self._api("/nd.bizuserres.s/v1/file/get_file_detail", {"fileId": file_id})
        except GuangYaApiError:
            data = None
        if isinstance(data, dict):
            info = data.get("fileInfo") or data.get("info") or data
            if isinstance(info, dict) and info:
                return info
        data = self._api("/nd.bizuserres.s/v1/file/get_info_by_file_id", {"fileId": file_id})
        if isinstance(data, dict):
            info = data.get("fileInfo") or data.get("info") or data
            return info if isinstance(info, dict) else {}
        return {}

    # ── 目录 / 文件操作 ──

    def create_dir(self, parent_id: str, dir_name: str, fail_if_exist: bool = True) -> Dict[str, Any]:
        """在指定父目录下创建目录。"""
        data = self._api(
            "/nd.bizuserres.s/v1/file/create_dir",
            {"parentId": parent_id or "", "dirName": dir_name, "failIfNameExist": fail_if_exist},
        )
        return data if isinstance(data, dict) else {}

    def rename(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """重命名文件或目录。"""
        data = self._api("/nd.bizuserres.s/v1/file/rename", {"fileId": file_id, "newName": new_name})
        return data if isinstance(data, dict) else {}

    def delete_file(self, file_ids: List[str]) -> Dict[str, Any]:
        """删除一个或多个文件/目录（任务型，进入回收站）。"""
        data = self._api("/nd.bizuserres.s/v1/file/delete_file", {"fileIds": file_ids})
        return data if isinstance(data, dict) else {}

    def move_file(self, file_ids: List[str], target_parent_id: str) -> Dict[str, Any]:
        """移动文件/目录到目标父目录（任务型）。"""
        data = self._api(
            "/nd.bizuserres.s/v1/file/move_file",
            {"fileIds": file_ids, "parentId": target_parent_id},
        )
        return data if isinstance(data, dict) else {}

    def copy_file(self, file_ids: List[str], target_parent_id: str) -> Dict[str, Any]:
        """复制文件/目录到目标父目录（任务型）。"""
        data = self._api(
            "/nd.bizuserres.s/v1/file/copy_file",
            {"fileIds": file_ids, "parentId": target_parent_id},
        )
        return data if isinstance(data, dict) else {}

    # ── 任务状态 ──

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态（进行中的业务码按允许码放行）。"""
        data = self._api(
            "/nd.bizuserres.s/v1/get_task_status",
            {"taskId": task_id},
            allow_codes=(145, 146, 147, 155, 163),
        )
        return data if isinstance(data, dict) else {}

    def get_file_info_by_task_id(self, task_id: str) -> Dict[str, Any]:
        """按任务 ID 查询文件信息（上传确认用）。"""
        data = self._api(
            "/nd.bizuserres.s/v1/file/get_info_by_task_id",
            {"taskId": task_id},
            allow_codes=(145, 146, 147, 155, 163),
        )
        return data if isinstance(data, dict) else {}

    # ── 下载 ──

    def get_download_url(self, file_id: str) -> Dict[str, Any]:
        """获取文件下载链接。"""
        return self._api("/nd.bizuserres.s/v1/get_res_download_url", {"fileId": file_id})

    def get_vod_download_url(self, file_id: str, gcid: str) -> Dict[str, Any]:
        """按 gcid 获取 VOD 下载链接（直链获取失败时的兜底）。"""
        return self._api(
            "/nd.bizuserres.s/v1/file/get_vod_download_url",
            {"fileId": file_id, "gcid": gcid},
        )

    # ── 上传 ──

    def get_upload_token(
        self,
        file_name: str,
        file_size: int,
        file_md5: str,
        parent_id: str = "",
        capacity: int = 2,
    ) -> Dict[str, Any]:
        """获取上传票据（含 OSS 凭证）；156 表示云端已完成（秒传）。"""
        return self._api(
            "/nd.bizuserres.s/v1/get_res_center_token",
            {
                "capacity": capacity,
                "name": file_name,
                "res": {"fileSize": file_size, "md5": file_md5},
                "parentId": parent_id or "",
            },
            allow_codes=(self.FLASH_DONE_CODE,),
        )

    @staticmethod
    def calc_upload_part_size(file_size: int) -> int:
        """按文件大小选择 OSS 分片大小（对齐光鸭网页端策略）。"""
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024
        if file_size <= 4 * gb:
            return 16 * mb
        if file_size <= 32 * gb:
            return 32 * mb
        if file_size <= 128 * gb:
            return 64 * mb
        return 128 * mb

    def upload_file_multipart(
        self,
        endpoint: str,
        bucket_name: str,
        object_path: str,
        file_path: str,
        oss_access_key_id: str,
        oss_access_key_secret: str,
        security_token: str,
        progress_callback: Callable = None,
        store_root: str = None,
    ) -> str:
        """使用 OSS SDK 分片上传；提供 store_root 时启用断点续传。失败抛 GuangYaApiError。"""
        if not endpoint.startswith("http"):
            endpoint = f"https://{endpoint}"
        auth = oss2.StsAuth(oss_access_key_id, oss_access_key_secret, security_token)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            file_size = 0
        kwargs: Dict[str, Any] = {
            "part_size": self.calc_upload_part_size(file_size),
            "progress_callback": progress_callback,
        }
        if store_root:
            try:
                os.makedirs(store_root, exist_ok=True)
                kwargs["store"] = oss2.ResumableStore(root=store_root)
            except Exception as err:  # noqa: BLE001
                logger.debug(f"【光鸭云盘】断点续传目录不可用，忽略: {err}")
        try:
            result = oss2.resumable_upload(bucket, object_path, file_path, **kwargs)
        except Exception as err:  # noqa: BLE001
            raise GuangYaApiError(f"OSS 分片上传失败: {err}")
        return result.etag if hasattr(result, "etag") else str(result)

    @staticmethod
    def mask_token(token: Optional[str], keep: int = 10) -> str:
        """脱敏显示 token，仅保留首尾若干字符。"""
        if not token:
            return ""
        token = str(token)
        if len(token) <= keep * 2:
            return token
        return f"{token[:keep]}...{token[-keep:]}"

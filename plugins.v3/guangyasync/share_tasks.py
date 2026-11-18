"""持久化的分享转存队列。网络与宿主整理通过回调注入，导入时不启动线程。"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit


DEFAULTS = {
    "telegram_enabled": False, "telegram_user_ids": "",
    "share_source_dir": "/待整理", "share_target_dir": "/Media",
    "share_transfer_type": "move", "share_scrape": False,
    "share_type_folder": True, "share_category_folder": False,
}
ACTIVE = {"queued", "inspecting", "saving", "confirming", "saved", "organizing"}
LABELS = {"queued": "已排队", "inspecting": "读取分享", "saving": "正在转存",
          "confirming": "核对转存", "saved": "转存完成", "organizing": "正在整理",
          "completed": "整理完成", "partial": "部分完成，请检查整理队列",
          "failed": "失败", "needs_review": "结果未确认，请人工核对"}


def parse_share(text):
    """仅解析光鸭域名，不请求用户给定的 URL；一次只接受一个分享。"""
    if not isinstance(text, str) or len(text) > 10000:
        raise ValueError("分享消息为空或过长")
    found = {}
    for raw in re.findall(r"https?://[^\s<>\[\]（）]+", text):
        parsed = urlsplit(raw.rstrip(".,;，。；)"))
        host = (parsed.hostname or "").lower()
        if host != "guangyapan.com" and not host.endswith(".guangyapan.com"):
            continue
        parts = [parsed.path, parsed.fragment.split("?", 1)[0]]
        query = parse_qs(parsed.query)
        if "?" in parsed.fragment:
            query.update(parse_qs(parsed.fragment.split("?", 1)[1]))
        match = next((m for part in parts if (m := re.search(r"/(?:s|share)/([A-Za-z0-9_-]+)", part))), None)
        share_id = match.group(1) if match else next(iter(query.get("shareId", query.get("share_id", []))), "")
        if not share_id or not re.fullmatch(r"[A-Za-z0-9_-]{4,180}", share_id):
            continue
        code = next(iter(query.get("code", query.get("pwd", []))), "")
        if not code:
            external = re.search(r"(?:提取码|密码)\s*[:：]?\s*([A-Za-z0-9]{1,32})", text)
            code = external.group(1) if external else ""
        found[share_id] = unquote(code)
    if len(found) != 1:
        raise ValueError("请每次发送一条有效的光鸭分享链接，并附上提取码")
    return next(iter(found.items()))


def allowed_user(user, configured):
    users = set(filter(None, re.split(r"[\s,，;；]+", str(configured))))
    return bool(re.fullmatch(r"[1-9]\d*", str(user or ""))) and str(user) in users


def share_settings(config):
    settings = {key: config.get(key, value) for key, value in DEFAULTS.items()}
    for key in ("share_source_dir", "share_target_dir"):
        value = str(settings[key] or "").strip()
        path = PurePosixPath(value)
        if not value.startswith("/") or value.startswith("//") or "\\" in value or "\x00" in value or ".." in path.parts:
            raise ValueError("分享源目录和媒体目录必须为有效的云盘绝对路径")
        settings[key] = path.as_posix()
    source, target = (PurePosixPath(settings[key]) for key in ("share_source_dir", "share_target_dir"))
    if source == PurePosixPath("/") or source == target or source in target.parents or target in source.parents:
        raise ValueError("请选择独立的源目录与媒体目录，源目录不能是根目录")
    if settings["share_transfer_type"] not in {"move", "copy"}:
        raise ValueError("分享整理方式只支持移动或复制")
    users = re.split(r"[\s,，;；]+", str(settings["telegram_user_ids"]).strip())
    if any(user and not re.fullmatch(r"[1-9]\d*", user) for user in users):
        raise ValueError("Telegram 白名单须填写数字用户 ID，多个 ID 用逗号分隔")
    if settings["telegram_enabled"] and not any(users):
        raise ValueError("开启 Telegram 接收前，请先填写允许的用户 ID")
    return settings


def safe_name(name):
    if not name or name in {".", ".."} or any(c in name for c in ("/", "\\", "\x00")):
        raise ValueError("分享包含无效文件名")
    return name


def read_manifest(client, token, stopped=lambda: False):
    """递归校验分页和目录环；在写云盘前取得完整的文件清单。"""
    manifest, roots, seen = {}, [], set()

    def walk(parent="", prefix="", depth=0):
        if depth > 40:
            raise ValueError("分享目录层级超过 40 层")
        count, total = 0, 0
        for page in range(1, 1001):
            if stopped():
                raise InterruptedError()
            data = client.share_files(token, parent, page)
            if not isinstance(data, dict) or not isinstance(data.get("list"), list):
                raise ValueError("分享目录响应不完整")
            rows = data["list"]
            total = max(total, int(data.get("total") or 0))
            if not rows:
                if count < total:
                    raise ValueError("分享分页缺失")
                return
            for raw in rows:
                file_id = str(raw.get("fileId") or raw.get("id") or raw.get("fid") or "")
                if not file_id or file_id in seen:
                    raise ValueError("分享目录包含重复条目或分页未前进")
                seen.add(file_id)
                if len(seen) > 10000:
                    raise ValueError("单个分享超过 10000 项，请分批处理")
                name = safe_name(str(raw.get("fileName") or raw.get("name") or ""))
                path = prefix + name
                if path in manifest:
                    raise ValueError("分享包含同名冲突")
                is_dir = str(raw.get("resType", raw.get("type", ""))).lower() in {"2", "dir", "folder"} or raw.get("isDir") is True
                manifest[path] = {"type": "dir" if is_dir else "file", "size": 0 if is_dir else int(raw.get("totalSize") or raw.get("fileSize") or raw.get("size") or 0)}
                if not parent:
                    roots.append(file_id)
                if is_dir:
                    walk(file_id, path + "/", depth + 1)
            count += len(rows)
            if total and count >= total:
                return
            if len(rows) < 100:
                if count < total:
                    raise ValueError("分享分页缺失")
                return
        raise ValueError("分享分页超过上限")

    walk()
    if not roots or not any(item["type"] == "file" for item in manifest.values()):
        raise ValueError("分享中没有文件")
    return roots, manifest


def ensure_folder(api, path):
    """查询失败不当作不存在；只在父目录确认后逐级创建。"""
    current = api.get_item_strict(Path("/"))
    for part in Path(path).parts[1:]:
        matches = [item for item in api.list_strict(current) if item.name == part]
        if len(matches) > 1 or matches and matches[0].type != "dir":
            raise ValueError("转存目录存在同名冲突")
        current = matches[0] if matches else api.create_folder(current, part)
        if not current:
            raise ValueError("无法创建转存目录")
        if not current.fileid:
            current = api.get_item_strict(Path(current.path))
        if not current or not current.fileid:
            raise ValueError("无法确认转存目录 ID")
    return current


def saved_manifest(api, folder, stopped=lambda: False):
    result, seen = {}, set()
    base = str(folder.path).rstrip("/") + "/"

    def walk(item, depth=0):
        if stopped():
            raise InterruptedError()
        if depth > 40 or item.fileid in seen:
            raise ValueError("转存目录结构异常")
        seen.add(item.fileid)
        for child in api.list_strict(item):
            path = str(child.path).rstrip("/")
            if not path.startswith(base):
                raise ValueError("转存目录路径异常")
            result[path[len(base):]] = {"type": child.type, "size": 0 if child.type == "dir" else int(child.size or 0)}
            if len(result) > 10000:
                raise ValueError("转存目录超过上限")
            if child.type == "dir":
                walk(child, depth + 1)
    walk(folder)
    return result


def validate_preview(ok, receipt):
    """自动任务先做只读预览；明显由年份误识别出的标题交给人工确认。"""
    items = receipt.get("items", []) if isinstance(receipt, dict) else []
    if not ok or not items or any(not item.get("success") for item in items):
        raise ValueError("识别预览未全部通过，资源已保留，请在云盘资源整理中预览并手动确认媒体")
    for item in items:
        title = re.sub(r"\s*\(\d{4}\)\s*$", "", str(item.get("title") or "")).strip()
        filename = PurePosixPath(item.get("source") or "").name
        if re.fullmatch(r"(?:19|20)\d{2}", title) and re.match(r"^(?:19|20)\d{2}(?:[ ._-]|$)", filename):
            raise ValueError("文件名仅含年份，识别结果疑似错误，资源已保留；请在原生整理界面手动指定媒体")
    return items


class ShareQueue:
    """单进程线程锁 + 跨重载/进程文件锁；每个阶段先落盘再执行写操作。"""

    def __init__(self, directory, services, notify=lambda job: None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "share_jobs.json"
        self.services, self.notify = services, notify
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.thread = None

    def _transaction(self, fn, write=True):
        with open(self.directory / "share_jobs.lock", "a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            jobs = json.loads(self.path.read_text()) if self.path.exists() else []
            result = fn(jobs)
            if not write:
                return copy.deepcopy(result)
            temp = self.path.with_suffix(".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(jobs, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
            return copy.deepcopy(result)

    def list(self):
        jobs = self._transaction(lambda rows: rows[-100:][::-1], write=False)
        return [{key: value for key, value in job.items() if key in {
            "id", "state", "message", "created_at", "updated_at", "staging_dir", "files", "bytes", "result", "title"
        }} for job in jobs]

    def submit(self, text, settings, recipient=None):
        share_id, code = parse_share(text)
        settings = share_settings(settings)

        def add(jobs):
            prior = next((job for job in reversed(jobs) if job["share_id"] == share_id), None)
            if prior:
                if prior["state"] == "failed":
                    prior.update(code=code, recipient=recipient, state="queued", message=LABELS["queued"], updated_at=time.time())
                    return {"id": prior["id"], "state": "queued", "duplicate": False}
                return {"id": prior["id"], "state": prior["state"], "duplicate": True}
            if sum(job["state"] in ACTIVE for job in jobs) >= 20:
                raise ValueError("队列已有 20 个任务，请等待处理完成")
            job_id = uuid.uuid4().hex[:12]
            now = time.time()
            job = {"id": job_id, "share_id": share_id, "code": code, "settings": settings,
                   "recipient": recipient, "state": "queued", "created_at": now, "updated_at": now,
                   "message": LABELS["queued"], "staging_dir": settings["share_source_dir"] + "/" + job_id}
            jobs.append(job)
            # 满额后拒绝新任务，不丢弃去重记录；管理员可离线归档队列文件。
            if len(jobs) > 1000:
                jobs.pop()
                raise ValueError("任务记录已达 1000 条，请先归档记录")
            return {"id": job_id, "state": "queued", "duplicate": False}
        result = self._transaction(add)
        self.wake.set()
        return result

    def update(self, job, state, message=None, **fields):
        job.update(fields, state=state, message=message or LABELS[state], updated_at=time.time())
        self._transaction(lambda rows: next(row for row in rows if row["id"] == job["id"]).update(job))
        if state in {"saved", "organizing", "completed", "partial", "failed", "needs_review"}:
            try:
                self.notify(copy.deepcopy(job))
            except Exception:
                pass  # 通知失败不能改变云盘任务结果。

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="guangya-share", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def _run(self):
        with open(self.directory / "share_worker.lock", "a+") as worker:
            while not self.stop_event.is_set():
                try:
                    fcntl.flock(worker, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    self.stop_event.wait(1)
            if self.stop_event.is_set():
                return
            # 上次未完成的写操作不自动重放；saved 可安全继续整理。
            for job in self._transaction(lambda rows: rows[:], write=False):
                if job["state"] in {"saving", "confirming", "organizing"}:
                    self.update(job, "needs_review", "运行中断，请检查云盘与原生整理队列后手动处理")
                elif job["state"] == "inspecting":
                    self.update(job, "queued")
            while not self.stop_event.is_set():
                job = self._transaction(lambda rows: next((row for row in rows if row["state"] in {"queued", "saved"}), None), write=False)
                if job:
                    self.process(job)
                else:
                    self.wake.wait(5)
                    self.wake.clear()

    def process(self, job):
        try:
            client, api, organize = self.services()
            if job["state"] != "saved":
                self.update(job, "inspecting")
                access = client.share_access(job["share_id"], job["code"])
                token = access.get("accessToken") or access.get("access_token")
                if not token:
                    raise ValueError("未取得分享访问凭据，请检查链接和提取码")
                roots, manifest = read_manifest(client, token, self.stop_event.is_set)
                files = sum(item["type"] == "file" for item in manifest.values())
                fields = dict(files=files, bytes=sum(item["size"] for item in manifest.values()), title=next(iter(manifest)))
                if self.stop_event.is_set():
                    return
                folder = ensure_folder(api, job["staging_dir"])
                if api.list_strict(folder):
                    raise ValueError("任务转存目录已有内容，请核对后处理")
                # 在第一次写请求之前持久化 saving；任何异常均不重放。
                self.update(job, "saving", **fields)
                for offset in range(0, len(roots), 20):
                    if self.stop_event.is_set():
                        raise InterruptedError()
                    receipt = client.restore_share(token, roots[offset:offset + 20], folder.fileid)
                    self.update(job, "confirming", task_id=str(receipt.get("taskId") or ""))
                    # 全部批次均写入后统一核对完整清单，写请求之间不重试。
                deadline = time.monotonic() + 180
                while True:
                    actual = saved_manifest(api, folder, self.stop_event.is_set)
                    if actual == manifest:
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("转存内容未能完整确认")
                    if self.stop_event.wait(3):
                        raise InterruptedError()
                self.update(job, "saved")
            if self.stop_event.is_set():
                return
            self.update(job, "organizing")
            ok, receipt = organize(job)
            items = receipt.get("items", []) if isinstance(receipt, dict) else []
            counts = {state: sum(item.get("state") == state for item in items) for state in (
                "completed", "failed", "skipped", "retry_wait", "accepted", "manual_review")}
            complete = ok and bool(items) and counts["completed"] == len(items)
            summary = "；".join(f"{label} {counts[state]}" for state, label in (
                ("completed", "完成"), ("skipped", "跳过"), ("failed", "失败"),
                ("retry_wait", "等待重试"), ("accepted", "已接收待确认"), ("manual_review", "待复核")) if counts[state])
            self.update(job, "completed" if complete else "partial",
                        ("整理完成：" if complete else "请检查原生整理队列：") + (summary or "没有已确认的整理结果"), result=counts)
        except InterruptedError:
            if job["state"] in {"saving", "confirming", "organizing"}:
                self.update(job, "needs_review", "运行已停止，请核对云盘与整理队列")
            elif job["state"] == "inspecting":
                self.update(job, "queued")
        except Exception as error:
            # 不把上游响应或 token 写入日志/任务 API。保留阶段与异常类型便于定位。
            uncertain = job["state"] in {"saving", "confirming", "organizing"}
            message = str(error) if isinstance(error, ValueError) else type(error).__name__
            self.update(job, "needs_review" if uncertain else "failed", f"{LABELS['needs_review' if uncertain else 'failed']}：{message}")

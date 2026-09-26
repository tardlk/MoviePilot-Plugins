# AGENTS.md — Strm2Emby 接手文档

面向**接手本仓库的 AI / 开发者**。描述**当前代码的真实结构、行为、坑与流程**，尽量给可验证的事实与命令，不给空话。
敏感信息（token、密码、主机账号）一律不写入本文件，用占位符。

---

## 0. 一分钟速览

- 这是什么：**MoviePilot V3 插件**，把「光鸭云盘」接入为 MoviePilot（下称 MP）的一种**存储**，并提供**目录同步**、**手动上传**、**上传记录/进度**、**LitePan 联动**。
- 插件 ID / 主类 / 存储名 / 配置前缀：`Strm2Emby` / `Strm2Emby` / `Strm2Emby`（`_disk_name`）/ `strm2emby_`。
- 仓库：`git@github.com:tardlk/MoviePilot-Plugins.git`（分支 `main`）。
- 插件目录：`plugins.v3/strm2emby/`（目录名 = 类名小写，MP 硬约定）。
- 前端：Vue3 + Vuetify + Module Federation，产物 `plugins.v3/strm2emby/dist/assets/`（**必须提交**，宿主加载 `remoteEntry.js`）。
- 依赖：`apscheduler` / `oss2` / `watchfiles` **全部由 MP 宿主内置**；插件**不再放 `pyproject.toml`**（见 §7 坑位）。
- 三个核心文件：`__init__.py`（主类）/ `guangya_client.py`（HTTP 传输层）/ `guangya_api.py`（存储语义层）。

---

## 1. 目录结构

```text
MoviePilot-Plugins/
├── README.md                     # 面向用户的项目说明
├── AGENTS.md                     # 本文件（面向 AI/开发者）
├── LICENSE                       # GPL-3.0
├── package.v3.json               # 插件市场索引（V3），版本/历史/release 开关
├── .gitignore
├── .github/workflows/release.yml # 推送 package.v3.json 变更时自动打 Release
├── icons/Strm2Emby.png
└── plugins.v3/strm2emby/
    ├── __init__.py               # 主类 Strm2Emby：生命周期/配置/API/存储契约/同步/上传/进度/事件
    ├── guangya_client.py         # 传输层 GuangYaClient：请求头、错误码、token 刷新、限流、设备码登录、上传票据、OSS 分片
    ├── guangya_api.py            # 存储层 GuangYaApi：分页列举、get_item(_strict)、任务型增删改、上传/秒传、usage/snapshot、缓存
    ├── models.py                 # get_api() 的 Pydantic 请求/响应模型
    ├── index.html / vite.config.js / package.json / package-lock.json
    ├── build-zip.js              # 本地打包可上传安装的 zip
    ├── src/                      # 前端源码
    │   ├── main.js / App.vue
    │   └── components/{Page,Config,AppPage,DirectorySync,ManualUpload,UploadHistory}.vue
    ├── dist/                     # 前端构建产物（提交）
    └── README.md                 # 插件目录专属说明
```

**职责边界**

| 层 | 文件 | 不该做的事 |
|---|---|---|
| 传输层 | `guangya_client.py` | 不做业务编排、不碰 FileItem |
| 存储层 | `guangya_api.py` | 不读写插件配置、不发事件 |
| 主类 | `__init__.py` | 不直接拼 HTTP 请求 |

---

## 2. MoviePilot V3 集成

### 2.1 存储 = 模块方法契约

MP 通过 `get_module()` 暴露的方法调用插件存储能力（契约见 MP 源码 `app/runtime/extensions/module/contracts.py`）。
本插件在 `Strm2Emby.get_module()` 暴露 16 个方法：

```
list_files, any_files, download_file, upload_file, delete_file, rename_file,
get_file_item, get_parent_item, snapshot_storage, storage_usage,
support_transtype, storage_manage, create_folder, get_folder, exists, get_item
```

**分派语义（重要）**：返回 `None` 表示「不是本存储，请继续找下一个 provider」。
因此本插件中：

- `None` 仅用于「条目 `storage` 不属于本插件」→ 让路；
- 属于本存储但无法处理（未登录等）→ 返回该方法的失败语义（列表 `[]` / 布尔 `False` / 对象 `None`）并记日志；
- 否则真实故障会被分派器误判为「该存储不具备此能力」，落到宿主 `FileManagerModule` 报「不支持的存储类型」，掩盖真因。

⚠️ 已知瑕疵：`exists()` 未做归属判断，非本存储会返回 `False` 而非 `None`（见 §8 TODO）。

### 2.2 存储注册（两处必须同时存在）

1. `init_plugin()` 里注册存储类型（append 语义，需先查重，避免重复条目）：

   ```python
   StorageHelper().add_storage(storage="Strm2Emby", name="Strm2Emby", conf={})
   ```

2. 监听链事件，把存储操作对象注入：

   ```python
   @eventmanager.register(ChainEventType.StorageOperSelection)
   def storage_oper_selection(self, event):
       if self._enabled and event.event_data.storage == self._disk_name:
           event.event_data.storage_oper = self._guangya_api
   ```

### 2.3 整理联动事件

```python
from app.schemas.types import EventType
@eventmanager.register(EventType.TransferComplete)
def transfer_complete(self, event): ...
```

事件载荷（真实观测，`transfer.completed`）键：`fileitem`（**下载源**）、`meta`、`mediainfo`、`transferinfo`、`downloader`、`download_hash`、`transfer_history_id`、`idempotency_key`。

- `transferinfo.success` / `overwrite_skipped`
- `transferinfo.target_item`（**整理后目标文件**，我们要上传的）
- `transferinfo.file_list_new`（目标文件清单，字符串路径列表）
- `fileitem` 是下载源，会被「必须在 `sync_source_dir` 下」的过滤自然排除。

### 2.4 出站 HTTP 与导入规范

- 出站走 `app.sdk.network.RequestUtils`；日志走 `app.sdk.logging.logger`；基类 `from app.sdk.plugin import _PluginBase`。
- 尽力只用稳定 SDK `app.sdk.*`；`app.monitor.*` 等为内部模块，**不**建议依赖。
- 前端联邦组件不得污染宿主样式：`vite.config.js` 保留 `vuetify-filter` PostCSS，前端**不导入** `vuetify/styles` / `@mdi` 全量样式；`vue`/`vuetify` 必须 `singleton`。

---

## 3. 插件 API（`auth: bear`，统一 `schemas.Response[T]`）

| 方法 | 路径（前缀 `/api/v1/plugin/Strm2Emby`） | 说明 |
|---|---|---|
| GET / POST | `/config` | 读取 / 保存配置（整份字段写入，见 §4） |
| GET | `/login/qrcode` | 获取扫码二维码（每次重建 `device_id` 并持久化） |
| GET | `/login/poll` | 轮询扫码登录，成功后持久化 token |
| POST | `/login/logout` | 退出登录 |
| GET | `/sync` | 立即触发一次全量目录同步（后台线程） |
| GET | `/fs/list?path=` | 浏览 MP 主机目录（**超级管理员**，受 `fs_allowed_roots` 约束） |
| POST | `/upload` | 手动上传 `{paths, remote_dir}`（**超级管理员**，后台线程，不删源文件） |
| GET | `/progress` | 当前上传/同步进度（含逐文件 items） |
| GET | `/history?limit=` | 上传/同步记录 |
| POST | `/history/clear` | 清空记录 |
| GET | `/litepan/status` | 最近一次 LitePan 联动结果 |
| POST | `/litepan/test` | 立即发一次 LitePan 测试事件 |

请求/响应模型在 `models.py`；`/config` **不返回** `access_token`/`refresh_token`/`litepan_api_key`
（API Key 仅以 `litepan_api_key_set` 表示是否已配置）。

---

## 4. 配置与持久化（关键坑）

- MP 的 `update_config()` 是**整份替换**，不是按字段合并。任何持久化都必须提交完整字段。
- 本插件统一走：
  - `_full_config()`：内存完整配置（含 token/API Key）；
  - `_merge_config(payload)`：以内存为基线叠加提交字段，**忽略客户端提交的 token**（只能扫码流程写入）；
  - `_persist_config()` / `update_config(self._full_config())`。
- `GET /config` 返回 `_config_dict()`（脱敏）。
- 前端 `DirectorySync.vue` 保存时只提交 `sync_*` 字段，靠 `_merge_config` 保留其他字段；`Config.vue` 保存时提交大部分字段。

### 配置字段（前缀 `strm2emby_`）

存储/登录：`enabled`、`access_token`、`refresh_token`、`client_id`、`device_id`、
`poll_interval`、`page_size`、`order_by`、`sort_type`、`min_interval`、`permanently_delete`。

目录同步：`sync_enabled`（**总开关**）、`sync_source_dir`（本地源，同时是整理联动的相对路径基准）、
`sync_remote_dir`、`sync_watch`（实时监控）、`sync_watch_polling`（强制轮询）、
`sync_poll_interval`（轮询间隔秒）、`sync_cron`、`sync_conflict`(`skip/overwrite/rename`)、
`sync_delete_source`、`sync_extensions`、`sync_on_transfer`（整理联动）。

安全：`fs_allowed_roots`（逗号分隔的允许浏览/上传根目录；空=不额外限制，仍需超管）。

LitePan：`litepan_enabled`、`litepan_base_url`、`litepan_api_key`（只写不读）、
`litepan_event`（默认 `MP`）、`litepan_message`、`litepan_source`、`litepan_path`、`litepan_debounce`。

---

## 5. 上传与秒传（`GuangYaApi.upload`）

1. 计算文件 MD5（分块）。
2. 取上传票据 `get_res_center_token`（`capacity=2`）：返回 **code 156 = 云端已完成（秒传）**。
3. 命中 156 → 按 `taskId` 轮询 `get_file_info_by_task_id` 取回条目。
4. 未命中 → OSS 分片上传（按大小 16/32/64/128MB；`store_root` 支持断点续传）。
5. 上传后确认：`_wait_upload_done` 轮询，`145/146/147/155/163` 视为**进行中**；每 5 次用
   `_confirm_uploaded_item(路径+文件名+大小)` 回查兜底。
6. OSS 已拿到 etag 但云端暂未确认 → 按「已上传」处理（最终一致），避免大文件误报失败。
7. 阶段回调 `hashing/uploading/confirming` 透传到前端进度。

`guangya_client` 对 HTTP 429 与业务码 354 做一次限流重试；401/403 触发加锁刷新 token 后重试一次。

### 成功码判定（曾出过事故，见 §7）

`GuangYaClient._is_success_code()`：`code ∈ (0,200,"0","200")` 视为成功；
**`code` 缺失时**再接受 `success=True` 或 `msg ∈ ("success","ok")`。
不再使用「msg 不是 error/fail 即成功」的宽松黑名单。

---

## 6. 目录同步的三种触发

统一入口：`_sync_file(local, source, remote_root, exts, trigger, delete_source, on_progress, on_phase)`
→ 过滤临时文件/扩展名 → 处理同名策略 → `get_folder(parent)` → `upload(...)` → 可选删源。

| 触发 | 常量 | 实现 | 依赖 |
|---|---|---|---|
| 整理联动 | `transfer` | `transfer_complete()` 事件 → 5s 去抖 → `_run_transfer_upload` | `EventType.TransferComplete` |
| 目录监控 | `watch` | `_watch_loop` → `_run_watch` → `_handle_watch_batch` | `watchfiles`（inotify/轮询） |
| 定时 | `sync` | `sync_directory()` 全量扫描 + `get_service()` 注册 Cron | `apscheduler` |
| 手动 | `manual` | `manual_upload()` → `_run_manual_upload`（后台线程） | — |

**整理联动过滤逻辑**（`transfer_complete`）：
`self._enabled and self._sync_enabled and self._sync_on_transfer` → `transferinfo.success` 且非 `overwrite_skipped`
→ 收集 `target_item` / `file_list_new` / 顶层 `fileitem` 并去重 → 仅保留「绝对路径 + 位于 `sync_source_dir` 下」
→ 5s 去抖合并 → `_run_transfer_upload`（复用 `_sync_file`，`delete_source=False`，触发 `sync_on_transfer` 记进度/记录/LitePan）。

⚠️ 注意：**整理联动目前受 `sync_enabled` 总开关约束**。只想「整理后才传」时，要 `sync_enabled=true`、
`sync_watch=false`、`sync_cron=""`、`sync_on_transfer=true`。关掉总开关会把整理联动一起禁掉（已踩坑）。

### 目录监控的健壮性（对齐宿主做法）

`_watch_loop` 先尝试 inotify，`_run_watch` 捕获异常后自动切 `force_polling=True` 轮询并退避重启：

- 轮询模式才传 `ignore_permission_denied=True`；inotify 模式不传，保证权限问题能抛出并触发回退，而不是静默不监控。
- `debounce=10000, step=1000`；轮询间隔取 `sync_poll_interval`（默认 2s）。
- 退避 `_WATCH_BACKOFF = (5,15,30,60,120,300)`。

**为什么需要轮询回退**：某些 NAS（如 UGREEN UGOS）的共享目录带「高级 ACL」（xattr `user.acl.v=1`），
非 root 用户 `inotify_add_watch` 返回 `EACCES`，而 `stat/find` 正常。宿主 MP 的
`app/monitor/watcher.py` 也是同样策略（`force_polling` + `ignore_permission_denied` + 退避）。

**轮询开销**：每 `poll_delay_ms` 递归 stat（只读元数据，不读内容），成本随条目数线性增长；
媒体库较大时建议间隔 30~60s，或改用 Cron。

### 并发与缓存

- 全量/监控/整理联动共用一把 `self._sync_lock`。
- 每轮开始 `GuangYaApi.clear_cache()`（清 `_id_cache`/`_item_cache`/`_dir_cache`），避免云端被外部删除后仍误判「已存在」。
- `GuangYaApi` 目录子项缓存只服务按名查询；对外 `list()` 始终 `refresh=True` 重新拉取。

---

## 7. 排错手册（真实踩过的坑）

| 现象 | 根因 | 处理 |
|---|---|---|
| 进「存储/目录」弹「不支持的存储类型：Strm2Emby」 | 未实现 `storage_manage` 模块方法 | 实现并声明 |
| `snapshot_storage() got an unexpected keyword argument 'previous_snapshot'` | V3 契约新增参数 | 方法签名补齐 |
| `StorageChain.get_folder()` 返回 None | 未声明 `get_folder` | 增加模块方法 |
| 云端文件被外部删后重复同步仍「跳过」 | `_item_cache` 未失效 | 每轮 `clear_cache()` |
| 大文件报「上传失败」但云端其实已有 | 156 秒传或 OSS 成功但确认超时 | 156 用 taskId 取回；OSS etag 后按已上传处理；搜日志 `上传诊断` |
| **根目录列举为空 / 同步报「创建目录 /Media 失败」** | `file/get_file_list` 成功响应是 `{msg:"success",data:{...}}` **不含 `code`**，严格成功码校验误判为失败 | `_is_success_code` 在 code 缺失时接受 `msg=success`（v1.0.4 修复） |
| **目录监控启动即崩 `Permission denied (os error 13)`** | 挂载/NAS 高级 ACL 不支持 inotify | 自动回退 `force_polling=True`；或勾选「强制轮询模式」（v1.0.3） |
| **界面一直「依赖未就绪」`runtime_status=dependency_pending`** | 插件放了 `pyproject.toml`，MP 在**插件加载之后**才安装依赖且不重分类 | 移除 `pyproject.toml`（依赖宿主内置），重载插件（v1.1.1） |
| 整理成功但没上传 | `sync_enabled`（总开关）被关，整理联动被一起禁用 | 保持 `sync_enabled=true`，关 `sync_watch`/`sync_cron` |
| 登录接口 404（`account.guangyapan.com`） | 光鸭上游接口变更 | 更新 `guangya_client.py` |
| 目录监控不触发 | 源目录无效 / 未启用 / 未登录 | 看 `strm2emby.log` 的「目录监控已启动/线程结束」 |

### 存储名变更注意

`_disk_name` 是 `FileItem.storage` 与归属判断的取值。把它从「光鸭云盘」改成「Strm2Emby」后，
**历史 FileItem / 已记录条目会失配**。新装无碍；若从旧版升级需注意。

---

## 8. 已知限制 / TODO

- `exists()` 未做归属让路（非本存储返回 `False` 而非 `None`），与文件头约定不一致，建议修。
- 整理联动受 `sync_enabled` 约束，误关总开关会失效；可考虑让整理联动独立、或在「联动开但总开关关」时告警。
- `GET /config` 每次都实时请求光鸭 API 拉账户统计（状态页/前端刷新会触发）。
- 未实现 `media_files`、`transfer`、`plan_transfer`/`execute_transfer_plan` 等整理计划内部接口。
- 进度 `self._progress` 存内存，重载即清空；上传**记录**持久化（`save_data("upload_history")`，上限 500 条）。
- 不同步空目录；不跟随软链接；不做媒体重命名（只按路径原样/整理后上传）。
- 大文件上传后光鸭列表索引有分钟级延迟，OSS 成功只做短等待即按「已上传」记录，最终一致。
- `watchfiles` 的 `ignore_permission_denied` 需 `>=0.22`；宿主通常自带较新版本，但依赖已从插件移除
  （不再由 MP 安装），若宿主过旧该参数会 `TypeError`。
- `/fs/list` 浏览的是 **MP 容器内可见路径**，不是 NAS 全盘。

---

## 9. 安全

- 不提交任何密钥；文档/脚本用占位符。
- token 只由扫码登录流程写入；`_merge_config()` 忽略客户端提交的 token；任何 API 不返回明文 token/API Key。
- `/fs/list`、`/upload` 依赖 `get_current_active_superuser`，仅超级管理员；
  `fs_allowed_roots` 非空时路径必须落在允许根目录内（`_is_path_allowed`）。
- 新增日志/错误处理避免输出完整 token（`GuangYaClient.mask_token`）。

---

## 10. 开发 / 构建 / 发布

### 前端

```bash
cd plugins.v3/strm2emby
npm install
npm run build:web      # 生成 dist/
npm run build          # build:web + build:zip（额外生成可上传的 zip）
```

需 Node 20。**改 `src/` 后必须重新构建并提交 `dist/`**（宿主加载 `dist/assets/remoteEntry.js`）。

### 版本一致性（发布前核对三处）

- `__init__.py` 的 `plugin_version`
- `package.v3.json` 的 `version`
- `package.v3.json` 的 `history` 最新键

三者必须一致（语义版本）。历史记录置顶、降序。

### 发布流程（自动）

`.github/workflows/release.yml`：推送 `package.v3.json` 变更触发 → 只打包 `"release": true` 的条目 →
按目录 `plugins.v3/<id_lower>` 打包 → Tag `插件ID_v版本`，资产 `插件目录小写_v版本.zip`；
目录自上一个同 Tag 以来无变化则跳过；同版本重跑会删旧 Release 重建。

本地手动打包：`npm run build:zip` → `strm2emby.zip`。

### 校验建议

```bash
python3 -m py_compile plugins.v3/strm2emby/__init__.py plugins.v3/strm2emby/*.py
node --check <打包脚本转 .mjs>
```

---

## 11. 运行环境与部署（示例：NAS + Docker）

> 具体主机名/账号/密码不写入文档；以下为结构示意。

- MP 以 Docker 容器运行（镜像 `jxxghp/moviepilot-v3`），容器名假设 `moviepilot`。
- 插件安装目录（容器内）：`/app/app/plugins/strm2emby`
- 备份目录：`/config/plugins_backup/strm2emby`（容器重建后据此恢复）
- 插件日志：`/config/logs/plugins/strm2emby.log`
- 主日志：`/config/logs/moviepilot.log`
- 插件配置持久化：`/config/user.db` 的 `plugininstance.config_data`（JSON）
- 常用操作：

  ```bash
  # 部署新版本（把本地插件目录内容拷进容器）
  docker cp <本地>/strm2emby/. moviepilot:/app/app/plugins/strm2emby/
  # 同步备份，避免容器重建后回退
  docker exec moviepilot sh -c 'rm -rf /config/plugins_backup/strm2emby && cp -r /app/app/plugins/strm2emby /config/plugins_backup/strm2emby'
  # 热重载插件
  curl -X POST -H "Authorization: Bearer <token>" http://<MP>:4000/api/v1/plugin/reload/Strm2Emby
  ```

- **热重载边界**：MP 的 reload 会清理插件子模块缓存（日志 `loader.py - 插件 ... 共清除 N 个模块缓存`），
  通常足够；**但若改动涉及依赖/模块级行为仍以重启容器最稳**。重启会使登录 token 失效，需要重新登录。
- 插件是否标记本地：`GET /api/v1/plugin/` 里 `is_local=true`、`runtime_status` 应为 `active`。

### 关键接口备忘（用于排障）

```bash
# 登录拿 token
curl -X POST http://<MP>:4000/api/v1/login/access-token \
  -d 'username=<user>&password=<pass>' -H 'Content-Type: application/x-www-form-urlencoded'

# 插件列表/状态、配置、进度、记录
curl -H "Authorization: Bearer $TOKEN" http://<MP>:4000/api/v1/plugin/
curl -H "Authorization: Bearer $TOKEN" http://<MP>:4000/api/v1/plugin/Strm2Emby/config
curl -H "Authorization: Bearer $TOKEN" http://<MP>:4000/api/v1/plugin/Strm2Emby/progress
curl -H "Authorization: Bearer $TOKEN" http://<MP>:4000/api/v1/plugin/Strm2Emby/history?limit=20

# 浏览该存储（走插件 list_files）
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"storage":"Strm2Emby","path":"/","type":"dir","name":""}' \
  'http://<MP>:4000/api/v1/storage/list?page=1&count=100'
```

---

## 12. 参考（MP 源码，容器内 `/app/app/`）

- 模块方法契约：`runtime/extensions/module/contracts.py`
- 存储兜底：`modules/filemanager/module.py`、`modules/filemanager/storages/`
- 存储注册/链：`application/storage.py`（`StorageHelper`）、`chain/storage.py`
- 插件事件类型：`schemas/types.py`（`EventType`、`ChainEventType`、`SystemConfigKey`）
- 事件数据契约：`schemas/event.py`、`schemas/transfer.py`（`TransferInfo`）
- 整理结果事件派发：`chain/transfer/settlement.py`
- 目录监控（宿主实现，可借鉴）：`monitor/monitor.py`、`monitor/watcher.py`、`monitor/poller.py`、`monitor/syslimits.py`
- 插件依赖与状态：`adapters/system/plugin/{manifest,package,dependency}.py`、`runtime/extensions/plugin/{lifecycle,registry}.py`
- 前端联邦加载：`MoviePilot-Frontend/src/utils/federationLoader.ts`

官方文档（`jxxghp/MoviePilot-Plugins` 仓库）：`docs/Plugin_Development.md`、`docs/Repository_Guide.md`、
`docs/V3_Plugin_Adaptation.md`、`docs/V3_API_Response_Adaptation.md`。

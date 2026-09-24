<div align="center">

# Strm2Emby · MoviePilot 插件

**把「光鸭云盘」接入 MoviePilot 存储，并内置目录同步、手动上传、上传记录与 LitePan 联动。**

[![version](https://img.shields.io/badge/version-1.0.3-blue?style=flat-square)](https://github.com/tardlk/MoviePilot-Plugins/releases)
[![MoviePilot](https://img.shields.io/badge/MoviePilot-V3-6C63FF?style=flat-square)](https://github.com/jxxghp/MoviePilot)
[![license](https://img.shields.io/badge/license-GPL--3.0-success?style=flat-square)](LICENSE)
[![author](https://img.shields.io/badge/author-tardlk-0ea5e9?style=flat-square)](https://github.com/tardlk)

</div>

---

## 简介

`Strm2Emby` 让 MoviePilot（下称 MP）把 **光鸭云盘** 当作一种存储来使用，可用于媒体整理 / 刮削的**源**或**目标**；同时提供独立的**目录同步**、**手动上传**能力，以及**上传记录 / 逐文件进度**，并可在上传完成后**联动 LitePan** 自动生成 STRM 并刷新 Emby / Jellyfin。

| 项目 | 说明 |
| :-- | :-- |
| 插件 ID | `Strm2Emby` |
| 显示名称 | Strm2Emby |
| 版本 | v1.0.3 |
| 标签 | 存储、工具 |
| 作者 | [tardlk](https://github.com/tardlk) |
| 兼容 | MoviePilot **V3**（`system_version: ">=3.0.0"`，不兼容 V2） |
| 目录 | [`plugins.v3/strm2emby`](plugins.v3/strm2emby) |
| 许可 | [GPL-3.0](LICENSE) |

---

## 功能特性

- **存储接入** — 在 MoviePilot 的「存储」中使用 `Strm2Emby`，支持列表、上传、下载、删除、重命名、移动、复制、空间用量与快照。
- **扫码登录** — 光鸭云盘 App 扫码授权，令牌自动持久化与刷新；任何 API 都不返回明文令牌。
- **目录同步** — 本地目录 → 光鸭目录，支持 **Cron 定时** 与 **实时目录监控（watchfiles）** 两种触发，保留相对目录结构。
- **手动上传** — 在「整理」全页浏览 MoviePilot 主机目录，选择文件或整个文件夹上传，仅超级管理员可用。
- **上传记录与逐文件进度** — 每个文件的结果（成功 / 跳过 / 失败、大小、远端路径、错误）与实时进度，命中秒传额外标注。
- **秒传与断点续传** — MD5 秒传；未命中时走 OSS 分片上传并支持断点续传。
- **LitePan 联动** — 上传成功后通知 LitePan，由其自动生成 STRM 并刷新 Emby / Jellyfin。

---

## 快速开始

### 安装

**方式一：插件市场（推荐）**

1. MoviePilot → **设置 → 插件市场** → 添加仓库地址：
   ```
   https://github.com/tardlk/MoviePilot-Plugins
   ```
2. 搜索 **「Strm2Emby」**（作者 `tardlk`）并安装。
3. 启用插件，打开 **左侧「整理」分组 → Strm2Emby**（或插件页）扫码登录光鸭云盘。

**方式二：Release 压缩包**

前往 [Releases](https://github.com/tardlk/MoviePilot-Plugins/releases) 下载最新的
`strm2emby_vX.Y.Z.zip`，在 MoviePilot 插件管理页上传安装。

### 使用

- 插件启用后，左侧导航 **「整理」** 分组会出现 **「Strm2Emby」** 全页入口，其中包含：
  **目录同步**、**手动上传**、**上传记录**。
- 插件自身的状态页只保留扫码登录 / 状态信息；**配置**在插件配置页（含 LitePan 联动）。

---

## 功能详解

### 目录同步

把 **本地目录** 同步到 **光鸭目录**。在左侧「整理 → Strm2Emby」全页的「目录同步」卡片中设置：

| 字段 | 说明 |
| :-- | :-- |
| 启用目录同步 | 总开关 |
| 目录监控（实时） | 基于 `watchfiles` 实时监听本地目录变化并上传；开启后可不填 Cron。inotify 不可用（网络盘 / 带高级 ACL 的目录）时会**自动回退轮询** |
| 本地源目录 | 要上传的本地目录，如 `/vol2/1000/Vol2/Media` |
| 光鸭目标目录 | 上传到光鸭的目录，如 `/Media`（不存在会自动创建） |
| 同步周期（Cron） | 定时兜底，如 `0 3 * * *` 表示每天 3 点；与目录监控可同时使用 |
| 仅同步扩展名 | 可选，逗号分隔，如 `.mkv,.mp4,.srt`；留空表示全部 |
| 同名文件处理 | `跳过`（默认，保留云端）/ `覆盖`（先删云端同名再上传）/ `保留两者`（自动重命名为 `名称 (1).后缀`） |
| 上传成功后删除本地 | 默认关闭 |

也可手动触发一次：`GET /api/v1/plugin/Strm2Emby/sync`。

### 手动上传

在左侧「整理 → Strm2Emby」全页的「手动上传」卡片中：

1. 在「服务器目录」输入 MoviePilot 主机上的绝对路径并浏览，点击文件加入选择、点击目录进入；
2. 目录右侧的「+」可把整个文件夹加入选择（逐个文件、保留相对结构上传）；
3. 填写「光鸭目标目录」（默认为目录同步的目标目录，不存在会自动创建）；
4. 点「开始上传」，结果会显示成功 / 跳过 / 失败数量。

手动上传复用「目录同步」的同名文件策略，且**不会删除本地源文件**。

> [!WARNING]
> 安全：浏览服务器目录（`/fs/list`）与手动上传（`/upload`）仅限 **MoviePilot 超级管理员**；
> 在「配置 → 查询参数」中可设置「允许浏览的根目录」（逗号分隔），设置后上述操作只能在这些目录内进行。

### 上传记录与进度

全页底部「上传记录」卡片记录**手动上传、目录同步、目录监控**的每个文件结果（时间、来源、成功 / 跳过 / 失败、大小、远端路径、错误），最多保留 **500** 条并可清空；上传 / 同步进行中显示整体百分比、成功 / 跳过 / 失败统计，以及**逐文件列表**——每个文件一行，带各自进度或状态；命中**秒传**（云端已有相同内容、按 MD5 命中、实际上传字节为 0）会额外标注「秒传」。

### LitePan 联动

上传成功后，通知 LitePan 生成 STRM 并刷新 Emby / Jellyfin。在「配置 → LitePan 联动」中开启并填写：

| 字段 | 说明 |
| :-- | :-- |
| LitePan 地址 | LitePan 服务根地址，如 `http://192.168.5.10:5211` |
| Task API Key | 在 LitePan「API Keys」新建的 **task** 类型 Key（只写不读，保存后不回显） |
| 事件名 | 默认 `MP`，需与 LitePan 外部事件触发器的「事件名」一致 |
| 事件消息 | 默认「事件名，请执行联动」；仅作提示，LitePan 不参与匹配 |
| 来源 | 默认空（不发送）；仅当 LitePan 规则配置了 `source` 时才需填写 |
| 事件路径 | 默认空（不发送）；仅当 LitePan 规则配置了 `path_prefix` 时才需填写 |
| 去抖秒数 | 一批上传静默该秒数后只通知一次（默认 30s） |

```text
本插件上传成功（目录同步 / 实时监控 / 手动上传, uploaded>0）
        │  去抖合并
        ▼
POST {LitePan}/api/open/automation/events   {event:"MP", message:"MP，请执行联动"}
        │
        ▼
LitePan 自动化规则：cache_clear → strm →（可选 strm_scrape）→ emby_refresh
```

- 触发范围：**本插件**的目录同步 / 实时监控 / 手动上传（**不含** MoviePilot 整理链）。
- 配置页提供「测试通知」按钮，并显示最近一次联动结果。

---

## 配置项（`strm2emby_*`）

| 分类 | 字段 | 默认 | 说明 |
| :-- | :-- | :-- | :-- |
| 通用 | `enabled` | false | 插件总开关 |
| 登录 | `access_token` / `refresh_token` | — | 登录令牌，仅存于宿主配置，API 不返回 |
| 登录 | `client_id` / `device_id` | 默认 / 自动 | 设备码登录身份 |
| 查询 | `poll_interval` / `page_size` / `order_by` / `sort_type` | 5 / 100 / 3 / 1 | 列表查询参数 |
| 查询 | `min_interval` | 0 | 两次云盘 API 请求的最小间隔（秒） |
| 存储 | `permanently_delete` | false | 删除时是否二次彻底删除 |
| 同步 | `sync_enabled` / `sync_source_dir` / `sync_remote_dir` | false / "" / `/` | 总开关 / 本地源 / 光鸭目标 |
| 同步 | `sync_watch` / `sync_watch_polling` / `sync_poll_interval` | false / false / 2 | 实时监控 / 强制轮询 / 轮询扫描间隔（秒） |
| 同步 | `sync_cron` | "" | 定时 Cron |
| 同步 | `sync_conflict` / `sync_delete_source` / `sync_extensions` | `skip` / false / "" | 同名策略 / 删源 / 扩展名白名单 |
| 安全 | `fs_allowed_roots` | "" | 允许浏览 / 手动上传的根目录（空=不额外限制，仍需超管） |
| LitePan | `litepan_enabled` / `litepan_base_url` | false / "" | 联动开关 / LitePan 地址 |
| LitePan | `litepan_api_key` | "" | task 类型 Key（只写不读） |
| LitePan | `litepan_event` / `litepan_message` / `litepan_source` / `litepan_path` | `MP` / "" / "" / "" | 事件名 / 消息 / 来源 / 路径 |
| LitePan | `litepan_debounce` | 30 | 去抖秒数 |

---

## 插件 API

所有端点均为 `auth: bear`，统一返回宿主 `schemas.Response`（`{success, message, data}`）。

| 方法 | 路径 | 说明 |
| :-- | :-- | :-- |
| GET / POST | `/api/v1/plugin/Strm2Emby/config` | 读取 / 保存配置 |
| GET | `/api/v1/plugin/Strm2Emby/login/qrcode` | 获取扫码二维码 |
| GET | `/api/v1/plugin/Strm2Emby/login/poll` | 轮询扫码登录 |
| POST | `/api/v1/plugin/Strm2Emby/login/logout` | 退出登录 |
| GET | `/api/v1/plugin/Strm2Emby/sync` | 立即执行一次目录同步 |
| GET | `/api/v1/plugin/Strm2Emby/fs/list?path=` | 浏览 MoviePilot 主机目录（仅超级管理员） |
| POST | `/api/v1/plugin/Strm2Emby/upload` | 手动上传 `{paths, remote_dir}`（仅超级管理员） |
| GET | `/api/v1/plugin/Strm2Emby/progress` | 当前上传 / 同步进度 |
| GET | `/api/v1/plugin/Strm2Emby/history?limit=` | 上传 / 同步记录 |
| POST | `/api/v1/plugin/Strm2Emby/history/clear` | 清空上传 / 同步记录 |
| GET | `/api/v1/plugin/Strm2Emby/litepan/status` | 最近一次 LitePan 联动结果 |
| POST | `/api/v1/plugin/Strm2Emby/litepan/test` | 立即发送一次 LitePan 测试事件 |

---

## 目录结构

```text
MoviePilot-Plugins/
├── plugins.v3/strm2emby/             # 插件本体：后端 + Vue 前端源码
│   ├── __init__.py                   # 主类 Strm2Emby（配置/登录/存储模块方法/目录同步/上传/进度）
│   ├── guangya_api.py                # 存储层 GuangYaApi（分页列举/严格查询/任务型增删改/上传/usage/snapshot）
│   ├── guangya_client.py             # 传输层 GuangYaClient（统一请求/错误码/刷新/限流/登录/上传票据/OSS）
│   ├── models.py                     # 各端点的 Pydantic 请求/数据模型
│   ├── pyproject.toml                # V3 插件额外 Python 依赖
│   ├── dist/assets/                  # Vue 联邦构建产物（宿主实际加载 remoteEntry.js）
│   ├── src/                          # 前端源码 components/{Config,Page,AppPage,ManualUpload,DirectorySync,UploadHistory}.vue
│   └── vite.config.js / package.json / build-zip.js
├── icons/Strm2Emby.png               # 插件图标
├── package.v3.json                   # V3 插件市场索引
├── .github/workflows/release.yml     # 自动发布工作流
├── LICENSE                           # GPL-3.0
└── README.md                         # 本文件
```

---

## 开发与构建

前端是 **Vue 联邦组件**，宿主实际加载的是构建产物 `plugins.v3/strm2emby/dist/assets/`，**需要本地构建**：

```bash
cd plugins.v3/strm2emby
npm install
npm run build:web      # 生成 dist/
npm run build          # build:web + build:zip，额外生成可上传的 zip
```

- 需 **Node 20**。
- 运行时依赖（`apscheduler`、`oss2`、`watchfiles`）声明在插件目录的 `pyproject.toml`，由 MoviePilot V3 宿主安装。

---

## 常见问题

<details>
<summary>装好后找不到入口？</summary>

入口在左侧 **「整理」分组 → Strm2Emby**。若刚安装 / 更新，请**硬刷新**页面（`Ctrl+Shift+R`）或重新登录。

</details>

<details>
<summary>LitePan 收到通知但没生成 STRM？</summary>

LitePan 有目录缓存，秒传文件的云端列表可能延迟。请在自动化规则里于 `strm` **之前**加一步 `cache_clear`，必要时重启 LitePan 清掉卡住的运行。

</details>

<details>
<summary>显示「上传失败」但云端其实已有该文件？</summary>

大文件上传后光鸭列表索引有分钟级延迟，插件会在确认不到时按「已上传」记录并事后收敛；可搜索日志 `上传诊断` 定位。秒传（上传票据返回 156）也属正常。

</details>

<details>
<summary>配置保存后令牌会不会丢失？</summary>

不会。配置采用整份字段写入，`_merge_config()` 保留未提交字段；令牌只由扫码登录流程更新，任何 API 都不返回明文。

</details>

---

## 许可

本项目遵循 **GPL-3.0** 许可，详见 [`LICENSE`](LICENSE)。

<div align="center"><sub>如果这个插件对你有帮助，欢迎 Star 本项目。</sub></div>

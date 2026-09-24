# Strm2Emby

MoviePilot V3 插件：把「光鸭云盘」接入 MoviePilot 存储，并内置目录同步、手动上传、上传记录与 LitePan 联动。

- 插件 ID / 主类：`Strm2Emby`
- 存储展示名：`Strm2Emby`
- 配置前缀：`strm2emby_`
- 版本：`1.1.0`
- 兼容：MoviePilot `>=3.0.0`（V3）

## 文件职责

| 文件 | 说明 |
| :-- | :-- |
| `__init__.py` | 主类 `Strm2Emby`：生命周期、配置、扫码登录、API、存储模块方法、目录同步/监控、手动上传、记录与进度、LitePan 联动 |
| `guangya_client.py` | 传输层 `GuangYaClient`：统一请求与错误码、加锁刷新令牌、限流重试、设备码登录、上传票据、OSS 分片上传 |
| `guangya_api.py` | 存储层 `GuangYaApi`：分页列举、严格查询、任务型增删改、下载、上传/秒传、空间用量、快照与缓存 |
| `models.py` | `get_api()` 各端点的请求 / 数据模型 |
| `src/` | Vue 联邦前端源码（`Config` / `Page` / `AppPage` / `ManualUpload` / `DirectorySync` / `UploadHistory`） |
| `dist/` | 联邦构建产物，宿主实际加载 `dist/assets/remoteEntry.js` |
| `pyproject.toml` | V3 插件额外 Python 依赖（宿主安装） |
| `build-zip.js` | 生成本地可上传安装的 zip |

## 构建前端

```bash
npm install
npm run build:web   # 生成 dist/
npm run build       # build:web + build:zip
```

需 Node 20。`dist/` 是宿主加载的产物，改动 `src/` 后必须重新构建并提交。

## 说明

完整的功能说明、配置项、插件 API 与常见问题见仓库根目录 [`README.md`](../../README.md)。

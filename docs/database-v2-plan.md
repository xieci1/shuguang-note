# 薯光笔记数据库化第二版计划

## 目标

第二版面向线上多人部署，把第一版 SQLite 本地存储升级为可扩展的数据与图片资产管理方案。

## 核心升级

- 数据库从 SQLite 切到 PostgreSQL，使用环境变量 `SHUGUANG_NOTE_DATABASE_URL` 控制连接。
- 引入 Alembic 管理表结构迁移，避免线上手动建表或丢数据。
- 图片从本地 `history/<task_id>/` 迁移到对象存储，例如 S3、R2、OSS 或 MinIO。
- 增加用户与作品归属：每条创作、图片任务、生成内容都关联 `user_id`。
- 增加任务队列：图片生成从同步 SSE 生成升级为后台任务，前端通过任务状态轮询或 WebSocket/SSE 订阅进度。

## 建议数据模型扩展

- `users`：用户账号、登录方式、角色。
- `assets`：统一管理图片、参考图、缩略图、对象存储 key、尺寸、大小。
- `generation_jobs`：统一管理文本、大纲、图片、重试等任务。
- `provider_usage`：记录模型、token、图片张数、耗时、错误，用于成本统计。
- `audit_logs`：记录重要操作，方便排查线上问题。

## API 演进

- 保留第一版兼容接口一段时间。
- 新增资源化接口：
  - `POST /api/creations`
  - `GET /api/creations/:id`
  - `POST /api/creations/:id/images`
  - `POST /api/creations/:id/content`
  - `GET /api/jobs/:job_id`
- 图片 URL 返回签名访问地址或 CDN 地址，不再暴露本地文件路径。

## 迁移与上线

- 先上线第一版 SQLite，确认所有创作数据都能完整落库。
- 编写 SQLite 到 PostgreSQL 的迁移脚本。
- 对象存储迁移时保留本地图片备份，迁移完成后数据库 `generated_images.url` 指向对象存储。
- 上线前跑一次全量校验：创作数、图片数、内容数、文件可访问率。

## 验收标准

- 多用户数据互相隔离。
- 服务重启后任务状态、图片、标题文案标签都能恢复。
- 图片资产不依赖本地磁盘，支持容器重建。
- 可以统计每个用户、每个服务商、每次任务的生成成本。

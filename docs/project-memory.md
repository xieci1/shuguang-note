# 薯光笔记项目记忆

更新时间：2026-06-09

## 当前项目状态

- 项目目录：以当前仓库根目录为准，部署时不要依赖本机绝对路径。
- 前端：Vue 3 + Vite，当前开发地址常用 `http://127.0.0.1:5186/`
- 后端：Flask，默认地址 `http://127.0.0.1:12398`
- 当前产品方向：小红书风格图文生成工具，页面品牌为“薯光笔记”
- 图片文件仍保存在 `history/<task_id>/`
- 现在已经引入 SQLite 数据库，默认数据库文件：`data/shuguang-note.sqlite3`
- 已新增小红书一键发布能力，当前走本机 `social-auto-upload` CLI 适配。

## 已完成的重要功能

- 首页、小红书风格 UI、动态进度和丰富主页内容已改过。
- `/ideas` 支持同一个话题一次生成 5 个不同选题/不同作品。
- 原模式保留：一个话题生成一个完整作品大纲。
- 图片生成支持：
  - 只生成 1 张封面预览
  - 生成整套图片
  - 指定单页生成
  - 多选页面生成
  - 失败重试
- 图片生成页和结果页已加 hover 预览。
- 进度条已做动态状态，但真实图片生成接口没有细粒度百分比，只能按页面完成情况推进。
- “我的创作”曾经看不到刚生成内容的问题已修过。
- 标题/文案/标签不是前端写死，来自 `/api/content`，提示词在 `backend/prompts/content_prompt.txt`。
- 已修复标题/文案/标签缓存串台：切换大纲/作品会清空旧内容。
- “我的创作”支持 `全部 / 已完成 / 已发布 / 草稿箱` 筛选。
- 已发布作品卡片左上角优先显示红色 `已发布` 角标，后端通过 `is_published` 字段返回。

## 小红书一键发布功能

当前策略：

- 首版只支持小红书图文发布。
- 不直接接 Postiz 服务，只借鉴 `account / media / draft / job` 抽象。
- 不合并 `social-auto-upload` 源码，薯光笔记通过 CLI wrapper 调用它。
- 用户已经接受直接发布；当前配置允许执行器点击最终发布按钮。

关键文件：

- `backend/models.py`
  - `PublishAccount`
  - `PublishDraft`
  - `PublishJob`
- `backend/services/publish.py`
  - 发布账号、草稿、任务、后台线程执行逻辑
  - `PublisherAdapter.prepare_payload()` 中 `post.click_publish` 当前为 `True`
  - 同一账号同时只允许一个发布任务运行
  - 成功后任务状态仍使用 `ready_for_review`，前端展示为 `已发布`
- `backend/routes/publish_routes.py`
  - 发布账号、草稿、任务 API
- `scripts/xhs_sau_login.py`
  - 调用 `sau xiaohongshu login --account <name> --headed`
- `scripts/xhs_sau_wrapper.py`
  - 调用 `sau xiaohongshu upload-note`
  - 已对图片路径去重，避免同一张图重复上传
  - 当 `SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH=true` 且 payload `click_publish=true` 时直接发布
- `publish_providers.yaml`
  - 当前本机配置已启用小红书发布器
  - `SAU_BIN` 建议在部署环境变量中配置，或确保 `sau` 已加入服务器 PATH。
  - `SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH: "true"`
- `publish_providers.yaml.example`
  - 示例配置也已改成直接发布语义

前端入口：

- `frontend/src/components/history/GalleryCard.vue`
  - “我的创作”作品卡片 hover 后有 `发布` 按钮
  - 已发布作品角标显示 `已发布`
- `frontend/src/views/HistoryView.vue`
  - 我的创作列表新增 `已发布` tab
  - 点击发布会加载作品详情并打开发布弹窗
- `frontend/src/components/publish/PublishRecordModal.vue`
  - 选择账号、标题、正文来源、标签、图片后发布
  - 标题来源包含内容生成标题、编辑内容里的 `标题：/副标题：`、作品标题兜底
  - 正文可选内容生成区文案、全部编辑内容、单页内容
  - 会过滤提示词、配图建议、画面建议等不适合发布的编辑内容
  - 支持 AI 生成标签，也可手动添加/删除标签
- `frontend/src/components/settings/PublishAccountSettings.vue`
  - 发布账号管理已放到系统设置
- `frontend/src/views/TasksView.vue`
  - 任务中心展示发布任务、状态和日志

已发布筛选逻辑：

- 作品本身仍保留生成状态，如 `completed`、`draft`、`partial`。
- `status=published` 是历史列表接口的特殊筛选，含义是存在成功发布任务。
- 成功发布任务状态目前识别 `ready_for_review` 和 `published`。
- `HistoryRecord` 列表项新增 `is_published?: boolean`，用于卡片角标。

发布账号与登录态：

- 账号数据在数据库 `publish_accounts`。
- 浏览器 profile 按账号隔离，路径形如：`data/browser_profiles/xhs/<account_id>`。
- 不保存密码，不把明文 Cookie 写入数据库。
- `data/browser_profiles/` 应保持在 `.gitignore` 中。

## 数据库化第一版已完成

目标：使用 SQLite + SQLAlchemy 管理创作数据，保持原 API 兼容。

新增/修改的关键文件：

- `backend/db.py`
  - SQLAlchemy engine/session 初始化
  - 默认 SQLite 地址：`data/shuguang-note.sqlite3`
  - 支持环境变量 `SHUGUANG_NOTE_DATABASE_URL`，兼容旧 `REDINK_DATABASE_URL`
- `backend/models.py`
  - `Creation`
  - `OutlinePage`
  - `GeneratedImage`
  - `GeneratedContent`
  - `ImageTask`
- `backend/services/history.py`
  - 已从 JSON 文件存储改成数据库存储
  - 保留原有 `HistoryService` 方法名和返回结构
  - 仍返回前端熟悉的结构：`outline.raw/pages`、`images.task_id/generated`、`status`、`thumbnail`
- `backend/services/image.py`
  - 图片生成、失败、重试时同步写入数据库
  - 通过 `task_id` 关联历史记录
- `backend/routes/content_routes.py`
  - 内容生成成功后，如果传入 `record_id`，会把标题、文案、标签保存到数据库
- `frontend/src/api/index.ts`
  - `generateContent` 增加可选 `recordId`
  - `HistoryDetail` 增加 `content`
- `frontend/src/components/result/ContentDisplay.vue`
  - 调用内容生成时传 `store.recordId`
- `frontend/src/views/HistoryView.vue`
  - 从“我的创作”打开记录时恢复已保存的标题、文案、标签
- `scripts/migrate_history_to_db.py`
  - 旧 JSON 历史迁移到 SQLite
  - 可重复运行
  - 会扫描 `history/<task_id>/` 补齐图片记录
- `docs/database-v2-plan.md`
  - 第二版演进计划

依赖变化：

- `pyproject.toml` 已增加 `sqlalchemy>=2.0.0`
- 当前机器没有 `uv` 命令，所以依赖是通过 `python -m pip install "sqlalchemy>=2.0.0"` 安装验证的

## 数据库迁移状态

- 已执行：`python scripts/migrate_history_to_db.py`
- 旧 history 数据已导入 `data/shuguang-note.sqlite3`
- 迁移脚本重复执行已验证通过
- PowerShell 中迁移输出中文可能乱码，但命令成功退出，不影响数据
- 旧 JSON 文件和图片文件没有删除，仍保留作为备份

## 已验证

已跑过：

- `python -m compileall backend scripts`
- `npm run build` 需要在 `frontend/` 目录运行
- 数据库服务自检：
  - 创建记录
  - 更新图片
  - 保存内容
  - 查询记录
  - 删除记录
- `python scripts/migrate_history_to_db.py`
- `/api/health` 返回 200
- `/api/history` 返回 200
- 发布相关测试：
  - `python -m pytest tests\test_publish_service.py tests\test_publish_routes.py -q`
  - `python -m pytest tests\test_history_service.py tests\test_publish_service.py -q`
- 前端构建：
  - `cd frontend`
  - `npm run build`
- 浏览器检查过：
  - “我的创作”有 `已发布` tab
  - 设置页有发布账号管理
  - 任务中心显示发布任务，不再显示旧的“填充任务/填充中”文案

后端已重启，新逻辑已生效。

## 已知注意事项

- 图片二进制没有入库，仍在本地 `history/<task_id>/`。
- 数据库只保存图片文件名、URL、页码、状态、错误信息和关联关系。
- 旧历史里可能存在多个记录关联同一个 `task_id`，迁移脚本已做兼容处理。
- Windows PowerShell/GBK 下，后端日志中的 emoji 和中文可能触发编码日志噪声，但接口本身可正常返回。
- `uv.lock` 没有更新，因为当前环境没有 `uv` 命令。
- 数据库表目前通过 `Base.metadata.create_all()` 启动时自动创建，暂未接 Alembic。
- 发布任务成功状态在数据库里仍叫 `ready_for_review`，这是为了避免扩大迁移；UI 已统一展示为 `已发布`。
- `social-auto-upload` 当前实际会自动发布并关闭/退出流程，若以后要改回人工确认，需要同步调整 wrapper 和 `SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH`。
- Windows 下如果登录二维码终端显示失败，可打开 `social-auto-upload/cookies/` 中保存的二维码图片扫码。

## 第二版方向

详见 `docs/database-v2-plan.md`。

核心方向：

- SQLite 切 PostgreSQL
- 引入 Alembic 迁移
- 图片迁移到对象存储
- 增加用户系统和作品归属
- 增加任务队列
- 记录服务商用量和生成成本

## 下一步建议

优先做：

1. 若继续扩展发布，考虑把 `ready_for_review` 正式迁移为 `published`，或新增明确的发布结果字段。
2. 修 Windows 控制台日志编码问题，避免 emoji 日志在 GBK 环境报错。
3. 给发布任务加“重新发布/复制草稿/查看发布 payload”能力，方便失败排查。
4. 如果继续部署，确认生产环境是否使用 SQLite；多人使用建议进入第二版 PostgreSQL 方案。

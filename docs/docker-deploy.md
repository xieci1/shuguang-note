# Docker 部署

## 服务器首次部署

```bash
git clone <你的仓库地址> shuguang-note
cd shuguang-note

# 首次启动前准备持久化目录和配置文件
mkdir -p data history output
cp -n text_providers.yaml.example text_providers.yaml
cp -n image_providers.yaml.example image_providers.yaml
cp -n publish_providers.yaml.example publish_providers.yaml

docker compose up -d --build
```

访问：

```text
http://服务器IP:12398
```

首次注册的用户会自动成为管理员。之后文本生成配置、图片生成配置可以在后台设置页修改，配置会保存到服务器当前目录的 YAML 文件中。

## 更新部署

```bash
cd shuguang-note
git pull
docker compose up -d --build
```

## 查看日志

```bash
docker compose logs -f shuguang-note
```

## 需要持久化的文件

- `data/`：SQLite 数据库、用户、额度、发布账号、浏览器登录态。默认数据库文件是 `data/shuguang-note.sqlite3`，旧版 `data/redink.sqlite3` 会在首次启动时自动兼容复制。
- `history/`：生成图片与历史任务图片
- `output/`：兼容旧输出目录
- `text_providers.yaml`：文本生成配置
- `image_providers.yaml`：图片生成配置
- `publish_providers.yaml`：发布执行器配置

## 发布到小红书

当前发布功能依赖外部 `sau` 命令。普通图文生成不需要它；如果要在 Docker 容器里直接打开登录和发布，需要在镜像或服务器环境中安装 `social-auto-upload` 并确保 `publish_providers.yaml` 里的 `SAU_BIN` 能找到该命令。

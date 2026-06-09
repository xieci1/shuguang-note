# Docker 部署

## 服务器首次部署

```bash
git clone git@github.com:xieci1/shuguang-note.git
cd shuguang-note

# 首次启动前准备持久化目录和配置文件
mkdir -p data history output
cp -n text_providers.yaml.example text_providers.yaml
cp -n image_providers.yaml.example image_providers.yaml
cp -n publish_providers.yaml.example publish_providers.yaml

docker compose up -d --build
```

启动后查看容器状态：

```bash
docker compose ps
docker compose logs -f shuguang-note
```

访问：

```text
http://服务器IP:12398
```

首次注册的用户会自动成为管理员。之后文本生成配置、图片生成配置可以在后台设置页修改，配置会保存到服务器当前目录的 YAML 文件中。

## 改完源码之后怎么部署

推荐流程是：本地改代码并推送到 GitHub，服务器拉取最新代码后重新构建 Docker 镜像。

本地电脑：

```bash
cd shuguang-note
git status
git add .
git commit -m "说明这次修改"
git push
```

提交前确认不要把真实密钥、Cookie、数据库、生成图片提交上去。下面这些文件和目录默认已被 `.gitignore` 忽略，不要手动强制提交：

- `data/*.sqlite3`
- `data/browser_profiles/`
- `history/`
- `output/`
- `scan_output/`
- `text_providers.yaml`
- `image_providers.yaml`
- `publish_providers.yaml`
- `xianyu_cookies.txt`

服务器：

```bash
cd shuguang-note
git pull
docker compose up -d --build
docker compose logs -f shuguang-note
```

如果是在服务器上直接修改源码，没有走 Git，也需要重新构建容器：

```bash
cd shuguang-note
docker compose up -d --build
docker compose logs -f shuguang-note
```

如果更新后页面没有变化、图片还是不显示，先强制重建并重启：

```bash
cd shuguang-note
docker compose down
docker compose up -d --build
docker compose logs -f shuguang-note
```

## 查看日志

```bash
docker compose logs -f shuguang-note
```

## 需要持久化的文件

这些文件和目录都挂载在服务器宿主机上，重新 `docker compose up -d --build` 不会删除它们：

- `data/`：SQLite 数据库、用户、额度、发布账号、浏览器登录态。默认数据库文件是 `data/shuguang-note.sqlite3`，旧版 `data/redink.sqlite3` 会在首次启动时自动兼容复制。
- `history/`：生成图片与历史任务图片
- `output/`：兼容旧输出目录
- `text_providers.yaml`：文本生成配置
- `image_providers.yaml`：图片生成配置
- `publish_providers.yaml`：发布执行器配置

如果要迁移服务器，把上面这些数据目录和 YAML 配置文件一起复制过去，再重新启动 Docker 即可。

## 发布到小红书

当前发布功能依赖外部 `sau` 命令。普通图文生成不需要它。

注意：设置页里的“打开登录”不是网页跳转，它会让后端在运行环境里启动 `sau xiaohongshu login --headed`。如果项目部署在服务器 Docker 里，浏览器窗口会出现在服务器/容器侧，不会弹到你当前电脑的浏览器页面。

如果服务器上要使用小红书登录和发布，需要满足：

- 镜像或服务器环境中已安装 `social-auto-upload`
- `publish_providers.yaml` 里的 `SAU_BIN` 能找到 `sau`
- 服务器具备可操作的图形环境，例如桌面、VNC、noVNC 或 X11 转发
- `data/browser_profiles/` 已持久化挂载，登录态才能在容器重启后保留

如果服务器没有图形环境，建议先只在服务器使用图文生成功能；小红书登录/发布放在有桌面环境的机器上执行，或者后续单独接入远程浏览器/noVNC 方案。

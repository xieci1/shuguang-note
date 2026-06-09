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

# 推荐设置远程浏览器密码，用于小红书扫码登录页面
cat > .env <<'EOF'
SHUGUANG_NOTE_VNC_PASSWORD=请改成强密码
# 如果前面有域名或反向代理，也可以显式指定：
# SHUGUANG_NOTE_REMOTE_BROWSER_URL=http://服务器IP:6080/vnc.html?autoconnect=true&resize=scale&path=websockify
EOF

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

远程浏览器登录页：

```text
http://服务器IP:6080/vnc.html
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

如果这次更新涉及 `publish_providers.yaml.example`，已部署过的服务器不会自动覆盖真实 `publish_providers.yaml`。需要手动对照示例补配置，尤其是 Docker 发布功能需要：

```yaml
env:
  SAU_BIN: /opt/social-auto-upload/.venv/bin/sau
  SAU_ROOT: /opt/social-auto-upload
  PYTHONPATH: /opt/social-auto-upload
  DISPLAY: ":99"
  SHUGUANG_NOTE_ALLOW_DIRECT_PUBLISH: "true"
startup_timeout_seconds: 2
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

Docker 镜像已内置一个远程浏览器桌面和 noVNC。设置页点击“打开登录”后，后端会启动 `sau xiaohongshu login --account <账号> --headed`，前端会自动打开远程浏览器页面，用户在网页里的浏览器窗口扫码登录即可。

如果服务器上要使用小红书登录和发布，需要满足：

- 服务器安全组/防火墙放行 `12398` 和 `6080`
- `.env` 中设置 `SHUGUANG_NOTE_VNC_PASSWORD`
- `publish_providers.yaml` 里的 `SAU_BIN` 能找到 `sau`，Docker 默认是 `/opt/social-auto-upload/.venv/bin/sau`
- `data/browser_profiles/` 已持久化挂载，登录态才能在容器重启后保留
- 第一版远程桌面是单实例，同一时间建议只让一个用户扫码登录，避免多人同时操作同一个远程桌面

如果使用域名或反向代理，建议在 `.env` 里显式配置远程浏览器地址：

```bash
SHUGUANG_NOTE_REMOTE_BROWSER_URL=https://你的域名/remote-browser/vnc.html?autoconnect=true&resize=scale&path=websockify
```

第一版默认直接暴露 `6080`，生产环境建议至少配置强密码，并限制只给可信用户访问。

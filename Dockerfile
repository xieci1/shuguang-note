# ============================================
# 薯光笔记 AI 图文创作平台 - Docker 镜像
# ============================================

# 阶段1: 构建前端
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

# 安装 pnpm
RUN npm install -g pnpm

# 复制前端依赖文件
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制前端源码
COPY frontend/ ./

# 构建前端
RUN pnpm build

# ============================================
# 阶段2: 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    chromium \
    fluxbox \
    fonts-liberation \
    fonts-noto-cjk \
    git \
    novnc \
    websockify \
    x11vnc \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir uv

# 安装小红书发布执行器。该项目通过 sau CLI 提供登录和发布能力。
RUN git clone --depth 1 https://github.com/dreammis/social-auto-upload.git /opt/social-auto-upload \
    && cd /opt/social-auto-upload \
    && uv sync --no-dev

# 复制 Python 项目配置
COPY pyproject.toml uv.lock* ./

# 安装 Python 依赖
RUN uv sync --no-dev --no-install-project

# 复制后端代码
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY docker/start.sh ./docker-start.sh

# 复制空白配置文件模板（不包含任何 API Key）
COPY docker/text_providers.yaml ./
COPY docker/image_providers.yaml ./
COPY publish_providers.yaml.example ./publish_providers.yaml

# 从构建阶段复制前端产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建数据目录
RUN mkdir -p data history output \
    && chmod +x ./docker-start.sh

# 设置环境变量
ENV FLASK_DEBUG=False
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=12398
ENV SHUGUANG_NOTE_OUTPUT_DIR=output
ENV SHUGUANG_NOTE_REMOTE_BROWSER=true
ENV SHUGUANG_NOTE_NOVNC_PORT=6080
ENV SAU_ROOT=/opt/social-auto-upload
ENV SAU_BIN=/opt/social-auto-upload/.venv/bin/sau
ENV PYTHONPATH=/opt/social-auto-upload
ENV PATH="/opt/social-auto-upload/.venv/bin:${PATH}"

# 暴露端口
EXPOSE 12398
EXPOSE 6080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run --no-sync python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"FLASK_PORT\", \"12398\")}/api/health')" || exit 1

# 启动命令
CMD ["./docker-start.sh"]

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
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir uv

# 复制 Python 项目配置
COPY pyproject.toml uv.lock* ./

# 安装 Python 依赖
RUN uv sync --no-dev --no-install-project

# 复制后端代码
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# 复制空白配置文件模板（不包含任何 API Key）
COPY docker/text_providers.yaml ./
COPY docker/image_providers.yaml ./
COPY publish_providers.yaml.example ./publish_providers.yaml

# 从构建阶段复制前端产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建数据目录
RUN mkdir -p data history output

# 设置环境变量
ENV FLASK_DEBUG=False
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=12398
ENV SHUGUANG_NOTE_OUTPUT_DIR=output

# 暴露端口
EXPOSE 12398

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run --no-sync python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"FLASK_PORT\", \"12398\")}/api/health')" || exit 1

# 启动命令
CMD ["uv", "run", "--no-sync", "python", "-m", "backend.app"]

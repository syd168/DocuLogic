# 多阶段构建：前端 + 后端 + Nginx 整合到一个容器
FROM python:3.10-slim AS builder

WORKDIR /build

# 安装 Node.js 用于构建前端
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装前端依赖
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# 复制前端源码并构建
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# 最终镜像
FROM python:3.10-slim

# 安装系统依赖和 Nginx
RUN apt-get update && apt-get install -y \
    nginx \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制 Python 依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY web/ ./web/
COPY web_server.py .

# 复制前端构建产物到 Nginx
COPY --from=builder /build/frontend/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# 删除默认站点配置(避免端口冲突)
RUN rm -f /etc/nginx/sites-enabled/default

# 创建必要的目录
RUN mkdir -p /app/out /app/logs /app/web/data

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    BACKEND_PORT=8000 \
    FRONTEND_PORT=80 \
    MODEL_PATH=/app/weights \
    OUTPUT_DIR=/data/output \
    JWT_SECRET=change-me-in-production \
    CORS_ORIGINS=http://localhost,http://127.0.0.1

# 暴露端口（仅前端端口）
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 启动脚本：同时运行 Nginx 和后端
CMD bash -c "nginx & python web_server.py"

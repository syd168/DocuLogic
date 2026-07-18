# 多阶段构建：前端 + 后端 + Nginx 整合到一个容器
FROM python:3.10-slim AS builder

WORKDIR /build

# 安装 Node.js 用于构建前端（构建阶段不走 HTTP 代理，避免 buildkit 注入的代理在容器内不可达）
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    bash -c 'apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*'

# 复制并安装前端依赖
COPY frontend/package*.json ./frontend/
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    bash -c 'cd frontend && npm install'

# 复制前端源码并构建
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# 最终镜像
FROM python:3.10-slim

# 安装系统依赖和 Nginx（国内镜像/apt 源直连，不走 buildkit 注入的 HTTP 代理）
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    bash -c 'apt-get update && apt-get install -y \
    nginx \
    curl \
    cron \
    sqlite3 \
    default-mysql-client \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*'

WORKDIR /app

# 复制 Python 依赖并安装
COPY requirements.txt .
COPY requirements-marker.txt .

# 使用华为源；构建时清除代理，避免 pip 经不可达的 buildkit 代理访问国内镜像
# PyTorch 包体积大（~900MB），单独安装并放宽超时/重试，避免 Read timed out
ARG PIP_INDEX=https://mirrors.huaweicloud.com/repository/pypi/simple
# 可选：构建时安装 Marker（GPL）。默认 0；设为 1 或 true 时安装 requirements-marker.txt
# 例：docker compose build --build-arg INSTALL_MARKER=1
ARG INSTALL_MARKER=0
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    pip install --no-cache-dir --default-timeout=1000 --retries 10 \
    torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
    -i ${PIP_INDEX}
RUN env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    pip install --no-cache-dir --default-timeout=300 --retries 5 \
    -r requirements.txt -i ${PIP_INDEX}
RUN if [ "${INSTALL_MARKER}" = "1" ] || [ "${INSTALL_MARKER}" = "true" ] || [ "${INSTALL_MARKER}" = "TRUE" ]; then \
      echo ">>> INSTALL_MARKER=${INSTALL_MARKER}: installing marker-pdf (GPL-3.0)..." && \
      env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        pip install --no-cache-dir --default-timeout=600 --retries 5 \
        -r requirements-marker.txt -i ${PIP_INDEX} ; \
    else \
      echo ">>> INSTALL_MARKER=${INSTALL_MARKER}: skip marker-pdf (default; see LICENSE-THIRD-PARTY.md)" ; \
    fi

# 复制后端代码
COPY web/ ./web/
COPY web_server.py .
# 复制文档解析器中间件/插件/配置（运行时必需）
COPY converts/middleware/ ./converts/middleware/
COPY converts/plugins/ ./converts/plugins/
COPY converts/configs/ ./converts/configs/
COPY converts/configs/ ./converts/configs.defaults/
# 复制本地预置文档解析器源码目录（由部署方提前下载，不纳入 Git）
# 注意：converts/models/marker 由根目录 .dockerignore 排除，不进入默认镜像
COPY converts/models/ ./converts/models/

# 复制前端构建产物到 Nginx
COPY --from=builder /build/frontend/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# 删除默认站点配置(避免端口冲突)
RUN rm -f /etc/nginx/sites-enabled/default

# 创建必要的目录
RUN mkdir -p /app/out /app/logs /app/web/data /app/backups

# 复制备份脚本
COPY scripts/backup_database.sh /app/backup_database.sh
RUN chmod +x /app/backup_database.sh

# 创建 cron 定时任务（每天凌晨 2 点执行备份）
RUN echo "0 2 * * * cd /app && bash backup_database.sh >> /app/backups/backup.log 2>&1" > /etc/cron.d/doculogic-backup \
    && chmod 0644 /etc/cron.d/doculogic-backup \
    && crontab /etc/cron.d/doculogic-backup

# 复制入口脚本
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 暴露端口（仅前端端口）
EXPOSE 80

# 健康检查：通过 Nginx 检查后端服务状态
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 使用入口脚本启动所有服务
CMD ["/app/entrypoint.sh"]

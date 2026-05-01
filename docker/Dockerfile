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
    cron \
    sqlite3 \
    default-mysql-client \
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

#RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
#使用华为源
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple

# 复制后端代码
COPY web/ ./web/
COPY web_server.py .
# 复制文档解析器中间件/插件/配置（运行时必需）
COPY converts/middleware/ ./converts/middleware/
COPY converts/plugins/ ./converts/plugins/
COPY converts/configs/ ./converts/configs/
# 复制本地预置文档解析器源码目录（由部署方提前下载，不纳入 Git）
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

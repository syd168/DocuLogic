#!/bin/bash
set -e

echo "╔==========================================================╗"
echo "║               DocuLogic Docker 启动                    ║"
echo "╚==========================================================╝"
echo ""

# ℹ️  Docker 环境变量已通过 docker-compose.yml 的 environment 配置注入
#    无需在容器内加载 .env 文件（符合去硬编码规范）
echo "ℹ️  使用 docker-compose 传入的环境变量配置"
echo ""

echo "📊 当前配置:"
echo "   • 环境: ${ENVIRONMENT:-development}"
echo "   • 数据库类型: ${DATABASE_TYPE:-sqlite}"
echo "   • Redis: ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}"
echo "   • 模型路径: ${MODEL_PATH:-/app/weights/logics-parsing-v2}"
echo ""

# 检查必要的目录和权限
echo "📁 检查目录结构和权限..."
mkdir -p /app/logs /app/out /app/web/data /app/backups /app/converts/configs

# 首次挂载空配置卷时，从镜像内置默认配置初始化
if [ -d /app/converts/configs.defaults ] && [ -z "$(ls -A /app/converts/configs 2>/dev/null)" ]; then
    echo "ℹ️  初始化解析器默认配置到持久化卷..."
    cp -a /app/converts/configs.defaults/. /app/converts/configs/
fi

# 检查关键挂载点是否可写
WRITABLE=true
for dir in /data/output /app/logs /app/web/data /app/backups; do
    if [ ! -w "$dir" ]; then
        echo "❌ 目录不可写: $dir"
        WRITABLE=false
    fi
done

if [ "$WRITABLE" = false ]; then
    echo ""
    echo "⚠️  警告：部分数据目录权限不足"
    echo "   请在宿主机执行: chown -R 1000:1000 ${DATA_DIR:-/data}"
    echo "   或调整 Docker 容器的用户映射"
    echo ""
fi

echo "✓ 目录结构就绪"
echo ""

# 启动服务
echo "🚀 启动 DocuLogic 服务..."
echo "   • Nginx (端口 80)"
echo "   • Cron (定时备份)"
echo "   • Backend (FastAPI)"
echo ""

# 启动 Nginx
nginx
echo "✓ Nginx 已启动"

# 启动 Cron
cron
echo "✓ Cron 定时任务已启动"

# 启动后端（使用 exec 替换当前进程，便于信号处理）
echo "✓ 正在启动后端服务..."
echo ""
exec python web_server.py

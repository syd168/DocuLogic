#!/usr/bin/env sh
# 启动后端 + 前端；等价于项目根执行: python3 run_dev.py start
# 与 start.bat 行为一致（均委托 run_dev.py）。
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

if [ -x "$ROOT/venv/bin/python" ]; then
  PYTHON_EXEC="$ROOT/venv/bin/python"
else
  PYTHON_EXEC="${PYTHON:-python3}"
fi

# 加载 .env 文件中的环境变量
if [ -f "$ROOT/.env" ]; then
  echo "📄 加载 .env 配置文件..."
  # 使用 set -a 自动导出所有变量，然后 source .env 文件
  set -a
  # 过滤掉注释和空行后 source
  grep -v '^\s*#' "$ROOT/.env" | grep -v '^\s*$' > /tmp/doculogic_env.tmp
  . /tmp/doculogic_env.tmp
  rm -f /tmp/doculogic_env.tmp
  set +a
  echo "✓ 环境变量已加载"
else
  echo "⚠️  警告：未找到 .env 文件，使用默认配置"
fi
echo ""

# 先执行一次前台启动以显示初始化信息，然后切换到后台
echo "╔==========================================================╗"
echo "║               DocuLogic 开发环境启动                   ║"
echo "╚==========================================================╝"
echo ""
echo "🔄 检查并停止已运行的服务..."

# 停止旧服务
"$PYTHON_EXEC" run_dev.py stop 2>&1 | grep -E "(🛑|ℹ️|✅)" || true
echo ""

# 创建日志目录
mkdir -p .run/logs

# 清空旧日志
> .run/logs/backend.log
> .run/logs/frontend.log

echo "🚀 正在启动服务（后台运行）..."
echo ""

# 在后台运行，直接输出到对应的日志文件
nohup "$PYTHON_EXEC" run_dev.py start >> .run/logs/backend.log 2>&1 &

# 等待几秒让服务启动
sleep 5

# 显示启动结果
echo "============================================================"
if [ -f ".run/.backend.pid" ]; then
  BACKEND_PID=$(cat .run/.backend.pid)
  echo "✓ 后端服务已启动 (PID: $BACKEND_PID)"
  echo "  API 地址: http://127.0.0.1:8000"
  echo "  API 文档: http://127.0.0.1:8000/api/docs"
else
  echo "✗ 后端服务启动失败，请查看日志"
fi

if [ -f ".run/.frontend.pid" ]; then
  FRONTEND_PID=$(cat .run/.frontend.pid)
  echo "✓ 前端服务已启动 (PID: $FRONTEND_PID)"
  echo "  前端地址: http://127.0.0.1:5173"
else
  echo "⚠️  前端服务可能未启动"
fi

echo ""
echo "📝 日志文件:"
echo "   • 后端日志: .run/logs/backend.log"
echo "   • 前端日志: .run/logs/frontend.log"
echo ""
echo "💡 提示:"
echo "   • 查看实时日志: tail -f .run/logs/backend.log"
echo "   • 停止服务: ./stop.sh"
echo ""

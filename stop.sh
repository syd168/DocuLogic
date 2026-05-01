#!/usr/bin/env sh
# 停止由 run_dev 记录的后端与前端进程；等价于: python3 run_dev.py stop
# 与 stop.bat 行为一致。
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

if [ -x "$ROOT/venv/bin/python" ]; then
  PYTHON_EXEC="$ROOT/venv/bin/python"
else
  PYTHON_EXEC="${PYTHON:-python3}"
fi

# 执行停止命令
"$PYTHON_EXEC" run_dev.py stop

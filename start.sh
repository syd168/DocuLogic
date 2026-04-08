#!/usr/bin/env sh
# 启动后端 + 前端；等价于项目根执行: python3 project_ctl.py start
# 与 start.bat 行为一致（均委托 project_ctl.py）。
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
if [ -x "$ROOT/venv/bin/python" ]; then
  exec "$ROOT/venv/bin/python" project_ctl.py start
fi
exec "${PYTHON:-python3}" project_ctl.py start

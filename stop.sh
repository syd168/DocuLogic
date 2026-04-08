#!/usr/bin/env sh
# 停止由 project_ctl 记录的后端与前端进程；等价于: python3 project_ctl.py stop
# 与 stop.bat 行为一致。
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
if [ -x "$ROOT/venv/bin/python" ]; then
  exec "$ROOT/venv/bin/python" project_ctl.py stop
fi
exec "${PYTHON:-python3}" project_ctl.py stop

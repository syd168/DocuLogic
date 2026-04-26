#!/usr/bin/env python3
"""
本地开发：跨平台启动 / 停止 DocuLogic 后端（FastAPI）与前端（Vite）。

推荐（项目根目录，与脚本等价）:
  ./start.sh && ./stop.sh          # Linux / macOS
  start.bat                        # Windows 双击或 cmd；停止用 stop.bat

或直接:
  python3 run_dev.py start
  python3 run_dev.py stop

（若项目根存在 venv/，start.sh / stop.sh / *.bat 会优先使用该解释器。）

环境变量:
  BACKEND_PORT   默认 8000
  FRONTEND_PORT  默认 5173
  VITE_PROXY_TARGET  前端 dev 代理的后端地址，默认 http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / ".run"
PID_FILE = RUN_DIR / "pids.json"
MODELS_ROOT_DIR = ROOT / "converts" / "models"

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "5173"))


def _is_windows() -> bool:
    return sys.platform == "win32"


def _read_pids() -> dict:
    if not PID_FILE.is_file():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_pids(backend: int | None, frontend: int | None) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if backend is not None:
        data["backend"] = backend
    if frontend is not None:
        data["frontend"] = frontend
    PID_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    if _is_windows():
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(0.3)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def stop() -> None:
    pids = _read_pids()
    for key in ("frontend", "backend"):
        pid = pids.get(key)
        if isinstance(pid, int):
            print(f"Stopping {key} (PID {pid})...")
            _kill_pid(pid)
    if PID_FILE.is_file():
        try:
            PID_FILE.unlink()
        except OSError:
            pass
    print("Stopped.")


def start() -> None:
    stop()

    if not (ROOT / "web_server.py").is_file():
        print("Error: web_server.py not found at project root.", file=sys.stderr)
        sys.exit(1)

    node_modules = ROOT / "frontend" / "node_modules"
    if not node_modules.is_dir():
        print("frontend/node_modules not found. Run: cd frontend && npm install", file=sys.stderr)
        sys.exit(1)

    if not MODELS_ROOT_DIR.is_dir() or not any(MODELS_ROOT_DIR.iterdir()):
        print("Error: converts/models 目录为空或不存在，请先下载至少一个转换器源码目录后再本地启动。", file=sys.stderr)
        print(f"  - {MODELS_ROOT_DIR}", file=sys.stderr)
        sys.exit(1)

    # 后端
    env = os.environ.copy()
    env.setdefault("JWT_SECRET", "dev-only-change-in-production")
    env["BACKEND_PORT"] = str(BACKEND_PORT)
    env["FRONTEND_ORIGIN"] = f"http://127.0.0.1:{FRONTEND_PORT}"

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    backend_log = RUN_DIR / "backend.log"
    frontend_log = RUN_DIR / "frontend.log"
    _be_out = open(backend_log, "a", encoding="utf-8", buffering=1)
    print(f"Starting backend on port {BACKEND_PORT} (log: {backend_log})...")
    if _is_windows():
        be = subprocess.Popen(
            [sys.executable, str(ROOT / "web_server.py")],
            cwd=str(ROOT),
            env=env,
            stdout=_be_out,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
        )
    else:
        be = subprocess.Popen(
            [sys.executable, str(ROOT / "web_server.py")],
            cwd=str(ROOT),
            env=env,
            stdout=_be_out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    # 前端：通过 node 直接跑 vite，避免 npx 子进程难以跟踪
    vite_bin = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite_bin.is_file():
        print("vite not found in frontend/node_modules.", file=sys.stderr)
        _kill_pid(be.pid)
        sys.exit(1)

    node_exe = shutil_which("node")
    if not node_exe:
        print("node not found in PATH. Install Node.js LTS.", file=sys.stderr)
        _kill_pid(be.pid)
        sys.exit(1)

    fe_env = os.environ.copy()
    fe_env["VITE_DEV_PORT"] = str(FRONTEND_PORT)
    fe_env["VITE_PROXY_TARGET"] = f"http://127.0.0.1:{BACKEND_PORT}"

    _fe_out = open(frontend_log, "a", encoding="utf-8", buffering=1)
    print(f"Starting frontend (Vite) on port {FRONTEND_PORT} (log: {frontend_log})...")
    if _is_windows():
        fe = subprocess.Popen(
            [node_exe, str(vite_bin), "--host", "0.0.0.0", "--port", str(FRONTEND_PORT)],
            cwd=str(ROOT / "frontend"),
            env=fe_env,
            stdout=_fe_out,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
        )
    else:
        fe = subprocess.Popen(
            [node_exe, str(vite_bin), "--host", "0.0.0.0", "--port", str(FRONTEND_PORT)],
            cwd=str(ROOT / "frontend"),
            env=fe_env,
            stdout=_fe_out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    _write_pids(be.pid, fe.pid)
    print("-" * 50)
    print(f"Backend API:  http://127.0.0.1:{BACKEND_PORT}/  （根路径为 JSON；页面请用下面 Frontend UI）")
    print(f"API docs:     http://127.0.0.1:{BACKEND_PORT}/api/docs")
    print(f"Frontend UI:  http://127.0.0.1:{FRONTEND_PORT}/  （浏览器请打开此地址）")
    print(f"默认解析输出: {ROOT / 'out'}（可用环境变量 OUTPUT_DIR 或系统设置覆盖）")
    print(
        f"模型路径: {os.environ.get('MODEL_PATH', str(ROOT / 'weights' / 'logics-parsing-v2'))}"
        "（可通过 MODEL_PATH 环境变量或系统设置修改）"
    )
    print("PID file:", PID_FILE)
    print("Stop with: python run_dev.py stop")


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description="DocuLogic local dev: backend + Vite frontend")
    ap.add_argument("action", choices=["start", "stop"])
    args = ap.parse_args()
    if args.action == "stop":
        stop()
    else:
        start()


if __name__ == "__main__":
    main()

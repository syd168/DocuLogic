"""项目根目录与默认路径。

本地开发：默认模型快照目录为 ``weights/logics-parsing-v2``。
Docker：``docker-compose`` 将宿主机 ``MODEL_DIR`` 挂载为容器内 ``/app/weights/``，
环境变量 ``MODEL_PATH`` 默认指向 ``/app/weights/logics-parsing-v2``（须含 ``config.json`` 等快照文件）。
解析产出默认在项目根 ``out/``。
"""
from __future__ import annotations

from pathlib import Path

# web/app -> web -> 仓库根
WEB_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = WEB_ROOT.parent

# 当前推荐目录
DEFAULT_MODEL_WEIGHTS_DIR = PROJECT_ROOT / "weights" / "logics-parsing-v2"

# 多用户解析任务输出（可通过系统设置或环境变量 OUTPUT_DIR 覆盖）
DEFAULT_PARSE_OUTPUT_DIR = PROJECT_ROOT / "out"

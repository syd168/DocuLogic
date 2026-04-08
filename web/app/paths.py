"""项目根目录与默认路径（推理权重在 logics-parsingv2/，解析产出默认在项目根 out/）。"""
from __future__ import annotations

from pathlib import Path

# web/app -> web -> 仓库根
WEB_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = WEB_ROOT.parent

# 与 logics-parsingv2 目录布局一致（不移动该目录内文件时，权重放于此）
DEFAULT_MODEL_WEIGHTS_DIR = PROJECT_ROOT / "logics-parsingv2" / "weights" / "Logics-Parsing-v2"

# 多用户解析任务输出（可通过系统设置或环境变量 OUTPUT_DIR 覆盖）
DEFAULT_PARSE_OUTPUT_DIR = PROJECT_ROOT / "out"

#!/usr/bin/env python3
"""
DocuLogic Web Server：仅启动 FastAPI（无 Vite 前端）。
完整开发环境（后端 + 前端）请用项目根 ./start.sh 或 python3 run_dev.py start。
"""

import os
import sys
from pathlib import Path

# 确保web目录在Python路径中
web_dir = Path(__file__).parent / "web"
sys.path.insert(0, str(web_dir))

# 默认模型路径优先级：
# 1. 项目根目录下的 weights/logics-parsing-v2（当前推荐）
# 2. 项目根目录下的 weights/logics-parsingv2（兼容旧约定）
# 3. 项目根目录下的 weights/（兼容旧约定）
# 4. 环境变量 MODEL_PATH（最高优先级，会覆盖以上默认值）
_root = Path(__file__).resolve().parent

# 首先尝试当前推荐目录：weights/logics-parsing-v2
model_path_current = _root / "weights" / "logics-parsing-v2"
if model_path_current.is_dir() and (model_path_current / "config.json").exists():
    os.environ.setdefault("MODEL_PATH", str(model_path_current.resolve()))
    print(f"✓ 检测到模型目录: {model_path_current.resolve()}")
else:
    # 兼容：旧约定放在 weights/logics-parsingv2
    model_path_v2 = _root / "weights" / "logics-parsingv2"
    # 兼容：旧约定直接放在 weights/
    model_path_flat = _root / "weights"
    if model_path_v2.is_dir() and (model_path_v2 / "config.json").exists():
        os.environ.setdefault("MODEL_PATH", str(model_path_v2.resolve()))
        print(f"✓ 检测到模型目录（兼容旧约定）: {model_path_v2.resolve()}")
    elif model_path_flat.is_dir() and (model_path_flat / "config.json").exists():
        os.environ.setdefault("MODEL_PATH", str(model_path_flat.resolve()))
        print(f"✓ 检测到模型目录（兼容旧约定）: {model_path_flat.resolve()}")
    else:
        print(f"⚠ Warning: 未找到模型目录")
        print(f"   期望位置: {model_path_current} 或 {model_path_v2} 或 {model_path_flat}")
        print(f"   解决方案:")
        print(f"   1. 将模型文件放到: {model_path_current}")
        print(f"   2. 或设置环境变量: export MODEL_PATH=/path/to/model")
        print(f"   3. 或在后台系统设置中配置模型路径")

# 导入并运行 FastAPI（sys.path 已包含 web/，包名为 app）
from app.main import app

if __name__ == "__main__":
    import uvicorn
    
    if not os.environ.get("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "dev-only-change-in-production"
        print("Warning: JWT_SECRET 未设置，已使用开发默认值，生产环境务必配置。")

    print("Starting DocuLogic Platform...")
    print(f"Model path: {os.environ.get('MODEL_PATH', 'Not set')}")
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    fe_port = os.environ.get("FRONTEND_PORT", "5173")
    print(f"API 根路径: http://127.0.0.1:{port}/  （仅 JSON；带界面请用前端端口 {fe_port}）")
    print(f"API 文档: http://127.0.0.1:{port}/api/docs")
    print(f"前端（Vue）请单独启动: http://127.0.0.1:{fe_port}/")
    print("-" * 50)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
    )
#!/usr/bin/env python3
"""
DocuLogic Web Server：仅启动 FastAPI（无 Vite 前端）。
完整开发环境（后端 + 前端）请用项目根 ./start.sh 或 python run_dev.py start。
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件（如果存在）


# 确保web目录在Python路径中
web_dir = Path(__file__).parent / "web"
sys.path.insert(0, str(web_dir))

_root = Path(__file__).resolve().parent

# 保存 PID 文件到 .run 目录
run_dir = _root / ".run"
run_dir.mkdir(parents=True, exist_ok=True)
pid_file = run_dir / ".backend.pid"
with open(pid_file, 'w') as f:
    f.write(str(os.getpid()))

# ========== 自动发现模式说明 ==========
# 📌 新方式：采用插件自动发现机制
# 系统启动时会自动扫描 converts/plugins/ 目录并加载所有可用文档解析器
# 同时自动发现模型文件位置（优先级：环境变量 > 配置文件 > 约定目录）
# 
# 若需为特定文档解析器指定模型路径，设置环境变量：
#   MODEL_PATH_LOGICS_PARSING_V2=/path/to/logics-model# 
# 或在后台系统设置中配置各文档解析器的模型路径
# ========================================

print("Starting DocuLogic Platform...")
print("✓ 使用自动发现模式加载文档解析器插件和模型")
print()

# 导入并运行 FastAPI（sys.path 已包含 web/，包名为 app）
from app.main import app

# 初始化插件注册表（自动发现模式）
# 这会在应用启动时自动扫描 converts/plugins 目录并加载所有可用插件
try:
    from converts.middleware.registry import list_plugins
    plugins_dict = list_plugins()
    if plugins_dict:
        print(f"✓ 已加载文档解析器插件 ({len(plugins_dict)} 个):")
        for engine_id, class_name in sorted(plugins_dict.items()):
            print(f"   • {engine_id:25} ({class_name})")
    else:
        print("⚠ Warning: 未发现任何文档解析器插件")
except Exception as e:
    print(f"✗ 初始化插件注册表失败: {e}")

# 自动发现所有文档解析器的模型路径
try:
    from converts.middleware.model_discovery import discover_all_converter_models
    model_paths = discover_all_converter_models(_root)
    if not model_paths:
        print("⚠ Warning: 未发现任何文档解析器的模型文件")
        print("   如需使用文档解析功能，请先下载相应的模型文件")
except Exception as e:
    print(f"⚠ 自动发现模型路径时出错: {e}")

if __name__ == "__main__":
    import uvicorn
    
    if not os.environ.get("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "dev-only-change-in-production"
        print("Warning: JWT_SECRET 未设置，已使用开发默认值，生产环境务必配置。")

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
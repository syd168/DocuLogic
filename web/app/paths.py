"""项目根目录与路径工具（支持多转换器架构）。

## 架构说明

本项目采用插件化的多转换器架构，支持动态加载多个文档解析引擎。

### 模型路径查找优先级（从高到低）

1. **环境变量**: `MODEL_PATH_<ENGINE_ID>`（大写，`-` 转换为 `_`）
   - 示例: `MODEL_PATH_LOGICS_PARSING_V2=/custom/path`
2. **配置文件**: `converts/configs/<engine_id>.jsonc` 中的 `download.dest_dir`
3. **约定目录**: `weights/<engine_id>/` 或 `weights/<engine_id>-*`

### 已弃用的配置

- ❌ `MODEL_PATH`: 仅用于旧版单模型架构，不支持多转换器
- ✅ 改用: `MODEL_PATH_<ENGINE_ID>` 格式

### 路径常量说明

- `PROJECT_ROOT`: 项目根目录（通用工具，始终可用）
- `WEB_ROOT`: Web 应用根目录（通用工具，始终可用）
- `DEFAULT_PARSE_OUTPUT_DIR`: 默认解析输出目录（可通过系统设置覆盖）
- `get_default_model_weights_dir(engine_id)`: 动态获取指定转换器的默认模型路径（推荐）

详细配置规范请参考项目记忆：「转换器自动发现机制配置规范」
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ============================================================================
# 基础路径常量（通用工具，不依赖具体转换器）
# ============================================================================

# web/app -> web -> 仓库根
WEB_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = WEB_ROOT.parent

# 多用户解析任务输出（可通过系统设置或环境变量 OUTPUT_DIR 覆盖）
DEFAULT_PARSE_OUTPUT_DIR = PROJECT_ROOT / "out"


# ============================================================================
# 动态模型路径获取（支持多转换器架构）
# ============================================================================

def get_default_model_weights_dir(engine_id: str) -> Optional[Path]:
    """
    动态获取指定转换器的默认模型路径。
    
    按照以下优先级查找：
    1. 环境变量: MODEL_PATH_<ENGINE_ID>
    2. 配置文件: converts/configs/<engine_id>.jsonc 中的 download.dest_dir
    3. 约定目录: weights/<engine_id>/
    
    Args:
        engine_id: 转换器引擎 ID（如 "logics-parsing-v2"）
        
    Returns:
        模型路径的 Path 对象，如果未找到则返回 None
        
    Example:
        >>> path = get_default_model_weights_dir("logics-parsing-v2")
        >>> if path and path.exists():
        ...     print(f"模型路径: {path}")
    """
    # 标准化 engine_id（将 - 转换为 _ 用于环境变量名）
    env_var_name = f"MODEL_PATH_{engine_id.upper().replace('-', '_')}"
    
    # 优先级 1: 环境变量
    env_path = os.environ.get(env_var_name, "").strip()
    if env_path:
        return Path(env_path).resolve()
    
    # 优先级 2: 配置文件
    config_path = PROJECT_ROOT / "converts" / "configs" / f"{engine_id}.jsonc"
    if config_path.exists():
        try:
            import json
            import re
            
            raw = config_path.read_text(encoding="utf-8")
            # 移除注释（简单的 JSONC 处理）
            raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
            cleaned_lines = []
            for line in raw.splitlines():
                in_str = False
                escaped = False
                cut_at = None
                for i, ch in enumerate(line):
                    if escaped:
                        escaped = False
                        continue
                    if ch == "\\" and in_str:
                        escaped = True
                        continue
                    if ch == '"':
                        in_str = not in_str
                        continue
                    if not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                        cut_at = i
                        break
                cleaned_lines.append((line[:cut_at] if cut_at is not None else line).rstrip())
            
            data = json.loads("\n".join(cleaned_lines).strip() or "{}")
            if isinstance(data, dict):
                dl = data.get("download")
                if isinstance(dl, dict):
                    dest = str(dl.get("dest_dir") or "").strip()
                    if dest:
                        p = Path(dest)
                        if not p.is_absolute():
                            p = PROJECT_ROOT / p
                        return p.resolve()
        except Exception:
            pass  # 配置文件解析失败，继续尝试下一级
    
    # 优先级 3: 约定目录
    weights_dir = PROJECT_ROOT / "weights" / engine_id
    if weights_dir.is_dir():
        return weights_dir.resolve()
    
    # 尝试带版本号的目录（如 weights/logics-parsing-v2-1.0）
    weights_parent = PROJECT_ROOT / "weights"
    if weights_parent.is_dir():
        for item in weights_parent.iterdir():
            if item.is_dir() and item.name.startswith(f"{engine_id}-"):
                return item.resolve()
    
    return None


def list_available_models() -> dict[str, Path]:
    """
    列出所有可用的模型目录。
    
    Returns:
        {engine_id: model_path} 映射
        
    Example:
        >>> models = list_available_models()
        >>> for engine_id, path in models.items():
        ...     print(f"{engine_id}: {path}")
    """
    available = {}
    weights_dir = PROJECT_ROOT / "weights"
    
    if weights_dir.is_dir():
        for item in weights_dir.iterdir():
            if item.is_dir():
                # 跳过隐藏目录和临时文件
                if not item.name.startswith("."):
                    available[item.name] = item.resolve()
    
    return available

"""
文档解析器模型路径自动发现模块

根据已加载的文档解析器插件，自动发现其模型所在的目录。
支持：
1. 环境变量 MODEL_PATH_<ENGINE_ID>（最高优先级）
2. 文档解析器配置文件中的 download.dest_dir
3. 默认约定目录 weights/<engine_id> 或 weights/<engine_id>-*
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_jsonc(content: str) -> dict:
    """解析 JSONC 格式（支持注释和尾逗号）。"""
    # 移除块注释 /* ... */
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
    
    # 逐行处理，移除行注释
    cleaned_lines = []
    for ln in content.splitlines():
        in_str = False
        escaped = False
        cut = None
        for i, ch in enumerate(ln):
            if escaped:
                escaped = False
                continue
            if ch == "\\" and in_str:
                escaped = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str and ch == "/" and i + 1 < len(ln) and ln[i + 1] == "/":
                cut = i
                break
        cleaned_lines.append((ln[:cut] if cut is not None else ln).rstrip())
    
    try:
        return json.loads("\n".join(cleaned_lines).strip() or "{}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSONC 解析失败: {e}")
        return {}


def discover_converter_model_path(engine_id: str, project_root: Path) -> Optional[Path]:
    """
    自动发现指定文档解析器的模型路径。
    
    优先级：
    1. 环境变量 MODEL_PATH_<ENGINE_ID>（大写）
    2. 文档解析器配置文件的 download.dest_dir
    3. 约定目录：weights/<engine_id>
    
    Args:
        engine_id: 文档解析器引擎 ID
        project_root: 项目根目录
        
    Returns:
        模型路径，如果未找到返回 None
    """
    # 1. 检查环境变量
    env_var_name = f"MODEL_PATH_{engine_id.upper().replace('-', '_')}"
    env_path = os.environ.get(env_var_name, "").strip()
    if env_path:
        path = Path(env_path)
        if path.exists():
            logger.info(f"✓ 通过环境变量 {env_var_name} 发现模型: {path}")
            return path.resolve()
        else:
            logger.warning(f"环境变量 {env_var_name} 指定的路径不存在: {env_path}")
    
    # 2. 检查配置文件
    config_name = engine_id.replace("-", "_") + ".jsonc"
    config_path = project_root / "converts" / "configs" / config_name
    
    if config_path.exists():
        try:
            content = config_path.read_text(encoding="utf-8")
            data = _parse_jsonc(content)
            
            if isinstance(data, dict):
                download = data.get("download")
                if isinstance(download, dict):
                    dest_dir = str(download.get("dest_dir") or "").strip()
                    if dest_dir:
                        path = Path(dest_dir)
                        if not path.is_absolute():
                            path = project_root / path
                        
                        if path.exists():
                            logger.info(f"✓ 从配置文件发现模型 ({config_name}): {path}")
                            return path.resolve()
                        else:
                            logger.debug(f"配置文件中的模型路径不存在: {path}")
        except Exception as e:
            logger.debug(f"读取配置文件 {config_path} 失败: {e}")
    
    # 3. 约定目录（weights/<engine_id> 或 weights/<engine_id>-*）
    weights_dir = project_root / "weights"
    
    if weights_dir.exists():
        # 精确匹配
        exact_path = weights_dir / engine_id
        if exact_path.exists() and exact_path.is_dir():
            logger.info(f"✓ 发现约定目录模型: {exact_path}")
            return exact_path.resolve()
        
        # 前缀匹配（处理版本号等后缀）
        for item in sorted(weights_dir.iterdir()):
            if item.is_dir() and item.name.startswith(engine_id):
                logger.info(f"✓ 发现前缀匹配的模型目录: {item}")
                return item.resolve()
    
    logger.debug(f"未发现文档解析器 {engine_id} 的模型路径")
    return None


def discover_all_converter_models(project_root: Path) -> dict[str, Path]:
    """
    自动发现所有已注册文档解析器的模型路径。
    
    Args:
        project_root: 项目根目录
        
    Returns:
        {engine_id: model_path} 映射
    """
    from converts.middleware.registry import get_plugins
    
    results = {}
    
    try:
        plugins = get_plugins()
        logger.info(f"开始扫描 {len(plugins)} 个文档解析器的模型路径...")
        
        for engine_id in sorted(plugins.keys()):
            model_path = discover_converter_model_path(engine_id, project_root)
            if model_path:
                results[engine_id] = model_path
    except Exception as e:
        logger.error(f"扫描文档解析器模型路径失败: {e}")
    
    if results:
        logger.info(f"✓ 共发现 {len(results)} 个文档解析器的模型:")
        for engine_id, path in sorted(results.items()):
            logger.info(f"   • {engine_id:25} → {path}")
    
    return results

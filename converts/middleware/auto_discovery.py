"""
文档解析器插件自动发现与加载模块

自动扫描 converts/plugins 目录，动态加载符合规范的插件：
- 每个插件应该是一个包含 __init__.py 的子目录
- 插件包应导出一个或多个实现 ConverterPlugin 接口的类
- 推荐在 __init__.py 中通过 __all__ 导出插件类
"""
from __future__ import annotations

import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

from .plugin_base import ConverterPlugin

logger = logging.getLogger(__name__)

# 加载的插件缓存
_DISCOVERED_PLUGINS: dict[str, ConverterPlugin] = {}
_PLUGIN_ALIASES: dict[str, str] = {}
_DISCOVERY_INITIALIZED = False


def _is_plugin_class(obj: Any) -> bool:
    """检查对象是否是有效的插件类（不是协议本身）。"""
    if not inspect.isclass(obj):
        return False
    if obj is ConverterPlugin:
        return False
    
    # 检查是否符合 ConverterPlugin 接口
    required_attrs = {"engine_id", "run", "get_download_schema", "start_download", "get_download_status", "stop_download", "clear_downloaded_files"}
    obj_attrs = set(dir(obj))
    
    return required_attrs.issubset(obj_attrs)


def _try_load_plugin_from_module(module_name: str, module) -> list[tuple[str, ConverterPlugin]]:
    """从模块中提取所有插件实例。"""
    plugins: list[tuple[str, ConverterPlugin]] = []
    
    # 首先尝试从 __all__ 加载（推荐方式）
    if hasattr(module, "__all__"):
        for class_name in module.__all__:
            if not hasattr(module, class_name):
                logger.warning(f"模块 {module_name} 的 __all__ 中包含不存在的类: {class_name}")
                continue
            
            cls = getattr(module, class_name)
            if not _is_plugin_class(cls):
                logger.warning(f"模块 {module_name} 的类 {class_name} 不符合 ConverterPlugin 接口")
                continue
            
            try:
                instance = cls()
                if not hasattr(instance, "engine_id"):
                    logger.warning(f"插件 {class_name} 缺少 engine_id 属性")
                    continue
                
                engine_id = instance.engine_id
                plugins.append((engine_id, instance))
                logger.info(f"✓ 已加载插件: {engine_id} (来自 {module_name}.{class_name})")
            except Exception as e:
                logger.error(f"加载插件 {module_name}.{class_name} 时出错: {e}")
    else:
        # 降级：扫描模块中所有符合条件的类
        for name, obj in inspect.getmembers(module):
            if not name.startswith("_") and _is_plugin_class(obj):
                try:
                    instance = obj()
                    if hasattr(instance, "engine_id"):
                        engine_id = instance.engine_id
                        plugins.append((engine_id, instance))
                        logger.info(f"✓ 已加载插件: {engine_id} (来自 {module_name}.{name})")
                except Exception as e:
                    logger.error(f"加载插件 {module_name}.{name} 时出错: {e}")
    
    return plugins


def discover_plugins() -> dict[str, ConverterPlugin]:
    """
    自动发现并加载所有可用插件。
    
    扫描 converts/plugins 目录，动态导入所有包并加载符合接口的插件类。
    
    Returns:
        发现的插件字典 {engine_id: plugin_instance}
    """
    global _DISCOVERED_PLUGINS, _DISCOVERY_INITIALIZED
    
    if _DISCOVERY_INITIALIZED:
        return _DISCOVERED_PLUGINS
    
    plugins_dir = Path(__file__).resolve().parent.parent / "plugins"
    
    if not plugins_dir.exists():
        logger.warning(f"插件目录不存在: {plugins_dir}")
        _DISCOVERY_INITIALIZED = True
        return _DISCOVERED_PLUGINS
    
    logger.info(f"开始扫描插件目录: {plugins_dir}")
    
    # 确保 plugins 目录在 sys.path 中
    plugins_parent = str(plugins_dir.parent)
    if plugins_parent not in sys.path:
        sys.path.insert(0, plugins_parent)
    
    # 扫描子目录
    for item in sorted(plugins_dir.iterdir()):
        if not item.is_dir():
            continue
        
        # 跳过 __pycache__ 和以下划线开头的目录
        if item.name.startswith("_") or item.name == "__pycache__":
            continue
        
        # 检查是否是有效的包（包含 __init__.py）
        if not (item / "__init__.py").exists():
            logger.debug(f"跳过非包目录: {item.name}")
            continue
        
        plugin_package_name = f"converts.plugins.{item.name}"
        
        try:
            logger.debug(f"尝试加载插件包: {plugin_package_name}")
            module = importlib.import_module(plugin_package_name)
            
            # 从模块中提取插件
            found_plugins = _try_load_plugin_from_module(plugin_package_name, module)
            
            for engine_id, instance in found_plugins:
                if engine_id in _DISCOVERED_PLUGINS:
                    logger.warning(f"引擎 ID 重复: {engine_id}，将覆盖之前的注册")
                _DISCOVERED_PLUGINS[engine_id] = instance
        
        except ImportError as e:
            logger.error(f"无法导入插件包 {plugin_package_name}: {e}")
        except Exception as e:
            logger.error(f"加载插件包 {plugin_package_name} 时出错: {e}")
    
    logger.info(f"插件发现完成，共发现 {len(_DISCOVERED_PLUGINS)} 个插件: {', '.join(_DISCOVERED_PLUGINS.keys())}")
    _DISCOVERY_INITIALIZED = True
    return _DISCOVERED_PLUGINS


def register_plugin_aliases(aliases: dict[str, str]) -> None:
    """
    注册引擎 ID 别名。
    
    Args:
        aliases: {别名: engine_id} 映射
    """
    global _PLUGIN_ALIASES
    _PLUGIN_ALIASES.update(aliases)
    logger.debug(f"已注册 {len(aliases)} 个插件别名")


def normalize_engine_id(engine_id: str) -> str:
    """
    标准化引擎 ID。
    
    先检查别名，再返回原值。
    
    Args:
        engine_id: 原始引擎 ID
        
    Returns:
        标准化后的引擎 ID
    """
    key = str(engine_id or "").strip()
    if not key:
        return key
    return _PLUGIN_ALIASES.get(key, key)


def get_plugin(engine_id: str) -> ConverterPlugin:
    """
    获取指定的插件实例。
    
    Args:
        engine_id: 引擎 ID（支持别名）
        
    Returns:
        插件实例
        
    Raises:
        ValueError: 插件未注册
    """
    # 确保插件已发现
    if not _DISCOVERY_INITIALIZED:
        discover_plugins()
    
    normalized = normalize_engine_id(engine_id)
    plugin = _DISCOVERED_PLUGINS.get(normalized)
    if plugin is None:
        available = ", ".join(sorted(_DISCOVERED_PLUGINS.keys()))
        raise ValueError(f"未注册的文档解析器: {engine_id} (可用: {available})")
    return plugin


def list_plugins() -> dict[str, str]:
    """
    列出所有已发现的插件。
    
    Returns:
        {engine_id: plugin_class_name} 映射
    """
    if not _DISCOVERY_INITIALIZED:
        discover_plugins()
    
    return {
        engine_id: type(plugin).__name__
        for engine_id, plugin in _DISCOVERED_PLUGINS.items()
    }


def get_plugins() -> dict[str, ConverterPlugin]:
    """获取所有已发现的插件实例。"""
    if not _DISCOVERY_INITIALIZED:
        discover_plugins()
    
    return _DISCOVERED_PLUGINS.copy()

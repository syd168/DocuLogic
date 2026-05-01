"""
文档解析器插件注册表（自动发现模式）

支持两种使用模式：
1. 自动发现（推荐）：通过 discover_plugins() 自动扫描 converts/plugins 目录
2. 手动注册：通过 register_plugin() 手动注册解析器和别名

初始化时，如果 _AUTO_DISCOVERY_ENABLED=True，会自动发现所有解析器。
否则保持向后兼容，使用硬编码的解析器列表。
"""
from __future__ import annotations

import logging
import os

from converts.middleware.plugin_base import ConverterPlugin

logger = logging.getLogger(__name__)

# 自动发现开关（可通过环境变量 PLUGIN_AUTO_DISCOVERY 控制）
_AUTO_DISCOVERY_ENABLED = os.environ.get("PLUGIN_AUTO_DISCOVERY", "1").lower() in ("1", "true", "yes")

# 内部状态
_PLUGINS: dict[str, ConverterPlugin] = {}
_ENGINE_ID_ALIASES: dict[str, str] = {}
_INITIALIZED = False


def _init_plugins() -> None:
    """初始化解析器注册表（仅执行一次）。"""
    global _INITIALIZED, _PLUGINS, _ENGINE_ID_ALIASES
    
    if _INITIALIZED:
        return
    
    _INITIALIZED = True
    
    if _AUTO_DISCOVERY_ENABLED:
        logger.info("启用自动发现模式，正在扫描解析器...")
        try:
            from converts.middleware.auto_discovery import (
                discover_plugins,
                register_plugin_aliases,
            )
            
            # 自动发现插件
            discovered = discover_plugins()
            _PLUGINS.update(discovered)
            
            # 注册别名（向后兼容）
            default_aliases = {}
            register_plugin_aliases(default_aliases)
            
            logger.info(f"✓ 自动发现完成，共加载 {len(_PLUGINS)} 个解析器")
        except Exception as e:
            logger.error(f"自动发现解析器失败: {e}，降级为手动注册模式", exc_info=True)
            _enable_fallback_mode()
    else:
        logger.info("禁用自动发现，使用手动注册模式")
        _enable_fallback_mode()


def _enable_fallback_mode() -> None:
    """降级到手动注册模式（已废弃，仅保留空实现以防报错）。"""
    global _PLUGINS, _ENGINE_ID_ALIASES
    
    logger.warning("⚠️ 自动发现失败且后备模式已禁用。请检查 converts/plugins/ 目录。")
    # 不再硬编码加载任何插件，完全依赖自动发现
    pass


def normalize_engine_id(engine_id: str) -> str:
    """
    标准化引擎 ID（处理别名）。
    
    Args:
        engine_id: 原始引擎 ID
        
    Returns:
        标准化后的引擎 ID
    """
    _init_plugins()
    
    key = str(engine_id or "").strip()
    if not key:
        return key
    
    # 先检查别名
    if key in _ENGINE_ID_ALIASES:
        return _ENGINE_ID_ALIASES[key]
    
    # 检查自动发现的别名
    try:
        from converts.middleware.auto_discovery import normalize_engine_id as auto_normalize
        return auto_normalize(key)
    except Exception:
        pass
    
    return key


def get_plugin(engine_id: str) -> ConverterPlugin:
    """
    获取指定的解析器实例。
    
    Args:
        engine_id: 解析器 ID（支持别名）
        
    Returns:
        解析器实例
        
    Raises:
        ValueError: 解析器未注册
    """
    _init_plugins()
    
    normalized = normalize_engine_id(engine_id)
    plugin = _PLUGINS.get(normalized)
    
    if plugin is None:
        available = ", ".join(sorted(_PLUGINS.keys())) or "（无可用解析器）"
        raise ValueError(f"未注册的文档解析器: {engine_id} (可用: {available})")
    
    return plugin


def register_plugin(engine_id: str, plugin: ConverterPlugin, aliases: list[str] | None = None) -> None:
    """
    手动注册解析器（用于扩展或测试）。
    
    Args:
        engine_id: 解析器 ID
        plugin: 解析器实例
        aliases: 别名列表
    """
    _init_plugins()
    
    _PLUGINS[engine_id] = plugin
    logger.info(f"✓ 已注册解析器: {engine_id}")
    
    if aliases:
        for alias in aliases:
            _ENGINE_ID_ALIASES[alias] = engine_id
        logger.info(f"✓ 已注册 {len(aliases)} 个别名: {', '.join(aliases)}")


def list_plugins() -> dict[str, str]:
    """
    列出所有已注册的解析器。
    
    Returns:
        {parser_id: parser_class_name} 映射
    """
    _init_plugins()
    
    return {
        engine_id: type(plugin).__name__
        for engine_id, plugin in _PLUGINS.items()
    }


def get_plugins() -> dict[str, ConverterPlugin]:
    """获取所有已注册的解析器实例。"""
    _init_plugins()
    return _PLUGINS.copy()

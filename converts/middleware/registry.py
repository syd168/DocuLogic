from __future__ import annotations

from converts.middleware.plugin_base import ConverterPlugin
from converts.plugins.logics_parsing_v2.plugin import LogicsParsingV2Plugin
from converts.plugins.paddle_ocr_v3_5.plugin import PaddleOcrV35Plugin


_PLUGINS: dict[str, ConverterPlugin] = {
    LogicsParsingV2Plugin.engine_id: LogicsParsingV2Plugin(),
    PaddleOcrV35Plugin.engine_id: PaddleOcrV35Plugin(),
}

_ENGINE_ID_ALIASES: dict[str, str] = {
    "logics": LogicsParsingV2Plugin.engine_id,
    "logics-parsing": LogicsParsingV2Plugin.engine_id,
    "paddleocr": PaddleOcrV35Plugin.engine_id,
    "paddle-ocr": PaddleOcrV35Plugin.engine_id,
    "paddle_ocr": PaddleOcrV35Plugin.engine_id,
}


def normalize_engine_id(engine_id: str) -> str:
    key = str(engine_id or "").strip()
    if not key:
        return key
    return _ENGINE_ID_ALIASES.get(key, key)


def get_plugin(engine_id: str) -> ConverterPlugin:
    normalized = normalize_engine_id(engine_id)
    plugin = _PLUGINS.get(normalized)
    if plugin is None:
        raise ValueError(f"未注册的转换器: {engine_id}")
    return plugin

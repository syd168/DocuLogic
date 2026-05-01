from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import PROJECT_ROOT

CONVERTER_CONFIG_DIR = PROJECT_ROOT / "converts" / "configs"
_ENGINE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def _get_default_template_from_plugin(engine_id: str) -> str | None:
    """尝试从已注册的插件中获取默认配置模板。"""
    try:
        from converts.middleware.registry import get_plugin
        plugin = get_plugin(engine_id)
        if hasattr(plugin, 'default_config') and plugin.default_config:
            import json
            # 如果已经是对象化格式，直接返回；如果是旧格式，可能需要转换
            return json.dumps(plugin.default_config, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return None


def _validate_engine_id(engine_id: str) -> str:
    eid = str(engine_id or "").strip()
    if not eid:
        raise ValueError("engine_id 不能为空")
    if not _ENGINE_ID_RE.match(eid):
        raise ValueError("engine_id 非法")
    return eid


def _config_path(engine_id: str) -> Path:
    eid = _validate_engine_id(engine_id)
    return CONVERTER_CONFIG_DIR / f"{eid}.jsonc"


def _strip_jsonc_comments(text: str) -> str:
    # Remove /* ... */ first
    no_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out: list[str] = []
    for line in no_block.splitlines():
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
        out.append((line[:cut_at] if cut_at is not None else line).rstrip())
    return "\n".join(out)


def parse_jsonc(text: str) -> dict:
    raw = _strip_jsonc_comments(text).strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"配置文件不是合法 JSON/JSONC: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("文档解析器配置必须是 JSON 对象")
    return data


def ensure_converter_config(engine_id: str) -> Path:
    path = _config_path(engine_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # 优先从插件获取默认配置，其次使用通用模板
        default_text = _get_default_template_from_plugin(engine_id)
        if not default_text:
            default_text = "{\n  // custom parser config\n}\n"
        path.write_text(default_text, encoding="utf-8")
    return path


def read_converter_config_text(engine_id: str) -> str:
    path = ensure_converter_config(engine_id)
    return path.read_text(encoding="utf-8")


def read_converter_config(engine_id: str) -> dict:
    """读取配置并与插件默认配置合并，确保新增字段有默认值。"""
    file_data = parse_jsonc(read_converter_config_text(engine_id))
    
    # 获取插件定义的默认配置
    try:
        from converts.middleware.registry import get_plugin
        plugin = get_plugin(engine_id)
        default_data = getattr(plugin, 'default_config', {})
        
        if default_data and isinstance(default_data, dict):
            # 深度合并：文件配置优先，缺失项使用默认配置
            merged = _deep_merge(default_data, file_data)
            return merged
    except Exception:
        pass
        
    return file_data

def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 优先级更高。"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def write_converter_config_text(engine_id: str, content: str) -> Path:
    path = ensure_converter_config(engine_id)
    parse_jsonc(content)  # validate before saving
    path.write_text(content, encoding="utf-8")
    return path


def write_converter_config_data(engine_id: str, data: dict) -> Path:
    if not isinstance(data, dict):
        raise ValueError("文档解析器配置必须是对象")
    path = ensure_converter_config(engine_id)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    return path

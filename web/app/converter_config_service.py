from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import PROJECT_ROOT

CONVERTER_CONFIG_DIR = PROJECT_ROOT / "converts" / "configs"
_ENGINE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

DEFAULT_CONFIG_TEMPLATES: dict[str, str] = {
    "logics-parsing-v2": """{
  "_ui": {
    "order": [
      "prompt",
      "download"
    ],
    "labels": {
      "prompt": "提示词模板",
      "download": "模型下载配置"
    },
    "hints": {
      "prompt": "用于控制 Logics 解析输出风格（如 QwenVL HTML）。",
      "download": "下载按钮会按该配置执行。"
    }
  },
  // Logics-Parsing-v2 运行参数
  "prompt": "QwenVL HTML",
  // 下载配置（前端“下载模型文件”按钮读取这里）
  "download": {
    "mode": "snapshot",
    "dest_dir": "weights/logics-parsing-v2",
    "repos": {
      "huggingface": "Logics-MLLM/Logics-Parsing-v2",
      "modelscope": "Alibaba-DT/Logics-Parsing-v2"
    }
  }
}
""",
    "paddle-ocr-v3.5": """{
  // api | local
  "runtime_mode": "api",
  // PaddleOCR API endpoint, must end with /layout-parsing
  "api_url": "https://your-service.example.com/layout-parsing",
  // PaddleOCR access token
  "access_token": "replace-with-token",
  // HTTP timeout in seconds
  "timeout_seconds": 600,
  // Pipeline switches
  "use_doc_unwarping": false,
  "use_doc_orientation_classify": false,
  "visualize": false,
  // Additional options forwarded to parse_document(**extra_options).
  // Check PaddleOCR docs for parse_document/API optional fields.
  "extra_options": {},
  // local mode command (optional): placeholders {input_path} {output_dir} {job_id}
  "local_command": "",
  // local mode markdown output path template (optional)
  "local_output_markdown": "{output_dir}/{job_id}.md",
  "local_output_raw": "{output_dir}/{job_id}_raw.md"
}
""",
}


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
        raise ValueError("转换器配置必须是 JSON 对象")
    return data


def ensure_converter_config(engine_id: str) -> Path:
    path = _config_path(engine_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        default_text = DEFAULT_CONFIG_TEMPLATES.get(engine_id, "{\n  // custom converter config\n}\n")
        path.write_text(default_text, encoding="utf-8")
    return path


def read_converter_config_text(engine_id: str) -> str:
    path = ensure_converter_config(engine_id)
    return path.read_text(encoding="utf-8")


def read_converter_config(engine_id: str) -> dict:
    return parse_jsonc(read_converter_config_text(engine_id))


def write_converter_config_text(engine_id: str, content: str) -> Path:
    path = ensure_converter_config(engine_id)
    parse_jsonc(content)  # validate before saving
    path.write_text(content, encoding="utf-8")
    return path


def write_converter_config_data(engine_id: str, data: dict) -> Path:
    if not isinstance(data, dict):
        raise ValueError("转换器配置必须是对象")
    path = ensure_converter_config(engine_id)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    return path

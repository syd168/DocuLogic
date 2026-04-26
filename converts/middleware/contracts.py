from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict


ProgressCallback = Callable[[str, int], None]


@dataclass
class ConversionJobInput:
    """统一转换任务输入（最小实现版本）。"""

    engine_id: str
    payload: Dict[str, Any]
    progress_callback: ProgressCallback | None = None
    engine_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionJobResult:
    """统一转换任务输出（透传现有返回结构）。"""

    data: Dict[str, Any]


@dataclass
class ConverterDownloadRequest:
    """统一下载任务输入。"""

    engine_id: str
    source: str = "modelscope"
    repo_id: str = ""
    target_dir: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConverterDownloadStatus:
    """统一下载任务状态。"""

    task_id: str
    engine_id: str
    is_downloading: bool
    success: bool
    error: str | None = None
    message: str = ""
    dest: str = ""
    repo: str = ""
    source: str = ""


@dataclass
class ConverterDownloadSchema:
    """插件可下载能力描述。"""

    engine_id: str
    supports_download: bool
    default_source: str = "modelscope"
    allowed_sources: list[str] = field(default_factory=lambda: ["modelscope", "huggingface"])
    default_repo_by_source: Dict[str, str] = field(default_factory=dict)
    default_target_dir: str = ""
    supports_repo_override: bool = True
    supports_target_override: bool = True
    notes: str = ""

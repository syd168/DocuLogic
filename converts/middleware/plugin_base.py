from __future__ import annotations

from typing import Protocol

from .contracts import (
    ConversionJobInput,
    ConversionJobResult,
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)


class ConverterPlugin(Protocol):
    """转换器插件最小接口。"""

    engine_id: str

    def run(self, job_input: ConversionJobInput) -> ConversionJobResult:
        ...

    def get_download_schema(self) -> ConverterDownloadSchema:
        ...

    def start_download(self, request: ConverterDownloadRequest) -> ConverterDownloadStatus:
        ...

    def get_download_status(self, task_id: str) -> ConverterDownloadStatus:
        ...

    def stop_download(self, task_id: str) -> ConverterDownloadStatus:
        ...

    def clear_downloaded_files(self, target_dir: str = "") -> dict:
        ...

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
    """文档解析器插件最小接口。"""

    engine_id: str
    
    # 默认配置模板（可选，用于初始化配置文件）
    default_config: dict | None

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

    def get_config_schema(self) -> dict:
        """获取配置界面的渲染 Schema（可选）。
        
        默认返回空对象，子类可选择性实现。
        """
        return {}

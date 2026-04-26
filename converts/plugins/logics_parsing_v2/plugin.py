from __future__ import annotations

from converts.middleware.contracts import (
    ConversionJobInput,
    ConversionJobResult,
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)
from converts.plugins.download_runner import PluginDownloadRunner


class LogicsParsingV2Plugin:
    engine_id = "logics-parsing-v2"
    _downloader = PluginDownloadRunner(
        engine_id=engine_id,
        default_source="modelscope",
        allowed_sources=["huggingface", "modelscope"],
        repos={
            "huggingface": "Logics-MLLM/Logics-Parsing-v2",
            "modelscope": "Alibaba-DT/Logics-Parsing-v2",
        },
        target_dir="weights/logics-parsing-v2",
        notes="Logics 默认下载并保存到 weights/logics-parsing-v2",
    )

    def run(self, job_input: ConversionJobInput) -> ConversionJobResult:
        legacy_process_fn = job_input.engine_context.get("legacy_process_fn")
        if legacy_process_fn is None:
            raise ValueError("logics 插件缺少 legacy_process_fn")

        payload = job_input.payload
        result = legacy_process_fn(
            input_path=payload["input_path"],
            output_dir=payload["output_dir"],
            job_id=payload["job_id"],
            progress_callback=job_input.progress_callback,
            prompt=payload["prompt"],
            cancel_event=payload["cancel_event"],
            max_pdf_pages=payload["max_pdf_pages"],
            show_page_numbers=payload["show_page_numbers"],
            image_output_mode=payload["image_output_mode"],
        )
        return ConversionJobResult(data=result)

    def get_download_schema(self) -> ConverterDownloadSchema:
        return self._downloader.get_schema()

    def start_download(self, request: ConverterDownloadRequest) -> ConverterDownloadStatus:
        return self._downloader.start(request)

    def get_download_status(self, task_id: str) -> ConverterDownloadStatus:
        return self._downloader.status(task_id)

    def stop_download(self, task_id: str) -> ConverterDownloadStatus:
        return self._downloader.stop(task_id)

    def clear_downloaded_files(self, target_dir: str = "") -> dict:
        return self._downloader.clear_files(target_dir)

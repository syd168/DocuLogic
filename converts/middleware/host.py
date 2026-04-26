from __future__ import annotations

import logging

from converts.middleware.contracts import (
    ConversionJobInput,
    ConversionJobResult,
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)
from converts.middleware.registry import get_plugin


def run_conversion_job(job_input: ConversionJobInput) -> ConversionJobResult:
    plugin = get_plugin(job_input.engine_id)
    logger = logging.getLogger("app")
    job_id = str(job_input.payload.get("job_id", "")).strip()
    if job_id:
        logger.info(
            "中间件路由: job_id=%s engine_id=%s plugin=%s",
            job_id,
            job_input.engine_id,
            plugin.__class__.__name__,
        )
    else:
        logger.info(
            "中间件路由: engine_id=%s plugin=%s",
            job_input.engine_id,
            plugin.__class__.__name__,
        )
    return plugin.run(job_input)


def get_download_schema(engine_id: str) -> ConverterDownloadSchema:
    plugin = get_plugin(engine_id)
    return plugin.get_download_schema()


def start_download(request: ConverterDownloadRequest) -> ConverterDownloadStatus:
    plugin = get_plugin(request.engine_id)
    return plugin.start_download(request)


def get_download_status(engine_id: str, task_id: str) -> ConverterDownloadStatus:
    plugin = get_plugin(engine_id)
    return plugin.get_download_status(task_id)


def stop_download(engine_id: str, task_id: str) -> ConverterDownloadStatus:
    plugin = get_plugin(engine_id)
    return plugin.stop_download(task_id)


def clear_downloaded_files(engine_id: str, target_dir: str = "") -> dict:
    plugin = get_plugin(engine_id)
    return plugin.clear_downloaded_files(target_dir)

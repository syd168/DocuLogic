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
    
    # UI 元数据（用于前端动态渲染）
    ui_meta = {
        "status_label": "解析器状态：",
        "path_label": "解析器目录：",
        "model_path_label": "解析器的模型下载保存路径",
        "model_path_placeholder": "相对项目根目录，例如 weights/…",
        "excluded_config_keys": [],  # 不需要排除的字段
    }
    
    # 默认配置模板
    default_config = {
        "prompt": "QwenVL HTML",
        "output_format": "markdown",
        "temperature": 0.1,
        "max_pdf_pages": 50,
        "download": {
            "mode": "snapshot",
            "dest_dir": "weights/logics-parsing-v2",
            "repos": {
                "huggingface": "Logics-MLLM/Logics-Parsing-v2",
                "modelscope": "Alibaba-DT/Logics-Parsing-v2"
            }
        }
    }
    _downloader = PluginDownloadRunner(
        engine_id=engine_id,
        default_source="modelscope",
        allowed_sources=["huggingface", "modelscope"],
        repos={
            "huggingface": "Logics-MLLM/Logics-Parsing-v2",
            "modelscope": "Alibaba-DT/Logics-Parsing-v2",
        },
        target_dir="weights/logics-parsing-v2",  # 仅作为默认值，实际会被自动推导覆盖
        notes=f"模型将自动下载到 weights/logics-parsing-v2",
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

    def get_config_schema(self) -> dict:
        """定义前端配置界面的渲染规则（UI 与数据分离）。"""
        return {
            "fields": [
                {
                    "key": "output_format",
                    "label": "输出格式",
                    "type": "select",
                    "options": [
                        {"label": "Markdown (推荐)", "value": "markdown"},
                        {"label": "HTML", "value": "html"},
                        {"label": "JSON (结构化)", "value": "json"}
                    ],
                    "hint": "选择解析结果的最终输出格式。"
                },
                {
                    "key": "prompt",
                    "label": "提示词模板",
                    "type": "textarea",
                    "hint": "用于控制 Logics 解析输出风格（如 QwenVL HTML）。",
                    "placeholder": "请输入提示词..."
                },
                {
                    "key": "temperature",
                    "label": "温度系数 (Temperature)",
                    "type": "number",
                    "hint": "控制输出的随机性，解析文档建议设为 0.1 - 0.3。"
                },
                {
                    "key": "max_pdf_pages",
                    "label": "最大处理页数",
                    "type": "number",
                    "hint": "单次任务最多处理的 PDF 页数，防止显存溢出。"
                },
                {
                    "key": "download",
                    "label": "模型下载配置",
                    "type": "object",
                    "hint": "下载按钮会按该配置执行。",
                    "children": [
                        {"key": "dest_dir", "label": "目标路径", "type": "text"},
                        {"key": "repos", "label": "仓库地址", "type": "json"}
                    ]
                }
            ]
        }

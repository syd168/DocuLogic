from __future__ import annotations

import importlib.util
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable

from converts.middleware.contracts import (
    ConversionJobInput,
    ConversionJobResult,
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)
from converts.plugins.download_runner import PluginDownloadRunner


_parse_document_fn: Callable[..., dict[str, Any]] | None = None


def _load_parse_document_callable() -> Callable[..., dict[str, Any]]:
    global _parse_document_fn
    if _parse_document_fn is not None:
        return _parse_document_fn

    repo_root = Path(__file__).resolve().parents[3]
    lib_path = (
        repo_root
        / "converts"
        / "models"
        / "PaddleOCR-3.5.0"
        / "skills"
        / "paddleocr-doc-parsing"
        / "scripts"
        / "lib.py"
    )
    if not lib_path.exists():
        raise FileNotFoundError(f"PaddleOCR 解析库不存在: {lib_path}")

    spec = importlib.util.spec_from_file_location("paddleocr_doc_parsing_lib", str(lib_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 PaddleOCR 解析库: {lib_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "parse_document", None)
    if fn is None or not callable(fn):
        raise RuntimeError("PaddleOCR 解析库缺少 parse_document 可调用入口")
    _parse_document_fn = fn
    return fn


class PaddleOcrV35Plugin:
    engine_id = "paddle-ocr-v3.5"
    _downloader = PluginDownloadRunner(
        engine_id=engine_id,
        default_source="huggingface",
        allowed_sources=["huggingface", "modelscope"],
        repos={
            "huggingface": "PaddlePaddle/PaddleOCR-VL-0.9B",
            "modelscope": "PaddlePaddle/PaddleOCR-VL-0.9B",
        },
        target_dir="weights/paddle-ocr-v3.5/PaddleOCR-VL-0.9B",
        notes="PaddleOCR 模型默认保存在 weights/paddle-ocr-v3.5/PaddleOCR-VL-0.9B",
        fallback_source={"modelscope": "huggingface"},
    )

    def run(self, job_input: ConversionJobInput) -> ConversionJobResult:
        payload = job_input.payload
        input_path = str(payload["input_path"])
        output_dir = str(payload["output_dir"])
        job_id = str(payload["job_id"])
        cancel_event = payload.get("cancel_event")
        progress_callback = job_input.progress_callback

        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("已停止：尚未生成任何内容")

        if progress_callback:
            progress_callback("PaddleOCR 正在准备解析...", 10)

        parse_document = _load_parse_document_callable()
        converter_config = payload.get("converter_runtime_config") or {}
        runtime_mode = str(converter_config.get("runtime_mode") or "api").strip().lower()

        if runtime_mode == "local":
            local_command = str(converter_config.get("local_command") or "").strip()
            if not local_command:
                raise ValueError("PaddleOCR 本地模式缺少 local_command 配置")
            rendered_cmd = local_command.format(
                input_path=input_path,
                output_dir=output_dir,
                job_id=job_id,
            )
            proc = subprocess.run(
                shlex.split(rendered_cmd),
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                raise RuntimeError(f"PaddleOCR 本地模式执行失败（exit={proc.returncode}）：{detail[:500]}")

            os.makedirs(output_dir, exist_ok=True)
            md_tpl = str(converter_config.get("local_output_markdown") or "{output_dir}/{job_id}.md")
            raw_tpl = str(converter_config.get("local_output_raw") or "{output_dir}/{job_id}_raw.md")
            output_md_path = md_tpl.format(output_dir=output_dir, job_id=job_id)
            output_raw_path = raw_tpl.format(output_dir=output_dir, job_id=job_id)
            text = ""
            if os.path.exists(output_md_path):
                text = Path(output_md_path).read_text(encoding="utf-8")
            elif proc.stdout:
                text = proc.stdout
                Path(output_md_path).write_text(text, encoding="utf-8")
            if not os.path.exists(output_raw_path):
                Path(output_raw_path).write_text(text, encoding="utf-8")

            return ConversionJobResult(
                data={
                    "raw_output": text,
                    "markdown_output": text,
                    "output_files": {
                        "raw": output_raw_path,
                        "markdown": output_md_path,
                    },
                    "user_stopped": False,
                    "partial": False,
                    "pages_parsed": 1,
                }
            )

        api_url = str(converter_config.get("api_url") or "").strip()
        access_token = str(converter_config.get("access_token") or "").strip()
        timeout_seconds = int(converter_config.get("timeout_seconds") or 600)
        use_doc_unwarping = bool(converter_config.get("use_doc_unwarping", False))
        use_doc_orientation_classify = bool(converter_config.get("use_doc_orientation_classify", False))
        visualize = bool(converter_config.get("visualize", False))

        if not api_url:
            raise ValueError("PaddleOCR 配置缺失：paddle_api_url")
        if not access_token:
            raise ValueError("PaddleOCR 配置缺失：paddle_access_token")

        os.environ["PADDLEOCR_DOC_PARSING_API_URL"] = api_url
        os.environ["PADDLEOCR_ACCESS_TOKEN"] = access_token
        os.environ["PADDLEOCR_DOC_PARSING_TIMEOUT"] = str(max(1, timeout_seconds))

        extra_options = converter_config.get("extra_options") or {}
        if not isinstance(extra_options, dict):
            raise ValueError("PaddleOCR 配置错误：extra_options 必须是对象")

        api_result = parse_document(
            file_path=input_path,
            useDocUnwarping=use_doc_unwarping,
            useDocOrientationClassify=use_doc_orientation_classify,
            visualize=visualize,
            **extra_options,
        )

        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("已停止：解析过程中用户请求停止")

        if not bool(api_result.get("ok")):
            err = api_result.get("error") or {}
            msg = str(err.get("message") or "PaddleOCR 解析失败")
            raise RuntimeError(msg)

        if progress_callback:
            progress_callback("PaddleOCR 正在整理输出...", 70)

        text = str(api_result.get("text") or "")
        pages = (((api_result.get("result") or {}).get("result") or {}).get("layoutParsingResults") or [])
        pages_parsed = len(pages) if isinstance(pages, list) and pages else 1

        os.makedirs(output_dir, exist_ok=True)
        output_raw_path = os.path.join(output_dir, f"{job_id}_raw.md")
        output_md_path = os.path.join(output_dir, f"{job_id}.md")
        with open(output_raw_path, "w", encoding="utf-8") as f:
            f.write(text)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(text)

        if progress_callback:
            progress_callback("处理完成！", 100)

        return ConversionJobResult(
            data={
                "raw_output": text,
                "markdown_output": text,
                "output_files": {
                    "raw": output_raw_path,
                    "markdown": output_md_path,
                },
                "user_stopped": False,
                "partial": False,
                "pages_parsed": int(max(1, pages_parsed)),
            }
        )

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

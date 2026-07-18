from __future__ import annotations

import logging
import threading
from pathlib import Path
from uuid import uuid4

from converts.middleware.contracts import (
    ConversionJobInput,
    ConversionJobResult,
    ConverterDownloadRequest,
    ConverterDownloadSchema,
    ConverterDownloadStatus,
)

_log = logging.getLogger(__name__)


def _require_marker():
    """延迟导入，保证未安装 marker-pdf 时插件仍可被发现。"""
    try:
        from marker.config.parser import ConfigParser  # noqa: F401
        from marker.converters.pdf import PdfConverter  # noqa: F401
        from marker.models import create_model_dict  # noqa: F401
        from marker.output import text_from_rendered  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "未安装可选依赖 Marker。\n"
            "安装：pip install -r requirements-marker.txt\n"
            "注意：Marker 代码为 GPL-3.0，模型权重为 OpenRAIL-M，启用即表示接受其许可条款。"
        ) from e


class MarkerPlugin:
    """Marker（marker-pdf）文档解析插件 — 可选依赖，默认不捆绑。"""

    engine_id = "marker"

    ui_meta = {
        "status_label": "解析器状态：",
        "path_label": "解析器说明：",
        "model_path_label": "Marker 模型缓存说明",
        "model_path_placeholder": "surya 等模型默认缓存到本机（如 ~/.cache），无需填写",
        "excluded_config_keys": [],
    }

    default_config = {
        "output_format": "markdown",
        "force_ocr": False,
        "use_llm": False,
        "disable_image_extraction": False,
        "max_pdf_pages": 50,
        "download": {
            "mode": "warmup",
            "dest_dir": "weights/marker",
            "notes": "点击下载将预热并缓存 surya/Marker 依赖模型（通常写入本机 cache）",
        },
    }

    def __init__(self) -> None:
        self._models = None
        self._models_lock = threading.Lock()
        self._dl_lock = threading.Lock()
        self._statuses: dict[str, ConverterDownloadStatus] = {}
        self._tasks: dict[str, dict] = {}

    def _get_artifact_dict(self):
        with self._models_lock:
            if self._models is None:
                _require_marker()
                from marker.models import create_model_dict

                _log.info("[marker] loading surya/marker models (may download on first run)")
                self._models = create_model_dict()
            return self._models

    def run(self, job_input: ConversionJobInput) -> ConversionJobResult:
        _require_marker()
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.output import text_from_rendered

        payload = job_input.payload
        input_path = Path(str(payload["input_path"]))
        output_dir = Path(str(payload["output_dir"]))
        job_id = str(payload.get("job_id") or "job")
        cancel_event = payload.get("cancel_event")
        progress_callback = job_input.progress_callback
        cfg = payload.get("converter_runtime_config") or {}
        if not isinstance(cfg, dict):
            cfg = {}

        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
            raise ValueError("已停止：用户取消任务")

        output_dir.mkdir(parents=True, exist_ok=True)
        if progress_callback:
            progress_callback("Marker：准备模型…", 5)

        output_format = str(cfg.get("output_format") or "markdown").strip().lower()
        if output_format not in ("markdown", "json", "html", "chunks"):
            output_format = "markdown"

        force_ocr = bool(cfg.get("force_ocr", False))
        use_llm = bool(cfg.get("use_llm", False))
        disable_image_extraction = bool(cfg.get("disable_image_extraction", False))

        max_pages = payload.get("max_pdf_pages")
        if max_pages is None:
            max_pages = cfg.get("max_pdf_pages")
        page_range = None
        try:
            n = int(max_pages) if max_pages is not None else 0
            if n > 0:
                page_range = f"0-{n - 1}"
        except (TypeError, ValueError):
            page_range = None

        cli_options: dict = {
            "output_format": output_format,
            "force_ocr": force_ocr,
            "use_llm": use_llm,
            "disable_image_extraction": disable_image_extraction,
        }
        if page_range:
            cli_options["page_range"] = page_range

        if progress_callback:
            progress_callback("Marker：开始解析文档…", 15)

        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
            raise ValueError("已停止：用户取消任务")

        config_parser = ConfigParser(cli_options)
        converter_kwargs = {
            "config": config_parser.generate_config_dict(),
            "artifact_dict": self._get_artifact_dict(),
            "processor_list": config_parser.get_processors(),
            "renderer": config_parser.get_renderer(),
        }
        llm_service = config_parser.get_llm_service() if use_llm else None
        if llm_service is not None:
            converter_kwargs["llm_service"] = llm_service

        converter = PdfConverter(**converter_kwargs)
        rendered = converter(str(input_path))

        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
            raise ValueError("已停止：用户取消任务")

        if progress_callback:
            progress_callback("Marker：写入结果…", 85)

        text, ext, images = text_from_rendered(rendered)
        # DocuLogic 下载接口约定使用 .mmd 作为 markdown 文件名
        if ext == "md":
            out_name = f"{job_id}.mmd"
            out_key = "markdown"
        else:
            out_name = f"{job_id}.{ext}"
            out_key = "markdown" if ext in ("md", "html") else "raw"

        out_path = output_dir / out_name
        out_path.write_text(text or "", encoding="utf-8")

        raw_path = output_dir / f"{job_id}_raw.mmd"
        if out_key == "markdown" and ext == "md":
            raw_path.write_text(text or "", encoding="utf-8")
        else:
            raw_path.write_text(text or "", encoding="utf-8")

        assets_dir = output_dir / "assets"
        image_output_mode = str(payload.get("image_output_mode") or "base64").lower()
        if images and image_output_mode != "none":
            assets_dir.mkdir(parents=True, exist_ok=True)
            for img_name, img in images.items():
                try:
                    if hasattr(img, "convert"):
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img.save(assets_dir / Path(str(img_name)).name)
                except Exception as e:
                    _log.warning("[marker] save image failed name=%s err=%s", img_name, e)

        # 可视化：无 bbox 图时用首张提取图或留空路径兼容前端
        vis_path = output_dir / f"{job_id}_vis.png"
        if not vis_path.exists() and images:
            try:
                first = next(iter(images.values()))
                if hasattr(first, "convert"):
                    if first.mode != "RGB":
                        first = first.convert("RGB")
                    first.save(vis_path)
            except Exception:
                pass

        pages_parsed = 0
        try:
            meta = getattr(rendered, "metadata", None) or {}
            if isinstance(meta, dict):
                pages_parsed = int(meta.get("page_count") or meta.get("pages") or 0)
        except Exception:
            pages_parsed = 0
        if pages_parsed <= 0 and page_range:
            try:
                pages_parsed = int(str(page_range).split("-")[-1]) + 1
            except Exception:
                pages_parsed = 1
        if pages_parsed <= 0:
            pages_parsed = 1

        if progress_callback:
            progress_callback("处理完成！", 100)

        output_files = {
            "visualization": str(vis_path) if vis_path.exists() else "",
            "raw": str(raw_path),
            "markdown": str(out_path),
        }

        return ConversionJobResult(
            data={
                "raw_output": text or "",
                "markdown_output": text or "",
                "output_files": output_files,
                "user_stopped": False,
                "partial": False,
                "pages_parsed": pages_parsed,
            }
        )

    def get_download_schema(self) -> ConverterDownloadSchema:
        return ConverterDownloadSchema(
            engine_id=self.engine_id,
            supports_download=True,
            default_source="huggingface",
            allowed_sources=["huggingface"],
            default_repo_by_source={},
            default_target_dir="weights/marker",
            supports_repo_override=False,
            supports_target_override=False,
            notes=(
                "可选引擎：需先 pip install -r requirements-marker.txt。"
                "「下载」会预热 surya/Marker 模型到本机缓存；首次解析也会自动下载。"
                "许可：代码 GPL-3.0，模型 OpenRAIL-M。"
            ),
        )

    def start_download(self, request: ConverterDownloadRequest) -> ConverterDownloadStatus:
        _require_marker()
        task_id = uuid4().hex
        status = ConverterDownloadStatus(
            task_id=task_id,
            engine_id=self.engine_id,
            is_downloading=True,
            success=False,
            message="正在预热 Marker/surya 模型（首次可能较久）…",
            source="huggingface",
            repo="surya/marker (auto cache)",
            dest="~/.cache (surya default)",
        )
        with self._dl_lock:
            self._statuses[task_id] = status
            self._tasks[task_id] = {"cancelled": False}

        def _worker() -> None:
            try:
                if self._tasks.get(task_id, {}).get("cancelled"):
                    raise RuntimeError("用户停止下载")
                self._get_artifact_dict()
                with self._dl_lock:
                    cur = self._statuses.get(task_id)
                    if cur:
                        self._statuses[task_id] = ConverterDownloadStatus(
                            **{
                                **cur.__dict__,
                                "is_downloading": False,
                                "success": True,
                                "message": "模型预热完成（已缓存，可开始解析）",
                            }
                        )
            except Exception as e:
                with self._dl_lock:
                    cur = self._statuses.get(task_id)
                    if cur:
                        self._statuses[task_id] = ConverterDownloadStatus(
                            **{
                                **cur.__dict__,
                                "is_downloading": False,
                                "success": False,
                                "error": str(e),
                                "message": f"预热失败: {str(e)[:300]}",
                            }
                        )

        threading.Thread(target=_worker, daemon=True).start()
        return status

    def get_download_status(self, task_id: str) -> ConverterDownloadStatus:
        with self._dl_lock:
            s = self._statuses.get(task_id)
            if s is None:
                raise RuntimeError(f"下载任务不存在: {task_id}")
            return s

    def stop_download(self, task_id: str) -> ConverterDownloadStatus:
        with self._dl_lock:
            s = self._statuses.get(task_id)
            if s is None:
                raise RuntimeError(f"下载任务不存在: {task_id}")
            task = self._tasks.get(task_id) or {}
            task["cancelled"] = True
            self._tasks[task_id] = task
            if not s.is_downloading:
                return s
            updated = ConverterDownloadStatus(
                **{
                    **s.__dict__,
                    "is_downloading": False,
                    "success": False,
                    "error": "用户停止下载",
                    "message": "下载已停止（若模型正在加载，进程可能仍短暂占用资源）",
                }
            )
            self._statuses[task_id] = updated
            return updated

    def clear_downloaded_files(self, target_dir: str = "") -> dict:
        # Marker/surya 使用全局 cache，禁止误删用户整个 ~/.cache
        return {
            "ok": True,
            "deleted": False,
            "path": target_dir or "weights/marker",
            "message": (
                "Marker 模型由 surya 缓存管理，不会自动删除本机 cache。"
                "如需清理请手动删除 HuggingFace/surya 缓存目录。"
            ),
        }

    def get_config_schema(self) -> dict:
        return {
            "fields": [
                {
                    "key": "output_format",
                    "label": "输出格式",
                    "type": "select",
                    "options": [
                        {"label": "Markdown (推荐)", "value": "markdown"},
                        {"label": "HTML", "value": "html"},
                        {"label": "JSON", "value": "json"},
                        {"label": "Chunks", "value": "chunks"},
                    ],
                    "hint": "Marker 渲染输出格式。",
                },
                {
                    "key": "force_ocr",
                    "label": "强制 OCR",
                    "type": "boolean",
                    "hint": "对整页强制 OCR（含行内数学场景更稳）。",
                },
                {
                    "key": "use_llm",
                    "label": "启用 LLM 增强",
                    "type": "boolean",
                    "hint": "需额外配置 LLM 后端；默认关闭。",
                },
                {
                    "key": "disable_image_extraction",
                    "label": "禁用图片提取",
                    "type": "boolean",
                    "hint": "不从文档中抽取图片资源。",
                },
                {
                    "key": "max_pdf_pages",
                    "label": "最大处理页数",
                    "type": "number",
                    "hint": "限制页数范围（0 起），防止超长文档占满显存。",
                },
                {
                    "key": "download",
                    "label": "模型下载配置",
                    "type": "object",
                    "hint": "Marker 使用自动缓存；点击「后台下载」仅做预热。",
                    "children": [
                        {"key": "dest_dir", "label": "说明路径", "type": "text"},
                    ],
                },
            ]
        }

from __future__ import annotations

import logging
import os
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


def resolve_marker_cache_dir() -> Path:
    """Marker/surya 模型目录，与 Logics 一样落在 weights/<engine_id>。

    优先级：
    1. 环境变量 MODEL_CACHE_DIR（surya Settings 官方字段）
    2. Docker: /app/weights/marker（与 MODEL_DIR 卷一致）
    3. 本地: <cwd>/weights/marker
    """
    env = (os.environ.get("MODEL_CACHE_DIR") or "").strip()
    if env:
        return Path(env).expanduser()
    if Path("/app/weights").is_dir():
        return Path("/app/weights/marker")
    return Path.cwd() / "weights" / "marker"


def ensure_marker_cache_env() -> Path:
    """在导入 surya/marker 之前设置 MODEL_CACHE_DIR，避免写入容器内 ~/.cache。"""
    dest = resolve_marker_cache_dir()
    dest.mkdir(parents=True, exist_ok=True)
    resolved = str(dest.resolve())
    # surya.settings.Settings 通过 pydantic 读取 MODEL_CACHE_DIR
    os.environ["MODEL_CACHE_DIR"] = resolved
    return dest


def _require_marker():
    """延迟导入，保证未安装 marker-pdf 时插件仍可被发现。"""
    ensure_marker_cache_env()
    try:
        from marker.config.parser import ConfigParser  # noqa: F401
        from marker.converters.pdf import PdfConverter  # noqa: F401
        from marker.models import create_model_dict  # noqa: F401
        from marker.output import text_from_rendered  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "未安装可选依赖 Marker（marker-pdf）。"
            "本地执行: pip install -r requirements-marker.txt；"
            "Docker 执行: ./docker/install-marker.sh "
            "或重新部署 ./docker/deploy.sh --with-marker。"
            f"详情: {e}"
        ) from e


class MarkerPlugin:
    """Marker（marker-pdf）文档解析插件 — 可选依赖，默认不捆绑。"""

    engine_id = "marker"

    ui_meta = {
        "status_label": "解析器状态：",
        "path_label": "解析器说明：",
        "model_path_label": "Marker 模型目录（与 Logics 同属 weights）",
        "model_path_placeholder": "weights/marker（Docker: /app/weights/marker）",
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
            "notes": "下载到 weights/marker（Docker 宿主机 MODEL_DIR/marker，与 Logics 同卷）",
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
                cache_dir = ensure_marker_cache_env()
                _require_marker()
                from marker.models import create_model_dict

                _log.info(
                    "[marker] loading surya/marker models from %s (may download on first run)",
                    cache_dir,
                )
                self._models = create_model_dict()
            return self._models

    def is_model_loaded(self) -> bool:
        with self._models_lock:
            return self._models is not None

    def ensure_runtime_models(self):
        """预热/确保 Marker 模型已加载（供管理后台「重新加载」调用）。"""
        return self._get_artifact_dict()

    def unload_runtime_models(self) -> str:
        """释放 Marker/surya 运行时模型，便于与其它引擎切换时腾出显存。"""
        with self._models_lock:
            if self._models is None:
                return "Marker 模型未加载，无需卸载"
            try:
                models = self._models
                self._models = None
                del models
            except Exception as e:
                self._models = None
                _log.warning("[marker] unload error: %s", e)
        try:
            import gc

            gc.collect()
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        _log.info("[marker] runtime models unloaded")
        return "已卸载 Marker/surya 运行时模型"

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
        images = images or {}
        image_output_mode = str(payload.get("image_output_mode") or "base64").lower()
        if image_output_mode not in ("base64", "separate", "none"):
            image_output_mode = "base64"

        # Marker 默认写 ![](_page_x.jpeg)，图片需落盘并按系统「图片输出模式」改写引用
        text = self._materialize_images(
            text or "",
            images,
            output_dir,
            image_output_mode,
        )

        # DocuLogic 下载接口约定使用 .mmd 作为 markdown 文件名
        if ext == "md":
            out_name = f"{job_id}.mmd"
        else:
            out_name = f"{job_id}.{ext}"

        out_path = output_dir / out_name
        out_path.write_text(text, encoding="utf-8")

        raw_path = output_dir / f"{job_id}_raw.mmd"
        raw_path.write_text(text, encoding="utf-8")

        # 可视化：无 bbox 图时用首张提取图；多图时再打 vis.zip（供「可视化」下载）
        vis_path = output_dir / f"{job_id}_vis.png"
        assets_dir = output_dir / "assets"
        if not vis_path.exists() and images:
            try:
                first = next(iter(images.values()))
                if hasattr(first, "convert"):
                    if first.mode != "RGB":
                        first = first.convert("RGB")
                    first.save(vis_path)
            except Exception:
                pass

        download_zip_path = None
        if image_output_mode == "separate":
            download_zip_path = self._pack_result_zip(
                output_dir=output_dir,
                job_id=job_id,
                markdown_path=out_path,
                raw_path=raw_path,
                vis_path=vis_path if vis_path.exists() else None,
                assets_dir=assets_dir if assets_dir.is_dir() else None,
            )
            # 多图时生成 _vis.zip，避免「可视化」链接只下到单张 png
            self._pack_vis_zip(output_dir, job_id, assets_dir if assets_dir.is_dir() else None)

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
        if download_zip_path:
            output_files["download_zip"] = download_zip_path

        return ConversionJobResult(
            data={
                "raw_output": text,
                "markdown_output": text,
                "output_files": output_files,
                "user_stopped": False,
                "partial": False,
                "pages_parsed": pages_parsed,
            }
        )

    @staticmethod
    def _materialize_images(
        text: str,
        images: dict,
        output_dir: Path,
        image_output_mode: str,
    ) -> str:
        """按 image_output_mode 保存图片并改写 markdown 中的图片引用。"""
        import base64
        import io
        import re

        if not images:
            return text

        assets_dir = output_dir / "assets"
        normalized: dict[str, object] = {}
        for raw_name, img in images.items():
            name = Path(str(raw_name)).name
            if name:
                normalized[name] = img

        if image_output_mode == "none":
            def _strip(m: re.Match) -> str:
                alt = m.group(1) or ""
                return f"\n\n*[图片已省略{('：' + alt) if alt else ''}]*\n\n"

            return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _strip, text)

        if image_output_mode == "base64":
            def _to_b64(m: re.Match) -> str:
                alt = m.group(1) or ""
                src = Path(m.group(2).strip()).name
                img = normalized.get(src)
                if img is None:
                    for k, v in normalized.items():
                        if k == src or Path(k).stem == Path(src).stem:
                            img = v
                            src = k
                            break
                if img is None or not hasattr(img, "save"):
                    return m.group(0)
                try:
                    buf = io.BytesIO()
                    pil = img
                    if hasattr(pil, "convert") and getattr(pil, "mode", "RGB") != "RGB":
                        pil = pil.convert("RGB")
                    fmt = "JPEG" if src.lower().endswith((".jpg", ".jpeg")) else "PNG"
                    pil.save(buf, format=fmt)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
                    return f"![{alt}](data:{mime};base64,{b64})"
                except Exception as e:
                    _log.warning("[marker] base64 embed failed src=%s err=%s", src, e)
                    return m.group(0)

            return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _to_b64, text)

        # separate：落盘 + 改写相对路径
        assets_dir.mkdir(parents=True, exist_ok=True)
        for name, img in normalized.items():
            try:
                if hasattr(img, "convert") and getattr(img, "mode", "RGB") != "RGB":
                    img = img.convert("RGB")
                if hasattr(img, "save"):
                    img.save(assets_dir / name)
            except Exception as e:
                _log.warning("[marker] save image failed name=%s err=%s", name, e)

        def _to_assets(m: re.Match) -> str:
            alt = m.group(1) or ""
            src = Path(m.group(2).strip()).name
            if (assets_dir / src).is_file():
                return f"![{alt}](./assets/{src})"
            return m.group(0)

        return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _to_assets, text)

    @staticmethod
    def _pack_result_zip(
        *,
        output_dir: Path,
        job_id: str,
        markdown_path: Path,
        raw_path: Path,
        vis_path: Path | None,
        assets_dir: Path | None,
    ) -> str | None:
        """打包完整结果为 {job_id}_result.zip（与 Logics / 下载 API 约定一致）。"""
        import zipfile

        zip_path = output_dir / f"{job_id}_result.zip"
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if markdown_path.is_file():
                    zf.write(markdown_path, arcname=markdown_path.name)
                if raw_path.is_file():
                    zf.write(raw_path, arcname=raw_path.name)
                if vis_path is not None and vis_path.is_file():
                    zf.write(vis_path, arcname=vis_path.name)
                if assets_dir is not None and assets_dir.is_dir():
                    for img_file in sorted(assets_dir.iterdir()):
                        if img_file.is_file():
                            zf.write(img_file, arcname=f"assets/{img_file.name}")
            return str(zip_path)
        except Exception as e:
            _log.warning("[marker] result zip failed: %s", e)
            return None

    @staticmethod
    def _pack_vis_zip(output_dir: Path, job_id: str, assets_dir: Path | None) -> None:
        """将 assets 中全部图片打成 _vis.zip，供 /download/.../visualization 使用。"""
        import zipfile

        if assets_dir is None or not assets_dir.is_dir():
            return
        files = [p for p in sorted(assets_dir.iterdir()) if p.is_file()]
        if len(files) < 2:
            return  # 单图仍用 _vis.png 即可
        vis_zip = output_dir / f"{job_id}_vis.zip"
        try:
            with zipfile.ZipFile(vis_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for img_file in files:
                    zf.write(img_file, arcname=img_file.name)
            _log.info("[marker] wrote vis zip with %s images: %s", len(files), vis_zip)
        except Exception as e:
            _log.warning("[marker] vis zip failed: %s", e)

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
                "模型下载到 weights/marker（Docker: /app/weights/marker，与 Logics 同 MODEL_DIR 卷）。"
                "许可：代码 GPL-3.0，模型 OpenRAIL-M。"
            ),
        )

    def start_download(self, request: ConverterDownloadRequest) -> ConverterDownloadStatus:
        cache_dir = ensure_marker_cache_env()
        _require_marker()
        task_id = uuid4().hex
        status = ConverterDownloadStatus(
            task_id=task_id,
            engine_id=self.engine_id,
            is_downloading=True,
            success=False,
            message=f"正在预热 Marker/surya 模型到 {cache_dir}（首次可能较久）…",
            source="huggingface",
            repo="surya/marker (datalab models)",
            dest=str(cache_dir),
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
        """清理 Marker 模型目录（仅限 weights/marker 或显式 MODEL_CACHE_DIR）。"""
        from shutil import rmtree

        cache = Path(target_dir).expanduser() if target_dir.strip() else resolve_marker_cache_dir()
        # 安全：只允许删除约定的 marker 权重目录，禁止误删 ~/.cache 根
        resolved = cache.resolve()
        allowed = {
            (Path.cwd() / "weights" / "marker").resolve(),
            Path("/app/weights/marker").resolve(),
        }
        env_dir = (os.environ.get("MODEL_CACHE_DIR") or "").strip()
        if env_dir:
            allowed.add(Path(env_dir).expanduser().resolve())
        if resolved not in allowed and "marker" not in resolved.as_posix().lower():
            return {
                "ok": False,
                "deleted": False,
                "path": str(resolved),
                "message": "拒绝删除：路径不在 Marker 权重目录约定内",
            }
        if not resolved.is_dir():
            return {
                "ok": True,
                "deleted": False,
                "path": str(resolved),
                "message": "目录不存在，无需清理",
            }
        try:
            for child in resolved.iterdir():
                if child.is_dir():
                    rmtree(child)
                else:
                    child.unlink(missing_ok=True)
            return {
                "ok": True,
                "deleted": True,
                "path": str(resolved),
                "message": "已清理 Marker 模型文件",
            }
        except Exception as e:
            return {
                "ok": False,
                "deleted": False,
                "path": str(resolved),
                "message": f"清理失败: {e}",
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

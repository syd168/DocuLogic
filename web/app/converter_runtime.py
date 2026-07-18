"""解析器运行时显存交接：切换默认引擎时卸载其它引擎占用的模型。"""
from __future__ import annotations

import gc
import logging
from typing import Any

_log = logging.getLogger(__name__)

LOGICS_ENGINE_ID = "logics-parsing-v2"


def unload_engines_except(keep_engine_id: str, *, wait_timeout: float = 120.0) -> dict[str, Any]:
    """卸载所有「非 keep」引擎的运行时模型，释放显存。

    Returns:
        {"keep": str, "actions": [{"engine_id", "unloaded", "detail"}, ...]}
    """
    keep = (keep_engine_id or "").strip()
    actions: list[dict[str, Any]] = []

    # 1) Logics：由 main 全局单例管理
    if keep != LOGICS_ENGINE_ID:
        from . import main as main_module

        ok = main_module.unload_model(wait_for_inference=True, wait_timeout=wait_timeout)
        if not ok:
            raise ValueError(
                "仍有 Logics 解析任务在使用模型，无法切换解析器。"
                "请等待任务完成或停止任务后再保存。"
            )
        actions.append(
            {
                "engine_id": LOGICS_ENGINE_ID,
                "unloaded": True,
                "detail": "已卸载 Logics 模型",
            }
        )
        _log.info("[converter-switch] unloaded logics-parsing-v2 (keep=%s)", keep)

    # 2) 其它插件：可选 unload_runtime_models()
    from converts.middleware.registry import get_plugins

    for eid, plugin in get_plugins().items():
        if eid == keep:
            continue
        if eid == LOGICS_ENGINE_ID:
            continue  # 已处理
        unload_fn = getattr(plugin, "unload_runtime_models", None)
        if not callable(unload_fn):
            continue
        try:
            detail = unload_fn() or f"已卸载 {eid}"
            actions.append({"engine_id": eid, "unloaded": True, "detail": str(detail)})
            _log.info("[converter-switch] unloaded plugin engine=%s keep=%s", eid, keep)
        except Exception as e:
            _log.warning("[converter-switch] unload %s failed: %s", eid, e)
            actions.append(
                {
                    "engine_id": eid,
                    "unloaded": False,
                    "detail": f"卸载失败: {e}",
                }
            )

    try:
        import torch

        if torch.cuda.is_available():
            gc.collect()
            torch.cuda.empty_cache()
    except Exception:
        pass

    return {"keep": keep, "actions": actions}


def is_engine_model_loaded(engine_id: str) -> bool:
    """当前引擎是否已有运行时模型在内存中。"""
    eid = (engine_id or "").strip()
    if not eid:
        return False
    if eid == LOGICS_ENGINE_ID:
        from . import main as main_module

        return main_module.get_inference_model() is not None
    try:
        from converts.middleware.registry import get_plugin

        plugin = get_plugin(eid)
        fn = getattr(plugin, "is_model_loaded", None)
        if callable(fn):
            return bool(fn())
    except Exception:
        return False
    return False


def unload_current_engine(engine_id: str, *, wait_timeout: float = 120.0) -> dict[str, Any]:
    """卸载指定引擎（用于管理后台「卸载模型」按钮）。"""
    eid = (engine_id or "").strip() or LOGICS_ENGINE_ID
    if eid == LOGICS_ENGINE_ID:
        from . import main as main_module

        ok = main_module.unload_model(wait_for_inference=True, wait_timeout=wait_timeout)
        if not ok:
            raise ValueError("仍有解析任务在使用模型，无法卸载。请等待任务完成后再试。")
        return {"engine_id": eid, "unloaded": True, "message": "✅ Logics 模型已卸载，显存已释放"}

    from converts.middleware.registry import get_plugin

    plugin = get_plugin(eid)
    unload_fn = getattr(plugin, "unload_runtime_models", None)
    if not callable(unload_fn):
        return {
            "engine_id": eid,
            "unloaded": False,
            "message": f"解析器 {eid} 无需/不支持运行时卸载",
        }
    detail = unload_fn()
    return {
        "engine_id": eid,
        "unloaded": True,
        "message": str(detail) if detail else f"✅ {eid} 运行时模型已卸载",
    }

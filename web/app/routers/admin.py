"""管理员：系统配置与模型下载。"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from converts.middleware.contracts import ConverterDownloadRequest
from converts.middleware.host import (
    clear_downloaded_files as plugin_clear_downloaded_files,
    get_download_schema as plugin_get_download_schema,
    get_download_status as plugin_get_download_status,
    stop_download as plugin_stop_download,
    start_download as plugin_start_download,
)
from ..auth_security import hash_password
from ..database import get_db
from ..deps import get_current_admin
from ..models import ParseJob, User
from ..settings_service import (
    get_app_settings_row,
    get_effective_pdf_max_pages_for_user,
    get_pdf_max_pages,
    settings_to_admin_dict,
    update_settings_from_body,
)
from ..converter_config_service import (
    read_converter_config,
    read_converter_config_text,
    write_converter_config_data,
    write_converter_config_text,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
_log = logging.getLogger(__name__)


def _is_cuda_oom(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "cuda" in s and "out of memory" in s


def _friendly_model_reload_message(exc: BaseException) -> str:
    if _is_cuda_oom(exc):
        return (
            "GPU 显存不足，无法加载模型。请先关闭其他占用显存的程序或推理任务，"
            "必要时重启本服务进程以释放显存，然后再试「重新加载模型」。"
            "若长期不足，可考虑换用显存更大的显卡或使用更小的模型权重。"
        )
    raw = str(exc)
    # 模型被删除后，底层可能抛出“未配置模型路径”（默认目录不存在时会返回空）。
    # 对管理端重载操作统一提示为模型文件缺失/损坏，更贴近用户可操作项。
    if "未配置模型路径" in raw or "模型目录不存在" in raw or "模型文件不完整" in raw:
        return "模型文件夹不存在、模型不存在或模型已损坏。请先下载/恢复模型文件后再重试。"
    msg = str(exc)
    if len(msg) > 500:
        return msg[:500] + "…"
    return msg


class AdminSettingsBody(BaseModel):
    registration_enabled: Optional[bool] = None
    captcha_login_enabled: Optional[bool] = None
    captcha_register_enabled: Optional[bool] = None
    captcha_forgot_enabled: Optional[bool] = None
    pdf_max_pages: Optional[int] = None
    output_dir: Optional[str] = None
    default_converter_id: Optional[str] = None
    email_mock: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: Optional[bool] = None
    register_email_enabled: Optional[bool] = None
    register_phone_enabled: Optional[bool] = None
    login_email_enabled: Optional[bool] = None
    login_phone_enabled: Optional[bool] = None
    forgot_email_enabled: Optional[bool] = None
    forgot_phone_enabled: Optional[bool] = None
    sms_mock: Optional[bool] = None
    sms_http_url: Optional[str] = None
    sms_http_secret: Optional[str] = None
    sms_http_headers_json: Optional[str] = None
    sms_http_body_template: Optional[str] = None
    show_page_numbers: Optional[bool] = None
    image_output_mode: Optional[str] = None  # base64 / separate / none
    stale_job_timeout_minutes: Optional[int] = None
    login_timeout_minutes: Optional[int] = None
    # 密码规则
    password_min_length: Optional[int] = None
    password_require_uppercase: Optional[bool] = None
    password_require_lowercase: Optional[bool] = None
    password_require_digit: Optional[bool] = None
    password_require_special: Optional[bool] = None
    # 文件上传限制
    max_upload_size_mb: Optional[int] = None
    allow_multi_file_upload: Optional[bool] = None


class ModelDownloadBody(BaseModel):
    source: Literal["huggingface", "modelscope"] = "modelscope"
    repo_id: Optional[str] = Field(None, description="留空则使用配置中的默认仓库 ID")
    engine_id: Optional[str] = Field(None, description="转换器 ID，留空使用默认转换器")
    target_dir: Optional[str] = Field(None, description="目标路径（可选，留空用插件默认）")


class ConverterConfigBody(BaseModel):
    content: str


class ConverterConfigDataBody(BaseModel):
    data: dict


class ConverterDownloadStartBody(BaseModel):
    source: Optional[Literal["huggingface", "modelscope"]] = None
    repo_id: Optional[str] = None
    target_dir: Optional[str] = None
    extras: Optional[dict] = None


class ConverterClearFilesBody(BaseModel):
    target_dir: Optional[str] = None


@router.get("/converter/config/{engine_id}")
async def admin_get_converter_config(
    engine_id: str,
    _: User = Depends(get_current_admin),
):
    content = read_converter_config_text(engine_id)
    return {"ok": True, "engine_id": engine_id, "content": content}


@router.put("/converter/config/{engine_id}")
async def admin_put_converter_config(
    engine_id: str,
    body: ConverterConfigBody,
    _: User = Depends(get_current_admin),
):
    path = write_converter_config_text(engine_id, body.content)
    return {"ok": True, "engine_id": engine_id, "path": str(path)}


@router.get("/converter/config-data/{engine_id}")
async def admin_get_converter_config_data(
    engine_id: str,
    _: User = Depends(get_current_admin),
):
    data = read_converter_config(engine_id)
    return {"ok": True, "engine_id": engine_id, "data": data}


@router.put("/converter/config-data/{engine_id}")
async def admin_put_converter_config_data(
    engine_id: str,
    body: ConverterConfigDataBody,
    _: User = Depends(get_current_admin),
):
    path = write_converter_config_data(engine_id, body.data)
    return {"ok": True, "engine_id": engine_id, "path": str(path)}


@router.get("/converter/{engine_id}/download/schema")
async def admin_get_converter_download_schema(
    engine_id: str,
    _: User = Depends(get_current_admin),
):
    try:
        schema = plugin_get_download_schema(engine_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True, "engine_id": engine_id, "schema": schema.__dict__}


@router.post("/converter/{engine_id}/download/start")
async def admin_start_converter_download(
    engine_id: str,
    body: ConverterDownloadStartBody,
    _: User = Depends(get_current_admin),
):
    req = ConverterDownloadRequest(
        engine_id=engine_id,
        source=str(body.source or "modelscope"),
        repo_id=(body.repo_id or "").strip(),
        target_dir=(body.target_dir or "").strip(),
        extras=body.extras or {},
    )
    try:
        status = plugin_start_download(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _engine_download_task[engine_id] = status.task_id
    return {"ok": True, "engine_id": engine_id, "task_id": status.task_id, "status": status.__dict__}


@router.get("/converter/{engine_id}/download/status/{task_id}")
async def admin_get_converter_download_status(
    engine_id: str,
    task_id: str,
    _: User = Depends(get_current_admin),
):
    try:
        status = plugin_get_download_status(engine_id, task_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True, "engine_id": engine_id, "task_id": task_id, "status": status.__dict__}


@router.post("/converter/{engine_id}/download/stop/{task_id}")
async def admin_stop_converter_download(
    engine_id: str,
    task_id: str,
    _: User = Depends(get_current_admin),
):
    try:
        status = plugin_stop_download(engine_id, task_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "engine_id": engine_id, "task_id": task_id, "status": status.__dict__}


@router.post("/converter/{engine_id}/model-files/clear")
async def admin_clear_converter_model_files(
    engine_id: str,
    body: ConverterClearFilesBody,
    _: User = Depends(get_current_admin),
):
    from .. import main as main_module

    if main_module.get_inference_model() is not None:
        raise HTTPException(status_code=400, detail="模型已加载，禁止删除模型文件。请先卸载模型后再执行删除。")
    if _is_any_download_running():
        raise HTTPException(status_code=400, detail="存在下载任务进行中，无法删除模型文件。")

    target_dir = (body.target_dir or "").strip()

    try:
        result = plugin_clear_downloaded_files(engine_id, target_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "engine_id": engine_id, **result}


@router.post("/converter/paddle/check")
async def admin_check_paddle_converter(
    _: User = Depends(get_current_admin),
):
    cfg = read_converter_config("paddle-ocr-v3.5")
    runtime_mode = str(cfg.get("runtime_mode") or "api").strip().lower()
    if runtime_mode == "local":
        cmd = str(cfg.get("local_command") or "").strip()
        if not cmd:
            raise HTTPException(status_code=400, detail="PaddleOCR 本地模式缺少 local_command 配置")
        return {"ok": True, "message": "PaddleOCR 本地模式配置已就绪（检测到 local_command）。"}

    api_url = str(cfg.get("api_url") or "").strip()
    token = str(cfg.get("access_token") or "").strip()
    missing = []
    if not api_url or "your-service.example.com" in api_url:
        missing.append("paddle_api_url")
    if not token or token == "replace-with-token":
        missing.append("paddle_access_token")

    if missing:
        raise HTTPException(status_code=400, detail=f"PaddleOCR 配置不完整，缺少: {', '.join(missing)}")
    return {
        "ok": True,
        "message": "PaddleOCR 配置已就绪（已检测到 API URL 与 Access Token）。",
    }


_engine_download_task: dict[str, str] = {}


def _is_any_download_running() -> bool:
    for engine_id, task_id in list(_engine_download_task.items()):
        try:
            if plugin_get_download_status(engine_id, task_id).is_downloading:
                return True
        except Exception:
            continue
    return False


@router.get("/settings")
async def admin_get_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return settings_to_admin_dict(db)


@router.put("/settings")
async def admin_put_settings(
    body: AdminSettingsBody,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    data = body.model_dump(exclude_none=True)
    
    # 验证上传大小配置
    if "max_upload_size_mb" in data:
        from ..settings_service import validate_upload_size_config
        validation = validate_upload_size_config(data["max_upload_size_mb"])
        
        # 如果后端配置超过 Nginx，拒绝保存
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=validation["warning"]
            )
    
    try:
        return update_settings_from_body(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/model/download")
async def admin_download_model(
    body: ModelDownloadBody,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """兼容旧接口：内部转发到插件化下载接口。"""
    row = get_app_settings_row(db)
    engine_id = (body.engine_id or getattr(row, "default_converter_id", "logics-parsing-v2") or "logics-parsing-v2").strip()
    req = ConverterDownloadRequest(
        engine_id=engine_id,
        source=body.source,
        repo_id=(body.repo_id or "").strip(),
        target_dir=(body.target_dir or "").strip(),
        extras={},
    )
    try:
        status = plugin_start_download(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _engine_download_task[engine_id] = status.task_id
    return {
        "ok": True,
        "message": f"🚀 已启动 {engine_id} 下载任务",
        "engine_id": engine_id,
        "task_id": status.task_id,
        "source": status.source,
    }


@router.get("/model/status")
async def admin_get_model_status(
    engine_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """获取当前模型下载和加载状态"""
    from .. import main as main_module
    row = get_app_settings_row(db)
    eid = (engine_id or getattr(row, "default_converter_id", "logics-parsing-v2") or "logics-parsing-v2").strip()
    m = main_module.get_inference_model()
    task_id = _engine_download_task.get(eid, "")
    download = {
        "is_downloading": False,
        "success": False,
        "error": None,
        "message": "",
        "dest": "",
        "repo": "",
        "source": "",
    }
    if task_id:
        try:
            ds = plugin_get_download_status(eid, task_id)
            download = {
                "is_downloading": ds.is_downloading,
                "success": ds.success,
                "error": ds.error,
                "message": ds.message,
                "dest": ds.dest,
                "repo": ds.repo,
                "source": ds.source,
            }
        except Exception:
            pass

    return {
        "ok": True,
        "model_loaded": m is not None,
        "downloading": download["is_downloading"],
        "download_success": download["success"],
        "download_error": download["error"],
        "download_message": download["message"],
        "download_dest": download["dest"],
        "download_repo": download["repo"],
        "download_source": download["source"],
        "download_task_id": task_id,
        "engine_id": eid,
    }


@router.post("/model/reload")
async def admin_reload_model(
    current_user: User = Depends(get_current_admin),
):
    """手动重新加载模型（先卸载再加载）"""
    from .. import main as main_module

    # 审计日志：记录谁在什么时候执行了模型重载
    _log.info(f"🔐 管理员 [{current_user.username}] (ID:{current_user.id}) 请求重新加载模型")

    # 检查是否有下载任务正在进行
    if _is_any_download_running():
        raise HTTPException(
            status_code=400, 
            detail="下载任务正在进行中，请等待下载完成后再尝试重新加载模型"
        )
    
    _log.info("开始重新加载模型...")
    
    try:
        # 使用新的懒加载机制重新加载模型
        _log.info("正在从配置加载模型...")
        main_module.reload_model_from_settings()
        
    except Exception as e:
        _log.exception("重新加载模型失败")
        code = 503 if _is_cuda_oom(e) else 500
        error_msg = _friendly_model_reload_message(e)
        raise HTTPException(status_code=code, detail=f"重新加载失败：{error_msg}") from None
    
    m = main_module.get_inference_model()
    
    if m is not None:
        _log.info("✅ 模型重新加载成功")
        return {
            "ok": True,
            "model_loaded": True,
            "message": "✅ 模型已成功重新加载\n\n模型已就绪，可以开始解析文档了！",
        }
    else:
        _log.warning("⚠️ 模型重新加载后仍为 None")
        return {
            "ok": True,
            "model_loaded": False,
            "message": "⚠️ 模型目录不存在或加载失败\n\n请检查：\n1. 模型路径是否正确\n2. 模型文件是否完整\n3. 是否有足够的显存/内存",
        }


@router.post("/model/unload")
async def admin_unload_model(
    current_user: User = Depends(get_current_admin),
):
    """手动卸载模型以释放显存"""
    from .. import main as main_module

    # 审计日志：记录谁在什么时候执行了模型卸载
    _log.info(f"🔐 管理员 [{current_user.username}] (ID:{current_user.id}) 请求卸载模型")

    # 检查是否有下载任务正在进行
    if _is_any_download_running():
        raise HTTPException(
            status_code=400, 
            detail="下载任务正在进行中，请等待下载完成后再尝试卸载模型"
        )
    
    # 检查模型是否已加载
    current_model = main_module.get_inference_model()
    if current_model is None:
        return {
            "ok": True,
            "model_loaded": False,
            "message": "ℹ️ 模型未加载，无需卸载",
        }
    
    _log.info("开始卸载模型以释放显存...")

    try:
        if not main_module.unload_model(wait_for_inference=False):
            raise HTTPException(
                status_code=409,
                detail="仍有解析任务在使用模型，请等待任务完成或停止后再卸载。",
            )
        _log.info("✅ 模型已成功卸载")

        return {
            "ok": True,
            "model_loaded": False,
            "message": (
                "✅ 模型已从内存中卸载\n\n"
                "大模型权重已释放；nvidia-smi 中仍可能看到本服务进程，"
                "但「显存占用」应明显下降（PyTorch 会保留少量缓存池属正常现象）。\n\n"
                "下次上传文档时将自动重新加载模型。"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("卸载模型失败")
        raise HTTPException(status_code=500, detail=f"卸载失败：{str(e)}") from None


def _other_active_admin_count(db: Session, exclude_id: int) -> int:
    return (
        db.query(User)
        .filter(User.is_admin.is_(True), User.is_active.is_(True), User.id != exclude_id)
        .count()
    )


def _try_apply_admin_user_flags(
    db: Session,
    current: User,
    u: User,
    *,
    is_active: Optional[bool],
    is_admin: Optional[bool],
) -> Optional[str]:
    """更新 is_active / is_admin（与单条 PATCH 相同规则）。成功返回 None，失败返回错误原因。"""
    if is_active is None and is_admin is None:
        return "未指定变更"

    if u.id != current.id and u.is_admin and (is_active is not None or is_admin is not None):
        return "不能禁用或修改其他管理员账号的状态与角色"

    if u.id == current.id:
        if is_admin is False:
            return "不能取消自己的管理员权限"
        if is_active is False:
            return "不能禁用当前登录账号"

    new_admin = u.is_admin if is_admin is None else bool(is_admin)
    new_active = u.is_active if is_active is None else bool(is_active)

    if u.is_admin and (not new_admin or not new_active):
        if _other_active_admin_count(db, u.id) < 1:
            return "至少保留一名可登录的管理员"

    if is_active is not None:
        u.is_active = new_active
    if is_admin is not None:
        u.is_admin = new_admin
    return None


@router.get("/users")
async def admin_list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    query = db.query(User)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(User.username.ilike(term), User.email.ilike(term)))
    total = query.count()
    rows = query.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    global_pdf = get_pdf_max_pages(db)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pdf_max_pages_global": global_pdf,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "phone": getattr(u, "phone", None) or "",
                "is_admin": bool(u.is_admin),
                "is_active": bool(u.is_active),
                "pdf_max_pages": getattr(u, "pdf_max_pages", None),
                # 实际可解析页数：管理员为 null（前端显示「无限制」）；普通用户为 min(全局, 个人)
                "pdf_effective_max_pages": (
                    None
                    if u.is_admin
                    else get_effective_pdf_max_pages_for_user(u, db)
                ),
                "can_download_images": bool(getattr(u, "can_download_images", True)),
                "image_output_mode": getattr(u, "image_output_mode", None),
                "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
            }
            for u in rows
        ],
    }


class AdminUsersBatchBody(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=200)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


@router.post("/users/batch")
async def admin_batch_users(
    body: AdminUsersBatchBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
):
    if body.is_active is None and body.is_admin is None:
        raise HTTPException(status_code=400, detail="请至少指定 is_active 或 is_admin")

    ids = list(dict.fromkeys(body.user_ids))[:200]
    updated: list[int] = []
    failed: list[dict] = []

    for uid in ids:
        u = db.query(User).filter(User.id == uid).first()
        if not u:
            failed.append({"id": uid, "detail": "用户不存在"})
            continue
        err = _try_apply_admin_user_flags(
            db, current, u, is_active=body.is_active, is_admin=body.is_admin
        )
        if err:
            failed.append({"id": uid, "detail": err})
            continue
        updated.append(uid)

    db.commit()
    return {"ok": True, "updated": updated, "failed": failed}


class AdminUsersBatchPdfBody(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=200)
    """个人 PDF 页数上限；null 表示与系统全局一致（清空个人覆盖）。"""
    pdf_max_pages: Optional[int] = None


@router.post("/users/batch-pdf-pages")
async def admin_batch_users_pdf_pages(
    body: AdminUsersBatchPdfBody,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    ids = list(dict.fromkeys(body.user_ids))[:200]
    updated: list[int] = []
    failed: list[dict] = []

    v = body.pdf_max_pages
    if v is not None and int(v) < 1:
        raise HTTPException(status_code=400, detail="PDF 页数上限至少为 1，或使用系统默认（传 null）")

    for uid in ids:
        u = db.query(User).filter(User.id == uid).first()
        if not u:
            failed.append({"id": uid, "detail": "用户不存在"})
            continue
        if u.is_admin:
            failed.append({"id": uid, "detail": "管理员账号不在此批量范围内（解析不受个人页数限制）"})
            continue
        if v is None:
            u.pdf_max_pages = None
        else:
            u.pdf_max_pages = int(v)
        updated.append(uid)

    db.commit()
    return {"ok": True, "updated": updated, "failed": failed}


class AdminUsersBatchDeleteBody(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=200)


@router.post("/users/batch-delete")
async def admin_batch_delete_users(
    body: AdminUsersBatchDeleteBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
):
    ids = list(dict.fromkeys(body.user_ids))[:200]
    deleted: list[int] = []
    failed: list[dict] = []

    for uid in ids:
        if uid == current.id:
            failed.append({"id": uid, "detail": "不能删除当前登录账号"})
            continue
        u = db.query(User).filter(User.id == uid).first()
        if not u:
            failed.append({"id": uid, "detail": "用户不存在"})
            continue
        if u.is_admin:
            failed.append({"id": uid, "detail": "不能删除管理员账号"})
            continue
        db.query(ParseJob).filter(ParseJob.user_id == uid).delete(synchronize_session=False)
        db.delete(u)
        deleted.append(uid)

    db.commit()
    return {"ok": True, "deleted": deleted, "failed": failed}


class AdminUserPatchBody(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    new_password: Optional[str] = Field(None, max_length=128)
    pdf_max_pages: Optional[int] = Field(
        None,
        description="个人 PDF 解析页数上限；null 表示与系统全局一致",
    )
    can_download_images: Optional[bool] = Field(
        None,
        description="是否允许下载图片资源（仅当输出模式为 separate 时生效）",
    )
    image_output_mode: Optional[str] = Field(
        None,
        description="个人图片输出模式；null 表示跟随系统设置（base64 / separate / none）",
    )


class AdminUserCreateBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    is_admin: bool = False
    is_active: bool = True
    pdf_max_pages: Optional[int] = Field(
        None,
        description="个人 PDF 解析页数上限；null 表示与系统全局一致",
    )
    can_download_images: bool = Field(
        True,
        description="是否允许下载图片资源（仅当输出模式为 separate 时生效）",
    )
    image_output_mode: Optional[str] = Field(
        None,
        description="个人图片输出模式；null 表示跟随系统设置（base64 / separate / none）",
    )


@router.patch("/users/{user_id}")
async def admin_patch_user(
    user_id: int,
    body: AdminUserPatchBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 禁止编辑其他管理员账号
    if u.is_admin and u.id != current.id:
        raise HTTPException(
            status_code=403,
            detail="不能编辑其他管理员账号。密码请由该管理员本人登录后在「密码修改」中修改"
        )

    if body.is_active is not None or body.is_admin is not None:
        err = _try_apply_admin_user_flags(
            db, current, u, is_active=body.is_active, is_admin=body.is_admin
        )
        if err:
            raise HTTPException(status_code=400, detail=err)

    if body.new_password and body.new_password.strip():
        pwd = body.new_password.strip()
        if len(pwd) < 8:
            raise HTTPException(status_code=400, detail="新密码至少 8 位")
        u.hashed_password = hash_password(pwd)

    patch = body.model_dump(exclude_unset=True)
    if "pdf_max_pages" in patch:
        v = patch["pdf_max_pages"]
        if v is None:
            u.pdf_max_pages = None
        else:
            if int(v) < 1:
                raise HTTPException(status_code=400, detail="PDF 页数上限至少为 1")
            u.pdf_max_pages = int(v)
    
    if "can_download_images" in patch:
        u.can_download_images = bool(patch["can_download_images"])

    if "image_output_mode" in patch:
        v = patch["image_output_mode"]
        if v is None:
            u.image_output_mode = None
        else:
            mode = str(v).strip().lower()
            if mode not in ("base64", "separate", "none"):
                raise HTTPException(status_code=400, detail="图片输出模式必须是 base64、separate、none 或 null")
            u.image_output_mode = mode

    db.commit()
    return {"ok": True}


@router.post("/users/create")
async def admin_create_user(
    body: AdminUserCreateBody,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """管理员创建新用户。"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"用户名 '{body.username}' 已被使用")
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == body.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail=f"邮箱 '{body.email}' 已被注册")
    
    # 验证密码长度
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    
    # 验证 PDF 页数
    if body.pdf_max_pages is not None and body.pdf_max_pages < 1:
        raise HTTPException(status_code=400, detail="PDF 页数上限至少为 1")
    
    # 验证图片输出模式
    if body.image_output_mode is not None:
        mode = str(body.image_output_mode).strip().lower()
        if mode not in ("base64", "separate", "none"):
            raise HTTPException(status_code=400, detail="图片输出模式必须是 base64、separate 或 none")
    
    # 创建用户
    new_user = User(
        username=body.username.strip(),
        email=body.email.strip().lower(),
        hashed_password=hash_password(body.password),
        is_admin=bool(body.is_admin),
        is_active=bool(body.is_active),
        pdf_max_pages=int(body.pdf_max_pages) if body.pdf_max_pages is not None else None,
        can_download_images=bool(body.can_download_images),
        image_output_mode=str(body.image_output_mode).strip().lower() if body.image_output_mode is not None else None,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "ok": True,
        "message": f"用户 '{new_user.username}' 创建成功",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "is_admin": new_user.is_admin,
            "is_active": new_user.is_active,
            "pdf_max_pages": new_user.pdf_max_pages,
        }
    }


# ==================== 用户会话管理 API ====================

@router.get("/users/{user_id}/session")
def get_user_session_info(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """获取用户当前会话信息（管理员专用）"""
    from ..session_manager import get_user_session
    
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    session_data = get_user_session(user_id)
    
    if not session_data:
        return {
            "ok": True,
            "has_session": False,
            "message": "用户当前没有活跃会话",
        }
    
    return {
        "ok": True,
        "has_session": True,
        "session": {
            "user_id": session_data.get("user_id"),
            "username": session_data.get("username"),
            "ip_address": session_data.get("ip_address", ""),
            "user_agent": session_data.get("user_agent", ""),
            "login_at": session_data.get("login_at"),
            "last_active": session_data.get("last_active"),
        }
    }


@router.post("/users/{user_id}/kick")
def kick_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """踢出用户（强制登出）"""
    from ..session_manager import kick_user as do_kick_user
    
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不能踢出自己
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能踢出自己")
    
    # 执行踢出操作
    success = do_kick_user(user_id, admin_username=admin.username)
    
    _log.info(f"管理员 {admin.username} 踢出了用户 {user.username} (ID: {user_id})")
    
    return {
        "ok": True,
        "message": f"已踢出用户 '{user.username}'",
        "kicked_user": user.username,
    }


@router.get("/sessions/online-users")
def get_online_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """获取所有在线用户列表（管理员专用）"""
    from ..session_manager import cache
    
    # 查找所有用户会话键
    session_keys = cache.keys("user_session:*")
    
    online_users = []
    for key in session_keys:
        session_data = cache.get(key)
        if session_data:
            user_id = session_data.get("user_id")
            # 从数据库获取用户详细信息
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                online_users.append({
                    "user_id": user_id,
                    "username": session_data.get("username"),
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "ip_address": session_data.get("ip_address", ""),
                    "user_agent": session_data.get("user_agent", ""),
                    "login_at": session_data.get("login_at"),
                    "last_active": session_data.get("last_active"),
                })
    
    return {
        "ok": True,
        "total": len(online_users),
        "users": online_users,
    }

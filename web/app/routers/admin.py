"""管理员：系统配置与模型下载。"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth_security import hash_password
from ..database import get_db
from ..deps import get_current_admin
from ..models import ParseJob, User
from ..settings_service import (
    get_app_settings_row,
    get_effective_model_path_str,
    get_effective_pdf_max_pages_for_user,
    get_pdf_max_pages,
    settings_to_admin_dict,
    update_settings_from_body,
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
    model_local_path: Optional[str] = None
    hf_repo_id: Optional[str] = None
    ms_repo_id: Optional[str] = None
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


def _get_dir_size(path: Path) -> int:
    """计算目录总大小（字节）"""
    total = 0
    if path.exists():
        for p in path.rglob('*'):
            if p.is_file():
                total += p.stat().st_size
    return total


def _monitor_download_progress(dest: Path, initial_size: int) -> None:
    """后台线程：监控下载进度并更新状态"""
    global _download_status
    
    while _download_status.get("is_downloading", False):
        try:
            current_size = _get_dir_size(dest)
            downloaded_mb = current_size / (1024 * 1024)
            
            # 每5秒更新一次进度
            source = _download_status.get("source", "")
            repo = _download_status.get("repo", "")
            dest_str = _download_status.get("dest", "")
            
            _download_status["message"] = (
                f"📦 正在下载模型...\n\n"
                f"来源：{source}\n"
                f"仓库：{repo}\n"
                f"目标：{dest_str}\n\n"
                f"📊 已下载：{downloaded_mb:.1f} MB\n\n"
                f"💡 下载过程中您可以继续其他操作，完成后会自动加载"
            )
        except Exception:
            pass
        
        time.sleep(5)  # 每5秒更新一次


def _download_model_sync(dest: Path, source: str, repo: str) -> None:
    """同步下载模型到指定目录"""
    dest.mkdir(parents=True, exist_ok=True)
    if source == "huggingface":
        try:
            from huggingface_hub import snapshot_download
        except ImportError as e:
            raise RuntimeError("请安装 huggingface_hub：pip install huggingface_hub") from e
        snapshot_download(repo_id=repo, local_dir=str(dest), local_dir_use_symlinks=False, resume_download=True)
    else:
        try:
            from modelscope import snapshot_download
        except ImportError as e:
            raise RuntimeError("请安装 modelscope：pip install modelscope") from e
        snapshot_download(repo_id=repo, local_dir=str(dest))


# 全局变量：跟踪下载任务状态
_download_status = {
    "is_downloading": False,
    "success": False,
    "error": None,
    "message": "",
    "dest": "",
    "repo": "",
    "source": "",
}


def _download_job(source: str, repo: str, dest: Path) -> None:
    """后台下载任务，更新全局状态并尝试自动加载模型"""
    global _download_status
    
    try:
        _download_status["is_downloading"] = True
        _download_status["success"] = False
        _download_status["error"] = None
        _download_status["message"] = "🚀 正在启动下载任务...\n\n准备从仓库下载模型文件\n请稍候，这可能需要几分钟到几小时（取决于网络和模型大小）"
        _download_status["dest"] = str(dest)
        _download_status["repo"] = repo
        _download_status["source"] = source
        
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[model download] starting: {source}/{repo} -> {dest}")
        
        # 获取初始目录大小
        initial_size = _get_dir_size(dest)
        
        # 启动进度监控线程
        monitor_thread = threading.Thread(
            target=_monitor_download_progress,
            args=(dest, initial_size),
            daemon=True
        )
        monitor_thread.start()
        
        # 开始下载
        _download_status["message"] = f"📦 开始下载模型\n\n来源：{source}\n仓库：{repo}\n目标：{dest}\n\n⏳ 正在下载中..."
        _download_model_sync(dest, source, repo)
        
        # 下载完成，停止监控线程
        _download_status["is_downloading"] = False
        monitor_thread.join(timeout=2)
        
        _download_status["success"] = True
        _download_status["message"] = f"✅ 下载完成！\n\n模型已成功下载到：\n{dest}\n\n正在自动加载模型..."
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[model download] finished -> {dest}")
        
        # 下载完成后自动尝试加载模型
        try:
            from .. import main as main_module
            main_module.reload_model_from_settings()
            m = main_module.get_inference_model()
            if m is not None:
                _download_status["message"] = f"✅ 模型下载成功并已自动加载！\n\n模型路径：{dest}\n状态：已就绪\n\n🎉 现在可以开始解析文档了！"
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print("[model download] auto-reload successful")
            else:
                _download_status["message"] = f"⚠️ 模型下载完成，但加载失败\n\n模型路径：{dest}\n问题：请检查模型文件完整性\n\n建议：点击「重新加载模型」重试"
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print("[model download] auto-reload failed: model is None")
        except Exception as load_err:
            _download_status["message"] = f"⚠️ 模型下载完成，但自动加载失败\n\n错误信息：{str(load_err)[:200]}\n\n建议：\n1. 检查模型文件是否完整\n2. 点击「重新加载模型」重试\n3. 查看后端日志获取详细错误"
            if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                print(f"[model download] auto-reload error: {load_err}")
            
    except Exception as e:
        _download_status["is_downloading"] = False
        _download_status["success"] = False
        _download_status["error"] = str(e)
        _download_status["message"] = f"❌ 下载失败\n\n错误类型：{type(e).__name__}\n错误信息：{str(e)[:300]}\n\n可能原因：\n1. 网络连接问题\n2. 仓库 ID 不正确\n3. 磁盘空间不足\n\n建议：检查网络后重试"
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[model download] error: {e}")


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """启动后台模型下载任务，下载完成后自动尝试加载"""
    global _download_status
    
    # 检查是否已有下载任务在进行
    if _download_status.get("is_downloading", False):
        raise HTTPException(status_code=400, detail="已有下载任务正在进行中，请稍后再试")
    
    row = get_app_settings_row(db)
    repo = (body.repo_id or "").strip()
    if not repo:
        repo = (row.hf_repo_id if body.source == "huggingface" else row.ms_repo_id) or ""
    if not repo:
        raise HTTPException(status_code=400, detail="未配置仓库 ID，请在系统设置中配置 hf_repo_id 或 ms_repo_id")

    dest_str = get_effective_model_path_str(db)
    if not dest_str:
        raise HTTPException(status_code=400, detail="请先配置模型本地路径（系统设置中的 model_local_path）或环境变量 MODEL_PATH")
    dest = Path(dest_str)
    
    # 检查模型目录是否已存在
    model_exists = dest.exists() and any(dest.iterdir())
    
    # 重置下载状态
    _download_status = {
        "is_downloading": True,
        "success": False,
        "error": None,
        "message": "正在启动下载任务...",
        "dest": str(dest),
        "repo": repo,
        "source": body.source,
    }

    background_tasks.add_task(_download_job, body.source, repo, dest)
    
    return {
        "ok": True, 
        "message": f"🚀 模型下载任务已启动\n\n来源：{body.source}\n仓库：{repo}\n目标：{dest}\n\n💡 提示：\n• 下载过程可能需要较长时间（取决于网络和模型大小）\n• 下载完成后会自动尝试加载模型\n• 您可以在下载过程中继续其他操作\n• 稍后可点击「重新加载模型」手动刷新",
        "dest": str(dest), 
        "repo": repo,
        "source": body.source,
        "model_exists": model_exists,
    }


@router.get("/model/status")
async def admin_get_model_status(
    _: User = Depends(get_current_admin),
):
    """获取当前模型下载和加载状态"""
    from .. import main as main_module
    
    m = main_module.get_inference_model()
    
    return {
        "ok": True,
        "model_loaded": m is not None,
        "downloading": _download_status.get("is_downloading", False),
        "download_success": _download_status.get("success", False),
        "download_error": _download_status.get("error"),
        "download_message": _download_status.get("message", ""),
        "download_dest": _download_status.get("dest", ""),
        "download_repo": _download_status.get("repo", ""),
        "download_source": _download_status.get("source", ""),
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
    if _download_status.get("is_downloading", False):
        raise HTTPException(
            status_code=400, 
            detail="下载任务正在进行中，请等待下载完成后再尝试重新加载模型"
        )
    
    _log.info("开始重新加载模型...")
    
    try:
        # 先卸载现有模型（释放显存）
        current_model = main_module.get_inference_model()
        if current_model is not None:
            _log.info("检测到已加载的模型，正在卸载...")
            
            # 1. 记录卸载前的显存使用情况
            try:
                import torch
                if torch.cuda.is_available():
                    allocated_before = torch.cuda.memory_allocated() / (1024**3)
                    reserved_before = torch.cuda.memory_reserved() / (1024**3)
                    _log.info(f"📊 卸载前显存状态: 已分配={allocated_before:.2f}GB, 已保留={reserved_before:.2f}GB")
            except Exception:
                pass
            
            # 2. 显式删除模型内部引用
            try:
                if hasattr(current_model, 'model'):
                    del current_model.model
                    _log.info("已删除 model 属性")
                if hasattr(current_model, 'processor'):
                    del current_model.processor
                    _log.info("已删除 processor 属性")
            except Exception as e:
                _log.warning(f"删除模型属性时出错: {e}")
            
            # 3. 删除全局模型引用
            main_module.model = None
            del current_model
            _log.info("已删除全局模型引用")
            
            # 4. 多次强制垃圾回收
            import gc
            for i in range(3):
                gc.collect()
            _log.info("已执行垃圾回收 (3次)")
            
            # 5. 清理 CUDA 缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()  # 等待所有 CUDA 操作完成
                    
                    # 记录卸载后的显存使用情况
                    allocated_after = torch.cuda.memory_allocated() / (1024**3)
                    reserved_after = torch.cuda.memory_reserved() / (1024**3)
                    freed = allocated_before - allocated_after
                    _log.info(f"✅ 卸载后显存状态: 已分配={allocated_after:.2f}GB, 已保留={reserved_after:.2f}GB, 释放={freed:.2f}GB")
            except Exception as e:
                _log.warning(f"清理 CUDA 缓存时出错: {e}")
            
            _log.info("模型卸载完成")
        
        # 重新加载模型
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

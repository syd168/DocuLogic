import logging
import os

from .logging_setup import configure_logging

configure_logging()

import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import asyncio
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocketDisconnect

from .auth_security import decode_token
from .database import SessionLocal, get_db, init_db
from .deps import get_current_user
from .job_events import cancel_job, register_job, remove_job
from .model_inference import LogicsParsingModel
from .models import ParseJob, User
from .paths import PROJECT_ROOT
from .rate_limit import limiter
from .routers import admin as admin_router
from .routers import auth as auth_router
from .routers import captcha_api as captcha_router
from .settings_service import (
    get_effective_output_dir,
    get_effective_model_path_str,
    get_effective_pdf_max_pages_for_user,
    get_pdf_max_pages,
    get_max_upload_size_mb,
    resolve_job_pdf_max_pages,
    settings_to_admin_dict,
    settings_to_public_dict,
)
from .websocket_manager import manager

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR.parent / "static"

STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="DocuLogic Platform", docs_url="/api/docs", redoc_url=None)

# 安全响应头中间件
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    添加安全响应头，增强 Web 应用安全性
    
    包括：
    - X-Content-Type-Options: 防止 MIME 类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: XSS 过滤器
    - Strict-Transport-Security: 强制 HTTPS（生产环境）
    - Content-Security-Policy: 内容安全策略
    - Referrer-Policy: 控制 Referer 信息
    - Permissions-Policy: 限制浏览器功能
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 防止 MIME 类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 防止点击劫持（禁止嵌入 iframe）
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS 过滤器（现代浏览器已内置，但保留作为后备）
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 强制 HTTPS（仅在生产环境且使用 HTTPS 时启用）
        if os.environ.get("HTTPS_ENABLED", "").lower() in ("1", "true", "yes"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # 内容安全策略（CSP）
        # 允许同源资源、必要的 CDN、内联样式（Vue 需要）
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # 控制 Referer 信息泄露
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 限制浏览器功能（禁用不必要的 API）
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors = os.environ.get(
    "CORS_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000,"
    "http://127.0.0.1:5173,http://localhost:5173,"
    "http://127.0.0.1:4173,http://localhost:4173",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 仅允许必要的方法
    allow_headers=["Content-Type", "Authorization", "Accept"],  # 最小化允许的头部
)

app.include_router(auth_router.router)
app.include_router(captcha_router.router)
app.include_router(admin_router.router)

model: Optional[LogicsParsingModel] = None


def get_inference_model() -> Optional[LogicsParsingModel]:
    return model


def reload_model_from_settings() -> None:
    global model
    db = SessionLocal()
    try:
        path_str = get_effective_model_path_str(db)
        if not path_str:
            model = None
            raise ValueError("未配置模型路径，请在系统设置中配置 MODEL_PATH")
        
        p = Path(path_str)
        if not p.exists():
            model = None
            raise FileNotFoundError(f"模型目录不存在：{path_str}\n\n请检查：\n1. 模型路径是否正确\n2. 模型文件是否已下载\n3. 可通过「后台下载到模型目录」功能自动下载")
        
        # 检查关键文件是否存在
        has_safetensors = any(p.glob("*.safetensors"))
        has_pytorch = any(p.glob("pytorch_model*.bin"))
        
        if not has_safetensors and not has_pytorch:
            model = None
            raise FileNotFoundError(
                f"模型文件不完整：{path_str}\n\n"
                f"未找到模型权重文件（.safetensors 或 .bin）\n\n"
                f"可能原因：\n"
                f"1. 模型下载未完成\n"
                f"2. 模型目录指向错误\n"
                f"3. 模型文件损坏\n\n"
                f"建议：点击「后台下载到模型目录」重新下载完整模型"
            )
        
        # 记录加载前的显存状态
        try:
            import torch
            if torch.cuda.is_available():
                allocated_before = torch.cuda.memory_allocated() / (1024**3)
                reserved_before = torch.cuda.memory_reserved() / (1024**3)
                print(f"📊 加载前显存状态: 已分配={allocated_before:.2f}GB, 已保留={reserved_before:.2f}GB")
        except Exception:
            pass
        
        try:
            model = LogicsParsingModel(path_str)
            
            # 记录加载后的显存状态
            try:
                import torch
                if torch.cuda.is_available():
                    allocated_after = torch.cuda.memory_allocated() / (1024**3)
                    reserved_after = torch.cuda.memory_reserved() / (1024**3)
                    used = allocated_after - allocated_before
                    print(f"✅ 模型加载成功! 显存使用: {allocated_after:.2f}GB (新增 {used:.2f}GB)")
                    
                    # 如果显存使用超过 90%，给出警告
                    total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    usage_percent = (allocated_after / total_gpu_memory) * 100
                    if usage_percent > 90:
                        print(f"⚠️  警告: 显存使用率已达 {usage_percent:.1f}% ({allocated_after:.2f}GB / {total_gpu_memory:.2f}GB)")
                        print(f"   建议: 关闭其他占用显存的程序，或考虑增加显存")
            except Exception:
                print("✅ 模型加载成功!")
        except Exception as e:
            model = None
            error_msg = str(e)
            
            # 友好的错误提示
            if "pytorch_model.bin" in error_msg or "model.safetensors" in error_msg:
                raise FileNotFoundError(
                    f"模型文件格式错误：{path_str}\n\n"
                    f"错误详情：{error_msg[:200]}\n\n"
                    f"可能原因：\n"
                    f"1. 模型文件不完整或损坏\n"
                    f"2. 模型版本不兼容\n\n"
                    f"建议：删除当前模型后重新下载"
                ) from e
            elif "CUDA out of memory" in error_msg:
                # 提供更详细的显存信息和建议
                try:
                    import torch
                    if torch.cuda.is_available():
                        total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        alloc_mem = torch.cuda.memory_allocated() / (1024**3)
                        free_mem = total_mem - alloc_mem
                        
                        raise RuntimeError(
                            f"显存不足，无法加载模型\n\n"
                            f"GPU 信息:\n"
                            f"- 总显存: {total_mem:.2f} GB\n"
                            f"- 已分配: {alloc_mem:.2f} GB\n"
                            f"- 可用: {free_mem:.2f} GB\n\n"
                            f"建议解决方案:\n"
                            f"1. 关闭其他占用显存的程序（如 Jupyter、其他训练任务）\n"
                            f"2. 重启服务以释放显存碎片\n"
                            f"3. 设置环境变量: PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True\n"
                            f"4. 使用更小的模型或降低精度\n\n"
                            f"如需立即尝试，可执行:\n"
                            f"docker restart doculogic-app"
                        ) from e
                except RuntimeError:
                    raise  # 重新抛出上面的 RuntimeError
                except Exception:
                    raise RuntimeError(
                        f"显存不足，无法加载模型\n\n"
                        f"建议：\n"
                        f"1. 关闭其他占用显存的程序\n"
                        f"2. 重启服务以释放显存\n"
                        f"3. 设置环境变量: PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
                    ) from e
            else:
                raise RuntimeError(f"模型加载失败：{error_msg[:300]}") from e
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """缺少权重或加载失败时仍启动 HTTP 服务（推理接口返回 503），避免进程直接退出导致浏览器无法访问。
    若需旧行为（无模型则拒绝启动），设置 STRICT_MODEL_START=1。"""
    global model
    logging.getLogger("app").info("文件日志: %s", PROJECT_ROOT / "logs" / "app.log")
    init_db()
    strict = os.environ.get("STRICT_MODEL_START", "").lower() in ("1", "true", "yes")
    db = SessionLocal()
    try:
        path_str = get_effective_model_path_str(db)
        if path_str and Path(path_str).exists():
            try:
                model = LogicsParsingModel(path_str)
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print("✅ 模型加载成功!")
            except Exception as e:
                model = None
                error_msg = str(e)
                
                # 友好的错误提示
                if "pytorch_model.bin" in error_msg or "model.safetensors" in error_msg:
                    msg = (
                        f"模型文件格式错误：{path_str}\n\n"
                        f"错误详情：{error_msg[:200]}\n\n"
                        f"可能原因：\n"
                        f"1. 模型文件不完整或损坏\n"
                        f"2. 模型版本不兼容\n\n"
                        f"建议：删除当前模型后重新下载"
                    )
                elif "CUDA out of memory" in error_msg:
                    msg = (
                        f"显存不足，无法加载模型\n\n"
                        f"建议：\n"
                        f"1. 关闭其他占用显存的程序\n"
                        f"2. 使用更小的模型"
                    )
                else:
                    msg = f"模型加载失败：{error_msg[:300]}"
                
                if strict:
                    raise RuntimeError(msg) from e
                print("⚠️ WARNING: " + msg)
        else:
            model = None
            msg = (
                "未找到有效模型目录。\n\n"
                "请配置 MODEL_PATH / 系统设置中的模型路径，或点击「后台下载到模型目录」自动下载。\n"
                "推理接口将返回 503。"
            )
            if strict:
                raise RuntimeError(msg)
            print("⚠️ WARNING: " + msg)
        
        # 检测并恢复僵尸任务（启动时自动执行一次）
        _recover_stale_jobs(db)
        
        # 清理过期的验证码
        _cleanup_expired_codes(db)
    finally:
        db.close()


def _get_job_for_actor(db: Session, job_id: str, actor: User) -> Optional[ParseJob]:
    row = db.query(ParseJob).filter(ParseJob.job_id == job_id).first()
    if not row:
        return None
    if getattr(actor, "is_admin", False):
        return row
    if row.user_id == actor.id:
        return row
    return None


def _recover_stale_jobs(db: Session, max_stale_minutes: Optional[int] = None) -> int:
    """
    检测并恢复僵尸任务。
    
    僵尸任务定义：
    - 状态为 processing
    - 创建时间超过配置的超时时长（默认从系统设置读取）
    - 对应的 job_id 不在当前运行的 cancel_events 中（说明后台进程已停止）
    
    参数：
        db: 数据库会话
        max_stale_minutes: 可选，手动指定的超时时长（分钟）。如果为 None，则从系统设置读取。
    
    返回：恢复的任务数量
    """
    from .job_events import is_job_running
    from .paths import PROJECT_ROOT
    
    # 如果没有指定超时时长，从系统设置读取
    if max_stale_minutes is None:
        from .models import AppSettings
        settings_row = db.query(AppSettings).filter(AppSettings.id == 1).first()
        max_stale_minutes = getattr(settings_row, "stale_job_timeout_minutes", 10) if settings_row else 10
    
    now = datetime.utcnow()
    cutoff_time = now - timedelta(minutes=max_stale_minutes)
    
    # 查询所有超时的 processing 任务
    stale_jobs = (
        db.query(ParseJob)
        .filter(
            ParseJob.status == "processing",
            ParseJob.created_at < cutoff_time,
        )
        .all()
    )
    
    recovered_count = 0
    out_base = get_effective_output_dir(db)
    
    for job in stale_jobs:
        job_id = job.job_id
        
        # 检查该任务是否仍在运行（在 cancel_events 中）
        if is_job_running(job_id):
            # 任务仍在运行，跳过
            continue
        
        # 使用乐观锁：仅当状态仍为 processing 时才更新
        # 避免竞态条件：任务可能在检查和更新之间完成
        updated = db.query(ParseJob).filter(
            ParseJob.job_id == job_id,
            ParseJob.status == "processing"  # 乐观锁条件
        ).update({
            "status": "failed",
            "completed_at": now
        })
        
        if updated:
            # 任务是僵尸任务，清理输出目录
            print(f"[僵尸任务恢复] 检测到僵尸任务: {job_id}, 创建时间: {job.created_at}")
            
            job_dir = out_base / job_id
            if job_dir.exists():
                try:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    print(f"[僵尸任务恢复] 已清理目录: {job_dir}")
                except Exception as e:
                    print(f"[僵尸任务恢复] 清理目录失败: {e}")
            
            recovered_count += 1
    
    if recovered_count > 0:
        db.commit()
        logging.getLogger("app").info(
            f"启动时恢复 {recovered_count} 个僵尸任务（超时 {max_stale_minutes} 分钟）"
        )
    
    return recovered_count


def _cleanup_expired_codes(db: Session) -> int:
    """
    清理过期的验证码。
    
    防止数据库中积累大量过期验证码，降低存储压力和潜在的安全风险。
    
    参数：
        db: 数据库会话
    
    返回：清理的验证码数量
    """
    from .models import VerificationCode
    
    now = datetime.utcnow()
    deleted_count = db.query(VerificationCode).filter(
        VerificationCode.expires_at < now
    ).delete()
    
    if deleted_count > 0:
        db.commit()
        logging.getLogger("app").info(f"启动时清理 {deleted_count} 个过期验证码")
    
    return deleted_count


@app.get("/")
async def api_root():
    """前后端分离后，页面由前端静态服务提供；此处仅作 API 入口说明。"""
    return {
        "service": "DocuLogic API",
        "docs": "/api/docs",
        "health": "/health",
    }


@app.post("/upload")
@limiter.limit("30/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    prompt: str = Form("QwenVL HTML"),
    pdf_pages: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not model:
        raise HTTPException(
            status_code=503, 
            detail=(
                "模型未加载，无法解析文档\n\n"
                "可能原因：\n"
                "1. 模型尚未下载\n"
                "2. 模型加载失败\n\n"
                "解决方法：\n"
                "• 前往「系统设置」→「模型管理」\n"
                "• 点击「后台下载到模型目录」自动下载\n"
                "• 或点击「重新加载模型」尝试重新加载"
            )
        )

    allowed_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".pdf"}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # 从系统设置获取文件大小限制
    max_upload_size_mb = get_max_upload_size_mb(db)
    MAX_FILE_SIZE = max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大支持 {max_upload_size_mb}MB"
        )
    
    # 检查是否允许多文件上传
    from .settings_service import get_allow_multi_file_upload
    allow_multi = get_allow_multi_file_upload(db)
    
    if not allow_multi:
        # 禁止多文件上传时，检查用户是否有正在处理的任务
        active_jobs = db.query(ParseJob).filter(
            ParseJob.user_id == current_user.id,
            ParseJob.status.in_(["processing", "queued"])
        ).count()
        
        if active_jobs > 0:
            raise HTTPException(
                status_code=429,
                detail="当前有任务正在处理中，请等待完成后再上传新文件（已禁用多文件上传）"
            )

    actor = db.query(User).filter(User.id == current_user.id).first()
    if not actor:
        raise HTTPException(status_code=401, detail="用户不存在")

    max_pdf_pages: Optional[int] = None
    if file_extension == ".pdf":
        try:
            max_pdf_pages = resolve_job_pdf_max_pages(actor, db, pdf_pages)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    job_id = str(uuid.uuid4())
    out_base = get_effective_output_dir(db)
    input_dir = out_base / job_id
    input_dir.mkdir(exist_ok=True)
    input_file_path = input_dir / f"input{file_extension}"

    with open(input_file_path, "wb") as buffer:
        buffer.write(content)

    cancel_ev = register_job(job_id)
    db.add(
        ParseJob(
            job_id=job_id,
            user_id=actor.id,
            status="processing",
            original_filename=file.filename or "",
        )
    )
    db.commit()

    background_tasks.add_task(
        process_document_task,
        str(input_file_path),
        str(input_dir),
        job_id,
        prompt,
        cancel_ev,
        max_pdf_pages,
        actor.id,  # 传递 user_id
    )

    return JSONResponse(
        {
            "job_id": job_id,
            "message": "Document uploaded successfully.",
            "websocket_url": f"/ws/{job_id}",
        }
    )


async def process_document_task(
    input_file_path: str,
    output_dir: str,
    job_id: str,
    prompt: str,
    cancel_event,
    max_pdf_pages: Optional[int] = None,
    user_id: Optional[int] = None,
):
    loop = asyncio.get_running_loop()

    def progress_callback(message: str, progress: int):
        if progress >= 0:
            asyncio.run_coroutine_threadsafe(
                manager.send_progress(job_id, message, progress),
                loop,
            )
        else:
            asyncio.run_coroutine_threadsafe(
                manager.send_error(job_id, message),
                loop,
            )

    db = SessionLocal()
    try:
        # 读取是否显示页码和图片输出模式的设置
        from .models import AppSettings
        settings_row = db.query(AppSettings).filter(AppSettings.id == 1).first()
        show_page_numbers = bool(getattr(settings_row, "show_page_numbers", True)) if settings_row else True
        
        # 获取图片输出模式：优先使用用户个人设置，否则使用系统设置
        user_row = db.query(User).filter(User.id == user_id).first()
        if user_row and getattr(user_row, "image_output_mode", None):
            image_output_mode = user_row.image_output_mode
        else:
            image_output_mode = getattr(settings_row, "image_output_mode", "base64") if settings_row else "base64"
        
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[调试] 任务 {job_id}: 图片输出模式={image_output_mode}")  # 移除用户ID，保护隐私
        
        try:
            result = await asyncio.to_thread(
                model.process_document,
                input_file_path,
                output_dir,
                job_id,
                progress_callback,
                prompt,
                cancel_event,
                max_pdf_pages,
                show_page_numbers,
                image_output_mode,
            )
            user_stopped = bool(result.get("user_stopped"))
            partial = bool(result.get("partial"))
            await manager.send_completion(
                job_id,
                result["output_files"],
                partial=partial,
                user_stopped=user_stopped,
            )
            row = db.query(ParseJob).filter(ParseJob.job_id == job_id).first()
            if row:
                row.status = "stopped" if user_stopped else "completed"
                row.completed_at = datetime.utcnow()
                pp = result.get("pages_parsed")
                if pp is not None:
                    try:
                        row.pages_parsed = max(0, int(pp))
                    except (TypeError, ValueError):
                        pass
                db.commit()
        except Exception as e:
            # 错误信息脱敏：仅记录详细日志，不暴露给用户
            import logging
            logger = logging.getLogger("app")
            logger.exception(f"任务 {job_id} 处理失败")  # 详细错误仅服务端日志
            
            error_msg = "文档处理失败，请联系管理员"  # 用户友好提示
            if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                print(error_msg)
            
            # 检查是否是用户主动停止
            is_user_stopped = "已停止" in str(e)
            
            if is_user_stopped:
                # 用户主动停止，发送 completion 消息而不是 error
                row = db.query(ParseJob).filter(ParseJob.job_id == job_id).first()
                if row:
                    row.status = "stopped"
                    row.completed_at = datetime.utcnow()
                    db.commit()
                
                # 尝试获取已生成的文件
                output_files = {}
                job_dir = Path(output_dir)
                if job_dir.exists():
                    vis_png = job_dir / f"{job_id}_vis.png"
                    vis_zip = job_dir / f"{job_id}_vis.zip"
                    raw_mmd = job_dir / f"{job_id}_raw.mmd"
                    mmd = job_dir / f"{job_id}.mmd"
                    
                    if vis_png.exists():
                        output_files["visualization"] = str(vis_png)
                    elif vis_zip.exists():
                        output_files["visualization"] = str(vis_zip)
                    
                    if raw_mmd.exists():
                        output_files["raw"] = str(raw_mmd)
                    if mmd.exists():
                        output_files["markdown"] = str(mmd)
                
                await manager.send_completion(
                    job_id,
                    output_files,
                    partial=True,
                    user_stopped=True,
                )
            else:
                # 真正的错误
                await manager.send_error(job_id, error_msg)
                row = db.query(ParseJob).filter(ParseJob.job_id == job_id).first()
                if row:
                    row.status = "failed"
                    row.completed_at = datetime.utcnow()
                    db.commit()
                # 推理失败时默认删除本任务输出目录（含上传的 input），避免长期堆积；排查时可设 KEEP_FAILED_JOB_ARTIFACTS=1
                _keep_failed = os.environ.get("KEEP_FAILED_JOB_ARTIFACTS", "").lower() in (
                    "1",
                    "true",
                    "yes",
                )
                if not _keep_failed:
                    shutil.rmtree(output_dir, ignore_errors=True)
                    logging.getLogger("app").info("已清理失败任务目录: %s", output_dir)
    finally:
        db.close()
        remove_job(job_id)


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    # WebSocket 生命周期较长，单独开 Session，避免 Depends(get_db) 过早关闭
    db = SessionLocal()
    try:
        token = websocket.cookies.get("access_token")
        if not token:
            await websocket.close(code=4401)
            return
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            await websocket.close(code=4401)
            return
        try:
            uid = int(payload["sub"])
        except (TypeError, ValueError):
            await websocket.close(code=4401)
            return
        
        # 检查 Token 是否在黑名单中
        from .session_manager import is_token_blacklisted, validate_token_with_session
        if is_token_blacklisted(token):
            await websocket.close(code=4401)
            return
        
        # 验证 Token 是否与会话匹配（单点登录检查）
        if not validate_token_with_session(token, uid):
            await websocket.close(code=4401)
            return
        
        user = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
        if not user:
            await websocket.close(code=4401)
            return
        row = db.query(ParseJob).filter(ParseJob.job_id == job_id).first()
        if not row:
            await websocket.close(code=4404)
            return
        if not user.is_admin and row.user_id != user.id:
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"WebSocket error for job {job_id}: {e}")
    finally:
        manager.disconnect(job_id)


@app.get("/api/settings/public")
async def api_settings_public(db: Session = Depends(get_db)):
    """未登录可访问：注册开关、验证码开关、页数上限等。"""
    return settings_to_public_dict(db)


@app.get("/api/settings")
async def api_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    u = db.query(User).filter(User.id == current_user.id).first() or current_user
    out = {
        "pdf_max_pages": get_effective_pdf_max_pages_for_user(u, db),
        "pdf_max_pages_global": get_pdf_max_pages(db),
        "model_loaded": model is not None,
        "output_dir": str(get_effective_output_dir(db)),
        "is_admin": bool(getattr(current_user, "is_admin", False)),
    }
    if getattr(current_user, "is_admin", False):
        out["admin"] = settings_to_admin_dict(db)
    return out


@app.get("/api/jobs")
async def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    filename: Optional[str] = None,
):
    """普通用户仅自己的任务；管理员可查看全部。支持分页与创建日期、文件名筛选。"""
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    q = db.query(ParseJob)
    if not getattr(current_user, "is_admin", False):
        q = q.filter(ParseJob.user_id == current_user.id)
    if date_from and date_from.strip():
        try:
            df = datetime.strptime(date_from.strip()[:10], "%Y-%m-%d")
            q = q.filter(ParseJob.created_at >= df)
        except ValueError:
            pass
    if date_to and date_to.strip():
        try:
            dt = datetime.strptime(date_to.strip()[:10], "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(ParseJob.created_at < dt)
        except ValueError:
            pass
    if filename and filename.strip():
        # 转义 SQL LIKE 特殊字符，防止通配符注入
        escaped = filename.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        fn = f"%{escaped}%"
        q = q.filter(ParseJob.original_filename.ilike(fn, escape="\\"))

    total = q.count()
    rows = (
        q.order_by(ParseJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    user_map: dict[int, str] = {}
    if getattr(current_user, "is_admin", False) and rows:
        uids = {r.user_id for r in rows}
        for u in db.query(User).filter(User.id.in_(uids)).all():
            user_map[u.id] = u.username

    out_base = get_effective_output_dir(db)
    out = []
    for r in rows:
        job_dir = out_base / r.job_id
        has_files = job_dir.is_dir() and any(job_dir.iterdir())
        cache_cleared = r.cache_cleared_at is not None
        can_dl = (
            not cache_cleared
            and r.status in ("completed", "stopped", "failed")
            and has_files
        )
        item = {
            "job_id": r.job_id,
            "original_filename": r.original_filename or "",
            "status": r.status,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            "completed_at": r.completed_at.isoformat() + "Z" if r.completed_at else None,
            "pages_parsed": getattr(r, "pages_parsed", None),
            "cache_cleared": cache_cleared,
            "can_download": can_dl,
            "clearable": r.status in ("completed", "stopped", "failed")
            and not cache_cleared
            and has_files,
        }
        if getattr(current_user, "is_admin", False):
            item["user_id"] = r.user_id
            item["username"] = user_map.get(r.user_id, "")
        out.append(item)
    return {"jobs": out, "total": total, "page": page, "page_size": page_size}


@app.post("/api/jobs/{job_id}/stop")
@limiter.limit("60/minute")
async def stop_job(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_job_for_actor(db, job_id, current_user)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row.status != "processing":
        raise HTTPException(status_code=400, detail="任务未在运行中")
    ok = cancel_job(job_id)
    return {"ok": ok, "message": "已请求停止" if ok else "无法停止"}


class ClearCacheBody(BaseModel):
    job_ids: List[str]


class BatchDeleteJobsBody(BaseModel):
    job_ids: List[str]


@app.post("/api/jobs/clear-cache")
@limiter.limit("20/minute")
async def clear_job_cache(
    request: Request,
    body: ClearCacheBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cleared = []
    for jid in body.job_ids:
        row = _get_job_for_actor(db, jid, current_user)
        if not row:
            continue
        if row.status not in ("completed", "stopped", "failed"):
            continue
        if row.cache_cleared_at is not None:
            continue
        job_dir = get_effective_output_dir(db) / jid
        if job_dir.is_dir():
            shutil.rmtree(job_dir, ignore_errors=True)
        row.cache_cleared_at = datetime.utcnow()
        cleared.append(jid)
    db.commit()
    return {"ok": True, "cleared": cleared}


@app.post("/api/jobs/batch-delete")
@limiter.limit("30/minute")
async def batch_delete_jobs(
    request: Request,
    body: BatchDeleteJobsBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除任务记录及输出目录。规则与 DELETE /api/jobs/{job_id} 一致；进行中任务记入 failed。"""
    raw = body.job_ids or []
    ids = list(dict.fromkeys(str(j).strip() for j in raw if str(j).strip()))[:500]
    if not ids:
        return {"ok": True, "deleted": [], "failed": []}

    out_base = get_effective_output_dir(db)
    deleted: List[str] = []
    failed: list[dict] = []

    for jid in ids:
        row = _get_job_for_actor(db, jid, current_user)
        if not row:
            failed.append({"job_id": jid, "detail": "任务不存在或无权操作"})
            continue
        if row.status == "processing":
            failed.append({"job_id": jid, "detail": "任务进行中，请先停止后再删除"})
            continue
        try:
            job_dir = out_base / jid
            if job_dir.is_dir():
                shutil.rmtree(job_dir, ignore_errors=True)
            remove_job(jid)
            manager.disconnect(jid)
            db.delete(row)
            deleted.append(jid)
        except Exception as e:
            failed.append({"job_id": jid, "detail": str(e)})

    db.commit()
    return {"ok": True, "deleted": deleted, "failed": failed}


@app.delete("/api/jobs/{job_id}")
@limiter.limit("60/minute")
async def delete_job_record(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除任务记录及输出目录。普通用户仅能删自己的任务；管理员可删任意任务。进行中任务需先停止。"""
    row = _get_job_for_actor(db, job_id, current_user)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row.status == "processing":
        raise HTTPException(status_code=400, detail="任务进行中，请先停止后再删除")
    job_dir = get_effective_output_dir(db) / job_id
    if job_dir.is_dir():
        shutil.rmtree(job_dir, ignore_errors=True)
    remove_job(job_id)
    manager.disconnect(job_id)
    db.delete(row)
    db.commit()
    return {"ok": True}


class RecoverStaleJobsBody(BaseModel):
    max_stale_minutes: Optional[int] = None  # None 表示使用系统设置


@app.post("/api/admin/recover-stale-jobs")
@limiter.limit("10/minute")
async def recover_stale_jobs_endpoint(
    request: Request,
    body: RecoverStaleJobsBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    管理员接口：手动检测并恢复僵尸任务。
    
    僵尸任务定义：
    - 状态为 processing
    - 创建时间超过配置的超时时长（默认从系统设置读取）
    - 对应的后台进程已停止（不在 cancel_events 中）
    
    此操作会：
    1. 将僵尸任务标记为 failed
    2. 清理对应的输出目录
    3. 设置 completed_at 时间戳
    
    只有管理员可以调用此接口。
    """
    # 检查是否为管理员
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 如果指定了超时时长，进行验证；否则使用系统设置
    if body.max_stale_minutes is not None:
        max_minutes = body.max_stale_minutes
        if max_minutes < 1 or max_minutes > 1440:  # 最大 24 小时
            raise HTTPException(status_code=400, detail="max_stale_minutes 必须在 1-1440 之间")
    else:
        max_minutes = None  # 让 _recover_stale_jobs 从系统设置读取
    
    recovered_count = _recover_stale_jobs(db, max_stale_minutes=max_minutes)
    
    return {
        "ok": True,
        "recovered_count": recovered_count,
        "message": f"已恢复 {recovered_count} 个僵尸任务"
    }


def _resolve_visualization_path(job_dir: Path, job_id: str):
    z = job_dir / f"{job_id}_vis.zip"
    png = job_dir / f"{job_id}_vis.png"
    if z.is_file():
        return z, f"{job_id}_vis.zip", "application/zip"
    if png.is_file():
        return png, f"{job_id}_vis.png", "image/png"
    raise HTTPException(status_code=404, detail="Visualization file not found")


@app.get("/download/{job_id}/assets/{image_filename}")
async def download_asset_image(
    job_id: str,
    image_filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载单独的图片资源文件（仅当输出模式为 separate 时生成）"""
    # 检查用户是否有下载图片的权限
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 管理员始终有权限；普通用户需要检查 can_download_images
    if not getattr(user, "is_admin", False) and not getattr(user, "can_download_images", True):
        raise HTTPException(status_code=403, detail="您没有下载图片资源的权限")
    
    row = _get_job_for_actor(db, job_id, current_user)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.cache_cleared_at is not None:
        raise HTTPException(
            status_code=410,
            detail="该任务的缓存已清除，无法下载",
        )

    job_dir = get_effective_output_dir(db) / job_id
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")
    
    # 安全检查：防止路径遍历攻击
    import os
    safe_filename = os.path.basename(image_filename)  # 仅保留文件名，去除路径
    if not safe_filename or safe_filename != image_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    assets_dir = job_dir / "assets"
    file_path = (assets_dir / safe_filename).resolve()  # 解析绝对路径
    
    # 确保文件在允许的目录内
    if not str(file_path).startswith(str(assets_dir.resolve())):
        raise HTTPException(status_code=403, detail="非法访问")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # 确定 MIME 类型
    ext = file_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    media_type = mime_types.get(ext, "application/octet-stream")
    
    return FileResponse(path=file_path, filename=safe_filename, media_type=media_type)


@app.get("/download/{job_id}/{file_type}")
async def download_result(
    job_id: str,
    file_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_job_for_actor(db, job_id, current_user)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.cache_cleared_at is not None:
        raise HTTPException(
            status_code=410,
            detail="该任务的缓存已清除，无法下载",
        )

    job_dir = get_effective_output_dir(db) / job_id
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")

    if file_type == "visualization":
        file_path, filename, media = _resolve_visualization_path(job_dir, job_id)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache",
            }
        )

    file_types = {
        "raw": (f"{job_id}_raw.mmd", "text/plain; charset=utf-8"),
        "markdown": (f"{job_id}.mmd", "text/plain; charset=utf-8"),
        "result": (f"{job_id}_result.zip", "application/zip"),
    }
    if file_type not in file_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    fname, media = file_types[file_type]
    file_path = job_dir / fname
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=fname,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Cache-Control": "no-cache",
        }
    )


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    综合健康检查端点
    
    检查项：
    - Nginx: 通过请求到达此端点即表示 Nginx 正常
    - Backend: FastAPI 服务正常运行
    - Database: 数据库连接正常
    - Model: 模型加载状态（可选）
    """
    checks = {
        "nginx": "ok",  # 能到达此端点说明 Nginx 正常
        "backend": "ok",  # FastAPI 正常运行
    }
    
    # 检查数据库连接
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    # 检查模型状态（不影响整体健康状态）
    checks["model_loaded"] = model is not None
    
    # 如果数据库异常，返回 503
    if checks["database"] != "ok":
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "checks": checks}
        )
    
    return {"status": "healthy", "checks": checks}


@app.post("/api/jobs/batch-download")
async def batch_download_results(
    job_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量下载多个任务的解析结果
    
    参数：
        job_ids: 任务 ID 列表
    
    返回：
        ZIP 文件，包含所有任务的解析结果
    """
    import zipfile
    import tempfile
    from io import BytesIO
    
    if not job_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个任务")
    
    # 验证所有任务ID并检查权限
    valid_jobs = []
    for job_id in job_ids:
        row = _get_job_for_actor(db, job_id, current_user)
        if not row:
            continue
        if row.cache_cleared_at is not None:
            continue
        if row.status != "completed":
            continue
        
        job_dir = get_effective_output_dir(db) / job_id
        if not job_dir.is_dir():
            continue
        
        valid_jobs.append((job_id, row, job_dir))
    
    if not valid_jobs:
        raise HTTPException(status_code=404, detail="没有找到可下载的任务")
    
    # 创建临时 ZIP 文件
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for job_id, job_row, job_dir in valid_jobs:
                # 为每个任务创建子目录
                task_prefix = f"{job_id}_{job_row.original_filename or 'document'}"
                # 清理文件名中的非法字符
                task_prefix = "".join(c for c in task_prefix if c.isalnum() or c in (' ', '-', '_', '.'))
                
                # 添加 Markdown 文件
                md_file = job_dir / f"{job_id}.mmd"
                if md_file.exists():
                    arc_name = f"{task_prefix}/{job_id}.mmd"
                    zipf.write(md_file, arc_name)
                
                # 添加原始输出文件
                raw_file = job_dir / f"{job_id}_raw.mmd"
                if raw_file.exists():
                    arc_name = f"{task_prefix}/{job_id}_raw.mmd"
                    zipf.write(raw_file, arc_name)
                
                # 添加可视化文件
                vis_zip = job_dir / f"{job_id}_vis.zip"
                vis_png = job_dir / f"{job_id}_vis.png"
                if vis_zip.exists():
                    arc_name = f"{task_prefix}/{job_id}_vis.zip"
                    zipf.write(vis_zip, arc_name)
                elif vis_png.exists():
                    arc_name = f"{task_prefix}/{job_id}_vis.png"
                    zipf.write(vis_png, arc_name)
                
                # 添加 assets 文件夹（如果存在）
                assets_dir = job_dir / "assets"
                if assets_dir.is_dir():
                    for asset_file in assets_dir.iterdir():
                        if asset_file.is_file():
                            arc_name = f"{task_prefix}/assets/{asset_file.name}"
                            zipf.write(asset_file, arc_name)
        
        # 生成下载文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"DocuLogic_批量下载_{timestamp}.zip"
        
        return FileResponse(
            path=temp_zip.name,
            filename=download_filename,
            media_type="application/zip",
            background=BackgroundTasks().add_task(lambda p=Path(temp_zip.name): p.unlink(missing_ok=True))
        )
    
    except Exception as e:
        # 清理临时文件
        Path(temp_zip.name).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"批量下载失败: {str(e)}")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

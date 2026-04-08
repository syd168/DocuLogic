import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

from passlib.exc import UnknownHashError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth_security import (
    CODE_EXPIRE_MINUTES,
    create_access_token,
    generate_digit_code,
    get_login_timeout_minutes,
    hash_password,
    hash_verification_code,
    should_refresh_token,
    verify_code_hash,
    verify_password,
)
from ..verification_cache import (
    store_verification_code,
    get_verification_code_hash,
    delete_verification_code,
    verify_verification_code,
)
from ..session_manager import (
    create_user_session,
    destroy_user_session,
    revoke_token,
    check_single_login,
)
from ..captcha import verify_captcha
from ..database import get_db
from ..deps import get_current_user
from ..email_svc import send_forgot_password_email, send_verification_email
from ..models import User, VerificationCode
from ..phone_utils import normalize_cn_mobile, sms_recipient_key, synthetic_email_for_phone
from ..rate_limit import limiter
from ..settings_service import (
    get_app_settings_row,
    get_effective_email_config,
    get_effective_sms_config,
    register_requires_email_verification,
    register_requires_phone_verification,
)
from ..sms_svc import send_sms_code


def _require_captcha(flag: bool, captcha_id: Optional[str], captcha_code: Optional[str]) -> None:
    if not flag:
        return
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=400, detail="请完成图形验证码")
    if not verify_captcha(captcha_id, captcha_code):
        raise HTTPException(status_code=400, detail="图形验证码错误或已过期")


router = APIRouter(prefix="/api/auth", tags=["auth"])
_log = logging.getLogger(__name__)


def _resolve_login_user(db: Session, st, ident_raw: str) -> Optional[User]:
    raw = ident_raw.strip()
    if not raw:
        return None
    phone = normalize_cn_mobile(raw)
    if phone:
        if not bool(getattr(st, "login_phone_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭手机号登录")
        return db.query(User).filter(User.phone == phone).first()
    if not bool(getattr(st, "login_email_enabled", True)):
        raise HTTPException(status_code=400, detail="当前已关闭用户名或邮箱登录")
    return (
        db.query(User)
        .filter(or_(User.username == raw, User.email == raw.lower()))
        .first()
    )


class SendCodeBody(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_channel(self):
        e = str(self.email).strip() if self.email is not None else ""
        p = normalize_cn_mobile(self.phone or "")
        if bool(e) == bool(p):
            raise ValueError("请填写邮箱或手机号之一")
        return self


class RegisterBody(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    code: Optional[str] = Field(None, max_length=6)
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_ascii(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,32}$", v):
            raise ValueError("用户名须为 3–32 位字母、数字或下划线")
        return v

    @model_validator(mode="after")
    def one_contact(self):
        e = str(self.email).strip() if self.email is not None else ""
        p = normalize_cn_mobile(self.phone or "")
        if bool(e) == bool(p):
            raise ValueError("请填写邮箱或手机号之一")
        return self


class ForgotSendBody(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one(self):
        e = str(self.email).strip() if self.email is not None else ""
        p = normalize_cn_mobile(self.phone or "")
        if bool(e) == bool(p):
            raise ValueError("请填写邮箱或手机号之一")
        return self


class ForgotResetBody(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def one_id(self):
        e = str(self.email).strip() if self.email is not None else ""
        p = normalize_cn_mobile(self.phone or "")
        if bool(e) == bool(p):
            raise ValueError("请填写邮箱或手机号之一")
        return self


class LoginBody(BaseModel):
    username: str = Field(..., description="用户名、邮箱或手机号")
    password: str
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None


@router.post("/send-code")
@limiter.limit("5/minute")
async def send_verification_code(request: Request, body: SendCodeBody, db: Session = Depends(get_db)):
    st = get_app_settings_row(db)
    if not st.registration_enabled:
        raise HTTPException(status_code=403, detail="注册已关闭")
    if not bool(getattr(st, "register_email_enabled", True)) and not bool(getattr(st, "register_phone_enabled", True)):
        raise HTTPException(status_code=403, detail="注册已关闭")
    _require_captcha(st.captcha_register_enabled, body.captcha_id, body.captcha_code)

    if body.email:
        if not bool(getattr(st, "register_email_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭邮箱注册")
        if not register_requires_email_verification(db):
            raise HTTPException(
                status_code=400,
                detail="当前未配置发信服务，无需邮箱验证码，请直接在注册页填写信息完成注册",
            )
        email = str(body.email).lower().strip()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已注册")

        code = generate_digit_code(6)
        try:
            send_verification_email(db, email, code)
        except Exception:
            _log.exception("send verification email failed email=%s", email)
            raise HTTPException(status_code=502, detail="发送邮件失败") from None

        # 尝试存储到 Redis，失败则降级到数据库
        if not store_verification_code(email, code, "register"):
            # 降级到数据库存储
            expires = datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
            db.query(VerificationCode).filter(
                VerificationCode.email == email,
                VerificationCode.purpose == "register",
            ).delete()
            row = VerificationCode(
                email=email,
                code_hash=hash_verification_code(email, code),
                expires_at=expires,
                purpose="register",
            )
            db.add(row)
            db.commit()
            _log.info(f"验证码已存储到数据库（Redis不可用）: {email}")
        else:
            _log.debug(f"验证码已存储到 Redis: {email}")

        cfg = get_effective_email_config(db)
        return {"ok": True, "message": "验证码已发送", "email_mock": cfg["mock"]}

    # 手机注册验证码
    if not bool(getattr(st, "register_phone_enabled", True)):
        raise HTTPException(status_code=400, detail="当前已关闭手机号注册")
    phone = normalize_cn_mobile(body.phone or "")
    if not phone:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if not register_requires_phone_verification(db):
        raise HTTPException(
            status_code=400,
            detail="当前未配置短信服务，无需手机验证码，请直接在注册页填写信息完成注册",
        )
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")

    rkey = sms_recipient_key(phone)
    code = generate_digit_code(6)
    try:
        send_sms_code(db, phone, code, "register")
    except Exception as e:
        _log.exception("send sms register failed phone=%s", phone)
        raise HTTPException(status_code=502, detail="发送短信失败") from e

    expires = datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
    db.query(VerificationCode).filter(
        VerificationCode.email == rkey,
        VerificationCode.purpose == "register",
    ).delete()
    row = VerificationCode(
        email=rkey,
        code_hash=hash_verification_code(rkey, code),
        expires_at=expires,
        purpose="register",
    )
    db.add(row)
    db.commit()

    sms = get_effective_sms_config(db)
    return {"ok": True, "message": "验证码已发送", "sms_mock": sms["mock"]}


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, body: RegisterBody, db: Session = Depends(get_db)):
    st = get_app_settings_row(db)
    if not st.registration_enabled:
        raise HTTPException(status_code=403, detail="注册已关闭")
    if not bool(getattr(st, "register_email_enabled", True)) and not bool(getattr(st, "register_phone_enabled", True)):
        raise HTTPException(status_code=403, detail="注册已关闭")

    # 验证密码规则
    from ..settings_service import validate_password
    is_valid, error_msg = validate_password(body.password, db)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    code = (body.code or "").strip()

    if body.email:
        if not bool(getattr(st, "register_email_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭邮箱注册")
        email = str(body.email).lower().strip()
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="邮箱已被注册")
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=400, detail="用户名已被占用")

        need_code = register_requires_email_verification(db)
        if st.captcha_register_enabled and not need_code:
            _require_captcha(True, body.captcha_id, body.captcha_code)

        if need_code:
            if len(code) != 6:
                raise HTTPException(status_code=400, detail="请填写 6 位邮箱验证码")
            row = (
                db.query(VerificationCode)
                .filter(VerificationCode.email == email, VerificationCode.purpose == "register")
                .order_by(VerificationCode.created_at.desc())
                .first()
            )
            if not row or row.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="验证码无效或已过期，请重新获取")
            if not verify_code_hash(email, code, row.code_hash):
                raise HTTPException(status_code=400, detail="验证码错误")

        user = User(
            email=email,
            phone=None,
            username=body.username,
            hashed_password=hash_password(body.password),
        )
        db.add(user)
        if need_code:
            db.query(VerificationCode).filter(
                VerificationCode.email == email,
                VerificationCode.purpose == "register",
            ).delete()
        db.commit()
        db.refresh(user)

    else:
        if not bool(getattr(st, "register_phone_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭手机号注册")
        phone = normalize_cn_mobile(body.phone or "")
        if not phone:
            raise HTTPException(status_code=400, detail="手机号格式不正确")
        syn_email = synthetic_email_for_phone(phone)
        if db.query(User).filter(or_(User.phone == phone, User.email == syn_email)).first():
            raise HTTPException(status_code=400, detail="该手机号已注册")
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=400, detail="用户名已被占用")

        need_code = register_requires_phone_verification(db)
        if st.captcha_register_enabled and not need_code:
            _require_captcha(True, body.captcha_id, body.captcha_code)

        rkey = sms_recipient_key(phone)
        if need_code:
            if len(code) != 6:
                raise HTTPException(status_code=400, detail="请填写 6 位短信验证码")
            row = (
                db.query(VerificationCode)
                .filter(VerificationCode.email == rkey, VerificationCode.purpose == "register")
                .order_by(VerificationCode.created_at.desc())
                .first()
            )
            if not row or row.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="验证码无效或已过期，请重新获取")
            if not verify_code_hash(rkey, code, row.code_hash):
                raise HTTPException(status_code=400, detail="验证码错误")

        user = User(
            email=syn_email,
            phone=phone,
            username=body.username,
            hashed_password=hash_password(body.password),
        )
        db.add(user)
        if need_code:
            db.query(VerificationCode).filter(
                VerificationCode.email == rkey,
                VerificationCode.purpose == "register",
            ).delete()
        db.commit()
        db.refresh(user)

    # 使用动态配置的登录超时时间
    timeout_minutes = get_login_timeout_minutes(db)
    from datetime import timedelta
    token = create_access_token(
        {"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(minutes=timeout_minutes)
    )
    
    # 检查单点登录（如果用户已在其他终端登录，旧 token 将被拉黑）
    old_session = check_single_login(user.id, token)
    if old_session:
        logger.info(f"用户 {user.username} 在新终端登录，旧会话已被替换")
    
    # 创建新的用户会话
    create_user_session(
        user_id=user.id,
        username=user.username,
        token=token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        ttl_seconds=timeout_minutes * 60
    )
    
    resp = JSONResponse(
        content={"ok": True, "message": "注册成功", "username": user.username},
        status_code=201,
    )
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=timeout_minutes * 60,  # 转换为秒
        path="/",
    )
    return resp


@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, body: LoginBody, db: Session = Depends(get_db)):
    st = get_app_settings_row(db)
    if not bool(getattr(st, "login_email_enabled", True)) and not bool(getattr(st, "login_phone_enabled", True)):
        raise HTTPException(status_code=403, detail="登录已关闭")
    _require_captcha(st.captcha_login_enabled, body.captcha_id, body.captcha_code)

    password = body.password
    user = _resolve_login_user(db, st, body.username)

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail=f"账户已锁定，请于 {user.locked_until.strftime('%H:%M:%S')} UTC 后再试",
        )

    try:
        password_ok = verify_password(password, user.hashed_password)
    except UnknownHashError:
        _log.exception("密码哈希无法校验 user_id=%s（请检查数据库中 hashed_password 格式）", user.id)
        raise HTTPException(status_code=401, detail="用户名或密码错误") from None
    except Exception:
        _log.exception("校验密码时异常 user_id=%s", user.id)
        raise HTTPException(status_code=500, detail="登录校验失败，请稍后重试") from None

    if not password_ok:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_login_attempts = 0
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # 使用动态配置的登录超时时间
    timeout_minutes = get_login_timeout_minutes(db)
    token = create_access_token(
        {"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(minutes=timeout_minutes)
    )
    
    # 检查单点登录（如果用户已在其他终端登录，旧 token 将被拉黑）
    old_session = check_single_login(user.id, token)
    if old_session:
        logger.info(f"用户 {user.username} 在新终端登录，旧会话已被替换")
    
    # 创建新的用户会话
    create_user_session(
        user_id=user.id,
        username=user.username,
        token=token,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        ttl_seconds=timeout_minutes * 60
    )
    
    resp = JSONResponse(content={"ok": True, "username": user.username})
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=timeout_minutes * 60,  # 转换为秒
        path="/",
    )
    return resp


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """用户登出，将 Token 加入黑名单并销毁会话"""
    from ..deps import get_token_from_request
    from ..auth_security import decode_token
    
    token = get_token_from_request(request)
    if token:
        # 解码 token 获取用户 ID
        payload = decode_token(token)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
                # 将 token 加入黑名单
                revoke_token(token, reason="manual_logout")
                # 销毁用户会话
                destroy_user_session(user_id, reason="logout")
                logger.info(f"用户 {user_id} 已登出")
            except (TypeError, ValueError):
                pass
    
    resp = JSONResponse(content={"ok": True, "message": "已登出"})
    resp.delete_cookie("access_token", path="/")
    return resp


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    刷新 JWT Token
    
    如果当前 token 即将过期（剩余时间 < 60分钟），则颁发新 token。
    用户在活跃使用时，前端应定期调用此接口以保持登录状态。
    """
    from ..auth_security import decode_token, get_login_timeout_minutes
    from ..deps import get_token_from_request
    
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    
    # 验证当前 token 是否有效
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效令牌",
        )
    
    try:
        uid = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="无效令牌")
    
    # 检查用户是否存在且活跃
    user = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    
    # 检查是否需要刷新（剩余时间 < 60分钟）
    if not should_refresh_token(token, refresh_threshold_minutes=60):
        # 不需要刷新，返回当前 token 仍然有效
        return {
            "ok": True,
            "need_refresh": False,
            "message": "Token 仍然有效",
        }
    
    # 需要刷新，生成新 token
    timeout_minutes = get_login_timeout_minutes(db)
    expires_delta = timedelta(minutes=timeout_minutes)
    new_token = create_access_token(
        subject={"sub": str(user.id), "username": user.username},
        expires_delta=expires_delta,
    )
    
    # 设置新 token 到 cookie
    resp = JSONResponse(content={
        "ok": True,
        "need_refresh": True,
        "message": "Token 已刷新",
    })
    resp.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=False,  # 生产环境应设为 True（HTTPS）
        samesite="lax",
        path="/",
        max_age=timeout_minutes * 60,  # 秒
    )
    
    return resp


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户详细信息，包括权限和配额"""
    from ..settings_service import get_effective_pdf_max_pages_for_user, get_pdf_max_pages
    
    # 计算用户的实际 PDF 页数上限
    pdf_max_pages_global = get_pdf_max_pages(db)
    pdf_max_pages_effective = get_effective_pdf_max_pages_for_user(user, db)
    
    # 判断是否使用系统默认值
    pdf_use_default = user.pdf_max_pages is None
    
    # 图片输出模式
    image_output_mode = getattr(user, "image_output_mode", None)
    image_output_use_default = image_output_mode is None
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": getattr(user, "phone", None) or "",
        "is_admin": bool(getattr(user, "is_admin", False)),
        "is_active": bool(getattr(user, "is_active", True)),
        "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        # PDF 解析配额
        "pdf_max_pages_global": pdf_max_pages_global,
        "pdf_max_pages_personal": user.pdf_max_pages,
        "pdf_max_pages_effective": pdf_max_pages_effective,
        "pdf_use_default": pdf_use_default,
        # 图片输出配置
        "can_download_images": bool(getattr(user, "can_download_images", True)),
        "image_output_mode": image_output_mode,
        "image_output_use_default": image_output_use_default,
    }


@router.post("/forgot-send-code")
@limiter.limit("5/minute")
async def forgot_send_code(request: Request, body: ForgotSendBody, db: Session = Depends(get_db)):
    st = get_app_settings_row(db)
    if not bool(getattr(st, "forgot_email_enabled", True)) and not bool(getattr(st, "forgot_phone_enabled", True)):
        raise HTTPException(status_code=403, detail="找回密码已关闭")
    _require_captcha(st.captcha_forgot_enabled, body.captcha_id, body.captcha_code)

    if body.email:
        if not bool(getattr(st, "forgot_email_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭邮箱找回")
        email = str(body.email).lower().strip()
        u = db.query(User).filter(User.email == email).first()
        if not u:
            return {"ok": True, "message": "若账号已注册将收到验证码"}
        db.query(VerificationCode).filter(
            VerificationCode.email == email,
            VerificationCode.purpose == "forgot",
        ).delete()
        code = generate_digit_code(6)
        expires = datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
        row = VerificationCode(
            email=email,
            code_hash=hash_verification_code(email, code),
            expires_at=expires,
            purpose="forgot",
        )
        db.add(row)
        db.commit()
        try:
            send_forgot_password_email(db, email, code)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"邮件发送失败: {e}") from e
        is_mock = os.environ.get("EMAIL_MOCK", "true").lower() in ("1", "true", "yes")
        return {"ok": True, "message": "验证码已发送", "email_mock": is_mock}

    if not bool(getattr(st, "forgot_phone_enabled", True)):
        raise HTTPException(status_code=400, detail="当前已关闭手机号找回")
    phone = normalize_cn_mobile(body.phone or "")
    if not phone:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if not register_requires_phone_verification(db):
        raise HTTPException(status_code=400, detail="当前未配置短信服务，无法发送手机验证码")

    u = db.query(User).filter(User.phone == phone).first()
    if not u:
        return {"ok": True, "message": "若账号已注册将收到验证码"}

    rkey = sms_recipient_key(phone)
    db.query(VerificationCode).filter(
        VerificationCode.email == rkey,
        VerificationCode.purpose == "forgot",
    ).delete()
    code = generate_digit_code(6)
    expires = datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
    row = VerificationCode(
        email=rkey,
        code_hash=hash_verification_code(rkey, code),
        expires_at=expires,
        purpose="forgot",
    )
    db.add(row)
    db.commit()
    try:
        send_sms_code(db, phone, code, "forgot")
    except Exception as e:
        _log.exception("forgot sms failed")
        raise HTTPException(status_code=502, detail="发送短信失败") from e
    sms = get_effective_sms_config(db)
    return {"ok": True, "message": "验证码已发送", "sms_mock": sms["mock"]}


@router.post("/forgot-reset")
@limiter.limit("10/minute")
async def forgot_reset(request: Request, body: ForgotResetBody, db: Session = Depends(get_db)):
    st = get_app_settings_row(db)
    code = body.code.strip()

    if body.email:
        if not bool(getattr(st, "forgot_email_enabled", True)):
            raise HTTPException(status_code=400, detail="当前已关闭邮箱找回")
        email = str(body.email).lower().strip()
        row = (
            db.query(VerificationCode)
            .filter(VerificationCode.email == email, VerificationCode.purpose == "forgot")
            .order_by(VerificationCode.created_at.desc())
            .first()
        )
        if not row or row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="验证码无效或已过期")
        if not verify_code_hash(email, code, row.code_hash):
            raise HTTPException(status_code=400, detail="验证码错误")
        u = db.query(User).filter(User.email == email).first()
        if not u:
            raise HTTPException(status_code=400, detail="用户不存在")
        
        # 验证新密码规则
        from ..settings_service import validate_password
        is_valid, error_msg = validate_password(body.new_password, db)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        u.hashed_password = hash_password(body.new_password)
        db.query(VerificationCode).filter(
            VerificationCode.email == email,
            VerificationCode.purpose == "forgot",
        ).delete()
        db.commit()
        return {"ok": True, "message": "密码已重置，请使用新密码登录"}

    if not bool(getattr(st, "forgot_phone_enabled", True)):
        raise HTTPException(status_code=400, detail="当前已关闭手机号找回")
    phone = normalize_cn_mobile(body.phone or "")
    if not phone:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    rkey = sms_recipient_key(phone)
    row = (
        db.query(VerificationCode)
        .filter(VerificationCode.email == rkey, VerificationCode.purpose == "forgot")
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="验证码无效或已过期")
    if not verify_code_hash(rkey, code, row.code_hash):
        raise HTTPException(status_code=400, detail="验证码错误")
    u = db.query(User).filter(User.phone == phone).first()
    if not u:
        raise HTTPException(status_code=400, detail="用户不存在")
    
    # 验证新密码规则
    from ..settings_service import validate_password
    is_valid, error_msg = validate_password(body.new_password, db)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    u.hashed_password = hash_password(body.new_password)
    db.query(VerificationCode).filter(
        VerificationCode.email == rkey,
        VerificationCode.purpose == "forgot",
    ).delete()
    db.commit()
    return {"ok": True, "message": "密码已重置，请使用新密码登录"}


class ChangePasswordBody(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/change-password")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    body: ChangePasswordBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    # 验证新密码规则
    from ..settings_service import validate_password
    is_valid, error_msg = validate_password(body.new_password, db)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "密码已更新"}

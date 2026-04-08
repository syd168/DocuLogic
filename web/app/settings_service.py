"""
系统配置服务模块

负责管理系统全局配置（AppSettings），包括：
- 配置的读取和更新
- 路径验证和安全检查
- 邮件和短信服务配置管理
- PDF 解析配额计算
- 密码规则配置和验证

优先级策略：数据库配置 > 环境变量 > 默认值
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from .models import User

from .paths import DEFAULT_MODEL_WEIGHTS_DIR, DEFAULT_PARSE_OUTPUT_DIR, PROJECT_ROOT

_WEB_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = PROJECT_ROOT


def get_app_settings_row(db: Session):
    """
    获取系统配置行（单例，id=1）
    
    如果配置不存在则自动创建。
    
    Args:
        db: 数据库会话
        
    Returns:
        AppSettings 实例
    """
    from .models import AppSettings

    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row is None:
        row = AppSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def ensure_app_settings_row(db: Session):
    """确保系统配置行存在（不返回值）"""
    get_app_settings_row(db)


def _allowed_path_prefixes() -> list[Path]:
    raw = os.environ.get("SETTINGS_PATH_ALLOW_PREFIXES", "")
    if raw.strip():
        return [Path(p.strip()).expanduser().resolve() for p in raw.split(",") if p.strip()]
    return [
        _PROJECT_ROOT.resolve(),
        Path("/data").resolve() if Path("/data").exists() else _PROJECT_ROOT.resolve(),
    ]


def validate_output_dir(path: Path) -> Path:
    """
    验证输出目录路径是否在允许的前缀内
    
    出于安全考虑，限制输出目录必须在配置的路径前缀内。
    
    Args:
        path: 待验证的路径
        
    Returns:
        解析后的绝对路径
        
    Raises:
        ValueError: 路径不在允许的前缀内
    """
    p = path.expanduser().resolve()
    if not _path_allowed(p):
        raise ValueError("输出路径不在允许的前缀内（可设置 SETTINGS_PATH_ALLOW_PREFIXES）")
    return p


def validate_model_path(path: Path) -> Path:
    """
    验证模型路径是否在允许的前缀内
    
    Args:
        path: 待验证的模型路径
        
    Returns:
        解析后的绝对路径
        
    Raises:
        ValueError: 路径不在允许的前缀内
    """
    p = path.expanduser().resolve()
    if not _path_allowed(p):
        raise ValueError("模型路径不在允许的前缀内（可设置 SETTINGS_PATH_ALLOW_PREFIXES）")
    return p


def _path_allowed(p: Path) -> bool:
    try:
        rp = p.resolve()
    except OSError:
        return False
    for prefix in _allowed_path_prefixes():
        try:
            rp.relative_to(prefix)
            return True
        except ValueError:
            continue
    return False


def get_effective_output_dir(db: Session) -> Path:
    """优先级：数据库 output_dir > 环境变量 OUTPUT_DIR / PARSE_OUTPUT_DIR > 项目根 out/"""
    row = get_app_settings_row(db)
    if row.output_dir and str(row.output_dir).strip():
        p = validate_output_dir(Path(str(row.output_dir).strip()))
        p.mkdir(parents=True, exist_ok=True)
        return p
    env_out = (os.environ.get("OUTPUT_DIR") or os.environ.get("PARSE_OUTPUT_DIR") or "").strip()
    if env_out:
        p = validate_output_dir(Path(env_out))
        p.mkdir(parents=True, exist_ok=True)
        return p
    d = DEFAULT_PARSE_OUTPUT_DIR.resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_effective_model_path_str(db: Session) -> Optional[str]:
    """优先级：数据库 model_local_path > 环境变量 MODEL_PATH > logics-parsingv2/weights/Logics-Parsing-v2（若存在）"""
    row = get_app_settings_row(db)
    if row.model_local_path and str(row.model_local_path).strip():
        p = validate_model_path(Path(str(row.model_local_path).strip()))
        return str(p)
    env = os.environ.get("MODEL_PATH", "").strip()
    if env:
        return env
    if DEFAULT_MODEL_WEIGHTS_DIR.is_dir():
        return str(DEFAULT_MODEL_WEIGHTS_DIR.resolve())
    return None


def get_effective_email_config(db: Session) -> dict[str, Any]:
    """邮件发送参数：数据库优先，缺省项回退到环境变量。"""
    row = get_app_settings_row(db)
    mock = bool(row.email_mock) if getattr(row, "email_mock", None) is not None else os.environ.get("EMAIL_MOCK", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    host = (row.smtp_host or "").strip() or os.environ.get("SMTP_HOST", "").strip()
    raw_port = getattr(row, "smtp_port", None)
    if raw_port is not None and int(raw_port) > 0:
        port = int(raw_port)
    else:
        port = int(os.environ.get("SMTP_PORT", "587") or "587")
    user = (row.smtp_user or "").strip() or os.environ.get("SMTP_USER", "").strip()
    password = (row.smtp_password or "").strip() or os.environ.get("SMTP_PASSWORD", "")
    from_addr = (row.smtp_from or "").strip() or os.environ.get("SMTP_FROM", "").strip() or user
    use_tls = bool(row.smtp_use_tls) if getattr(row, "smtp_use_tls", None) is not None else True
    return {
        "mock": mock,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_tls": use_tls,
    }


def register_requires_email_verification(db: Session) -> bool:
    """注册是否需要邮箱验证码：非模拟模式且 SMTP 主机、账号、密码均已配置。"""
    cfg = get_effective_email_config(db)
    if cfg["mock"]:
        return False
    if not (cfg.get("host") or "").strip():
        return False
    if not (cfg.get("user") or "").strip():
        return False
    if not (cfg.get("password") or "").strip():
        return False
    return True


def get_effective_sms_config(db: Session) -> dict[str, Any]:
    """短信：数据库优先，URL/密钥可回退环境变量 SMS_HTTP_URL / SMS_HTTP_SECRET。"""
    import json

    row = get_app_settings_row(db)
    mock = bool(getattr(row, "sms_mock", True))
    url = ((getattr(row, "sms_http_url", None) or "") or os.environ.get("SMS_HTTP_URL", "")).strip()
    secret = ((getattr(row, "sms_http_secret", None) or "") or os.environ.get("SMS_HTTP_SECRET", "")).strip()
    raw_h = (getattr(row, "sms_http_headers_json", None) or "").strip()
    tpl = (getattr(row, "sms_http_body_template", None) or "").strip()
    headers: dict[str, Any] = {}
    if raw_h:
        try:
            headers = dict(json.loads(raw_h))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return {
        "mock": mock,
        "http_url": url,
        "http_secret": secret,
        "http_headers": headers,
        "http_body_template": tpl or None,
    }


def register_requires_phone_verification(db: Session) -> bool:
    """注册是否需要手机验证码：非模拟且已配置短信 HTTP 回调地址。"""
    cfg = get_effective_sms_config(db)
    if cfg["mock"]:
        return False
    return bool((cfg.get("http_url") or "").strip())


def get_pdf_max_pages(db: Optional[Session] = None) -> int:
    close = False
    if db is None:
        from .database import SessionLocal

        db = SessionLocal()
        close = True
    try:
        row = get_app_settings_row(db)
        return max(1, int(row.pdf_max_pages or int(os.environ.get("PDF_MAX_PAGES", "80"))))
    finally:
        if close:
            db.close()


def get_max_upload_size_mb(db: Optional[Session] = None) -> int:
    """
    获取最大上传文件大小（MB）
    
    Args:
        db: 数据库会话（可选，如不提供则创建临时会话）
        
    Returns:
        最大上传大小（MB），范围 1-500
    """
    close = False
    if db is None:
        from .database import SessionLocal

        db = SessionLocal()
        close = True
    try:
        row = get_app_settings_row(db)
        size_mb = getattr(row, "max_upload_size_mb", 50)
        if size_mb is None:
            size_mb = 50
        # 限制范围：1MB - 500MB
        return max(1, min(500, int(size_mb)))
    finally:
        if close:
            db.close()


def get_nginx_max_body_size_mb() -> int:
    """
    从环境变量读取 Nginx 的 client_max_body_size 配置（MB）
    
    Returns:
        Nginx 限制大小（MB），默认 55
    """
    nginx_size_str = os.environ.get("NGINX_MAX_BODY_SIZE", "55m")
    
    # 解析字符串，去除单位后缀
    nginx_size_str = nginx_size_str.strip().lower()
    
    if nginx_size_str.endswith('m'):
        # 例如: "55m" -> 55
        return int(nginx_size_str[:-1])
    elif nginx_size_str.endswith('g'):
        # 例如: "1g" -> 1024
        return int(nginx_size_str[:-1]) * 1024
    elif nginx_size_str.endswith('k'):
        # 例如: "55000k" -> 55 (向下取整)
        return int(nginx_size_str[:-1]) // 1024
    else:
        # 假设是字节数
        try:
            return int(nginx_size_str) // (1024 * 1024)
        except ValueError:
            return 55  # 默认值


def validate_upload_size_config(backend_mb: int) -> dict:
    """
    验证上传大小配置是否合理
    
    Args:
        backend_mb: 后端配置的大小（MB）
        
    Returns:
        验证结果字典：
        - valid: 是否有效
        - warning: 警告信息（如果有）
        - nginx_mb: Nginx 当前配置
        - recommended: 推荐的 Nginx 配置
    """
    nginx_mb = get_nginx_max_body_size_mb()
    recommended_nginx = max(nginx_mb, int(backend_mb * 1.1))
    
    result = {
        "valid": True,
        "warning": "",
        "nginx_mb": nginx_mb,
        "recommended": recommended_nginx,
    }
    
    # 检查后端配置是否超过 Nginx
    if backend_mb > nginx_mb:
        result["valid"] = False
        result["warning"] = (
            f"⚠️ 后端配置 ({backend_mb}MB) 超过 Nginx 限制 ({nginx_mb}MB)\n"
            f"   用户将无法上传 {nginx_mb}-{backend_mb}MB 之间的文件\n"
            f"   建议将 NGINX_MAX_BODY_SIZE 设置为 {recommended_nginx}m"
        )
    elif backend_mb == nginx_mb:
        result["warning"] = (
            f"💡 提示：后端与 Nginx 配置相同 ({backend_mb}MB)\n"
            f"   建议 Nginx 略大于后端（如 {recommended_nginx}m），以留有余量"
        )
    elif nginx_mb < backend_mb * 1.05:
        # Nginx 仅略大于后端（小于 5% 余量）
        result["warning"] = (
            f"💡 提示：Nginx 余量较小 ({nginx_mb}MB vs {backend_mb}MB)\n"
            f"   建议设置为 {recommended_nginx}m（{int((recommended_nginx/backend_mb-1)*100)}% 余量）"
        )
    
    return result


def get_admin_pdf_max_pages_cap() -> int:
    """管理员解析 PDF 时的页数上限（视为「无限制」的可执行上界）。"""
    return max(1, int(os.environ.get("ADMIN_PDF_MAX_PAGES", "100000")))


def get_effective_pdf_max_pages_for_user(user: "User", db: Session) -> int:
    """对普通用户：min(全局上限, 个人上限或全局)；管理员不受配额限制（使用环境变量上界）。"""
    if getattr(user, "is_admin", False):
        return get_admin_pdf_max_pages_cap()
    global_max = get_pdf_max_pages(db)
    raw = getattr(user, "pdf_max_pages", None)
    if raw is None:
        return global_max
    return max(1, min(global_max, int(raw)))


def get_password_rules(db: Optional[Session] = None) -> dict[str, Any]:
    """
    获取当前密码规则配置
    
    Args:
        db: 数据库会话（可选，如不提供则创建临时会话）
        
    Returns:
        密码规则字典，包含：
        - min_length: 最小长度
        - require_uppercase: 是否要求大写字母
        - require_lowercase: 是否要求小写字母
        - require_digit: 是否要求数字
        - require_special: 是否要求特殊字符
    """
    close = False
    if db is None:
        from .database import SessionLocal

        db = SessionLocal()
        close = True
    try:
        row = get_app_settings_row(db)
        return {
            "min_length": max(1, int(getattr(row, "password_min_length", 8) or 8)),
            "require_uppercase": bool(getattr(row, "password_require_uppercase", True)),
            "require_lowercase": bool(getattr(row, "password_require_lowercase", True)),
            "require_digit": bool(getattr(row, "password_require_digit", True)),
            "require_special": bool(getattr(row, "password_require_special", False)),
        }
    finally:
        if close:
            db.close()


def validate_password(password: str, db: Optional[Session] = None) -> tuple[bool, str]:
    """
    验证密码是否符合当前规则
    
    按顺序检查：
    1. 最小长度
    2. 大写字母（如启用）
    3. 小写字母（如启用）
    4. 数字（如启用）
    5. 特殊字符（如启用）
    
    Args:
        password: 待验证的明文密码
        db: 数据库会话（可选）
        
    Returns:
        (是否通过, 错误消息)，通过时错误消息为空字符串
    """
    rules = get_password_rules(db)
    
    # 检查最小长度
    if len(password) < rules["min_length"]:
        return False, f"密码长度至少为 {rules['min_length']} 个字符"
    
    # 检查大写字母
    if rules["require_uppercase"] and not any(c.isupper() for c in password):
        return False, "密码必须包含至少一个大写字母"
    
    # 检查小写字母
    if rules["require_lowercase"] and not any(c.islower() for c in password):
        return False, "密码必须包含至少一个小写字母"
    
    # 检查数字
    if rules["require_digit"] and not any(c.isdigit() for c in password):
        return False, "密码必须包含至少一个数字"
    
    # 检查特殊字符
    if rules["require_special"]:
        special_chars = set('!@#$%^&*()_+-=[]{}|;:,.<>?/~`')
        if not any(c in special_chars for c in password):
            return False, "密码必须包含至少一个特殊字符（如 !@#$%^&* 等）"
    
    return True, ""


def resolve_job_pdf_max_pages(user: "User", db: Session, requested: Optional[int]) -> int:
    """上传任务：requested 为希望解析的页数，None 表示解析到有效上限；返回实际采用的 max_pages。"""
    eff = get_effective_pdf_max_pages_for_user(user, db)
    if requested is None:
        return eff
    if requested < 1:
        raise ValueError("页数至少为 1")
    if requested > eff:
        raise ValueError(f"单次解析页数不能超过 {eff}")
    return int(requested)


def settings_to_public_dict(db: Session) -> dict[str, Any]:
    row = get_app_settings_row(db)
    return {
        "registration_enabled": bool(row.registration_enabled),
        "captcha_login": bool(row.captcha_login_enabled),
        "captcha_register": bool(row.captcha_register_enabled),
        "captcha_forgot": bool(row.captcha_forgot_enabled),
        "pdf_max_pages": max(1, int(row.pdf_max_pages or 80)),
        "register_requires_email_code": register_requires_email_verification(db),
        "register_requires_phone_code": register_requires_phone_verification(db),
        "register_email_allowed": bool(getattr(row, "register_email_enabled", True)),
        "register_phone_allowed": bool(getattr(row, "register_phone_enabled", True)),
        "login_email_allowed": bool(getattr(row, "login_email_enabled", True)),
        "login_phone_allowed": bool(getattr(row, "login_phone_enabled", True)),
        "forgot_email_allowed": bool(getattr(row, "forgot_email_enabled", True)),
        "forgot_phone_allowed": bool(getattr(row, "forgot_phone_enabled", True)),
    }


def settings_to_admin_dict(db: Session) -> dict[str, Any]:
    """管理员表单字段为数据库中的存储值；effective_* 为当前实际生效路径（只读展示）。"""
    row = get_app_settings_row(db)
    out_eff = get_effective_output_dir(db)
    mpath_eff = get_effective_model_path_str(db)
    return {
        "registration_enabled": bool(row.registration_enabled),
        "captcha_login_enabled": bool(row.captcha_login_enabled),
        "captcha_register_enabled": bool(row.captcha_register_enabled),
        "captcha_forgot_enabled": bool(row.captcha_forgot_enabled),
        "pdf_max_pages": max(1, int(row.pdf_max_pages or 80)),
        "output_dir": (str(row.output_dir).strip() if row.output_dir else ""),
        "model_local_path": (str(row.model_local_path).strip() if row.model_local_path else ""),
        "effective_output_dir": str(out_eff),
        "effective_model_path": mpath_eff,
        "hf_repo_id": row.hf_repo_id or "Logics-MLLM/Logics-Parsing-v2",
        "ms_repo_id": row.ms_repo_id or "Alibaba-DT/Logics-Parsing-v2",
        "updated_at": row.updated_at.isoformat() + "Z" if row.updated_at else None,
        "email_mock": bool(getattr(row, "email_mock", True)),
        "smtp_host": (row.smtp_host or "") if getattr(row, "smtp_host", None) is not None else "",
        "smtp_port": int(row.smtp_port) if getattr(row, "smtp_port", None) is not None else 587,
        "smtp_user": (row.smtp_user or "") if getattr(row, "smtp_user", None) is not None else "",
        "smtp_from": (row.smtp_from or "") if getattr(row, "smtp_from", None) is not None else "",
        "smtp_use_tls": bool(row.smtp_use_tls) if getattr(row, "smtp_use_tls", None) is not None else True,
        "smtp_password_configured": bool((getattr(row, "smtp_password", None) or "").strip()),
        "register_email_enabled": bool(getattr(row, "register_email_enabled", True)),
        "register_phone_enabled": bool(getattr(row, "register_phone_enabled", True)),
        "login_email_enabled": bool(getattr(row, "login_email_enabled", True)),
        "login_phone_enabled": bool(getattr(row, "login_phone_enabled", True)),
        "forgot_email_enabled": bool(getattr(row, "forgot_email_enabled", True)),
        "forgot_phone_enabled": bool(getattr(row, "forgot_phone_enabled", True)),
        "sms_mock": bool(getattr(row, "sms_mock", True)),
        "sms_http_url": (getattr(row, "sms_http_url", None) or "") or "",
        "sms_http_headers_json": (getattr(row, "sms_http_headers_json", None) or "") or "",
        "sms_http_body_template": (getattr(row, "sms_http_body_template", None) or "") or "",
        "sms_http_secret_configured": bool((getattr(row, "sms_http_secret", None) or "").strip()),
        "show_page_numbers": bool(getattr(row, "show_page_numbers", True)),
        "image_output_mode": getattr(row, "image_output_mode", "base64") or "base64",
        "stale_job_timeout_minutes": max(1, int(getattr(row, "stale_job_timeout_minutes", 10) or 10)),
        "login_timeout_minutes": max(1, int(getattr(row, "login_timeout_minutes", 10) or 10)),
        # 密码规则
        "password_min_length": max(1, int(getattr(row, "password_min_length", 8) or 8)),
        "password_require_uppercase": bool(getattr(row, "password_require_uppercase", True)),
        "password_require_lowercase": bool(getattr(row, "password_require_lowercase", True)),
        "password_require_digit": bool(getattr(row, "password_require_digit", True)),
        "password_require_special": bool(getattr(row, "password_require_special", False)),
        # 文件上传限制
        "max_upload_size_mb": max(1, min(500, int(getattr(row, "max_upload_size_mb", 50) or 50))),
        # Nginx 配置信息（只读）
        "nginx_max_body_size_mb": get_nginx_max_body_size_mb(),
    }


def apply_admin_usernames(db: Session) -> None:
    raw = os.environ.get("ADMIN_USERNAMES", "").strip()
    if not raw:
        return
    from .models import User

    names = {x.strip() for x in raw.split(",") if x.strip()}
    for u in db.query(User).filter(User.username.in_(names)).all():
        u.is_admin = True
    db.commit()


def update_settings_from_body(db: Session, body: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    from .models import AppSettings

    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row is None:
        row = AppSettings(id=1)
        db.add(row)

    if "registration_enabled" in body:
        row.registration_enabled = bool(body["registration_enabled"])
    if "captcha_login_enabled" in body:
        row.captcha_login_enabled = bool(body["captcha_login_enabled"])
    if "captcha_register_enabled" in body:
        row.captcha_register_enabled = bool(body["captcha_register_enabled"])
    if "captcha_forgot_enabled" in body:
        row.captcha_forgot_enabled = bool(body["captcha_forgot_enabled"])
    if "pdf_max_pages" in body:
        row.pdf_max_pages = max(1, int(body["pdf_max_pages"]))
    if "output_dir" in body:
        v = body["output_dir"]
        row.output_dir = (str(v).strip() or None) if v is not None else None
        if row.output_dir:
            validate_output_dir(Path(row.output_dir))
    if "model_local_path" in body:
        v = body["model_local_path"]
        row.model_local_path = (str(v).strip() or None) if v is not None else None
        if row.model_local_path:
            validate_model_path(Path(row.model_local_path))
    if "hf_repo_id" in body and body["hf_repo_id"]:
        row.hf_repo_id = str(body["hf_repo_id"]).strip()[:256]
    if "ms_repo_id" in body and body["ms_repo_id"]:
        row.ms_repo_id = str(body["ms_repo_id"]).strip()[:256]

    if "email_mock" in body:
        row.email_mock = bool(body["email_mock"])
    if "smtp_host" in body:
        v = body["smtp_host"]
        row.smtp_host = (str(v).strip() or None) if v is not None else None
    if "smtp_port" in body and body["smtp_port"] is not None:
        row.smtp_port = max(1, min(65535, int(body["smtp_port"])))
    if "smtp_user" in body:
        v = body["smtp_user"]
        row.smtp_user = (str(v).strip() or None) if v is not None else None
    if "smtp_from" in body:
        v = body["smtp_from"]
        row.smtp_from = (str(v).strip() or None) if v is not None else None
    if "smtp_use_tls" in body:
        row.smtp_use_tls = bool(body["smtp_use_tls"])
    if "smtp_password" in body and body["smtp_password"] and str(body["smtp_password"]).strip():
        row.smtp_password = str(body["smtp_password"]).strip()[:512]

    if "register_email_enabled" in body:
        row.register_email_enabled = bool(body["register_email_enabled"])
    if "register_phone_enabled" in body:
        row.register_phone_enabled = bool(body["register_phone_enabled"])
    if "login_email_enabled" in body:
        row.login_email_enabled = bool(body["login_email_enabled"])
    if "login_phone_enabled" in body:
        row.login_phone_enabled = bool(body["login_phone_enabled"])
    if "forgot_email_enabled" in body:
        row.forgot_email_enabled = bool(body["forgot_email_enabled"])
    if "forgot_phone_enabled" in body:
        row.forgot_phone_enabled = bool(body["forgot_phone_enabled"])
    if "sms_mock" in body:
        row.sms_mock = bool(body["sms_mock"])
    if "sms_http_url" in body:
        v = body["sms_http_url"]
        row.sms_http_url = (str(v).strip() or None) if v is not None else None
    if "sms_http_headers_json" in body:
        v = body["sms_http_headers_json"]
        row.sms_http_headers_json = (str(v).strip() or None) if v is not None else None
    if "sms_http_body_template" in body:
        v = body["sms_http_body_template"]
        row.sms_http_body_template = (str(v).strip() or None) if v is not None else None
    if "sms_http_secret" in body and body["sms_http_secret"] and str(body["sms_http_secret"]).strip():
        row.sms_http_secret = str(body["sms_http_secret"]).strip()[:512]

    if "show_page_numbers" in body:
        row.show_page_numbers = bool(body["show_page_numbers"])

    if "image_output_mode" in body:
        mode = str(body["image_output_mode"]).strip().lower()
        if mode not in ("base64", "separate", "none"):
            raise ValueError("image_output_mode 必须是 base64、separate 或 none")
        row.image_output_mode = mode

    if "stale_job_timeout_minutes" in body:
        row.stale_job_timeout_minutes = max(1, int(body["stale_job_timeout_minutes"]))

    if "login_timeout_minutes" in body:
        row.login_timeout_minutes = max(1, int(body["login_timeout_minutes"]))

    # 密码规则
    if "password_min_length" in body:
        row.password_min_length = max(1, min(128, int(body["password_min_length"])))
    if "password_require_uppercase" in body:
        row.password_require_uppercase = bool(body["password_require_uppercase"])
    if "password_require_lowercase" in body:
        row.password_require_lowercase = bool(body["password_require_lowercase"])
    if "password_require_digit" in body:
        row.password_require_digit = bool(body["password_require_digit"])
    if "password_require_special" in body:
        row.password_require_special = bool(body["password_require_special"])

    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return settings_to_admin_dict(db)

"""
数据库配置和迁移管理

本模块负责：
- 数据库连接配置（支持 SQLite 和其他数据库）
- 会话管理
- 数据库表结构初始化
- 增量数据迁移（向后兼容）
- 默认管理员账号创建
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

CURRENT_DIR = Path(__file__).parent
DEFAULT_SQLITE = CURRENT_DIR.parent / "data" / "app.db"  # 默认 SQLite 数据库路径
os.makedirs(DEFAULT_SQLITE.parent, exist_ok=True)

# 从环境变量读取数据库 URL，默认使用 SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE.resolve()}")

# 创建数据库引擎
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite 需要此参数以支持多线程
        echo=False,  # 不打印 SQL 日志
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，所有模型都继承自此"""
    pass


def init_db():
    """
    初始化数据库
    
    执行顺序：
    1. 创建所有表结构（基于 models.py 定义）
    2. 执行增量迁移（为已有表添加新字段）
    3. 引导初始数据（系统配置和管理员账号）
    
    应在应用启动时调用一次。
    """
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)  # 创建表结构
    # 执行增量迁移（按时间顺序）
    migrate_parse_jobs()
    migrate_parse_jobs_pages_parsed()
    migrate_users_and_codes()
    migrate_app_settings()
    migrate_app_settings_email()
    migrate_users_phone()
    migrate_users_pdf_max_pages()
    migrate_app_settings_auth_sms()
    migrate_app_settings_login_timeout()
    migrate_app_settings_password_rules()  # 密码规则配置
    _bootstrap_settings_and_admins()  # 引导初始数据


def _bootstrap_settings_and_admins():
    from .settings_service import apply_admin_usernames, ensure_app_settings_row

    db = SessionLocal()
    try:
        ensure_app_settings_row(db)
        apply_admin_usernames(db)
    finally:
        db.close()
    _ensure_default_admin_user()


def _ensure_default_admin_user() -> None:
    """若不存在用户名为 admin 的账号，则创建默认管理员（密码 admin123，仅首次）。"""
    from .auth_security import hash_password
    from .models import User

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first():
            return
        db.add(
            User(
                email="admin@logics-parsing.local",
                username="admin",
                hashed_password=hash_password("admin123"),
                is_admin=True,
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()


def migrate_parse_jobs():
    """SQLite 增量迁移：为已有 parse_jobs 表添加列。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("parse_jobs"):
        return
    cols = {c["name"] for c in insp.get_columns("parse_jobs")}
    stmts = []
    if "status" not in cols:
        stmts.append("ALTER TABLE parse_jobs ADD COLUMN status VARCHAR(32) DEFAULT 'processing'")
    if "original_filename" not in cols:
        stmts.append("ALTER TABLE parse_jobs ADD COLUMN original_filename VARCHAR(512)")
    if "completed_at" not in cols:
        stmts.append("ALTER TABLE parse_jobs ADD COLUMN completed_at DATETIME")
    if "cache_cleared_at" not in cols:
        stmts.append("ALTER TABLE parse_jobs ADD COLUMN cache_cleared_at DATETIME")
    if not stmts:
        return
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))
        conn.execute(text("UPDATE parse_jobs SET status = 'completed' WHERE status IS NULL"))
        conn.execute(
            text(
                "UPDATE parse_jobs SET completed_at = created_at "
                "WHERE completed_at IS NULL AND status IN ('completed', 'stopped')"
            )
        )


def migrate_parse_jobs_pages_parsed():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("parse_jobs"):
        return
    cols = {c["name"] for c in insp.get_columns("parse_jobs")}
    if "pages_parsed" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE parse_jobs ADD COLUMN pages_parsed INTEGER"))


def migrate_users_and_codes():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "is_admin" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
    if insp.has_table("verification_codes"):
        cols = {c["name"] for c in insp.get_columns("verification_codes")}
        with engine.begin() as conn:
            if "purpose" not in cols:
                conn.execute(text("ALTER TABLE verification_codes ADD COLUMN purpose VARCHAR(16) DEFAULT 'register'"))
                conn.execute(
                    text("UPDATE verification_codes SET purpose = 'register' WHERE purpose IS NULL OR TRIM(COALESCE(purpose,'')) = ''")
                )


def migrate_app_settings():
    """确保存在 id=1 的配置行（表由 SQLAlchemy create_all 创建）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_settings"):
        return
    with engine.begin() as conn:
        conn.execute(text("INSERT OR IGNORE INTO app_settings (id) VALUES (1)"))


def migrate_app_settings_email():
    """SQLite 增量迁移：邮件相关列。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("app_settings")}
    stmts = []
    if "email_mock" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN email_mock BOOLEAN DEFAULT 1")
    if "smtp_host" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_host VARCHAR(256)")
    if "smtp_port" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_port INTEGER DEFAULT 587")
    if "smtp_user" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_user VARCHAR(256)")
    if "smtp_password" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_password VARCHAR(512)")
    if "smtp_from" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_from VARCHAR(256)")
    if "smtp_use_tls" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN smtp_use_tls BOOLEAN DEFAULT 1")
    if not stmts:
        return
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


def migrate_users_phone():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "phone" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(16)"))


def migrate_users_pdf_max_pages():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "pdf_max_pages" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN pdf_max_pages INTEGER"))


def migrate_app_settings_auth_sms():
    """注册/登录/找回方式开关 + 短信 HTTP 配置。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("app_settings")}
    stmts = []
    if "register_email_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN register_email_enabled BOOLEAN DEFAULT 1")
    if "register_phone_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN register_phone_enabled BOOLEAN DEFAULT 1")
    if "login_email_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN login_email_enabled BOOLEAN DEFAULT 1")
    if "login_phone_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN login_phone_enabled BOOLEAN DEFAULT 1")
    if "forgot_email_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN forgot_email_enabled BOOLEAN DEFAULT 1")
    if "forgot_phone_enabled" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN forgot_phone_enabled BOOLEAN DEFAULT 1")
    if "sms_mock" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN sms_mock BOOLEAN DEFAULT 1")
    if "sms_http_url" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN sms_http_url VARCHAR(1024)")
    if "sms_http_secret" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN sms_http_secret VARCHAR(512)")
    if "sms_http_headers_json" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN sms_http_headers_json VARCHAR(2048)")
    if "sms_http_body_template" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN sms_http_body_template VARCHAR(4096)")
    if not stmts:
        return
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


def migrate_app_settings_login_timeout():
    """添加登录超时时长字段。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("app_settings")}
    if "login_timeout_minutes" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE app_settings ADD COLUMN login_timeout_minutes INTEGER DEFAULT 10"))


def migrate_app_settings_password_rules():
    """添加密码规则配置字段。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("app_settings")}
    stmts = []
    if "password_min_length" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN password_min_length INTEGER DEFAULT 8")
    if "password_require_uppercase" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN password_require_uppercase BOOLEAN DEFAULT 1")
    if "password_require_lowercase" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN password_require_lowercase BOOLEAN DEFAULT 1")
    if "password_require_digit" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN password_require_digit BOOLEAN DEFAULT 1")
    if "password_require_special" not in cols:
        stmts.append("ALTER TABLE app_settings ADD COLUMN password_require_special BOOLEAN DEFAULT 0")
    if not stmts:
        return
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

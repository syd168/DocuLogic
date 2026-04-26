import os
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from .settings_service import get_effective_email_config


def _send_plain(db: Session, to_email: str, subject: str, text_body: str) -> None:
    cfg = get_effective_email_config(db)
    if cfg["mock"]:
        print(f"[EMAIL_MOCK] to={to_email}\n{subject}\n{text_body}")
        return

    host = cfg["host"]
    port = cfg["port"]
    user = cfg["user"]
    password = cfg["password"]
    from_addr = cfg["from_addr"] or user

    if not host or not user:
        raise RuntimeError("SMTP 主机或用户名未配置")
    if not password:
        raise RuntimeError("SMTP 密码未配置")

    msg = MIMEText(text_body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        if cfg["use_tls"]:
            server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())


def send_forgot_password_email(db: Session, to_email: str, code: str) -> None:
    """找回密码验证码。"""
    minutes = os.environ.get("CODE_EXPIRE_MINUTES", "10")
    body = (
        f"您正在重置密码，验证码：{code}，{minutes} 分钟内有效。\n"
        f"如非本人操作请忽略。"
    )
    _send_plain(db, to_email, "找回密码验证码 - DocuLogic", body)


def send_verification_email(db: Session, to_email: str, code: str) -> None:
    """发送注册验证码。"""
    minutes = os.environ.get("CODE_EXPIRE_MINUTES", "10")
    body = (
        f"您的注册验证码是：{code}，{minutes} 分钟内有效。\n"
        f"如非本人操作请忽略。"
    )
    _send_plain(db, to_email, "注册验证码 - DocuLogic", body)

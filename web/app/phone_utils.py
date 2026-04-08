"""手机号：规范化与登录/验证码用的 recipient 键。"""
from __future__ import annotations

import re

# 验证码表复用 email 列存储 recipient；手机验证码使用此前缀，避免与真实邮箱冲突
SMS_RECIPIENT_PREFIX = "sms:"


def normalize_cn_mobile(raw: str) -> str:
    """中国大陆手机：仅保留数字，返回 11 位；不合法返回空串。"""
    digits = re.sub(r"\D", "", (raw or "").strip())
    if re.fullmatch(r"1[3-9]\d{9}", digits):
        return digits
    return ""


def synthetic_email_for_phone(phone: str) -> str:
    """手机注册且无邮箱时占位的唯一邮箱（保留域名为内部使用）。"""
    p = normalize_cn_mobile(phone)
    return f"{p}@phone.sms.local"


def sms_recipient_key(phone: str) -> str:
    """写入 verification_codes.email 列的键，与 hash 一致。"""
    p = normalize_cn_mobile(phone)
    return f"{SMS_RECIPIENT_PREFIX}{p}" if p else ""

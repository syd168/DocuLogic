"""手机短信：模拟模式或 HTTP 回调对接第三方（JSON POST）。"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from .settings_service import get_effective_sms_config

_log = logging.getLogger(__name__)


def _render_template(tpl: str, phone: str, code: str, purpose: str) -> str:
    return (
        tpl.replace("{phone}", phone)
        .replace("{code}", code)
        .replace("{purpose}", purpose)
    )


def _validate_sms_url(url: str) -> bool:
    """
    校验 SMS HTTP URL 的安全性，防止 SSRF 攻击
    
    Args:
        url: 待校验的 URL
        
    Returns:
        True 如果 URL 安全
        
    Raises:
        ValueError: 如果 URL 不安全
    """
    parsed = urlparse(url)
    
    # 1. 仅允许 http/https 协议
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的协议: {parsed.scheme}，仅允许 http/https")
    
    # 2. 禁止内网地址（防止 SSRF）
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("无效的 URL")
    
    try:
        # 解析域名获取 IP 地址
        ip_addresses = socket.getaddrinfo(hostname, None)
        for addr in ip_addresses:
            ip = ipaddress.ip_address(addr[4][0])
            # 检查是否为私有地址、回环地址或链路本地地址
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"禁止访问内网地址: {ip}")
    except socket.gaierror:
        raise ValueError(f"无法解析域名: {hostname}")
    
    return True


def send_sms_code(db: Session, phone: str, code: str, purpose: str) -> None:
    """
    purpose: register | forgot
    未配置 URL 且非 mock 时抛出 RuntimeError，供接口返回友好错误。
    """
    cfg = get_effective_sms_config(db)
    if cfg["mock"]:
        _log.info(
            "[SMS_MOCK] phone=%s purpose=%s code=%s",
            phone,
            purpose,
            code,
        )
        print(f"[SMS_MOCK] to={phone} purpose={purpose}\n验证码：{code}")
        return

    url = (cfg.get("http_url") or "").strip()
    if not url:
        raise RuntimeError("短信 HTTP 回调地址未配置")

    # ✅ 校验 URL 安全性，防止 SSRF 攻击
    try:
        _validate_sms_url(url)
    except ValueError as e:
        _log.error(f"SMS URL 校验失败: {e}")
        raise RuntimeError(f"短信配置错误: {str(e)}") from e

    tpl = (cfg.get("http_body_template") or "").strip() or '{"phone":"{phone}","code":"{code}","purpose":"{purpose}"}'
    body_raw = _render_template(tpl, phone, code, purpose)
    try:
        payload: Any = json.loads(body_raw)
    except json.JSONDecodeError:
        payload = body_raw.encode("utf-8")
    else:
        payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {"Content-Type": "application/json", "User-Agent": "Logics-Parsing-SMS/1.0"}
    extra = cfg.get("http_headers") or {}
    if isinstance(extra, dict):
        # ✅ 白名单过滤自定义头部，防止 HTTP 头部注入
        ALLOWED_CUSTOM_HEADERS = {
            "x-api-key",
            "x-auth-token",
            "x-client-id",
            "x-request-id",
        }
        for k, v in extra.items():
            k_lower = k.lower().strip()
            # 1. 禁止覆盖关键头部
            if k_lower in ("content-type", "user-agent", "host", "authorization", "cookie"):
                _log.warning(f"禁止覆盖关键头部: {k}")
                continue
            
            # 2. 仅允许白名单头部或 x- 开头的自定义头部
            if k_lower not in ALLOWED_CUSTOM_HEADERS and not k_lower.startswith("x-"):
                _log.warning(f"不允许的自定义头部: {k}")
                continue
            
            # 3. 清理头部值（防止 CRLF 注入）
            v_clean = str(v).replace("\r", "").replace("\n", "")
            headers[k] = v_clean

    req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    secret = (cfg.get("http_secret") or "").strip()
    if secret:
        req.add_header("X-Sms-Secret", secret)

    timeout = float(os.environ.get("SMS_HTTP_TIMEOUT", "15") or "15")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"短信网关返回 HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        _log.exception("SMS HTTP error")
        raise RuntimeError(f"短信网关错误: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        _log.exception("SMS URL error")
        raise RuntimeError(f"短信发送失败: {e.reason}") from e

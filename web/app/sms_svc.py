"""手机短信：模拟模式或 HTTP 回调对接第三方（JSON POST）。"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from sqlalchemy.orm import Session

from .settings_service import get_effective_sms_config

_log = logging.getLogger(__name__)


def _render_template(tpl: str, phone: str, code: str, purpose: str) -> str:
    return (
        tpl.replace("{phone}", phone)
        .replace("{code}", code)
        .replace("{purpose}", purpose)
    )


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
        headers.update({k: str(v) for k, v in extra.items() if v is not None})

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

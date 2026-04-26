"""图形验证码：支持 Redis 和内存两种存储方式。"""
from __future__ import annotations

import logging
import os
import random
import re
import string
import time
from uuid import uuid4

# ✅ 优先使用 Redis，降级到内存存储
try:
    import redis
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_DB = int(os.environ.get("REDIS_DB", "1"))  # 使用 DB 1 存储验证码
    
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2
    )
    # 测试连接
    redis_client.ping()
    USE_REDIS = True
    _log = logging.getLogger(__name__)
    _log.info(f"✅ 验证码使用 Redis 存储: {REDIS_HOST}:{REDIS_PORT}")
except (ImportError, redis.ConnectionError, Exception) as e:
    # 降级到内存存储
    import threading
    USE_REDIS = False
    _store: dict[str, tuple[str, float]] = {}
    _lock = threading.Lock()
    _log = logging.getLogger(__name__)
    _log.warning(f"⚠️ Redis 不可用，验证码使用内存存储: {str(e)}")

_TTL = 300  # 5分钟过期


def _cleanup() -> None:
    """清理过期的验证码（仅内存模式需要）"""
    if USE_REDIS:
        return  # Redis 自动过期，无需手动清理
    
    now = time.time()
    dead = [k for k, (_, exp) in _store.items() if exp < now]
    for k in dead:
        _store.pop(k, None)


def create_captcha() -> tuple[str, str]:
    """返回 (captcha_id, svg_xml)"""
    _cleanup()
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cid = str(uuid4())
    
    if USE_REDIS:
        # ✅ 使用 Redis 存储，支持多进程/分布式部署
        try:
            redis_client.setex(f"captcha:{cid}", _TTL, code.upper())
        except Exception as e:
            _log.error(f"Redis 存储验证码失败: {e}，降级到内存")
            with _lock:
                _store[cid] = (code.upper(), time.time() + _TTL)
    else:
        # 内存存储（降级方案）
        with _lock:
            _store[cid] = (code.upper(), time.time() + _TTL)
    
    svg = _svg(code)
    return cid, svg


def verify_captcha(captcha_id: str, user_input: str) -> bool:
    """验证验证码，一次性使用"""
    if not captcha_id or user_input is None:
        return False
    
    if USE_REDIS:
        # ✅ 从 Redis 获取并删除（一次性使用）
        try:
            stored = redis_client.get(f"captcha:{captcha_id.strip()}")
            if stored:
                redis_client.delete(f"captcha:{captcha_id.strip()}")
                return stored.upper() == str(user_input).strip().upper()
            return False
        except Exception as e:
            _log.error(f"Redis 验证验证码失败: {e}，降级到内存")
            # 降级到内存验证
            pass
    
    # 内存存储验证（降级方案）
    _cleanup()
    with _lock:
        item = _store.pop(captcha_id.strip(), None)
    if not item:
        return False
    code, _ = item
    return code == str(user_input).strip().upper()


def _svg(text: str) -> str:
    w, h = 140, 44
    noise = "".join(
        f'<line x1="{random.randint(0,w)}" y1="{random.randint(0,h)}" '
        f'x2="{random.randint(0,w)}" y2="{random.randint(0,h)}" stroke="rgba(100,180,255,0.25)" stroke-width="1"/>'
        for _ in range(6)
    )
    letters = []
    for i, ch in enumerate(text):
        x = 18 + i * 26 + random.randint(-3, 3)
        y = 30 + random.randint(-4, 4)
        rot = random.randint(-18, 18)
        letters.append(
            f'<text x="{x}" y="{y}" fill="#3dd6f5" font-size="22" font-family="monospace" '
            f'font-weight="bold" transform="rotate({rot} {x} {y-8})">{_esc(ch)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">'
        f'<rect width="100%" height="100%" fill="#0c1222"/>'
        f"{noise}"
        f'{"".join(letters)}'
        f"</svg>"
    )


def _esc(ch: str) -> str:
    return re.sub(r"[&<>]", lambda m: {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[m.group(0)], ch)

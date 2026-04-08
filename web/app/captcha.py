"""简单图形验证码：内存存储 + SVG 文本（单机多进程需共享存储时可换 Redis）。"""
from __future__ import annotations

import random
import re
import string
import threading
import time
from uuid import uuid4

_TTL = 300
_store: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()


def _cleanup() -> None:
    now = time.time()
    dead = [k for k, (_, exp) in _store.items() if exp < now]
    for k in dead:
        _store.pop(k, None)


def create_captcha() -> tuple[str, str]:
    """返回 (captcha_id, svg_xml)"""
    _cleanup()
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    cid = str(uuid4())
    with _lock:
        _store[cid] = (code.upper(), time.time() + _TTL)
    svg = _svg(code)
    return cid, svg


def verify_captcha(captcha_id: str, user_input: str) -> bool:
    if not captcha_id or user_input is None:
        return False
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

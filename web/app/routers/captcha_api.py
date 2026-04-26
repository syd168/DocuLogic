"""图形验证码（无需登录）。"""
from fastapi import APIRouter

from ..captcha import create_captcha

router = APIRouter(prefix="/api/captcha", tags=["captcha"])


@router.get("/new")
async def captcha_new():
    captcha_id, svg = create_captcha()
    return {"captcha_id": captcha_id, "svg": svg}

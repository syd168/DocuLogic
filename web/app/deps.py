from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth_security import decode_token
from .database import get_db
from .models import User


def get_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
        )
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
    user = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = get_token_from_request(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        uid = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    return db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user = get_current_user(request, db)
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user

"""
Token 黑名单与会话管理服务

提供：
- Token 黑名单（支持强制登出）
- 用户会话管理（Redis 缓存）
- 单点登录控制（一个账号只能一个终端在线）
- 管理员踢出用户功能
"""
from typing import Optional, Dict, Any
import logging
import json
from datetime import datetime, timedelta

from .cache import cache

logger = logging.getLogger(__name__)


# ==================== Token 黑名单 ====================

def revoke_token(token: str, reason: str = "manual_logout", ttl_seconds: int = 86400 * 7) -> bool:
    """
    将 Token 加入黑名单（撤销 Token）
    
    Args:
        token: JWT Token 字符串
        reason: 撤销原因 (manual_logout/kicked_by_admin/password_changed/account_disabled)
        ttl_seconds: 黑名单保留时间（秒），默认 7 天（与 Token 有效期一致）
        
    Returns:
        是否成功
    """
    from app.auth_security import decode_token
    
    # 解码 token 获取过期时间和用户信息
    payload = decode_token(token)
    if not payload:
        logger.warning(f"⚠️ 无法解码 Token（可能已过期或密钥变更），跳过加入黑名单")
        return False
    
    # 计算剩余有效期，作为黑名单的 TTL
    if "exp" in payload:
        remaining_seconds = payload["exp"] - int(datetime.utcnow().timestamp())
        if remaining_seconds > 0:
            ttl_seconds = min(ttl_seconds, remaining_seconds + 60)  # 额外加60秒缓冲
        else:
            logger.info(f"ℹ️ Token 已过期，无需加入黑名单")
            return False
    
    key = f"token_blacklist:{token}"
    blacklist_data = {
        "reason": reason,
        "revoked_at": datetime.utcnow().isoformat(),
        "user_id": payload.get("sub"),
        "username": payload.get("username", ""),
    }
    
    success = cache.set(key, blacklist_data, ttl=ttl_seconds)
    if success:
        logger.info(f"✅ Token 已加入黑名单: user_id={payload.get('sub')}, reason={reason}")
    else:
        logger.error(f"❌ Token 加入黑名单失败: user_id={payload.get('sub')}")
    
    return success


def is_token_blacklisted(token: str) -> bool:
    """
    检查 Token 是否在黑名单中
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        是否在黑名单中
    """
    key = f"token_blacklist:{token}"
    return cache.exists(key)


def get_blacklist_reason(token: str) -> Optional[Dict[str, Any]]:
    """
    获取 Token 被拉黑的原因
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        黑名单信息字典，不存在返回 None
    """
    key = f"token_blacklist:{token}"
    return cache.get(key)


# ==================== 用户会话管理 ====================

def create_user_session(user_id: int, username: str, token: str, 
                       ip_address: str = "", user_agent: str = "",
                       ttl_seconds: int = 3600 * 24 * 7) -> bool:
    """
    创建用户会话记录（支持单点登录）
    
    Args:
        user_id: 用户 ID
        username: 用户名
        token: JWT Token
        ip_address: 登录 IP
        user_agent: 浏览器标识
        ttl_seconds: 会话有效期（秒），默认 7 天
        
    Returns:
        是否成功
    """
    session_key = f"user_session:{user_id}"
    session_data = {
        "user_id": user_id,
        "username": username,
        "token": token,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "login_at": datetime.utcnow().isoformat(),
        "last_active": datetime.utcnow().isoformat(),
    }
    
    success = cache.set(session_key, session_data, ttl=ttl_seconds)
    if success:
        logger.info(f"✅ 用户会话已创建: user_id={user_id}, username={username}")
    else:
        logger.error(f"❌ 用户会话创建失败: user_id={user_id}")
    
    return success


def get_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    获取用户当前会话信息
    
    Args:
        user_id: 用户 ID
        
    Returns:
        会话数据字典，不存在返回 None
    """
    session_key = f"user_session:{user_id}"
    return cache.get(session_key)


def update_session_activity(user_id: int) -> bool:
    """
    更新用户会话的最后活跃时间
    
    Args:
        user_id: 用户 ID
        
    Returns:
        是否成功
    """
    session_key = f"user_session:{user_id}"
    session_data = cache.get(session_key)
    
    if not session_data:
        return False
    
    session_data["last_active"] = datetime.utcnow().isoformat()
    return cache.set(session_key, session_data, ttl=3600 * 24 * 7)


def refresh_session_token(user_id: int, new_token: str, ttl_seconds: int) -> bool:
    """
    刷新会话中的 token（用于 refresh-token 场景，避免误判“异地登录”）。

    Args:
        user_id: 用户 ID
        new_token: 新 JWT token
        ttl_seconds: 会话续期秒数

    Returns:
        是否更新成功
    """
    session_key = f"user_session:{user_id}"
    session_data = cache.get(session_key)
    if not session_data:
        return False
    session_data["token"] = new_token
    session_data["last_active"] = datetime.utcnow().isoformat()
    return cache.set(session_key, session_data, ttl=max(60, int(ttl_seconds or 0)))


def destroy_user_session(user_id: int, reason: str = "logout") -> bool:
    """
    销毁用户会话（登出或踢出）
    
    Args:
        user_id: 用户 ID
        reason: 销毁原因 (logout/kicked/account_disabled)
        
    Returns:
        是否成功
    """
    session_key = f"user_session:{user_id}"
    session_data = cache.get(session_key)
    
    if session_data:
        # 将当前 token 加入黑名单
        token = session_data.get("token")
        if token:
            revoke_token(token, reason=reason)
    
    success = cache.delete(session_key)
    if success:
        logger.info(f"✅ 用户会话已销毁: user_id={user_id}, reason={reason}")
    else:
        logger.warning(f"⚠️ 用户会话销毁失败（可能已不存在）: user_id={user_id}")
    
    return True


def kick_user(user_id: int, admin_username: str = "") -> bool:
    """
    管理员踢出用户（强制登出）
    
    Args:
        user_id: 要踢出的用户 ID
        admin_username: 执行操作的管理员用户名
        
    Returns:
        是否成功
    """
    session_data = get_user_session(user_id)
    
    if not session_data:
        logger.warning(f"用户 {user_id} 没有活跃会话，无需踢出")
        return True
    
    username = session_data.get("username", f"user_{user_id}")
    logger.info(f"🚫 管理员 {admin_username} 正在踢出用户: {username} (ID: {user_id})")
    
    return destroy_user_session(user_id, reason=f"kicked_by_{admin_username}")


# ==================== 单点登录检查 ====================

def check_single_login(user_id: int, new_token: str) -> Optional[Dict[str, Any]]:
    """
    检查单点登录冲突
    
    如果用户已在其他终端登录，则：
    1. 将旧 token 加入黑名单
    2. 创建新会话
    
    Args:
        user_id: 用户 ID
        new_token: 新的 JWT Token
        
    Returns:
        如果有旧会话，返回旧会话信息；否则返回 None
    """
    old_session = get_user_session(user_id)
    print(f"🔍 check_single_login: user_id={user_id}, old_session={'存在' if old_session else '不存在'}")
    
    if old_session:
        old_token = old_session.get("token")
        print(f"   - old_token: {old_token[:30] if old_token else 'None'}...")
        print(f"   - new_token: {new_token[:30]}...")
        print(f"   - token相同? {old_token == new_token}")
        
        if old_token and old_token != new_token:
            # 将旧 token 加入黑名单
            print(f"   - 正在拉黑旧 token...")
            success = revoke_token(old_token, reason="single_login_replaced")
            print(f"   - revoke_token 返回值: {success}")
            if success:
                print(f"🔄 单点登录：用户 {user_id} 的旧 token 已被替换")
            else:
                # 即使无法拉黑（如 token 已过期），也不影响新会话创建
                print(f"⚠️ 单点登录：旧 token 未加入黑名单（可能已过期或无效），但新会话已创建 (user_id={user_id})")
        else:
            print(f"   - 跳过拉黑（token相同或为空）")
    
    return old_session


def validate_token_with_session(token: str, user_id: int) -> bool:
    """
    验证 Token 是否与当前会话匹配（单点登录校验）
    
    Args:
        token: JWT Token
        user_id: 用户 ID
        
    Returns:
        Token 是否有效且与会话匹配
    """
    # 1. 检查是否在黑名单中
    if is_token_blacklisted(token):
        logger.warning(f"🚫 Token 已被拉黑: user_id={user_id}")
        return False
    
    # 2. 检查是否与会话中的 token 匹配
    session = get_user_session(user_id)
    if session:
        session_token = session.get("token")
        if session_token != token:
            logger.warning(f"🚫 Token 不匹配（可能已在其他终端登录）: user_id={user_id}")
            return False
    
    return True

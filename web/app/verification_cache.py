"""
验证码 Redis 缓存服务

将验证码从数据库迁移到 Redis，提供：
- 自动过期（Redis TTL）
- 更快的读写性能
- 减少数据库压力
"""
from datetime import timedelta
from typing import Optional
import logging

from ..cache import cache
from ..auth_security import CODE_EXPIRE_MINUTES, hash_verification_code, verify_code_hash

logger = logging.getLogger(__name__)


def _make_key(identifier: str, purpose: str) -> str:
    """生成 Redis 键名"""
    return f"verify_code:{purpose}:{identifier.lower().strip()}"


def store_verification_code(identifier: str, code: str, purpose: str = "register") -> bool:
    """
    存储验证码到 Redis
    
    Args:
        identifier: 标识符（邮箱或手机号）
        code: 明文验证码
        purpose: 用途 (register/forgot)
        
    Returns:
        是否成功
    """
    key = _make_key(identifier, purpose)
    code_hash = hash_verification_code(identifier, code)
    ttl = CODE_EXPIRE_MINUTES * 60  # 转换为秒
    
    success = cache.set(key, code_hash, ttl=ttl)
    if success:
        logger.debug(f"验证码已存储到 Redis: {key}, TTL={ttl}s")
    else:
        logger.warning(f"验证码存储失败，降级到数据库: {key}")
    
    return success


def get_verification_code_hash(identifier: str, purpose: str = "register") -> Optional[str]:
    """
    从 Redis 获取验证码哈希
    
    Args:
        identifier: 标识符（邮箱或手机号）
        purpose: 用途 (register/forgot)
        
    Returns:
        验证码哈希，不存在返回 None
    """
    key = _make_key(identifier, purpose)
    code_hash = cache.get(key)
    
    if code_hash:
        logger.debug(f"从 Redis 获取验证码: {key}")
    else:
        logger.debug(f"Redis 中未找到验证码: {key}")
    
    return code_hash


def delete_verification_code(identifier: str, purpose: str = "register") -> bool:
    """
    删除验证码
    
    Args:
        identifier: 标识符（邮箱或手机号）
        purpose: 用途 (register/forgot)
        
    Returns:
        是否成功
    """
    key = _make_key(identifier, purpose)
    success = cache.delete(key)
    if success:
        logger.debug(f"验证码已从 Redis 删除: {key}")
    return success


def verify_verification_code(identifier: str, code: str, purpose: str = "register") -> bool:
    """
    验证验证码
    
    Args:
        identifier: 标识符（邮箱或手机号）
        code: 用户输入的验证码
        purpose: 用途 (register/forgot)
        
    Returns:
        验证码是否正确
    """
    code_hash = get_verification_code_hash(identifier, purpose)
    if not code_hash:
        return False
    
    return verify_code_hash(identifier, code, code_hash)


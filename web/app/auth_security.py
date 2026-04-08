"""
认证与安全工具模块

提供密码哈希、JWT Token 管理、验证码生成和验证等安全相关功能。
使用 bcrypt 进行密码加密，HS256 算法签名 JWT。
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# 密码哈希上下文，使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-use-openssl-rand-hex-32")  # JWT 密钥（生产环境必须修改）
JWT_ALGORITHM = "HS256"  # JWT 签名算法
# 默认 7 天，但实际使用时会从数据库读取动态配置
ACCESS_TOKEN_EXPIRE_DAYS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_DAYS", "7"))

# 安全检查：防止使用默认密钥
if JWT_SECRET == "change-me-use-openssl-rand-hex-32":
    import warnings
    warnings.warn(
        "⚠️  警告：检测到使用默认 JWT_SECRET！\n"
        "   生产环境必须修改 .env 文件中的 JWT_SECRET 为强随机值。\n"
        "   建议执行：python3 -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "   当前服务仍可启动，但存在严重安全风险！",
        RuntimeWarning,
        stacklevel=2
    )

# 验证码配置
CODE_EXPIRE_MINUTES = int(os.environ.get("CODE_EXPIRE_MINUTES", "10"))  # 验证码有效期（分钟）
CODE_PEPPER = os.environ.get("CODE_PEPPER", JWT_SECRET + "_email_code")  # 验证码加盐


def hash_password(password: str) -> str:
    """
    使用 bcrypt 哈希密码
    
    Args:
        password: 明文密码
        
    Returns:
        bcrypt 哈希后的密码字符串
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    验证明文密码是否与哈希值匹配
    
    Args:
        plain: 明文密码
        hashed: bcrypt 哈希值
        
    Returns:
        是否匹配
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    
    Args:
        subject: Token 载荷，通常包含用户 ID 和用户名
        expires_delta: 过期时间增量，默认使用 ACCESS_TOKEN_EXPIRE_DAYS
        
    Returns:
        JWT Token 字符串
    """
    to_encode = subject.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def should_refresh_token(token: str, refresh_threshold_minutes: int = 60) -> bool:
    """
    检查是否需要刷新 token
    
    如果 token 剩余有效期小于阈值，则应该刷新。
    
    Args:
        token: JWT Token 字符串
        refresh_threshold_minutes: 刷新阈值（分钟），默认 60 分钟
        
    Returns:
        是否应该刷新 token
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True
        
        remaining_seconds = exp_timestamp - datetime.utcnow().timestamp()
        remaining_minutes = remaining_seconds / 60
        
        # 如果剩余时间小于阈值，需要刷新
        return remaining_minutes < refresh_threshold_minutes
    except JWTError:
        return False


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 JWT Token
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        解码后的载荷字典，验证失败返回 None
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def get_login_timeout_minutes(db) -> int:
    """
    从数据库获取登录超时配置（分钟）
    
    Args:
        db: 数据库会话
        
    Returns:
        登录超时时长（分钟），最小值为 1
    """
    from .settings_service import get_app_settings_row
    row = get_app_settings_row(db)
    return max(1, int(getattr(row, "login_timeout_minutes", 10) or 10))


def generate_digit_code(n: int = 6) -> str:
    """
    生成指定长度的数字验证码
    
    Args:
        n: 验证码长度，默认 6 位
        
    Returns:
        数字验证码字符串
    """
    return "".join(secrets.choice("0123456789") for _ in range(n))


def hash_verification_code(email: str, code: str) -> str:
    """
    对验证码进行哈希处理（加盐）
    
    使用 CODE_PEPPER 和用户邮箱作为盐，防止彩虹表攻击。
    
    Args:
        email: 用户邮箱或手机号
        code: 明文验证码
        
    Returns:
        SHA256 哈希值
    """
    raw = f"{CODE_PEPPER}|{email.lower().strip()}|{code}".encode()
    return hashlib.sha256(raw).hexdigest()


def verify_code_hash(email: str, code: str, code_hash: str) -> bool:
    """
    验证验证码是否正确
    
    使用恒定时间比较防止时序攻击。
    
    Args:
        email: 用户邮箱或手机号
        code: 用户输入的验证码
        code_hash: 数据库中存储的哈希值
        
    Returns:
        验证码是否正确
    """
    return secrets.compare_digest(
        hash_verification_code(email, code),
        code_hash,
    )


def mask_email(email: str) -> str:
    """
    脱敏邮箱地址
    
    Args:
        email: 完整邮箱地址
        
    Returns:
        脱敏后的邮箱，如：us***@example.com
    """
    if not email or "@" not in email:
        return "***"
    parts = email.split("@")
    username = parts[0]
    domain = parts[1]
    
    # 保留前2个字符和最后一个字符
    if len(username) <= 3:
        masked_username = "*" * len(username)
    else:
        masked_username = username[:2] + "*" * (len(username) - 3) + username[-1]
    
    return f"{masked_username}@{domain}"


def mask_phone(phone: str) -> str:
    """
    脱敏手机号
    
    Args:
        phone: 完整手机号
        
    Returns:
        脱敏后的手机号，如：138****5678
    """
    if not phone or len(phone) < 7:
        return "***"
    
    # 保留前3位和后4位
    return phone[:3] + "****" + phone[-4:]


def mask_username(username: str) -> str:
    """
    脱敏用户名
    
    Args:
        username: 用户名
        
    Returns:
        脱敏后的用户名，如：us***
    """
    if not username or len(username) <= 2:
        return "***"
    
    # 保留前2个字符
    return username[:2] + "*" * (len(username) - 2)

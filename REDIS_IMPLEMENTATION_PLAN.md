# Redis 缓存三阶段实施方案

## 📋 当前进度

- ✅ **第一阶段**：Redis 基础设施 + 验证码缓存（已完成）
- ⏳ **第二阶段**：Token 黑名单 + 速率限制优化
- ⏳ **第三阶段**：模型状态缓存 + 其他优化

---

## 🎯 第一阶段：验证码缓存（已完成）

### 已完成内容

1. ✅ 创建 `web/app/cache.py` - Redis 缓存服务类
2. ✅ 创建 `web/app/verification_cache.py` - 验证码缓存层
3. ✅ 修改注册验证码发送逻辑（支持 Redis 优先、数据库降级）
4. ✅ 添加 redis 依赖到 requirements.txt

### 待完成（找回密码验证码）

需要修改以下函数使用 Redis：

#### 1. 找回密码发送验证码 (`/api/auth/forgot-send-code`)

**文件**: `web/app/routers/auth.py`  
**行号**: ~466-536

```python
# 当前代码（邮箱）
row = VerificationCode(
    email=email,
    code_hash=hash_verification_code(email, code),
    expires_at=expires,
    purpose="forgot",
)
db.add(row)
db.commit()

# 改为
if not store_verification_code(email, code, "forgot"):
    # 降级到数据库
    row = VerificationCode(...)
    db.add(row)
    db.commit()
```

#### 2. 找回密码验证 (`/api/auth/forgot-reset`)

**文件**: `web/app/routers/auth.py`  
**行号**: ~538-608

```python
# 当前代码
row = (
    db.query(VerificationCode)
    .filter(VerificationCode.email == email, VerificationCode.purpose == "forgot")
    .order_by(VerificationCode.created_at.desc())
    .first()
)
if not row or row.expires_at < datetime.utcnow():
    raise HTTPException(status_code=400, detail="验证码无效或已过期")
if not verify_code_hash(email, code, row.code_hash):
    raise HTTPException(status_code=400, detail="验证码错误")

# 改为
code_hash = get_verification_code_hash(email, "forgot")
if not code_hash:
    # 降级到数据库查询
    row = db.query(VerificationCode)...
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(...)
    code_hash = row.code_hash

if not verify_code_hash(email, code, code_hash):
    raise HTTPException(status_code=400, detail="验证码错误")

# 验证成功后删除
delete_verification_code(email, "forgot")
```

---

## 🚀 第二阶段：Token 黑名单 + 速率限制

### 2.1 Token 黑名单（支持主动撤销）

#### 问题
- JWT 无状态，无法主动撤销
- 用户退出后，token 在有效期内仍可用
- 修改密码后，旧 token 仍然有效

#### 解决方案

**创建**: `web/app/token_blacklist.py`

```python
"""
Token 黑名单服务

用于主动撤销 JWT Token（退出登录、修改密码等场景）
"""
from ..cache import cache
import logging

logger = logging.getLogger(__name__)


def blacklist_token(token_jti: str, ttl: int = 86400 * 7) -> bool:
    """
    将 Token 加入黑名单
    
    Args:
        token_jti: Token 的唯一标识（需要在生成 token 时添加 jti 字段）
        ttl: 黑名单有效期（秒），默认 7 天（与 token 有效期一致）
        
    Returns:
        是否成功
    """
    key = f"token_blacklist:{token_jti}"
    success = cache.set(key, "1", ttl=ttl)
    if success:
        logger.info(f"Token 已加入黑名单: {token_jti[:8]}...")
    return success


def is_token_blacklisted(token_jti: str) -> bool:
    """
    检查 Token 是否在黑名单中
    
    Args:
        token_jti: Token 的唯一标识
        
    Returns:
        是否在黑名单中
    """
    key = f"token_blacklist:{token_jti}"
    return cache.exists(key)


def remove_from_blacklist(token_jti: str) -> bool:
    """
    从黑名单中移除（罕见场景）
    
    Args:
        token_jti: Token 的唯一标识
        
    Returns:
        是否成功
    """
    key = f"token_blacklist:{token_jti}"
    return cache.delete(key)
```

#### 修改 auth_security.py - 生成带 jti 的 Token

```python
import uuid

def create_access_token(subject: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = subject.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),  # 添加唯一标识
    })
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

#### 修改 deps.py - 验证 Token 时检查黑名单

```python
from .token_blacklist import is_token_blacklisted

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="无效令牌")
    
    # 检查 Token 是否在黑名单中
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token 已失效")
    
    # ... 后续逻辑
```

#### 修改退出登录接口

```python
@router.post("/logout")
async def logout(request: Request):
    from .deps import get_token_from_request
    from .auth_security import decode_token
    from .token_blacklist import blacklist_token
    
    token = get_token_from_request(request)
    if token:
        payload = decode_token(token)
        if payload and "jti" in payload:
            blacklist_token(payload["jti"])
    
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("access_token", path="/")
    return resp
```

### 2.2 速率限制优化

#### 创建: `web/app/rate_limit_redis.py`

```python
"""
基于 Redis 的分布式速率限制
"""
from fastapi import Request, HTTPException
from ..cache import cache
import time
import logging

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Redis 速率限制器"""
    
    def __init__(self, default_window: int = 60):
        """
        Args:
            default_window: 默认时间窗口（秒）
        """
        self.default_window = default_window
    
    def check_rate_limit(
        self,
        key_prefix: str,
        identifier: str,
        max_requests: int,
        window: int = None
    ) -> bool:
        """
        检查是否超过速率限制
        
        Args:
            key_prefix: 键前缀（如 "login"）
            identifier: 标识符（如 IP、用户ID）
            max_requests: 最大请求数
            window: 时间窗口（秒），默认使用 default_window
            
        Returns:
            是否允许请求（True=允许，False=拒绝）
        """
        if window is None:
            window = self.default_window
        
        key = f"rate_limit:{key_prefix}:{identifier}"
        current_time = int(time.time())
        window_key = f"{key}:{current_time // window}"
        
        # 原子递增
        count = cache.incr(window_key, ttl=window)
        
        if count > max_requests:
            logger.warning(f"速率限制: {key_prefix} {identifier} ({count}/{max_requests})")
            return False
        
        return True


# 全局实例
rate_limiter = RedisRateLimiter()


def check_login_rate_limit(request: Request, max_requests: int = 5) -> None:
    """
    检查登录速率限制
    
    Args:
        request: FastAPI 请求对象
        max_requests: 每分钟最大请求数
        
    Raises:
        HTTPException: 超过限制时抛出 429
    """
    ip = request.client.host
    if not rate_limiter.check_rate_limit("login", ip, max_requests, window=60):
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过于频繁，请稍后再试（最多{max_requests}次/分钟）"
        )
```

#### 修改登录接口使用新的限流

```python
@router.post("/login")
async def login(request: Request, body: LoginBody, db: Session = Depends(get_db)):
    from ..rate_limit_redis import check_login_rate_limit
    
    # 使用 Redis 限流
    check_login_rate_limit(request, max_requests=5)
    
    # ... 后续逻辑
```

---

## 💡 第三阶段：模型状态缓存 + 其他优化

### 3.1 模型状态缓存

#### 创建: `web/app/model_status_cache.py`

```python
"""
模型状态缓存服务

缓存模型加载状态，减少文件系统检查频率
"""
from ..cache import cache
from ..model_inference import ModelInference
import logging
import json

logger = logging.getLogger(__name__)

CACHE_KEY = "model_status"
CACHE_TTL = 300  # 5 分钟


def get_cached_model_status() -> dict:
    """
    获取缓存的模型状态
    
    Returns:
        模型状态字典，缓存未命中返回 None
    """
    status = cache.get(CACHE_KEY)
    if status:
        logger.debug("从缓存获取模型状态")
    return status


def update_model_status(status: dict) -> bool:
    """
    更新模型状态缓存
    
    Args:
        status: 模型状态字典
        
    Returns:
        是否成功
    """
    success = cache.set(CACHE_KEY, status, ttl=CACHE_TTL)
    if success:
        logger.debug(f"模型状态已缓存 (TTL={CACHE_TTL}s)")
    return success


def invalidate_model_status() -> bool:
    """
    使模型状态缓存失效
    
    Returns:
        是否成功
    """
    return cache.delete(CACHE_KEY)
```

#### 修改 main.py 中的模型状态接口

```python
@app.get("/api/settings")
async def get_settings(...):
    from .model_status_cache import get_cached_model_status, update_model_status
    
    # 尝试从缓存获取
    cached_status = get_cached_model_status()
    if cached_status:
        model_loaded = cached_status.get("model_loaded", False)
    else:
        # 缓存未命中，检查实际状态
        model_loaded = inference_service.is_model_loaded()
        update_model_status({"model_loaded": model_loaded})
    
    return {
        "model_loaded": model_loaded,
        # ... 其他字段
    }
```

### 3.2 图形验证码迁移到 Redis

#### 修改 captcha.py

```python
from .cache import cache

CAPTCHA_TTL = 300  # 5 分钟

def generate_captcha() -> dict:
    captcha_id = str(uuid.uuid4())
    code = generate_random_code()
    
    # 存储到 Redis
    cache.set(f"captcha:{captcha_id}", code, ttl=CAPTCHA_TTL)
    
    return {
        "captcha_id": captcha_id,
        "svg": generate_svg(code),
    }

def verify_captcha(captcha_id: str, code: str) -> bool:
    stored_code = cache.get(f"captcha:{captcha_id}")
    if not stored_code:
        return False
    
    # 验证后立即删除（一次性使用）
    cache.delete(f"captcha:{captcha_id}")
    
    return secrets.compare_digest(stored_code.lower(), code.lower())
```

---

## 🔧 部署配置

### Docker Compose 添加 Redis

**文件**: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    # ... 现有配置
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      # - REDIS_PASSWORD=your_password  # 可选
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis_data:
```

### 环境变量配置

**文件**: `.env`

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=  # 如果需要密码认证
```

---

## 📊 性能对比预期

| 功能 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 验证码读写 | DB查询 ~10ms | Redis ~1ms | **10x** |
| 速率限制 | 内存/DB | Redis 原子操作 | **分布式支持** |
| Token 撤销 | 无法实现 | Redis 黑名单 | **新功能** |
| 模型状态检查 | 文件系统 ~50ms | Redis 缓存 ~1ms | **50x** |

---

## ⚠️ 注意事项

1. **Redis 为可选依赖**：所有功能都有数据库降级方案
2. **向后兼容**：不影响现有功能，逐步迁移
3. **监控建议**：添加 Redis 连接失败告警
4. **数据持久化**：验证码等临时数据不需要持久化，Token 黑名单建议开启 AOF

---

## 🎓 回滚方案

如果遇到问题，可以回滚到任一阶段：

```bash
# 回滚到第一阶段之前
git reset --hard <commit-hash-before-phase1>

# 或者禁用 Redis（自动降级到数据库）
# 在 .env 中设置
REDIS_HOST=invalid-host
```

---

## 📝 下一步行动

1. **测试第一阶段**：确保验证码 Redis 缓存正常工作
2. **实施第二阶段**：Token 黑名单 + 速率限制
3. **实施第三阶段**：模型状态缓存 + 图形验证码
4. **性能测试**：对比优化前后的响应时间
5. **监控部署**：添加 Redis 健康检查和告警

---

**祝实施顺利！** 🚀

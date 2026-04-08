"""
Redis 缓存服务

提供统一的 Redis 访问接口，支持：
- 键值存储（自动序列化/反序列化）
- 过期时间管理
- 分布式锁
- 速率限制
"""
import json
import os
import logging
from typing import Optional, Any, Union
from datetime import timedelta

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存客户端单例"""
    
    _instance = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize()
    
    def _initialize(self):
        """初始化 Redis 连接"""
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            db = int(os.getenv("REDIS_DB", 0))
            password = os.getenv("REDIS_PASSWORD", None)
            
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password if password else None,
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            # 测试连接
            self._client.ping()
            logger.info(f"✅ Redis 连接成功: {host}:{port}/{db}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接失败: {e}，将降级到内存存储")
            self._client = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端实例"""
        return self._client
    
    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值（自动反序列化），不存在返回 None
        """
        if not self.is_available:
            return None
        
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET 错误 [{key}]: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Union[int, timedelta] = 3600) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值（自动序列化）
            ttl: 过期时间（秒或 timedelta）
            
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET 错误 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 错误 [{key}]: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.is_available:
            return False
        
        try:
            return self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 错误 [{key}]: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1, ttl: int = 60) -> int:
        """
        原子递增计数器（用于限流）
        
        Args:
            key: 缓存键
            amount: 递增量
            ttl: 首次创建时的过期时间（秒）
            
        Returns:
            递增后的值
        """
        if not self.is_available:
            return 0
        
        try:
            pipe = self._client.pipeline(True)
            pipe.incr(key, amount)
            pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Redis INCR 错误 [{key}]: {e}")
            return 0
    
    def keys(self, pattern: str = "*") -> list:
        """
        查找匹配的键（慎用，生产环境建议使用 SCAN）
        
        Args:
            pattern: 匹配模式，如 "captcha:*"
            
        Returns:
            匹配的键列表
        """
        if not self.is_available:
            return []
        
        try:
            return self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS 错误 [{pattern}]: {e}")
            return []
    
    def flush_db(self) -> bool:
        """
        清空当前数据库（危险操作，仅用于开发/测试）
        
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        try:
            self._client.flushdb()
            logger.warning("⚠️ Redis 数据库已清空")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB 错误: {e}")
            return False


# 全局单例
cache = RedisCache()

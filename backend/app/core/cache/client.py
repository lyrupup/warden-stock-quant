"""缓存后端：优先 Redis，连接不可用时降级为进程内内存实现。

提供登录失败限速计数器与 JWT jti 黑名单能力，便于本地/单测在无 Redis
环境下运行（M1 测试即使用内存降级）。
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from app.core.config import get_settings


class CacheBackend:
    """缓存抽象：统一暴露限流与黑名单接口。"""

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        """计数 +1；首次写入设置 ttl 秒过期，返回当前计数。"""
        raise NotImplementedError

    async def get_int(self, key: str) -> int:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def add_to_blacklist(self, jti: str, ttl: int) -> None:
        raise NotImplementedError

    async def is_blacklisted(self, jti: str) -> bool:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """进程内缓存降级实现（仅适用于单进程/测试）。"""

    def __init__(self) -> None:
        # key -> (value, expire_epoch)
        self._counters: Dict[str, Tuple[int, float]] = {}
        self._blacklist: Dict[str, float] = {}

    def _purge(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._counters.items() if exp and exp < now]
        for k in expired:
            self._counters.pop(k, None)
        bl_expired = [j for j, exp in self._blacklist.items() if exp and exp < now]
        for j in bl_expired:
            self._blacklist.pop(j, None)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        now = time.time()
        self._purge(now)
        value, exp = self._counters.get(key, (0, 0.0))
        if not exp or exp < now:
            value, exp = 0, now + ttl
        value += 1
        self._counters[key] = (value, exp)
        return value

    async def get_int(self, key: str) -> int:
        now = time.time()
        value, exp = self._counters.get(key, (0, 0.0))
        if exp and exp < now:
            self._counters.pop(key, None)
            return 0
        return value

    async def delete(self, key: str) -> None:
        self._counters.pop(key, None)

    async def add_to_blacklist(self, jti: str, ttl: int) -> None:
        self._blacklist[jti] = time.time() + ttl

    async def is_blacklisted(self, jti: str) -> bool:
        now = time.time()
        exp = self._blacklist.get(jti)
        if exp is None:
            return False
        if exp < now:
            self._blacklist.pop(jti, None)
            return False
        return True


class RedisCache(CacheBackend):
    """基于 redis.asyncio 的实现。"""

    _BLACKLIST_PREFIX = "jwt:blacklist:"

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url, decode_responses=True)

    async def incr_with_ttl(self, key: str, ttl: int) -> int:
        value = await self._redis.incr(key)
        if value == 1:
            await self._redis.expire(key, ttl)
        return int(value)

    async def get_int(self, key: str) -> int:
        value = await self._redis.get(key)
        return int(value) if value is not None else 0

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def add_to_blacklist(self, jti: str, ttl: int) -> None:
        await self._redis.set(f"{self._BLACKLIST_PREFIX}{jti}", "1", ex=max(ttl, 1))

    async def is_blacklisted(self, jti: str) -> bool:
        return bool(await self._redis.exists(f"{self._BLACKLIST_PREFIX}{jti}"))


_cache: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """获取缓存单例：能连 Redis 用 Redis，否则降级内存。"""
    global _cache
    if _cache is not None:
        return _cache

    settings = get_settings()
    # 测试或显式 sqlite 场景下，默认走内存缓存，避免依赖外部 Redis。
    use_memory = settings.app_env in {"test", "testing"} or bool(settings.database_url)
    if not use_memory:
        try:
            _cache = RedisCache(settings.redis_url)
        except Exception:
            _cache = InMemoryCache()
    else:
        _cache = InMemoryCache()
    return _cache


def reset_cache() -> None:
    """重置缓存单例（测试隔离用）。"""
    global _cache
    _cache = None

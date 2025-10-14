"""
Multi-level caching system for Amazon PA API responses

Architecture:
- L1: In-memory cache (cachetools LRU) for ultra-fast access
- L2: Redis cache for distributed caching across instances
- Automatic fallback from Redis to memory if Redis unavailable
"""

from typing import Optional, Any, Callable
import json
import hashlib
import functools
import logging
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using memory cache only")

from cachetools import TTLCache
from config.settings import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Production-grade multi-level cache manager
    
    Features:
    - L1 in-memory cache with LRU eviction
    - L2 Redis cache for persistence
    - Automatic serialization/deserialization
    - Cache key generation with namespace support
    - TTL management per cache operation
    """
    
    def __init__(self):
        # L1: In-memory cache (max 1000 items)
        self.memory_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_search)
        
        # L2: Redis cache
        self.redis_client = None
        if REDIS_AVAILABLE and settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}. Using memory cache only.")
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache (checks L1 then L2)
        
        Args:
            key: Cache key
            namespace: Cache namespace for organization
        
        Returns:
            Cached value or None if not found
        """
        cache_key = self._generate_key(key, namespace)
        
        # Try L1 (memory) first
        if cache_key in self.memory_cache:
            logger.debug(f"Cache HIT (memory): {cache_key}")
            return self.memory_cache[cache_key]
        
        # Try L2 (Redis)
        if self.redis_client:
            try:
                value = await self.redis_client.get(cache_key)
                if value:
                    logger.debug(f"Cache HIT (redis): {cache_key}")
                    # Deserialize and populate L1
                    deserialized = json.loads(value)
                    self.memory_cache[cache_key] = deserialized
                    return deserialized
            except Exception as e:
                logger.warning(f"Redis GET error: {e}")
        
        logger.debug(f"Cache MISS: {cache_key}")
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        namespace: str = "default",
        ttl: Optional[int] = None
    ):
        """
        Set value in both cache levels
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            namespace: Cache namespace
            ttl: Time to live in seconds (uses default if None)
        """
        cache_key = self._generate_key(key, namespace)
        ttl = ttl or settings.cache_ttl_search
        
        # Set in L1 (memory)
        self.memory_cache[cache_key] = value
        
        # Set in L2 (Redis)
        if self.redis_client:
            try:
                serialized = json.dumps(value)
                await self.redis_client.setex(
                    cache_key,
                    timedelta(seconds=ttl),
                    serialized
                )
                logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Redis SET error: {e}")
    
    async def delete(self, key: str, namespace: str = "default"):
        """Delete key from all cache levels"""
        cache_key = self._generate_key(key, namespace)
        
        # Delete from L1
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # Delete from L2
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Cache DELETE: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis DELETE error: {e}")
    
    async def clear_namespace(self, namespace: str):
        """Clear all keys in a namespace"""
        pattern = f"{namespace}:*"
        
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} keys from namespace: {namespace}")
            except Exception as e:
                logger.warning(f"Redis CLEAR error: {e}")
    
    def _generate_key(self, key: str, namespace: str) -> str:
        """Generate namespaced cache key with hash"""
        return f"{namespace}:{self._hash_key(key)}"
    
    def _hash_key(self, key: str) -> str:
        """Generate deterministic hash for cache key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

# Singleton instance
cache_manager = CacheManager()

# Decorator for automatic caching
def cached(namespace: str = "default", ttl: Optional[int] = None):
    """
    Decorator to automatically cache function results
    
    Usage:
        @cached(namespace="products", ttl=3600)
        async def get_product(asin: str):
            return await expensive_api_call(asin)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            cache_key = json.dumps(key_data, sort_keys=True)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, namespace, ttl)
            
            return result
        
        return wrapper
    return decorator

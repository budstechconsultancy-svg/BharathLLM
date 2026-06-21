"""
Fix 4.2: Redis-backed LLM response caching.
Caches query answers to save expensive GPU inference on repeated identical queries.
TTL is configurable via CACHE_TTL_SECONDS env var (default: 3600 = 1 hour).
"""
import os
import json
import hashlib
import logging

from typing import Optional

log = logging.getLogger("QueryCache")

CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class QueryCache:
    def __init__(self):
        self._client = None
        self._enabled = False
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            import redis
            self._client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            self._client.ping()
            self._enabled = True
            log.info(f"QueryCache connected to Redis at {REDIS_URL}. TTL: {CACHE_TTL}s.")
        except ImportError:
            log.warning("QueryCache: 'redis' package not installed. Caching disabled. Run: pip install redis")
        except Exception as e:
            log.warning(f"QueryCache: Redis connection failed ({e}). Caching disabled. Queries will hit LLM directly.")

    @property
    def enabled(self) -> bool:
        self._initialize()
        return self._enabled

    def _make_key(self, question: str, department: str) -> str:
        """Create a deterministic, collision-resistant cache key."""
        raw = f"{question.lower().strip()}||{(department or '').lower().strip()}"
        return "bharatllm:query:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, question: str, department: str) -> Optional[dict]:
        """Return cached response dict if present, else None."""
        self._initialize()
        if not self._enabled:
            return None
        try:
            key = self._make_key(question, department)
            value = self._client.get(key)
            if value:
                log.info(f"Cache HIT for key: {key[:20]}...")
                cached = json.loads(value)
                cached["cache_hit"] = True
                return cached
        except Exception as e:
            log.error(f"QueryCache GET error: {e}")
        return None

    def set(self, question: str, department: str, response: dict) -> None:
        """Cache an LLM response dict with TTL."""
        self._initialize()
        if not self._enabled:
            return
        try:
            key = self._make_key(question, department)
            # Don't cache errors or very short answers
            if len(response.get("answer", "")) < 10:
                return
            payload = json.dumps({k: v for k, v in response.items() if k != "cache_hit"})
            self._client.setex(key, CACHE_TTL, payload)
            log.info(f"Cache SET for key: {key[:20]}... TTL: {CACHE_TTL}s")
        except Exception as e:
            log.error(f"QueryCache SET error: {e}")

    def ping(self) -> bool:
        """Health-check the Redis connection."""
        self._initialize()
        if not self._enabled:
            return False
        try:
            return self._client.ping()
        except Exception:
            return False


# Module-level singleton
_cache_instance: Optional['QueryCache'] = None

def get_cache() -> QueryCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache()
    return _cache_instance

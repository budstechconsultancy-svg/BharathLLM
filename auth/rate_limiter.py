import os
import redis
from fastapi import HTTPException, status

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_r_client = None  # lazy — created on first use so run_dev.py fakeredis patch applies

def _get_redis():
    global _r_client
    if _r_client is None:
        _r_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _r_client

ROLE_RATE_LIMITS = {
    "super_admin": 500,
    "dept_admin": 60,
    "ministry_admin": 60,
    "dept_user": 20,
    "ministry_user": 20,
    "api_key": 60,   # default, overridden by api_keys.rate_limit_per_min
}

def check_rate_limit(key: str, max_requests: int, window_seconds: int = 60):
    redis_key = f"rate:{key}"
    try:
        r = _get_redis()
        current = r.incr(redis_key)
        if current == 1:
            r.expire(redis_key, window_seconds)
            
        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later."
            )
    except redis.RedisError as e:
        import logging
        logging.getLogger("RateLimiter").warning(f"Rate limiter Redis unavailable: {e}. Allowing request.")

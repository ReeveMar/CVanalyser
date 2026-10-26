import os
import redis
from fastapi import Request, HTTPException, status

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Connect to Redis for rate limiting
try:
    limiter_redis = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Limiter Redis initialization warning: {e}")
    limiter_redis = None

def get_client_ip(request: Request) -> str:
    """Extract client IP, prioritizing X-Forwarded-For when behind Nginx reverse proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def rate_limit(key_prefix: str, limit: int = 10, period: int = 60):
    """
    Sliding window / counter rate limiter dependency using Redis.
    - key_prefix: Endpoint category (e.g., 'login', 'register', 'ai')
    - limit: Maximum requests permitted
    - period: Window duration in seconds
    """
    async def dependency(request: Request):
        if not limiter_redis:
            return  # Fail-open if Redis is temporarily unavailable

        client_ip = get_client_ip(request)
        redis_key = f"rl:{key_prefix}:{client_ip}"

        try:
            current_count = limiter_redis.incr(redis_key)
            if current_count == 1:
                limiter_redis.expire(redis_key, period)
            elif current_count > limit:
                ttl = limiter_redis.ttl(redis_key)
                retry_after = ttl if ttl > 0 else period
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please wait {retry_after} seconds before trying again.",
                    headers={"Retry-After": str(retry_after)}
                )
        except redis.RedisError as e:
            # Do not block legitimate users if Redis has a transient error
            print(f"Redis rate limiter warning: {e}")

    return dependency

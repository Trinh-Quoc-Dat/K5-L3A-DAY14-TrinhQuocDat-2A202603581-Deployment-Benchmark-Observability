from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from .config import settings
from .redis_client import r

SLIDING_WINDOW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000000 + tonumber(clock[2])
local cutoff = now - 60000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', cutoff)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil((tonumber(oldest[2]) - cutoff) / 1000000))
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 60)
return 0
"""


def check_rate_limit(key: str) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})

    digest = sha256(key.encode()).hexdigest()
    retry_after = r.eval(SLIDING_WINDOW, 1, f"day14:rate:{digest}", limit, uuid4().hex)
    if retry_after:
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)}
        )

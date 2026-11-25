from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def check_budget() -> datetime:
    day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = float(r.get(f"day14:cost:{day.date()}") or 0)
    if total >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")
    return day


def record_cost(input_tokens: int, output_tokens: int, day: datetime) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    key = f"day14:cost:{day.date()}"
    with r.pipeline() as transaction:
        transaction.incrbyfloat(key, cost)
        transaction.expireat(key, day + timedelta(days=1))
        transaction.execute()
    return cost

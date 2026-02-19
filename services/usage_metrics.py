from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func

from models import UsageLog


def monthly_usage_summary(quota_chars: int, now: datetime | None = None) -> dict[str, int | float | str]:
    current = now or datetime.now(UTC)
    month_start = datetime(current.year, current.month, 1, tzinfo=UTC)
    if current.month == 12:
        next_month_start = datetime(current.year + 1, 1, 1, tzinfo=UTC)
    else:
        next_month_start = datetime(current.year, current.month + 1, 1, tzinfo=UTC)

    used_chars = (
        UsageLog.query.with_entities(func.coalesce(func.sum(UsageLog.char_count), 0))
        .filter(UsageLog.timestamp >= month_start)
        .filter(UsageLog.timestamp < next_month_start)
        .scalar()
    )
    used_chars = int(used_chars or 0)
    percent_used = round((used_chars / quota_chars) * 100, 2) if quota_chars > 0 else 0.0

    return {
        "month_start": month_start.date().isoformat(),
        "month_end": next_month_start.date().isoformat(),
        "used_chars": used_chars,
        "quota_chars": quota_chars,
        "percent_used": percent_used,
    }

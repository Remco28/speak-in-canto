from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from admin import admin_required
from models import UsageLog


admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_api_bp.route("/usage/monthly", methods=["GET"])
@admin_required
def monthly_usage():
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

    used_chars = (
        UsageLog.query.with_entities(func.coalesce(func.sum(UsageLog.char_count), 0))
        .filter(UsageLog.timestamp >= month_start)
        .filter(UsageLog.timestamp < next_month_start)
        .scalar()
    )
    used_chars = int(used_chars or 0)

    quota_chars = int(current_app.config.get("MONTHLY_QUOTA_CHARS", 1_000_000))
    percent_used = round((used_chars / quota_chars) * 100, 2) if quota_chars > 0 else 0.0

    return jsonify(
        {
            "month_start": month_start.date().isoformat(),
            "month_end": (next_month_start.date()).isoformat(),
            "used_chars": used_chars,
            "quota_chars": quota_chars,
            "percent_used": percent_used,
        }
    )

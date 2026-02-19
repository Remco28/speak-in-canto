from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from admin import admin_required
from services.usage_metrics import monthly_usage_summary


admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_api_bp.route("/usage/monthly", methods=["GET"])
@admin_required
def monthly_usage():
    quota_chars = int(current_app.config.get("MONTHLY_QUOTA_CHARS", 1_000_000))
    return jsonify(monthly_usage_summary(quota_chars=quota_chars))

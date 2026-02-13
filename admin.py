from __future__ import annotations

from datetime import UTC, datetime
from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from models import UsageLog, User, db


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/users", methods=["GET"])
@admin_required
def users_list():
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users", methods=["POST"])
@admin_required
def users_create():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    is_admin = request.form.get("is_admin") == "on"

    if not username:
        flash("Username is required.", "error")
        return redirect(url_for("admin.users_list"))

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users_list"))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash("Username already exists.", "error")
        return redirect(url_for("admin.users_list"))

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
    )
    db.session.add(user)
    db.session.commit()

    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    users = User.query.order_by(User.created_at.asc()).all()
    usage = _monthly_usage()
    return render_template("admin_dashboard.html", users=users, usage=usage)


def _monthly_usage() -> dict[str, int | float]:
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
    percent_used = round((used_chars / quota_chars) * 100, 2) if quota_chars else 0.0

    return {
        "used_chars": used_chars,
        "quota_chars": quota_chars,
        "percent_used": percent_used,
    }

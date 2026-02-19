from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from models import User, db
from services.usage_metrics import monthly_usage_summary


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


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def users_delete(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.dashboard"))

    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash("Cannot delete the last admin user.", "error")
            return redirect(url_for("admin.dashboard"))

    if user.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "error")
        return redirect(url_for("admin.dashboard"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))


def _monthly_usage() -> dict[str, int | float]:
    quota_chars = int(current_app.config.get("MONTHLY_QUOTA_CHARS", 1_000_000))
    summary = monthly_usage_summary(quota_chars=quota_chars)
    return {
        "used_chars": int(summary["used_chars"]),
        "quota_chars": int(summary["quota_chars"]),
        "percent_used": float(summary["percent_used"]),
    }

from __future__ import annotations

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember_me = _as_bool(request.form.get("remember_me"))

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember_me)
            if _is_safe_local_redirect(next_url):
                return redirect(next_url)
            return redirect(url_for("index"))

        flash("Invalid username or password.", "error")

    return render_template("login.html", next_url=next_url)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "on", "yes"}


def _is_safe_local_redirect(value: str) -> bool:
    if not value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return False
    return value.startswith("/")

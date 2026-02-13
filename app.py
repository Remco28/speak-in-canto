from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import click
from flask import Flask, render_template
from flask_login import LoginManager, current_user, login_required
from werkzeug.security import generate_password_hash

from admin import admin_bp
from auth import auth_bp
from models import User, db
from routes_tts import tts_bp


login_manager = LoginManager()
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def _build_sqlite_path(app: Flask) -> Path:
    database_path = app.config["DATABASE_PATH"]
    path = Path(database_path)
    if not path.is_absolute():
        path = Path(app.root_path) / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _enable_sqlite_pragmas(app: Flask) -> None:
    db_path = _build_sqlite_path(app)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    finally:
        conn.close()


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("SECRET_KEY")
    if flask_env != "development" and not secret_key:
        raise RuntimeError("SECRET_KEY is required outside development.")

    app.config["SECRET_KEY"] = secret_key or "dev-secret-key"
    app.config["DATABASE_PATH"] = os.getenv("DATABASE_PATH", "instance/speak_in_canto.db")
    app.config["MAX_INPUT_CHARS"] = int(os.getenv("MAX_INPUT_CHARS", "12000"))
    app.config["TEMP_AUDIO_DIR"] = os.getenv("TEMP_AUDIO_DIR", "static/temp_audio")
    app.config["TEMP_AUDIO_TTL_HOURS"] = int(os.getenv("TEMP_AUDIO_TTL_HOURS", "4"))
    app.config["MAX_TEMP_AUDIO_FILES"] = int(os.getenv("MAX_TEMP_AUDIO_FILES", "120"))
    app.config["MAX_TEMP_AUDIO_BYTES"] = int(os.getenv("MAX_TEMP_AUDIO_BYTES", str(300 * 1024 * 1024)))
    app.config["TTS_TIMEOUT_SECONDS"] = float(os.getenv("TTS_TIMEOUT_SECONDS", "20"))

    sqlite_path = _build_sqlite_path(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tts_bp)

    @app.route("/")
    @login_required
    def index():
        return render_template("index.html", user=current_user)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.cli.command("create-admin")
    @click.option("--username", required=True, help="Admin username")
    @click.option("--password", required=True, help="Admin password")
    def create_admin(username: str, password: str) -> None:
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")

        with app.app_context():
            db.create_all()
            existing = User.query.filter_by(username=username).first()
            if existing:
                raise click.ClickException(f"User '{username}' already exists.")

            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                is_admin=True,
            )
            db.session.add(user)
            db.session.commit()
            click.echo(f"Admin user '{username}' created.")

    with app.app_context():
        db.create_all()
        _enable_sqlite_pragmas(app)

    return app


app = create_app()

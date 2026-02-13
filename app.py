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
from routes_admin_api import admin_api_bp
from routes_translate import translate_bp
from routes_tts import tts_bp
from routes_user import user_bp
from services.tts_google import GoogleTTSWrapper


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
    app.config["HQ_TEXT_TARGET_MAX_BYTES"] = int(os.getenv("HQ_TEXT_TARGET_MAX_BYTES", "350"))
    app.config["HQ_TEXT_HARD_MAX_BYTES"] = int(os.getenv("HQ_TEXT_HARD_MAX_BYTES", "700"))
    app.config["GROK_API_KEY"] = os.getenv("GROK_API_KEY", "")
    app.config["GROK_MODEL"] = os.getenv("GROK_MODEL", "grok-4-1-fast-non-reasoning")
    app.config["GROK_BASE_URL"] = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
    app.config["TRANSLATION_TIMEOUT_SECONDS"] = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "20"))
    app.config["MAX_TRANSLATION_INPUT_CHARS"] = int(os.getenv("MAX_TRANSLATION_INPUT_CHARS", "12000"))
    app.config["MONTHLY_QUOTA_CHARS"] = int(os.getenv("MONTHLY_QUOTA_CHARS", "1000000"))

    sqlite_path = _build_sqlite_path(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(translate_bp)

    @app.route("/")
    @login_required
    def index():
        voice_catalog = GoogleTTSWrapper.get_voice_catalog()
        return render_template(
            "reader.html",
            user=current_user,
            voice_catalog=voice_catalog,
            max_input_chars=app.config["MAX_INPUT_CHARS"],
            max_translation_input_chars=app.config["MAX_TRANSLATION_INPUT_CHARS"],
        )

    @app.route("/reader")
    @login_required
    def reader():
        voice_catalog = GoogleTTSWrapper.get_voice_catalog()
        return render_template(
            "reader.html",
            user=current_user,
            voice_catalog=voice_catalog,
            max_input_chars=app.config["MAX_INPUT_CHARS"],
            max_translation_input_chars=app.config["MAX_TRANSLATION_INPUT_CHARS"],
        )

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

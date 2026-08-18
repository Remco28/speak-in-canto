from __future__ import annotations

import os

from flask import Flask, render_template

from routes_dictionary import dictionary_bp
from routes_translate import translate_bp
from routes_tts import tts_bp
from services.runtime_config import apply_runtime_config
from services.tts_google import GoogleTTSWrapper


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    app.config["SECRET_KEY"] = secret_key
    apply_runtime_config(app.config, flask_env=flask_env)

    app.register_blueprint(tts_bp)
    app.register_blueprint(translate_bp)
    app.register_blueprint(dictionary_bp)

    @app.route("/")
    def index():
        return _render_reader(app)

    @app.route("/reader")
    def reader():
        return _render_reader(app)

    def _render_reader(flask_app: Flask):
        voice_catalog = GoogleTTSWrapper.get_voice_catalog()
        return render_template(
            "reader.html",
            voice_catalog=voice_catalog,
            max_input_chars=flask_app.config["MAX_INPUT_CHARS"],
            max_translation_input_chars=flask_app.config["MAX_TRANSLATION_INPUT_CHARS"],
        )

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    return app


app = create_app()

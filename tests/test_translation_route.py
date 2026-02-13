from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db
from services.translation_grok import TranslationServiceError, TranslationTimeoutError


class FakeTranslatorSuccess:
    def __init__(self, *_args, **_kwargs):
        pass

    def translate_to_english(self, _text):
        return type(
            "Result",
            (),
            {"translation": "Hello world.", "provider": "grok", "model": "grok-4-1-fast-non-reasoning"},
        )()


class FakeTranslatorTimeout:
    def __init__(self, *_args, **_kwargs):
        pass

    def translate_to_english(self, _text):
        raise TranslationTimeoutError("timed out")


class FakeTranslatorError:
    def __init__(self, *_args, **_kwargs):
        pass

    def translate_to_english(self, _text):
        raise TranslationServiceError("upstream failed")


class TranslationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        os.environ["FLASK_ENV"] = "development"
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["MAX_TRANSLATION_INPUT_CHARS"] = "20"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(
                username="user",
                password_hash=generate_password_hash("userpass123"),
                is_admin=False,
            )
            db.session.add(user)
            db.session.commit()

        self.client.post(
            "/login",
            data={"username": "user", "password": "userpass123"},
            follow_redirects=True,
        )

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @patch("routes_translate.GrokTranslationService", FakeTranslatorSuccess)
    def test_translate_success(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["translation"], "Hello world.")
        self.assertEqual(data["provider"], "grok")

    def test_translate_rejects_empty(self):
        response = self.client.post("/api/translate", json={"text": "    "})
        self.assertEqual(response.status_code, 400)

    def test_translate_rejects_over_limit(self):
        response = self.client.post("/api/translate", json={"text": "你" * 30})
        self.assertEqual(response.status_code, 413)

    @patch("routes_translate.GrokTranslationService", FakeTranslatorTimeout)
    def test_translate_timeout_maps_504(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 504)

    @patch("routes_translate.GrokTranslationService", FakeTranslatorError)
    def test_translate_provider_error_maps_502(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("Translation failed", response.get_json().get("error", ""))


if __name__ == "__main__":
    unittest.main()

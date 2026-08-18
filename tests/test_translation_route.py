from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app import create_app
from services.translation_openrouter import TranslationServiceError, TranslationTimeoutError


class FakeTranslatorSuccess:
    def __init__(self, *_args, **_kwargs):
        pass

    def translate_to_english(self, _text):
        return type(
            "Result",
            (),
            {"translation": "Hello world.", "provider": "openrouter", "model": "openrouter/free"},
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
        os.environ["FLASK_ENV"] = "development"
        os.environ["MAX_TRANSLATION_INPUT_CHARS"] = "20"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("routes_translate.OpenRouterTranslationService", FakeTranslatorSuccess)
    def test_translate_success(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["translation"], "Hello world.")
        self.assertEqual(data["provider"], "openrouter")

    def test_translate_rejects_empty(self):
        response = self.client.post("/api/translate", json={"text": "    "})
        self.assertEqual(response.status_code, 400)

    def test_translate_rejects_over_limit(self):
        response = self.client.post("/api/translate", json={"text": "你" * 30})
        self.assertEqual(response.status_code, 413)

    @patch("routes_translate.OpenRouterTranslationService", FakeTranslatorTimeout)
    def test_translate_timeout_maps_504(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 504)

    @patch("routes_translate.OpenRouterTranslationService", FakeTranslatorError)
    def test_translate_provider_error_maps_502(self):
        response = self.client.post("/api/translate", json={"text": "你好"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("Translation failed", response.get_json().get("error", ""))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from email.message import Message

from services.translation_openrouter import (
    OpenRouterTranslationService,
    TranslationServiceError,
)


class FakeResponse:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class OpenRouterTranslationTests(unittest.TestCase):
    @patch("services.translation_openrouter.request.urlopen")
    def test_openrouter_request_shape_and_response(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "id": "completion-id",
                "model": "minimax/minimax-m3:free",
                "choices": [{"message": {"role": "assistant", "content": "Hello world."}}],
            }
        )
        service = OpenRouterTranslationService(
            api_key="test-openrouter-key",
            site_url="https://example.test/canto",
            app_name="Speak in Canto",
        )

        result = service.translate_to_english("你好")

        self.assertEqual(result.translation, "Hello world.")
        self.assertEqual(result.provider, "openrouter")
        self.assertEqual(result.model, "minimax/minimax-m3:free")
        req = urlopen.call_args.args[0]
        timeout = urlopen.call_args.kwargs["timeout"]
        self.assertEqual(req.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(timeout, 20.0)
        self.assertEqual(req.get_header("Authorization"), "Bearer test-openrouter-key")
        self.assertEqual(req.get_header("Http-referer"), "https://example.test/canto")
        self.assertEqual(req.get_header("X-openrouter-title"), "Speak in Canto")
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], "minimax/minimax-m3:free")
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": "你好"})
        self.assertEqual(payload["temperature"], 0.2)

    def test_missing_key_is_rejected_before_network_call(self):
        service = OpenRouterTranslationService(api_key="")
        with self.assertRaisesRegex(TranslationServiceError, "OPENROUTER_API_KEY"):
            service.translate_to_english("你好")

    @patch("services.translation_openrouter.request.urlopen")
    def test_upstream_http_error_is_safely_mapped(self, urlopen):
        urlopen.side_effect = HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=Message(),
            fp=None,
        )
        service = OpenRouterTranslationService(api_key="test-openrouter-key")
        with self.assertRaisesRegex(TranslationServiceError, "OpenRouter error 401"):
            service.translate_to_english("你好")


if __name__ == "__main__":
    unittest.main()

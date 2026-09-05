from __future__ import annotations

import io
import json
import socket
import unittest
from unittest.mock import patch
from urllib import error

from services.translation_openrouter import (
    OpenRouterTranslationService,
    TranslationServiceError,
    TranslationTimeoutError,
    _extract_translation,
)


def _fake_response(payload: dict):
    body = json.dumps(payload).encode("utf-8")
    return type(
        "Resp",
        (),
        {
            "__enter__": lambda self: self,
            "__exit__": lambda *a: None,
            "read": lambda self: body,
        },
    )()


class ExtractTranslationTests(unittest.TestCase):
    def test_string_content(self):
        self.assertEqual(
            _extract_translation({"choices": [{"message": {"content": " hi "}}]}),
            "hi",
        )

    def test_list_content(self):
        payload = {"choices": [{"message": {"content": [{"text": "Hel"}, {"text": "lo"}]}}]}
        self.assertEqual(_extract_translation(payload), "Hello")

    def test_missing_choices(self):
        self.assertEqual(_extract_translation({}), "")

    def test_empty_choices(self):
        self.assertEqual(_extract_translation({"choices": []}), "")


class OpenRouterServiceTests(unittest.TestCase):
    def test_missing_api_key_raises(self):
        service = OpenRouterTranslationService(api_key="")
        with self.assertRaises(TranslationServiceError):
            service.translate_to_english("hello")

    @patch("services.translation_openrouter.request.urlopen")
    def test_success(self, urlopen):
        urlopen.return_value = _fake_response({"choices": [{"message": {"content": "Hello"}}]})
        service = OpenRouterTranslationService(api_key="k", model="openrouter/free")
        result = service.translate_to_english("你好")
        self.assertEqual(result.translation, "Hello")
        self.assertEqual(result.provider, "openrouter")
        self.assertEqual(result.model, "openrouter/free")

    @patch("services.translation_openrouter.request.urlopen")
    def test_http_403_1010(self, urlopen):
        exc = error.HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            403,
            "Forbidden",
            None,
            io.BytesIO(b'{"error":"1010"}'),
        )
        urlopen.side_effect = exc
        service = OpenRouterTranslationService(api_key="k")
        with self.assertRaises(TranslationServiceError) as ctx:
            service.translate_to_english("hello")
        self.assertIn("403/1010", str(ctx.exception))
        cause = ctx.exception.__cause__
        if cause is not None and hasattr(cause, "close"):
            cause.close()

    @patch("services.translation_openrouter.request.urlopen")
    def test_timeout_maps_to_timeout_error(self, urlopen):
        urlopen.side_effect = socket.timeout("timed out")
        service = OpenRouterTranslationService(api_key="k")
        with self.assertRaises(TranslationTimeoutError):
            service.translate_to_english("hello")

    @patch("services.translation_openrouter.request.urlopen")
    def test_empty_translation_raises(self, urlopen):
        urlopen.return_value = _fake_response({"choices": []})
        service = OpenRouterTranslationService(api_key="k")
        with self.assertRaises(TranslationServiceError):
            service.translate_to_english("hello")


class OpenRouterRetryTests(unittest.TestCase):
    def _http_error(self, code, body=b"busy"):
        return error.HTTPError(
            "https://openrouter.ai/api/v1/chat/completions",
            code,
            "Upstream",
            None,
            io.BytesIO(body),
        )

    @patch("services.translation_openrouter.time.sleep")
    @patch("services.translation_openrouter.request.urlopen")
    def test_transient_503_retries_then_succeeds(self, urlopen, sleep):
        urlopen.side_effect = [
            self._http_error(503),
            _fake_response({"choices": [{"message": {"content": "Hello"}}]}),
        ]
        service = OpenRouterTranslationService(
            api_key="k", max_retries=1, retry_backoff_seconds=0.5
        )
        result = service.translate_to_english("你好")
        self.assertEqual(result.translation, "Hello")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.5)

    @patch("services.translation_openrouter.time.sleep")
    @patch("services.translation_openrouter.request.urlopen")
    def test_timeout_retries_with_exponential_backoff(self, urlopen, sleep):
        urlopen.side_effect = socket.timeout("timed out")
        service = OpenRouterTranslationService(
            api_key="k", max_retries=2, retry_backoff_seconds=1.0
        )
        with self.assertRaises(TranslationTimeoutError):
            service.translate_to_english("hello")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1.0, 2.0])

    @patch("services.translation_openrouter.time.sleep")
    @patch("services.translation_openrouter.request.urlopen")
    def test_non_retryable_400_does_not_retry(self, urlopen, sleep):
        urlopen.side_effect = self._http_error(400, b"bad request")
        service = OpenRouterTranslationService(api_key="k", max_retries=2)
        with self.assertRaises(TranslationServiceError):
            service.translate_to_english("hello")
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("services.translation_openrouter.time.sleep")
    @patch("services.translation_openrouter.request.urlopen")
    def test_missing_key_never_retries(self, urlopen, sleep):
        service = OpenRouterTranslationService(api_key="", max_retries=2)
        with self.assertRaises(TranslationServiceError):
            service.translate_to_english("hello")
        urlopen.assert_not_called()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()

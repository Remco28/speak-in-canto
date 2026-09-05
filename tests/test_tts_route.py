from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app import create_app


class FakeStore:
    def __init__(self, *_args, **_kwargs):
        pass

    def cleanup(self, **_kwargs):
        return {"remaining_files": 0, "remaining_bytes": 0, "deleted_files": 0}

    def save_audio(self, _content):
        return type("Stored", (), {"url": "/static/temp_audio/fake.mp3"})()


class FakeTTSValid:
    def __init__(self, *_args, **_kwargs):
        pass

    def validate_voice(self, voice_name, voice_mode):
        if voice_mode not in ("standard", "high_quality"):
            return False
        return voice_name == "yue-HK-Standard-A"


class TTSRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["FLASK_ENV"] = "development"
        os.environ["MAX_INPUT_CHARS"] = "20"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("routes_tts.AudioStore", FakeStore)
    @patch("routes_tts.GoogleTTSWrapper", FakeTTSValid)
    def test_voice_allowlist_enforced(self):
        response = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你好", "voice_name": "invalid", "speaking_rate": 1.0},
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes_tts.AudioStore", FakeStore)
    @patch("routes_tts.GoogleTTSWrapper", FakeTTSValid)
    def test_input_limit_enforced(self):
        response = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你" * 30, "voice_name": "yue-HK-Standard-A", "speaking_rate": 1.0},
        )
        self.assertEqual(response.status_code, 413)

    @patch("routes_tts.AudioStore", FakeStore)
    @patch("routes_tts.GoogleTTSWrapper", FakeTTSValid)
    @patch(
        "routes_tts._synthesize_with_fallback",
        lambda *_args, **_kwargs: {
            "audio_chunks": [b"abc"],
            "timepoints": [{"mark_name": "c_0", "seconds": 0.1}],
            "mark_to_token": {"c_0": 0},
            "sync_mode": "full",
            "sync_supported": True,
            "duration_seconds": 0.1,
        },
    )
    def test_success_returns_audio_and_metadata(self):
        response = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你好", "voice_name": "yue-HK-Standard-A", "speaking_rate": 1.0},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["audio_url"], "/static/temp_audio/fake.mp3")
        self.assertEqual(data["sync_mode"], "full")
        self.assertTrue(data["sync_supported"])

    @patch("routes_tts.AudioStore", FakeStore)
    @patch("routes_tts.GoogleTTSWrapper", FakeTTSValid)
    def test_audio_dir_outside_static_is_rejected(self):
        # No filesystem access: the path only needs to resolve outside static.
        self.app.config["TEMP_AUDIO_DIR"] = "/tmp/speak-in-canto-outside-static"
        response = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你好", "voice_name": "yue-HK-Standard-A", "speaking_rate": 1.0},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("misconfigured", response.get_json().get("error", "").lower())


if __name__ == "__main__":
    unittest.main()

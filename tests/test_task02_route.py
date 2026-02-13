from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
from models import UsageLog, User, db


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

    def validate_voice(self, voice_name):
        return voice_name == "yue-HK-Standard-A"


class Task02RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        os.environ["FLASK_ENV"] = "development"
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["MAX_INPUT_CHARS"] = "20"

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
            "duration_seconds": 0.1,
        },
    )
    def test_usage_log_only_on_success(self):
        ok = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你好", "voice_name": "yue-HK-Standard-A", "speaking_rate": 1.0},
        )
        self.assertEqual(ok.status_code, 200)

        with self.app.app_context():
            self.assertEqual(UsageLog.query.count(), 1)

        fail = self.client.post(
            "/api/tts/synthesize",
            json={"text": "你好", "voice_name": "invalid", "speaking_rate": 1.0},
        )
        self.assertEqual(fail.status_code, 400)

        with self.app.app_context():
            self.assertEqual(UsageLog.query.count(), 1)


if __name__ == "__main__":
    unittest.main()

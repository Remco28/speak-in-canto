from __future__ import annotations

import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from models import User, UserVoicePin, db


class UserVoicePinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        os.environ["FLASK_ENV"] = "development"
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["DATABASE_PATH"] = self.db_path

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(username="user", password_hash=generate_password_hash("userpass123"), is_admin=False)
            db.session.add(user)
            db.session.commit()

        self.client.post("/login", data={"username": "user", "password": "userpass123"}, follow_redirects=True)

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_toggle_pin_adds_and_removes(self):
        add = self.client.post(
            "/api/user/voice-pins/toggle",
            json={"voice_id": "yue-HK-Standard-A", "voice_mode": "standard"},
        )
        self.assertEqual(add.status_code, 200)
        self.assertTrue(add.get_json()["pinned"])

        with self.app.app_context():
            self.assertEqual(UserVoicePin.query.count(), 1)

        remove = self.client.post(
            "/api/user/voice-pins/toggle",
            json={"voice_id": "yue-HK-Standard-A", "voice_mode": "standard"},
        )
        self.assertEqual(remove.status_code, 200)
        self.assertFalse(remove.get_json()["pinned"])

        with self.app.app_context():
            self.assertEqual(UserVoicePin.query.count(), 0)

    def test_get_pins(self):
        self.client.post(
            "/api/user/voice-pins/toggle",
            json={"voice_id": "yue-HK-Standard-A", "voice_mode": "standard"},
        )
        response = self.client.get("/api/user/voice-pins")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["pins"]), 1)
        self.assertEqual(data["pins"][0]["voice_id"], "yue-HK-Standard-A")


if __name__ == "__main__":
    unittest.main()

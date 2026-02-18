from __future__ import annotations

import os
import tempfile
import unittest

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from models import User, UsageLog, db, log_usage


class Task01TestCase(unittest.TestCase):
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

            admin = User(
                username="admin",
                password_hash=generate_password_hash("adminpass123"),
                is_admin=True,
            )
            user = User(
                username="user",
                password_hash=generate_password_hash("userpass123"),
                is_admin=False,
            )
            db.session.add_all([admin, user])
            db.session.commit()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _login(self, username: str, password: str):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_password_hash_verification(self) -> None:
        raw = "secret123"
        hashed = generate_password_hash(raw)
        self.assertTrue(check_password_hash(hashed, raw))

    def test_login_success_and_failure(self) -> None:
        failure = self._login("user", "wrongpass")
        self.assertEqual(failure.status_code, 200)
        self.assertIn(b"Invalid username or password.", failure.data)

        success = self._login("user", "userpass123")
        self.assertEqual(success.status_code, 200)
        self.assertIn(b"Canto Reader", success.data)

    def test_login_with_remember_me_sets_cookie(self) -> None:
        response = self.client.post(
            "/login",
            data={"username": "user", "password": "userpass123", "remember_me": "1"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        cookies = response.headers.getlist("Set-Cookie")
        self.assertTrue(any("remember_token=" in cookie for cookie in cookies))

    def test_login_rejects_external_next_redirect(self) -> None:
        response = self.client.post(
            "/login?next=https://evil.example",
            data={"username": "user", "password": "userpass123"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.location)

    def test_admin_route_protection_for_non_admin(self) -> None:
        self._login("user", "userpass123")
        response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 403)

    def test_duplicate_username_handling(self) -> None:
        self._login("admin", "adminpass123")
        response = self.client.post(
            "/admin/users",
            data={"username": "user", "password": "anotherpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Username already exists.", response.data)

    def test_log_usage_inserts_row(self) -> None:
        with self.app.app_context():
            user = User.query.filter_by(username="user").first()
            assert user is not None

            log_usage(user_id=user.id, char_count=128, voice_name="yue-HK-Standard-A")

            row = UsageLog.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.char_count, 128)
            self.assertEqual(row.voice_name, "yue-HK-Standard-A")


if __name__ == "__main__":
    unittest.main()

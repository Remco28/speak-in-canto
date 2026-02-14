from __future__ import annotations

import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from models import UsageLog, User, db


class Task03RouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        os.environ["FLASK_ENV"] = "development"
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["DATABASE_PATH"] = self.db_path
        os.environ["MAX_INPUT_CHARS"] = "1234"
        os.environ["MONTHLY_QUOTA_CHARS"] = "1000000"

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

            db.session.add_all(
                [
                    UsageLog(user_id=1, char_count=100),
                    UsageLog(user_id=1, char_count=250),
                ]
            )
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

    def test_reader_page_renders_counter_limit(self):
        self._login("user", "userpass123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1234", response.data)
        self.assertIn(b"Canto Reader", response.data)

    def test_admin_usage_api_requires_admin(self):
        self._login("user", "userpass123")
        response = self.client.get("/api/admin/usage/monthly")
        self.assertEqual(response.status_code, 403)

    def test_admin_usage_api_returns_aggregate(self):
        self._login("admin", "adminpass123")
        response = self.client.get("/api/admin/usage/monthly")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["used_chars"], 350)
        self.assertEqual(data["quota_chars"], 1000000)
        self.assertGreaterEqual(data["percent_used"], 0)
        self.assertIn("month_start", data)
        self.assertIn("month_end", data)

    def test_admin_dashboard_requires_admin(self):
        self._login("user", "userpass123")
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

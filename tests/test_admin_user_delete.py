from __future__ import annotations

import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from models import User, db


class AdminDeleteUserTests(unittest.TestCase):
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
            admin1 = User(username="admin1", password_hash=generate_password_hash("adminpass123"), is_admin=True)
            admin2 = User(username="admin2", password_hash=generate_password_hash("adminpass123"), is_admin=True)
            user = User(username="user", password_hash=generate_password_hash("userpass123"), is_admin=False)
            db.session.add_all([admin1, admin2, user])
            db.session.commit()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _login(self, username: str, password: str):
        return self.client.post("/login", data={"username": username, "password": password}, follow_redirects=True)

    def test_admin_can_delete_normal_user(self):
        self._login("admin1", "adminpass123")
        with self.app.app_context():
            target = User.query.filter_by(username="user").first()
            assert target is not None
            target_id = target.id

        response = self.client.post(f"/admin/users/{target_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            self.assertIsNone(db.session.get(User, target_id))

    def test_admin_cannot_delete_self(self):
        self._login("admin1", "adminpass123")
        with self.app.app_context():
            me = User.query.filter_by(username="admin1").first()
            assert me is not None
            me_id = me.id

        response = self.client.post(f"/admin/users/{me_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cannot delete your own", response.data.lower())

    def test_cannot_delete_last_admin(self):
        self._login("admin1", "adminpass123")
        with self.app.app_context():
            admin2 = User.query.filter_by(username="admin2").first()
            assert admin2 is not None
            admin2_id = admin2.id

        self.client.post(f"/admin/users/{admin2_id}/delete", follow_redirects=True)

        with self.app.app_context():
            admin1 = User.query.filter_by(username="admin1").first()
            assert admin1 is not None
            admin1_id = admin1.id

        response = self.client.post(f"/admin/users/{admin1_id}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cannot delete the last admin", response.data.lower())


if __name__ == "__main__":
    unittest.main()

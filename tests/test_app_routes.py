from __future__ import annotations

import os
import unittest

from app import create_app


class AppRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["FLASK_ENV"] = "development"
        os.environ["MAX_INPUT_CHARS"] = "1234"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_index_renders_reader_without_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Canto Reader", response.data)

    def test_reader_route_renders_counter_limit(self):
        response = self.client.get("/reader")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1234", response.data)

    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_legacy_auth_routes_are_gone(self):
        self.assertEqual(self.client.get("/login").status_code, 404)
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 404)


if __name__ == "__main__":
    unittest.main()

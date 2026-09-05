from __future__ import annotations

import os
import unittest

from app import create_app
from services.audio_policy import (
    audio_url_prefix,
    public_audio_url,
    resolve_temp_audio_dir,
)


class AudioPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["FLASK_ENV"] = "development"
        # Never inherit a stale TEMP_AUDIO_DIR from another test module.
        os.environ["TEMP_AUDIO_DIR"] = "static/temp_audio"
        self.app = create_app()
        self.app.config["TESTING"] = True

    def test_default_dir_resolves_inside_static_with_static_url(self):
        self.app.config["TEMP_AUDIO_DIR"] = "static/temp_audio"
        directory = resolve_temp_audio_dir(self.app)
        self.assertTrue(directory.endswith("static/temp_audio"))
        self.assertEqual(audio_url_prefix(self.app), "/static/temp_audio")
        self.assertEqual(
            public_audio_url(self.app, "tts_abc.mp3"),
            "/static/temp_audio/tts_abc.mp3",
        )

    def test_custom_subdir_inside_static_gets_matching_url(self):
        self.app.config["TEMP_AUDIO_DIR"] = "static/temp_audio/custom_sub"
        self.assertEqual(audio_url_prefix(self.app), "/static/temp_audio/custom_sub")
        self.assertEqual(
            public_audio_url(self.app, "tts_abc.mp3"),
            "/static/temp_audio/custom_sub/tts_abc.mp3",
        )

    def test_absolute_dir_outside_static_is_rejected(self):
        self.app.config["TEMP_AUDIO_DIR"] = "/tmp/speak-in-canto-outside-static"
        with self.assertRaises(ValueError) as ctx:
            resolve_temp_audio_dir(self.app)
        self.assertIn("static", str(ctx.exception).lower())

    def test_parent_traversal_outside_static_is_rejected(self):
        self.app.config["TEMP_AUDIO_DIR"] = "static/../instance/audio"
        with self.assertRaises(ValueError):
            resolve_temp_audio_dir(self.app)

    def test_public_audio_url_rejects_unsafe_filename(self):
        self.app.config["TEMP_AUDIO_DIR"] = "static/temp_audio"
        with self.assertRaises(ValueError):
            public_audio_url(self.app, "../evil.mp3")
        with self.assertRaises(ValueError):
            public_audio_url(self.app, "")


if __name__ == "__main__":
    unittest.main()

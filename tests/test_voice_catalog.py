from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from services.tts_google import GoogleTTSWrapper


class VoiceCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        GoogleTTSWrapper._voice_catalog_cache = None
        GoogleTTSWrapper._voice_catalog_cache_at = 0.0

    def test_standard_catalog_is_offline(self):
        catalog = GoogleTTSWrapper.get_standard_voice_catalog()
        self.assertGreaterEqual(len(catalog), 4)
        self.assertTrue(all("id" in v and "label" in v for v in catalog))

    @patch.object(GoogleTTSWrapper, "_get_client", side_effect=Exception("no credentials"))
    def test_catalog_degrades_without_credentials(self, _client):
        catalog = GoogleTTSWrapper.get_voice_catalog()
        self.assertGreaterEqual(len(catalog["standard"]), 4)
        self.assertEqual(catalog["high_quality"], [])

    def test_standard_validation_is_local_without_remote_call(self):
        wrapper = GoogleTTSWrapper()
        with patch.object(
            GoogleTTSWrapper,
            "get_voice_catalog",
            side_effect=AssertionError("standard validation must not fetch the catalog"),
        ):
            self.assertTrue(wrapper.validate_voice("yue-HK-Standard-A", "standard"))
            self.assertFalse(wrapper.validate_voice("unknown-voice", "standard"))
            self.assertFalse(wrapper.validate_voice("yue-HK-Standard-A", "bogus-mode"))
        with patch.object(
            GoogleTTSWrapper,
            "_get_client",
            side_effect=AssertionError("standard validation must not call list_voices"),
        ):
            self.assertTrue(wrapper.validate_voice("yue-HK-Standard-B", "standard"))

    def test_high_quality_validation_uses_dynamic_catalog(self):
        GoogleTTSWrapper._voice_catalog_cache = {
            "standard": GoogleTTSWrapper.get_standard_voice_catalog(),
            "high_quality": [{"id": "yue-HK-Chirp3-HD-Orus", "label": "Chirp 3 HD - Orus"}],
        }
        GoogleTTSWrapper._voice_catalog_cache_at = time.time()
        wrapper = GoogleTTSWrapper()
        self.assertTrue(wrapper.validate_voice("yue-HK-Chirp3-HD-Orus", "high_quality"))
        self.assertFalse(wrapper.validate_voice("yue-HK-Standard-A", "high_quality"))


if __name__ == "__main__":
    unittest.main()

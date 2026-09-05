from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


class FakeDictionaryTTS:
    standard_calls = 0
    high_quality_calls = 0

    def __init__(self, *_args, **_kwargs):
        pass

    def validate_voice(self, _voice_name, _voice_mode):
        return True

    def synthesize_ssml(self, _ssml, _voice_name, _speaking_rate):
        FakeDictionaryTTS.standard_calls += 1
        return type("Chunk", (), {"audio_content": b"STD", "timepoints": []})()

    def synthesize_text(self, _text, _voice_name):
        FakeDictionaryTTS.high_quality_calls += 1
        return type("Chunk", (), {"audio_content": b"HQ", "timepoints": []})()


class DictionaryRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        base = Path(self.tmp_dir.name)
        self.cedict_path = base / "cc-cedict.u8"
        self.canto_path = base / "cc-canto.u8"

        self.cedict_path.write_text(
            "你好 你好 [ni3 hao3] /hello/hi/\n廣東話 广东话 [guang3 dong1 hua4] /Cantonese language/\n",
            encoding="utf-8",
        )
        self.canto_path.write_text(
            "你好 你好 [nei5 hou2] {nei5 hou2} /hello (Cantonese)/\n",
            encoding="utf-8",
        )

        os.environ["FLASK_ENV"] = "development"
        os.environ["DICTIONARY_ENABLED"] = "true"
        os.environ["DICTIONARY_CC_CEDICT_PATH"] = str(self.cedict_path)
        os.environ["DICTIONARY_CC_CANTO_PATH"] = str(self.canto_path)
        os.environ["MAX_DICTIONARY_INPUT_CHARS"] = "120"
        os.environ["MAX_DICTIONARY_TERM_CHARS"] = "32"
        # TEMP_AUDIO_DIR must resolve inside the app static folder so the
        # returned audio URLs stay servable; keep the scratch dir under the
        # (gitignored) default temp_audio tree.
        os.environ["TEMP_AUDIO_DIR"] = "static/temp_audio/test_dict_scratch"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        FakeDictionaryTTS.standard_calls = 0
        FakeDictionaryTTS.high_quality_calls = 0

    def tearDown(self) -> None:
        scratch = Path(self.app.root_path) / "static" / "temp_audio" / "test_dict_scratch"
        shutil.rmtree(scratch, ignore_errors=True)
        os.environ.pop("TEMP_AUDIO_DIR", None)
        self.tmp_dir.cleanup()

    def test_lookup_success(self):
        response = self.client.post("/api/dictionary/lookup", json={"text": "你好廣東話", "index": 3})
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsNotNone(data["best"])
        self.assertEqual(data["best"]["term"], "廣東話")

    def test_lookup_out_of_range(self):
        response = self.client.post("/api/dictionary/lookup", json={"text": "你好", "index": 5})
        self.assertEqual(response.status_code, 400)

    def test_lookup_rejects_over_limit(self):
        response = self.client.post("/api/dictionary/lookup", json={"text": "你" * 121, "index": 0})
        self.assertEqual(response.status_code, 413)

    def test_lookup_disabled_returns_503(self):
        self.app.config["DICTIONARY_ENABLED"] = False
        response = self.client.post("/api/dictionary/lookup", json={"text": "你好", "index": 0})
        self.assertEqual(response.status_code, 503)

    @patch("routes_dictionary.GoogleTTSWrapper", FakeDictionaryTTS)
    def test_speak_standard_uses_cache(self):
        payload = {"text": "你好", "voice_name": "yue-HK-Standard-A", "voice_mode": "standard"}
        first = self.client.post("/api/dictionary/speak", json=payload)
        self.assertEqual(first.status_code, 200)
        first_data = first.get_json()
        self.assertEqual(first_data["cached"], False)

        second = self.client.post("/api/dictionary/speak", json=payload)
        self.assertEqual(second.status_code, 200)
        second_data = second.get_json()
        self.assertEqual(second_data["cached"], True)
        self.assertEqual(first_data["audio_url"], second_data["audio_url"])
        self.assertTrue(first_data["audio_url"].startswith("/static/temp_audio/test_dict_scratch/"))
        self.assertEqual(FakeDictionaryTTS.standard_calls, 1)

    @patch("routes_dictionary.GoogleTTSWrapper", FakeDictionaryTTS)
    def test_speak_high_quality_path(self):
        payload = {"text": "廣東話", "voice_name": "yue-HK-Chirp3-HD-Orus", "voice_mode": "high_quality"}
        response = self.client.post("/api/dictionary/speak", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["cached"], False)
        self.assertEqual(FakeDictionaryTTS.high_quality_calls, 1)


if __name__ == "__main__":
    unittest.main()

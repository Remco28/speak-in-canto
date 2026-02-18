from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.dictionary_loader import DictionaryLoader
from services.dictionary_lookup import DictionaryLookupService


class DictionaryServiceTests(unittest.TestCase):
    def test_loader_parses_cedict_and_cccanto_styles(self):
        cedict = """
# comment
你好 你好 [ni3 hao3] /hello/hi/
""".strip()

        cccanto = """
你好 你好 [nei5 hou2] {nei5 hou2} /hello (Cantonese)/
""".strip()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cedict_path = base / "cedict.u8"
            cccanto_path = base / "cccanto.u8"
            cedict_path.write_text(cedict, encoding="utf-8")
            cccanto_path.write_text(cccanto, encoding="utf-8")

            loader = DictionaryLoader()
            loaded_cedict = loader.load_file(cedict_path, source="cc-cedict")
            loaded_cccanto = loader.load_file(cccanto_path, source="cc-canto")
            merged = loader.merge(loaded_cedict, loaded_cccanto)

        self.assertIn("你好", merged)
        self.assertEqual(len(merged["你好"]), 2)
        self.assertEqual(merged["你好"][0].source, "cc-cedict")
        self.assertEqual(merged["你好"][1].source, "cc-canto")
        self.assertEqual(merged["你好"][1].jyutping, "nei5 hou2")

    def test_lookup_prefers_longer_phrase_match(self):
        dictionary_body = """
廣東 广东 [Guang3 dong1] /Guangdong province/
廣東話 广东话 [guang3 dong1 hua4] {gwong2 dung1 waa2} /Cantonese language/
話 话 [hua4] /speech/words/
""".strip()

        with tempfile.TemporaryDirectory() as tmp:
            dictionary_path = Path(tmp) / "mix.u8"
            dictionary_path.write_text(dictionary_body, encoding="utf-8")
            loader = DictionaryLoader()
            entries = loader.load_file(dictionary_path, source="mixed")

        lookup = DictionaryLookupService(entries)

        text = "我講廣東話。"
        # Click on 東 inside 廣東話
        idx = text.index("東")
        result = lookup.lookup_at(text, idx)

        self.assertIsNotNone(result.best)
        self.assertEqual(result.best.term, "廣東話")
        self.assertGreaterEqual(len(result.alternatives), 1)

    def test_lookup_handles_no_match(self):
        lookup = DictionaryLookupService(entries_by_term={})
        result = lookup.lookup_at("你好", 0)
        self.assertIsNone(result.best)
        self.assertEqual(result.alternatives, ())


if __name__ == "__main__":
    unittest.main()

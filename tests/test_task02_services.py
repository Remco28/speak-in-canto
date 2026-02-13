from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from services.audio_store import AudioStore
from services.ssml_builder import SSMLBuilder
from routes_tts import _synthesize_with_fallback
from services.tts_google import TTSServiceError


class FakeTTS:
    def __init__(self, modes: list[dict[str, object]]) -> None:
        self.calls = []
        self.modes = modes
        self.idx = 0

    def synthesize_ssml(self, ssml: str, voice_name: str, speaking_rate: float):
        self.calls.append(ssml)
        mode = self.modes[min(self.idx, len(self.modes) - 1)]
        self.idx += 1
        return type(
            "Chunk",
            (),
            {
                "audio_content": mode["audio"],
                "timepoints": mode["timepoints"],
            },
        )()


class Task02ServiceTests(unittest.TestCase):
    def test_chunking_respects_hard_limit(self):
        builder = SSMLBuilder()
        text = "你好。" * 300
        tokens = builder.build_tokens(builder.normalize_text(text))
        chunks = builder.build_token_chunks(tokens, mode="full")

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            ssml = builder.build_ssml_for_chunk(chunk, mode="full").ssml
            self.assertLessEqual(len(ssml.encode("utf-8")), 5000)

    def test_mark_names_stay_continuous_across_chunks(self):
        builder = SSMLBuilder()
        text = "你" * 1200
        tokens = builder.build_tokens(text)
        chunks = builder.build_token_chunks(tokens, mode="full")

        all_mark_names = []
        for chunk in chunks:
            built = builder.build_ssml_for_chunk(chunk, mode="full")
            all_mark_names.extend(list(built.mark_to_token.keys()))

        self.assertEqual(all_mark_names[0], "c_0")
        self.assertEqual(all_mark_names[-1], f"c_{len(tokens)-1}")

    def test_fallback_switches_to_reduced_mode(self):
        builder = SSMLBuilder()
        tokens = builder.build_tokens("你好世界")

        fake = FakeTTS(
            [
                {
                    "audio": b"A",
                    "timepoints": [{"mark_name": "c_0", "seconds": 0.1}],
                },
                {
                    "audio": b"B",
                    "timepoints": [
                        {"mark_name": "c_0", "seconds": 0.1},
                        {"mark_name": "c_1", "seconds": 0.2},
                        {"mark_name": "c_2", "seconds": 0.3},
                    ],
                },
            ]
        )

        result = _synthesize_with_fallback(builder, fake, tokens, "yue-HK-Standard-A", 1.0)
        self.assertEqual(result["sync_mode"], "reduced")
        self.assertGreaterEqual(len(result["timepoints"]), 3)

    def test_monotonic_timepoints_after_merge(self):
        builder = SSMLBuilder()
        tokens = builder.build_tokens("你好。世界。")

        fake = FakeTTS(
            [
                {
                    "audio": b"A",
                    "timepoints": [
                        {"mark_name": "c_0", "seconds": 0.1},
                        {"mark_name": "c_1", "seconds": 0.2},
                        {"mark_name": "c_2", "seconds": 0.3},
                        {"mark_name": "c_3", "seconds": 0.4},
                        {"mark_name": "c_4", "seconds": 0.5},
                        {"mark_name": "c_5", "seconds": 0.6},
                    ],
                },
            ]
        )

        result = _synthesize_with_fallback(builder, fake, tokens, "yue-HK-Standard-A", 1.0)
        seconds = [point["seconds"] for point in result["timepoints"]]
        self.assertEqual(seconds, sorted(seconds))

    def test_fallback_failure_raises_error(self):
        builder = SSMLBuilder()
        tokens = builder.build_tokens("你好世界")

        fake = FakeTTS(
            [
                {"audio": b"A", "timepoints": []},
                {"audio": b"B", "timepoints": []},
            ]
        )

        with self.assertRaises(TTSServiceError):
            _synthesize_with_fallback(builder, fake, tokens, "yue-HK-Standard-A", 1.0)

    def test_cleanup_ttl_and_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AudioStore(tmp)
            root = Path(tmp)

            # Create files with deterministic sizes and old/new mtimes.
            file1 = root / "a.mp3"
            file2 = root / "b.mp3"
            file3 = root / "c.mp3"
            file1.write_bytes(b"x" * 100)
            file2.write_bytes(b"y" * 100)
            file3.write_bytes(b"z" * 100)

            old_time = 1000000000
            os.utime(file1, (old_time, old_time))
            os.utime(file2, (old_time + 1, old_time + 1))
            os.utime(file3, (old_time + 2, old_time + 2))

            result = store.cleanup(ttl_hours=0, max_files=2, max_bytes=150)
            self.assertLessEqual(result["remaining_files"], 2)
            self.assertLessEqual(result["remaining_bytes"], 150)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from services.audio_store import AudioStore
from services.ssml_builder import SSMLBuilder
from routes_tts import _synthesize_high_quality, _synthesize_with_fallback
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
    def test_high_quality_retries_by_splitting_when_sentence_too_long(self):
        class FakeHQTTS:
            def synthesize_text(self, text, _voice_name):
                if len(text) > 50:
                    raise TTSServiceError("400 This request contains sentences that are too long.")
                return type("Chunk", (), {"audio_content": b"A", "timepoints": []})()

        builder = SSMLBuilder()
        tokens = builder.build_tokens("據" * 120)
        result = _synthesize_high_quality(builder, FakeHQTTS(), tokens, "yue-HK-Chirp3-HD-Orus")
        self.assertGreater(len(result["audio_chunks"]), 1)
        self.assertGreaterEqual(result["hq_total_calls"], 1)
        self.assertGreaterEqual(result["hq_split_retries"], 1)

    def test_high_quality_respects_split_depth_budget(self):
        class FakeAlwaysTooLong:
            def synthesize_text(self, _text, _voice_name):
                raise TTSServiceError("400 This request contains sentences that are too long.")

        builder = SSMLBuilder()
        tokens = builder.build_tokens("據" * 120)
        with self.assertRaises(TTSServiceError) as ctx:
            _synthesize_high_quality(
                builder,
                FakeAlwaysTooLong(),
                tokens,
                "yue-HK-Chirp3-HD-Orus",
                max_split_depth=2,
                max_tts_calls=128,
            )
        self.assertIn("split depth", str(ctx.exception).lower())

    def test_high_quality_respects_tts_call_budget(self):
        class FakeAlwaysTooLong:
            def synthesize_text(self, _text, _voice_name):
                raise TTSServiceError("400 This request contains sentences that are too long.")

        builder = SSMLBuilder()
        tokens = builder.build_tokens("據" * 120)
        with self.assertRaises(TTSServiceError) as ctx:
            _synthesize_high_quality(
                builder,
                FakeAlwaysTooLong(),
                tokens,
                "yue-HK-Chirp3-HD-Orus",
                max_split_depth=20,
                max_tts_calls=5,
            )
        self.assertIn("call budget", str(ctx.exception).lower())

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

    def test_chunk_end_mark_used_for_offset(self):
        class FakeBuild:
            def __init__(self, token_ids):
                self.ssml = "<speak>...</speak>"
                self.mark_to_token = {f"c_{tid}": tid for tid in token_ids}
                self.mark_count = len(token_ids)

        class FakeBuilder:
            def build_token_chunks(self, _tokens, mode="full"):
                return [[0, 1], [2, 3]]

            def build_ssml_for_chunk(self, chunk_tokens, mode="full"):
                return FakeBuild(chunk_tokens)

        builder = FakeBuilder()
        tokens = [0, 1, 2, 3]
        first_end_mark = "chunk_end_0"
        second_end_mark = "chunk_end_1"

        fake = FakeTTS(
            [
                {
                    "audio": b"A",
                    "timepoints": [
                        {"mark_name": "c_0", "seconds": 0.2},
                        {"mark_name": "c_1", "seconds": 0.4},
                        {"mark_name": first_end_mark, "seconds": 1.0},
                    ],
                },
                {
                    "audio": b"B",
                    "timepoints": [
                        {"mark_name": "c_2", "seconds": 0.1},
                        {"mark_name": "c_3", "seconds": 0.3},
                        {"mark_name": second_end_mark, "seconds": 0.9},
                    ],
                },
            ]
        )

        result = _synthesize_with_fallback(builder, fake, tokens, "yue-HK-Standard-A", 1.0)
        merged = result["timepoints"]
        # First point from second chunk should be offset by chunk end (1.0), not last char (0.4).
        # That means we should observe a point at approximately 1.1.
        self.assertTrue(any(abs(p["seconds"] - 1.1) < 1e-9 for p in merged))

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

    def test_high_quality_text_chunking_splits_long_sentence_without_punctuation(self):
        builder = SSMLBuilder()
        # No sentence-ending punctuation; this should still split into safe HQ chunks.
        text = "據" * 220
        tokens = builder.build_tokens(text)
        chunks = builder.build_text_chunks(tokens, target_max_bytes=350, hard_max_bytes=700)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.encode("utf-8")), 700)


if __name__ == "__main__":
    unittest.main()

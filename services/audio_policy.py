from __future__ import annotations

from flask import Flask

from services.audio_store import AudioStore


def cleanup_audio_store(app: Flask, store: AudioStore) -> None:
    store.cleanup(
        ttl_hours=int(app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )

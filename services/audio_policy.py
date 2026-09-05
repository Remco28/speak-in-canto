from __future__ import annotations

from pathlib import Path

from flask import Flask

from services.audio_store import AudioStore


def resolve_temp_audio_dir(app: Flask) -> str:
    path = Path(app.config.get("TEMP_AUDIO_DIR", "static/temp_audio"))
    if not path.is_absolute():
        path = Path(app.root_path) / path
    return str(path)


def cleanup_audio_store(app: Flask, store: AudioStore) -> None:
    store.cleanup(
        ttl_hours=int(app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )


def cleanup_audio_store_at_startup(app: Flask) -> None:
    try:
        cleanup_audio_store(app, AudioStore(resolve_temp_audio_dir(app)))
    except Exception:
        app.logger.warning("Startup audio cleanup failed.", exc_info=True)

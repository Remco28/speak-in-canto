from __future__ import annotations

from pathlib import Path

from flask import Flask

from services.audio_store import AudioStore


def resolve_temp_audio_dir(app: Flask) -> str:
    """Resolve TEMP_AUDIO_DIR to an absolute path inside the app static folder.

    The synthesis endpoints return a public ``/static/...`` URL for saved
    audio, so a directory outside the static folder would produce URLs that
    404. Reject such configuration loudly instead of returning a dead URL.
    """
    raw = str(app.config.get("TEMP_AUDIO_DIR", "static/temp_audio"))
    path = Path(raw)
    if not path.is_absolute():
        path = Path(app.root_path) / path
    static_root = _static_root(app)
    resolved = path.resolve()
    try:
        resolved.relative_to(static_root)
    except ValueError:
        raise ValueError(
            f"TEMP_AUDIO_DIR {raw!r} must resolve inside the app static folder "
            f"({static_root}) so audio URLs stay servable; got {resolved}"
        ) from None
    return str(resolved)


def audio_url_prefix(app: Flask) -> str:
    """Public URL prefix matching the resolved TEMP_AUDIO_DIR."""
    static_root = _static_root(app)
    resolved = Path(resolve_temp_audio_dir(app)).resolve()
    rel_dir = resolved.relative_to(static_root).as_posix()
    if rel_dir in ("", "."):
        return "/static"
    return f"/static/{rel_dir}"


def public_audio_url(app: Flask, filename: str) -> str:
    if not filename or "/" in filename or filename in (".", ".."):
        raise ValueError(f"Invalid audio filename: {filename!r}")
    return f"{audio_url_prefix(app)}/{filename}"


def resolve_audio_location(app: Flask) -> tuple[str, str]:
    """Return ``(absolute_dir, url_prefix)`` for audio storage and serving."""
    directory = resolve_temp_audio_dir(app)
    return directory, audio_url_prefix(app)


def cleanup_audio_store(app: Flask, store: AudioStore) -> None:
    store.cleanup(
        ttl_hours=int(app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )


def cleanup_audio_store_at_startup(app: Flask) -> None:
    try:
        directory, url_prefix = resolve_audio_location(app)
        cleanup_audio_store(app, AudioStore(directory, url_prefix=url_prefix))
    except Exception:
        app.logger.warning("Startup audio cleanup failed.", exc_info=True)


def _static_root(app: Flask) -> Path:
    static_folder = app.static_folder or str(Path(app.root_path) / "static")
    return Path(static_folder).resolve()

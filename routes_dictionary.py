from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from services.audio_policy import cleanup_audio_store
from services.audio_store import AudioStore
from services.dictionary_loader import DictionaryLoader
from services.dictionary_lookup import DictionaryLookupResult, DictionaryLookupService
from services.tts_google import GoogleTTSWrapper, TTSServiceError


dictionary_bp = Blueprint("dictionary", __name__, url_prefix="/api/dictionary")


class DictionaryUnavailableError(Exception):
    pass


@dictionary_bp.route("/lookup", methods=["POST"])
@login_required
def lookup():
    if not bool(current_app.config.get("DICTIONARY_ENABLED", True)):
        return jsonify({"error": "Dictionary mode is disabled."}), 503

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "")
    index = payload.get("index")

    if not isinstance(index, int):
        return jsonify({"error": "index must be an integer"}), 400

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return jsonify({"error": "text is required"}), 400

    max_chars = int(current_app.config.get("MAX_DICTIONARY_INPUT_CHARS", 12000))
    if len(normalized) > max_chars:
        return jsonify({"error": f"Input exceeds max length ({max_chars})."}), 413

    if index < 0 or index >= len(normalized):
        return jsonify({"error": "index is out of range"}), 400

    try:
        service = _get_dictionary_service()
    except DictionaryUnavailableError as exc:
        return jsonify({"error": str(exc)}), 503

    result = service.lookup_at(
        normalized,
        index,
        max_alternatives=int(current_app.config.get("MAX_DICTIONARY_ALTERNATIVES", 3)),
    )

    return jsonify(_serialize_result(result)), 200


@dictionary_bp.route("/speak", methods=["POST"])
@login_required
def speak():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()
    voice_name = str(payload.get("voice_name") or "")
    voice_mode = str(payload.get("voice_mode") or "standard")

    if not text:
        return jsonify({"error": "text is required"}), 400
    max_term_chars = int(current_app.config.get("MAX_DICTIONARY_TERM_CHARS", 64))
    if len(text) > max_term_chars:
        return jsonify({"error": f"text exceeds max length ({max_term_chars})."}), 413
    if voice_mode not in ("standard", "high_quality"):
        return jsonify({"error": "Unsupported voice_mode"}), 400

    tts = GoogleTTSWrapper(timeout_seconds=float(current_app.config.get("TTS_TIMEOUT_SECONDS", 20.0)))
    if not tts.validate_voice(voice_name, voice_mode):
        return jsonify({"error": "Unsupported voice_name"}), 400

    store = AudioStore(current_app.config.get("TEMP_AUDIO_DIR", "static/temp_audio"))
    cleanup_audio_store(current_app, store)

    cache_key = _dictionary_speak_cache_key(text=text, voice_name=voice_name, voice_mode=voice_mode)
    cached = store.get_audio_by_key(cache_key, prefix="dict")
    if cached:
        return jsonify({"audio_url": cached.url, "cached": True}), 200

    try:
        if voice_mode == "high_quality":
            chunk = tts.synthesize_text(text, voice_name)
        else:
            ssml = f"<speak>{escape(text)}</speak>"
            chunk = tts.synthesize_ssml(ssml, voice_name, 1.0)
    except TTSServiceError as exc:
        current_app.logger.exception("Dictionary TTS failed: %s", exc)
        return jsonify({"error": "Dictionary speech failed."}), 502

    stored = store.save_audio_with_key(chunk.audio_content, cache_key=cache_key, prefix="dict")
    cleanup_audio_store(current_app, store)
    return jsonify({"audio_url": stored.url, "cached": False}), 200


def _serialize_result(result: DictionaryLookupResult) -> dict:
    def _serialize_candidate(candidate):
        return {
            "term": candidate.term,
            "start": candidate.start,
            "end": candidate.end,
            "definitions": list(candidate.definitions),
            "source": candidate.source,
            "jyutping": candidate.jyutping,
        }

    return {
        "best": _serialize_candidate(result.best) if result.best else None,
        "alternatives": [_serialize_candidate(item) for item in result.alternatives],
    }


def _get_dictionary_service() -> DictionaryLookupService:
    app = current_app
    expected_key = (
        str(app.config.get("DICTIONARY_CC_CEDICT_PATH", "")),
        str(app.config.get("DICTIONARY_CC_CANTO_PATH", "")),
    )

    ext = app.extensions.setdefault("dictionary", {})
    if ext.get("key") == expected_key and isinstance(ext.get("service"), DictionaryLookupService):
        return ext["service"]

    cedict_path = _resolve_path(expected_key[0])
    canto_path = _resolve_path(expected_key[1])

    missing: list[str] = []
    if not cedict_path.exists():
        missing.append(str(cedict_path))
    if not canto_path.exists():
        missing.append(str(canto_path))
    if missing:
        raise DictionaryUnavailableError(f"Dictionary files missing: {', '.join(missing)}")

    loader = DictionaryLoader()
    merged = loader.merge(
        loader.load_file(cedict_path, source="cc-cedict"),
        loader.load_file(canto_path, source="cc-canto"),
    )
    service = DictionaryLookupService(merged)

    ext["key"] = expected_key
    ext["service"] = service
    ext["term_count"] = len(merged)
    return service


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(current_app.root_path) / path


def _dictionary_speak_cache_key(text: str, voice_name: str, voice_mode: str) -> str:
    payload = f"{voice_mode}|{voice_name}|{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]

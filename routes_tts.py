from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from models import log_usage
from services.audio_store import AudioStore
from services.ssml_builder import SSMLBuilder
from services.tts_google import GoogleTTSWrapper, TTSServiceError


tts_bp = Blueprint("tts", __name__, url_prefix="/api/tts")


@tts_bp.route("/synthesize", methods=["POST"])
@login_required
def synthesize():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "")
    voice_name = str(payload.get("voice_name") or "")
    speaking_rate = payload.get("speaking_rate", 1.0)

    try:
        speaking_rate = float(speaking_rate)
    except (TypeError, ValueError):
        return jsonify({"error": "speaking_rate must be numeric"}), 400

    speaking_rate = max(0.5, min(2.0, speaking_rate))

    builder = SSMLBuilder()
    normalized = builder.normalize_text(text)
    if not normalized:
        return jsonify({"error": "text is required"}), 400

    max_input_chars = int(current_app.config.get("MAX_INPUT_CHARS", 12000))
    if len(normalized) > max_input_chars:
        return jsonify({"error": f"Input exceeds max length ({max_input_chars})."}), 413

    tts = GoogleTTSWrapper(timeout_seconds=float(current_app.config.get("TTS_TIMEOUT_SECONDS", 20.0)))
    if not tts.validate_voice(voice_name):
        return jsonify({"error": "Unsupported voice_name"}), 400

    store = AudioStore(current_app.config.get("TEMP_AUDIO_DIR", "static/temp_audio"))
    store.cleanup(
        ttl_hours=int(current_app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(current_app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(current_app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )

    tokens = builder.build_tokens(normalized)

    try:
        synthesis = _synthesize_with_fallback(builder, tts, tokens, voice_name, speaking_rate)
    except ValueError:
        return jsonify({"error": "Input cannot be chunked within SSML limits."}), 413
    except TTSServiceError as exc:
        current_app.logger.exception("TTS synthesis failed: %s", exc)
        if current_app.debug or current_app.config.get("TESTING"):
            return jsonify({"error": f"TTS synthesis failed: {exc}"}), 502
        return jsonify({"error": "TTS synthesis failed."}), 502

    merged_audio = b"".join(synthesis["audio_chunks"])
    stored = store.save_audio(merged_audio)
    store.cleanup(
        ttl_hours=int(current_app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(current_app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(current_app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )

    non_whitespace_count = sum(1 for token in tokens if not token.char.isspace())
    log_usage(current_user.id, non_whitespace_count, voice_name=voice_name)

    response = {
        "audio_url": stored.url,
        "duration_seconds": synthesis["duration_seconds"],
        "timepoints": synthesis["timepoints"],
        "tokens": [
            {
                "token_id": token.token_id,
                "char": token.char,
                "raw_index": token.raw_index,
                "jyutping": token.jyutping,
            }
            for token in tokens
        ],
        "mark_to_token": synthesis["mark_to_token"],
        "sync_mode": synthesis["sync_mode"],
    }
    return jsonify(response), 200


def _synthesize_with_fallback(builder, tts, tokens, voice_name, speaking_rate):
    sync_mode = "full"
    chunks = builder.build_token_chunks(tokens, mode="full")

    all_audio: list[bytes] = []
    all_timepoints: list[dict[str, float]] = []
    mark_to_token: dict[str, int] = {}
    offset = 0.0

    for chunk_tokens in chunks:
        built_full = builder.build_ssml_for_chunk(chunk_tokens, mode="full")
        full = tts.synthesize_ssml(built_full.ssml, voice_name, speaking_rate)

        active_build = built_full
        active_chunk = full

        degraded = built_full.mark_count > 0 and len(full.timepoints) < max(1, int(built_full.mark_count * 0.6))
        if degraded:
            built_reduced = builder.build_ssml_for_chunk(chunk_tokens, mode="reduced")
            reduced = tts.synthesize_ssml(built_reduced.ssml, voice_name, speaking_rate)
            if built_reduced.mark_count > 0 and len(reduced.timepoints) < max(1, int(built_reduced.mark_count * 0.6)):
                raise TTSServiceError("Timepoints remained degraded in reduced mode")

            sync_mode = "reduced"
            active_build = built_reduced
            active_chunk = reduced

        all_audio.append(active_chunk.audio_content)

        # Merge timepoints with global offset.
        chunk_last = 0.0
        for point in active_chunk.timepoints:
            seconds = float(point["seconds"]) + offset
            all_timepoints.append({"mark_name": point["mark_name"], "seconds": seconds})
            chunk_last = max(chunk_last, float(point["seconds"]))

        mark_to_token.update(active_build.mark_to_token)
        offset += chunk_last

    duration_seconds = all_timepoints[-1]["seconds"] if all_timepoints else 0.0
    return {
        "audio_chunks": all_audio,
        "timepoints": all_timepoints,
        "mark_to_token": mark_to_token,
        "sync_mode": sync_mode,
        "duration_seconds": duration_seconds,
    }

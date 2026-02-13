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
    voice_mode = str(payload.get("voice_mode") or "standard")
    if voice_mode not in ("standard", "high_quality"):
        return jsonify({"error": "Unsupported voice_mode"}), 400
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
    if not tts.validate_voice(voice_name, voice_mode):
        return jsonify({"error": "Unsupported voice_name"}), 400

    store = AudioStore(current_app.config.get("TEMP_AUDIO_DIR", "static/temp_audio"))
    store.cleanup(
        ttl_hours=int(current_app.config.get("TEMP_AUDIO_TTL_HOURS", 4)),
        max_files=int(current_app.config.get("MAX_TEMP_AUDIO_FILES", 120)),
        max_bytes=int(current_app.config.get("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)),
    )

    tokens = builder.build_tokens(normalized)

    try:
        if voice_mode == "high_quality":
            synthesis = _synthesize_high_quality(
                builder,
                tts,
                tokens,
                voice_name,
                target_max_bytes=int(current_app.config.get("HQ_TEXT_TARGET_MAX_BYTES", 350)),
                hard_max_bytes=int(current_app.config.get("HQ_TEXT_HARD_MAX_BYTES", 700)),
            )
        else:
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
        "sync_supported": synthesis["sync_supported"],
        "voice_mode": voice_mode,
        "jyutping_available": builder.jyutping_available,
    }
    return jsonify(response), 200


def _synthesize_with_fallback(builder, tts, tokens, voice_name, speaking_rate):
    sync_mode = "full"
    chunks = builder.build_token_chunks(tokens, mode="full")

    all_audio: list[bytes] = []
    all_timepoints: list[dict[str, float]] = []
    mark_to_token: dict[str, int] = {}
    offset = 0.0

    for chunk_index, chunk_tokens in enumerate(chunks):
        end_mark = f"chunk_end_{chunk_index}"

        built_full = builder.build_ssml_for_chunk(chunk_tokens, mode="full")
        full = tts.synthesize_ssml(_inject_end_mark(built_full.ssml, end_mark), voice_name, speaking_rate)
        full_user_points, full_end_seconds = _split_timepoints(full.timepoints, end_mark)

        active_build = built_full
        active_chunk = full
        active_points = full_user_points
        active_end_seconds = full_end_seconds

        degraded = built_full.mark_count > 0 and len(full_user_points) < max(1, int(built_full.mark_count * 0.6))
        if degraded:
            built_reduced = builder.build_ssml_for_chunk(chunk_tokens, mode="reduced")
            reduced = tts.synthesize_ssml(_inject_end_mark(built_reduced.ssml, end_mark), voice_name, speaking_rate)
            reduced_user_points, reduced_end_seconds = _split_timepoints(reduced.timepoints, end_mark)
            if built_reduced.mark_count > 0 and len(reduced_user_points) < max(
                1, int(built_reduced.mark_count * 0.6)
            ):
                raise TTSServiceError("Timepoints remained degraded in reduced mode")

            sync_mode = "reduced"
            active_build = built_reduced
            active_chunk = reduced
            active_points = reduced_user_points
            active_end_seconds = reduced_end_seconds

        all_audio.append(active_chunk.audio_content)

        # Merge timepoints with global offset.
        chunk_last = 0.0
        for point in active_points:
            seconds = float(point["seconds"]) + offset
            all_timepoints.append({"mark_name": point["mark_name"], "seconds": seconds})
            chunk_last = max(chunk_last, float(point["seconds"]))

        mark_to_token.update(active_build.mark_to_token)
        if active_end_seconds is not None:
            offset += float(active_end_seconds)
        else:
            offset += chunk_last

    duration_seconds = all_timepoints[-1]["seconds"] if all_timepoints else 0.0
    return {
        "audio_chunks": all_audio,
        "timepoints": all_timepoints,
        "mark_to_token": mark_to_token,
        "sync_mode": sync_mode,
        "sync_supported": True,
        "duration_seconds": duration_seconds,
    }


def _synthesize_high_quality(builder, tts, tokens, voice_name, target_max_bytes=350, hard_max_bytes=700):
    chunks = builder.build_text_chunks(tokens, target_max_bytes=target_max_bytes, hard_max_bytes=hard_max_bytes)
    all_audio: list[bytes] = []
    for chunk_text in chunks:
        chunk_audio = _synthesize_high_quality_chunk_with_retry(tts, chunk_text, voice_name)
        all_audio.extend(chunk_audio)

    return {
        "audio_chunks": all_audio,
        "timepoints": [],
        "mark_to_token": {},
        "sync_mode": "none",
        "sync_supported": False,
        "duration_seconds": 0.0,
    }


def _synthesize_high_quality_chunk_with_retry(tts, chunk_text: str, voice_name: str) -> list[bytes]:
    try:
        chunk = tts.synthesize_text(chunk_text, voice_name)
        return [chunk.audio_content]
    except TTSServiceError as exc:
        if not _is_sentence_too_long_error(exc):
            raise

        split_index = _find_text_split_index(chunk_text)
        if split_index is None:
            raise

        left = chunk_text[:split_index].strip()
        right = chunk_text[split_index:].strip()
        if not left or not right:
            raise

        return _synthesize_high_quality_chunk_with_retry(tts, left, voice_name) + _synthesize_high_quality_chunk_with_retry(
            tts, right, voice_name
        )


def _is_sentence_too_long_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "sentences that are too long" in msg


def _find_text_split_index(text: str) -> int | None:
    if len(text) <= 1:
        return None

    midpoint = len(text) // 2
    preferred_breaks = "。！？!?，,；;：:\n "
    window = max(1, min(60, len(text) // 3))

    for offset in range(window + 1):
        right = midpoint + offset
        if right < len(text) and text[right] in preferred_breaks:
            return right + 1
        left = midpoint - offset
        if left > 0 and text[left] in preferred_breaks:
            return left + 1

    return midpoint


def _inject_end_mark(ssml: str, mark_name: str) -> str:
    return ssml.replace("</speak>", f'<mark name="{mark_name}"/></speak>', 1)


def _split_timepoints(points: list[dict[str, float]], end_mark: str) -> tuple[list[dict[str, float]], float | None]:
    user_points: list[dict[str, float]] = []
    end_seconds: float | None = None
    for point in points:
        name = point.get("mark_name")
        if name == end_mark:
            end_seconds = float(point.get("seconds", 0.0))
        else:
            user_points.append(point)
    return user_points, end_seconds

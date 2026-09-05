from __future__ import annotations

import time
from dataclasses import dataclass

from flask import Blueprint, current_app, jsonify, request

from services.audio_policy import (
    audio_url_prefix,
    cleanup_audio_store,
    resolve_temp_audio_dir,
)
from services.audio_store import AudioStore
from services.ssml_builder import SSMLBuilder
from services.tts_google import GoogleTTSWrapper, TTSServiceError


tts_bp = Blueprint("tts", __name__, url_prefix="/api/tts")


@dataclass
class HQSynthesisContext:
    total_calls: int = 0
    split_retries: int = 0
    transient_retries: int = 0
    max_depth_seen: int = 0


@tts_bp.route("/synthesize", methods=["POST"])
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

    store = _audio_store_for_request()
    if store is None:
        return jsonify({"error": "Server audio storage is misconfigured."}), 500
    cleanup_audio_store(current_app, store)

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
                max_split_depth=int(current_app.config.get("HQ_MAX_SPLIT_DEPTH", 8)),
                max_tts_calls=int(current_app.config.get("HQ_MAX_TTS_CALLS", 128)),
                max_synthesis_seconds=float(current_app.config.get("HQ_MAX_SYNTHESIS_SECONDS", 90.0)),
                max_transient_retries=int(current_app.config.get("HQ_MAX_TRANSIENT_RETRIES", 2)),
                transient_backoff_seconds=float(
                    current_app.config.get("HQ_TRANSIENT_BACKOFF_SECONDS", 1.0)
                ),
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
    cleanup_audio_store(current_app, store)

    if voice_mode == "high_quality":
        current_app.logger.info(
            "HQ TTS metrics: init_chunks=%s total_calls=%s split_retries=%s transient_retries=%s max_depth=%s",
            synthesis.get("hq_initial_chunks", 0),
            synthesis.get("hq_total_calls", 0),
            synthesis.get("hq_split_retries", 0),
            synthesis.get("hq_transient_retries", 0),
            synthesis.get("hq_max_depth", 0),
        )

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


def _audio_store_for_request() -> AudioStore | None:
    try:
        directory = resolve_temp_audio_dir(current_app)
        prefix = audio_url_prefix(current_app)
    except ValueError as exc:
        current_app.logger.error("Invalid TEMP_AUDIO_DIR: %s", exc)
        return None
    return AudioStore(directory, url_prefix=prefix)


def _synthesize_high_quality(
    builder,
    tts,
    tokens,
    voice_name,
    target_max_bytes=350,
    hard_max_bytes=700,
    max_split_depth=8,
    max_tts_calls=128,
    max_synthesis_seconds=90.0,
    max_transient_retries=2,
    transient_backoff_seconds=1.0,
):
    chunks = builder.build_text_chunks(tokens, target_max_bytes=target_max_bytes, hard_max_bytes=hard_max_bytes)
    start_mono = time.monotonic()
    all_audio: list[bytes] = []
    context = HQSynthesisContext()
    for chunk_text in chunks:
        chunk_audio = _synthesize_high_quality_chunk_with_retry(
            tts,
            chunk_text,
            voice_name,
            context=context,
            depth=0,
            max_split_depth=max_split_depth,
            max_tts_calls=max_tts_calls,
            start_mono=start_mono,
            max_synthesis_seconds=max_synthesis_seconds,
            transient_attempt=0,
            max_transient_retries=max_transient_retries,
            transient_backoff_seconds=transient_backoff_seconds,
        )
        all_audio.extend(chunk_audio)

    return {
        "audio_chunks": all_audio,
        "timepoints": [],
        "mark_to_token": {},
        "sync_mode": "none",
        "sync_supported": False,
        "duration_seconds": 0.0,
        "hq_initial_chunks": len(chunks),
        "hq_total_calls": context.total_calls,
        "hq_split_retries": context.split_retries,
        "hq_transient_retries": context.transient_retries,
        "hq_max_depth": context.max_depth_seen,
    }


def _synthesize_high_quality_chunk_with_retry(
    tts,
    chunk_text: str,
    voice_name: str,
    context: HQSynthesisContext,
    depth: int,
    max_split_depth: int,
    max_tts_calls: int,
    start_mono: float | None = None,
    max_synthesis_seconds: float = 90.0,
    transient_attempt: int = 0,
    max_transient_retries: int = 2,
    transient_backoff_seconds: float = 1.0,
) -> list[bytes]:
    if start_mono is None:
        start_mono = time.monotonic()
    if (time.monotonic() - start_mono) >= max_synthesis_seconds:
        raise TTSServiceError("High Quality synthesis exceeded time budget. Please shorten input.")
    if context.total_calls >= max_tts_calls:
        raise TTSServiceError("High Quality synthesis exceeded retry call budget. Please shorten input.")
    if depth > max_split_depth:
        raise TTSServiceError("High Quality synthesis exceeded split depth. Please shorten input.")

    context.max_depth_seen = max(context.max_depth_seen, depth)
    context.total_calls += 1
    try:
        chunk = tts.synthesize_text(chunk_text, voice_name)
        return [chunk.audio_content]
    except TTSServiceError as exc:
        if _is_sentence_too_long_error(exc):
            split_index = _find_text_split_index(chunk_text)
            if split_index is None:
                raise

            left = chunk_text[:split_index].strip()
            right = chunk_text[split_index:].strip()
            if not left or not right:
                raise

            context.split_retries += 1
            return _synthesize_high_quality_chunk_with_retry(
                tts,
                left,
                voice_name,
                context=context,
                depth=depth + 1,
                max_split_depth=max_split_depth,
                max_tts_calls=max_tts_calls,
                start_mono=start_mono,
                max_synthesis_seconds=max_synthesis_seconds,
                transient_attempt=0,
                max_transient_retries=max_transient_retries,
                transient_backoff_seconds=transient_backoff_seconds,
            ) + _synthesize_high_quality_chunk_with_retry(
                tts,
                right,
                voice_name,
                context=context,
                depth=depth + 1,
                max_split_depth=max_split_depth,
                max_tts_calls=max_tts_calls,
                start_mono=start_mono,
                max_synthesis_seconds=max_synthesis_seconds,
                transient_attempt=0,
                max_transient_retries=max_transient_retries,
                transient_backoff_seconds=transient_backoff_seconds,
            )

        if transient_attempt < max_transient_retries and _is_transient_error(exc):
            context.transient_retries += 1
            delay = transient_backoff_seconds * (2**transient_attempt)
            remaining = max_synthesis_seconds - (time.monotonic() - start_mono)
            if remaining <= 0:
                raise TTSServiceError(
                    "High Quality synthesis exceeded time budget. Please shorten input."
                ) from exc
            time.sleep(min(delay, remaining))
            return _synthesize_high_quality_chunk_with_retry(
                tts,
                chunk_text,
                voice_name,
                context=context,
                depth=depth,
                max_split_depth=max_split_depth,
                max_tts_calls=max_tts_calls,
                start_mono=start_mono,
                max_synthesis_seconds=max_synthesis_seconds,
                transient_attempt=transient_attempt + 1,
                max_transient_retries=max_transient_retries,
                transient_backoff_seconds=transient_backoff_seconds,
            )
        raise


_LENGTH_ERROR_HINTS = (
    "sentences that are too long",
    "sentence too long",
    "sentence is too long",
    "text too long",
    "text is too long",
    "input too long",
    "input is too long",
    "too long",
    "too large",
    "exceeds the maximum",
    "exceeds maximum",
    "maximum allowed length",
    "maximum length",
    "max length",
)


def _is_sentence_too_long_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if any(hint in msg for hint in _LENGTH_ERROR_HINTS):
        return True
    # Generic provider phrasing such as "exceeds 500 characters": length-like
    # words near "exceed", but never quota errors.
    if "exceed" in msg and "quota" not in msg:
        if any(word in msg for word in ("character", "length", "sentence", "text", "input", "utterance")):
            return True
    return False


_TRANSIENT_ERROR_HINTS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "too many requests",
    "rate limit",
    "rate-limit",
    "temporarily",
    "temporary failure",
    "try again",
    "timeout",
    "timed out",
    "deadline exceeded",
    "unavailable",
    "service unavailable",
    "internal error",
    "backend error",
    "connection reset",
    "connection aborted",
    "connection refused",
    "broken pipe",
    "overloaded",
)


def _is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(hint in msg for hint in _TRANSIENT_ERROR_HINTS)


_HQ_STRONG_BREAKS = "。！？!?\n…"
_HQ_WEAK_BREAKS = "，,；;：:、 \t「」『』（）()〈〉《》【】—·-"


def _find_text_split_index(text: str) -> int | None:
    if len(text) <= 1:
        return None

    midpoint = len(text) // 2
    window = max(1, min(60, len(text) // 3))

    # Prefer strong sentence boundaries first so fallback splits are less
    # likely to cut Cantonese text mid-clause, then fall back to clause breaks.
    for breaks in (_HQ_STRONG_BREAKS, _HQ_WEAK_BREAKS):
        for offset in range(window + 1):
            right = midpoint + offset
            if right < len(text) and text[right] in breaks:
                return right + 1
            left = midpoint - offset
            if left > 0 and text[left] in breaks:
                return left + 1

    index = midpoint
    # Avoid cutting inside an ASCII letter/digit run (e.g. "OpenRouter").
    steps = 0
    while (
        steps < window
        and 0 < index < len(text)
        and text[index - 1].isascii()
        and text[index - 1].isalnum()
        and text[index].isascii()
        and text[index].isalnum()
    ):
        index += 1
        steps += 1
    if index >= len(text):
        return midpoint
    return index


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

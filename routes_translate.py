from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from services.translation_grok import GrokTranslationService, TranslationServiceError, TranslationTimeoutError


translate_bp = Blueprint("translate", __name__, url_prefix="/api")


@translate_bp.route("/translate", methods=["POST"])
@login_required
def translate():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "")
    normalized = text.strip()
    if not normalized:
        return jsonify({"error": "text is required"}), 400

    max_chars = int(current_app.config.get("MAX_TRANSLATION_INPUT_CHARS", 12000))
    if len(normalized) > max_chars:
        return jsonify({"error": f"Input exceeds max length ({max_chars})."}), 413

    service = GrokTranslationService(
        api_key=str(current_app.config.get("GROK_API_KEY", "")),
        model=str(current_app.config.get("GROK_MODEL", "grok-4-1-fast-non-reasoning")),
        base_url=str(current_app.config.get("GROK_BASE_URL", "https://api.x.ai/v1")),
        timeout_seconds=float(current_app.config.get("TRANSLATION_TIMEOUT_SECONDS", 20.0)),
    )

    started = time.monotonic()
    try:
        result = service.translate_to_english(normalized)
    except TranslationTimeoutError as exc:
        latency = int((time.monotonic() - started) * 1000)
        current_app.logger.warning("Translation timeout after %sms for %s chars", latency, len(normalized))
        return jsonify({"error": "Translation request timed out."}), 504
    except TranslationServiceError as exc:
        latency = int((time.monotonic() - started) * 1000)
        current_app.logger.warning("Translation failed after %sms for %s chars: %s", latency, len(normalized), exc)
        if current_app.debug or current_app.config.get("TESTING"):
            return jsonify({"error": f"Translation failed: {exc}"}), 502
        return jsonify({"error": "Translation failed."}), 502

    latency = int((time.monotonic() - started) * 1000)
    current_app.logger.info("Translation success in %sms for %s chars", latency, len(normalized))

    return (
        jsonify(
            {
                "translation": result.translation,
                "provider": result.provider,
                "model": result.model,
            }
        ),
        200,
    )

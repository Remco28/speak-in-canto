from __future__ import annotations

import os


def apply_runtime_config(config: dict) -> None:
    config["PORT"] = _env_int("PORT", 8734)
    config["MAX_INPUT_CHARS"] = _env_int("MAX_INPUT_CHARS", 12000)
    config["TEMP_AUDIO_DIR"] = os.getenv("TEMP_AUDIO_DIR", "static/temp_audio")
    config["TEMP_AUDIO_TTL_HOURS"] = _env_int("TEMP_AUDIO_TTL_HOURS", 4)
    config["MAX_TEMP_AUDIO_FILES"] = _env_int("MAX_TEMP_AUDIO_FILES", 120)
    config["MAX_TEMP_AUDIO_BYTES"] = _env_int("MAX_TEMP_AUDIO_BYTES", 300 * 1024 * 1024)
    config["TTS_TIMEOUT_SECONDS"] = _env_float("TTS_TIMEOUT_SECONDS", 20.0)
    config["HQ_TEXT_TARGET_MAX_BYTES"] = _env_int("HQ_TEXT_TARGET_MAX_BYTES", 350)
    config["HQ_TEXT_HARD_MAX_BYTES"] = _env_int("HQ_TEXT_HARD_MAX_BYTES", 700)
    config["HQ_MAX_SPLIT_DEPTH"] = _env_int("HQ_MAX_SPLIT_DEPTH", 8)
    config["HQ_MAX_TTS_CALLS"] = _env_int("HQ_MAX_TTS_CALLS", 128)
    config["HQ_MAX_SYNTHESIS_SECONDS"] = _env_float("HQ_MAX_SYNTHESIS_SECONDS", 90.0)
    config["HQ_MAX_TRANSIENT_RETRIES"] = _env_int("HQ_MAX_TRANSIENT_RETRIES", 2)
    config["HQ_TRANSIENT_BACKOFF_SECONDS"] = _env_float("HQ_TRANSIENT_BACKOFF_SECONDS", 1.0)
    config["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
    config["OPENROUTER_MODEL"] = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    config["OPENROUTER_BASE_URL"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    config["TRANSLATION_TIMEOUT_SECONDS"] = _env_float("TRANSLATION_TIMEOUT_SECONDS", 20.0)
    config["OPENROUTER_MAX_RETRIES"] = _env_int("OPENROUTER_MAX_RETRIES", 1)
    config["OPENROUTER_RETRY_BACKOFF_SECONDS"] = _env_float("OPENROUTER_RETRY_BACKOFF_SECONDS", 1.0)
    config["MAX_TRANSLATION_INPUT_CHARS"] = _env_int("MAX_TRANSLATION_INPUT_CHARS", 12000)
    config["DICTIONARY_ENABLED"] = _env_bool("DICTIONARY_ENABLED", True)
    config["DICTIONARY_CC_CEDICT_PATH"] = os.getenv(
        "DICTIONARY_CC_CEDICT_PATH", "data/dictionaries/cc-cedict.u8"
    )
    config["DICTIONARY_CC_CANTO_PATH"] = os.getenv(
        "DICTIONARY_CC_CANTO_PATH", "data/dictionaries/cc-canto.u8"
    )
    config["MAX_DICTIONARY_INPUT_CHARS"] = _env_int("MAX_DICTIONARY_INPUT_CHARS", 12000)
    config["MAX_DICTIONARY_ALTERNATIVES"] = _env_int("MAX_DICTIONARY_ALTERNATIVES", 3)
    config["MAX_DICTIONARY_TERM_CHARS"] = _env_int("MAX_DICTIONARY_TERM_CHARS", 64)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default

from __future__ import annotations

import os


def apply_runtime_config(config: dict, flask_env: str) -> None:
    config["PORT"] = int(os.getenv("PORT", "8734"))
    config["MAX_INPUT_CHARS"] = int(os.getenv("MAX_INPUT_CHARS", "12000"))
    config["TEMP_AUDIO_DIR"] = os.getenv("TEMP_AUDIO_DIR", "static/temp_audio")
    config["TEMP_AUDIO_TTL_HOURS"] = int(os.getenv("TEMP_AUDIO_TTL_HOURS", "4"))
    config["MAX_TEMP_AUDIO_FILES"] = int(os.getenv("MAX_TEMP_AUDIO_FILES", "120"))
    config["MAX_TEMP_AUDIO_BYTES"] = int(os.getenv("MAX_TEMP_AUDIO_BYTES", str(300 * 1024 * 1024)))
    config["TTS_TIMEOUT_SECONDS"] = float(os.getenv("TTS_TIMEOUT_SECONDS", "20"))
    config["HQ_TEXT_TARGET_MAX_BYTES"] = int(os.getenv("HQ_TEXT_TARGET_MAX_BYTES", "350"))
    config["HQ_TEXT_HARD_MAX_BYTES"] = int(os.getenv("HQ_TEXT_HARD_MAX_BYTES", "700"))
    config["HQ_MAX_SPLIT_DEPTH"] = int(os.getenv("HQ_MAX_SPLIT_DEPTH", "8"))
    config["HQ_MAX_TTS_CALLS"] = int(os.getenv("HQ_MAX_TTS_CALLS", "128"))
    config["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
    config["OPENROUTER_MODEL"] = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    config["OPENROUTER_BASE_URL"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    config["TRANSLATION_TIMEOUT_SECONDS"] = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "20"))
    config["MAX_TRANSLATION_INPUT_CHARS"] = int(os.getenv("MAX_TRANSLATION_INPUT_CHARS", "12000"))
    config["DICTIONARY_ENABLED"] = _env_bool("DICTIONARY_ENABLED", True)
    config["DICTIONARY_CC_CEDICT_PATH"] = os.getenv(
        "DICTIONARY_CC_CEDICT_PATH", "data/dictionaries/cc-cedict.u8"
    )
    config["DICTIONARY_CC_CANTO_PATH"] = os.getenv(
        "DICTIONARY_CC_CANTO_PATH", "data/dictionaries/cc-canto.u8"
    )
    config["MAX_DICTIONARY_INPUT_CHARS"] = int(os.getenv("MAX_DICTIONARY_INPUT_CHARS", "12000"))
    config["MAX_DICTIONARY_ALTERNATIVES"] = int(os.getenv("MAX_DICTIONARY_ALTERNATIVES", "3"))
    config["MAX_DICTIONARY_TERM_CHARS"] = int(os.getenv("MAX_DICTIONARY_TERM_CHARS", "64"))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

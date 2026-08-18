# Environment Variables

This is the runtime environment variable reference for Canto Reader.

## Core Runtime
- `FLASK_ENV`
  - `development` or `production`.
- `PORT`
  - Listen port for the desktop app and home server (default `8734`).
- `SECRET_KEY`
  - No longer security-critical (no sessions/flash). A default is used when unset.

## Google TTS Credentials
Use one method:

1. File-based credentials:
- `GOOGLE_APPLICATION_CREDENTIALS`
  - Path to a service-account key file, e.g. `secrets/gcp-sa.json`.

2. Inline JSON credentials:
- `GCP_SERVICE_ACCOUNT_JSON`
  - Single-line JSON string.
  - `private_key` must contain escaped newlines (`\\n`).

## TTS Guardrails
- `MAX_INPUT_CHARS` (default `12000`)
- `TEMP_AUDIO_DIR` (default `static/temp_audio`)
- `TTS_TIMEOUT_SECONDS` (default `20`)
- `TEMP_AUDIO_TTL_HOURS` (default `4`)
- `MAX_TEMP_AUDIO_FILES` (default `120`)
- `MAX_TEMP_AUDIO_BYTES` (default `314572800`)

### High Quality TTS Safety Controls
- `HQ_TEXT_TARGET_MAX_BYTES` (default `350`)
- `HQ_TEXT_HARD_MAX_BYTES` (default `700`)
- `HQ_MAX_SPLIT_DEPTH` (default `8`)
- `HQ_MAX_TTS_CALLS` (default `128`)

These prevent provider sentence-length failures from causing unbounded retry fan-out.

## Translation (OpenRouter)
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (default `openrouter/free`; change to any OpenRouter slug, e.g. a `:free` Llama/Mistral/Qwen variant or a Grok slug)
- `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`)
- `TRANSLATION_TIMEOUT_SECONDS` (default `20`)
- `MAX_TRANSLATION_INPUT_CHARS` (default `12000`)

## Dictionary Mode (Local, No-AI)
- `DICTIONARY_ENABLED` (default `true`)
- `DICTIONARY_CC_CEDICT_PATH` (default `data/dictionaries/cc-cedict.u8`)
- `DICTIONARY_CC_CANTO_PATH` (default `data/dictionaries/cc-canto.u8`)
- `MAX_DICTIONARY_INPUT_CHARS` (default `12000`)
- `MAX_DICTIONARY_ALTERNATIVES` (default `3`)
- `MAX_DICTIONARY_TERM_CHARS` (default `64`)

## Laptop Baseline
```env
FLASK_ENV=development
PORT=8734
GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-sa.json
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## Home Server Baseline
```env
FLASK_ENV=production
PORT=8734
GOOGLE_APPLICATION_CREDENTIALS=/opt/canto-reader/secrets/gcp-sa.json
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DICTIONARY_ENABLED=true
DICTIONARY_CC_CEDICT_PATH=data/dictionaries/cc-cedict.u8
DICTIONARY_CC_CANTO_PATH=data/dictionaries/cc-canto.u8
```

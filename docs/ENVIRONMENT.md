# Environment Variables

This is the runtime environment variable reference for Speak-in-Canto.

## Core Runtime
- `SECRET_KEY`
  - Required outside development.
  - Use a long random value in production.
- `FLASK_ENV`
  - `development` or `production`.
- `DATABASE_PATH`
  - SQLite file path.
  - Coolify recommended: `/app/instance/speak_in_canto.db`.

## Auth & Session
- `SESSION_LIFETIME_HOURS` (default `12`)
- `REMEMBER_COOKIE_DAYS` (default `30`)
- `SESSION_REFRESH_EACH_REQUEST` (default `true`)
- `COOKIE_SECURE` (default `true` in production, `false` in development)
- `COOKIE_SAMESITE` (default `Lax`)

## Gunicorn (Container Runtime)
- `PORT`
  - Container listen port (default `8000` via `Dockerfile` command).
- `GUNICORN_WORKERS`
  - Recommended low-memory default: `1`.
- `GUNICORN_THREADS`
  - Recommended low-memory default: `2`.

## Google TTS Credentials
Use one method:

1. File-based credentials:
- `GOOGLE_APPLICATION_CREDENTIALS`
  - Example: `/app/secrets/gcp-sa.json`

2. Inline JSON credentials:
- `GCP_SERVICE_ACCOUNT_JSON`
  - Single-line JSON string.
  - `private_key` must contain escaped newlines (`\\n`).

## TTS Guardrails
- `MAX_INPUT_CHARS` (default `12000`)
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

## Translation (Grok)
- `GROK_API_KEY`
- `GROK_MODEL` (default `grok-4-1-fast-non-reasoning`)
- `GROK_BASE_URL` (default `https://api.x.ai/v1`)
- `TRANSLATION_TIMEOUT_SECONDS` (default `20`)
- `MAX_TRANSLATION_INPUT_CHARS` (default `12000`)

## Dictionary Mode (Local, No-AI)
- `DICTIONARY_ENABLED` (default `true`)
- `DICTIONARY_CC_CEDICT_PATH` (default `data/dictionaries/cc-cedict.u8`)
- `DICTIONARY_CC_CANTO_PATH` (default `data/dictionaries/cc-canto.u8`)
- `MAX_DICTIONARY_INPUT_CHARS` (default `12000`)
- `MAX_DICTIONARY_ALTERNATIVES` (default `3`)
- `MAX_DICTIONARY_TERM_CHARS` (default `64`)

## Usage / Quota
- `MONTHLY_QUOTA_CHARS` (default `1000000`)

## Recommended Production Baseline
```env
FLASK_ENV=production
DATABASE_PATH=/app/instance/speak_in_canto.db
SESSION_LIFETIME_HOURS=12
REMEMBER_COOKIE_DAYS=30
SESSION_REFRESH_EACH_REQUEST=true
COOKIE_SECURE=true
COOKIE_SAMESITE=Lax
GUNICORN_WORKERS=1
GUNICORN_THREADS=2
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-sa.json
GROK_MODEL=grok-4-1-fast-non-reasoning
GROK_BASE_URL=https://api.x.ai/v1
MAX_INPUT_CHARS=12000
MAX_TRANSLATION_INPUT_CHARS=12000
DICTIONARY_ENABLED=true
DICTIONARY_CC_CEDICT_PATH=data/dictionaries/cc-cedict.u8
DICTIONARY_CC_CANTO_PATH=data/dictionaries/cc-canto.u8
MAX_DICTIONARY_INPUT_CHARS=12000
MAX_DICTIONARY_ALTERNATIVES=3
MAX_DICTIONARY_TERM_CHARS=64
TTS_TIMEOUT_SECONDS=20
TRANSLATION_TIMEOUT_SECONDS=20
TEMP_AUDIO_TTL_HOURS=4
MAX_TEMP_AUDIO_FILES=120
MAX_TEMP_AUDIO_BYTES=314572800
HQ_TEXT_TARGET_MAX_BYTES=350
HQ_TEXT_HARD_MAX_BYTES=700
HQ_MAX_SPLIT_DEPTH=8
HQ_MAX_TTS_CALLS=128
MONTHLY_QUOTA_CHARS=1000000
```

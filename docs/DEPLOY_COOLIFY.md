# Deploying to Coolify

## Runtime
- Build source: this repository (`Dockerfile` at repo root)
- Service type: Web app
- Port: `8000` (container)
- Health check path: `/healthz`
- Process manager: Gunicorn (`app:app`)

## Required Environment Variables
- `SECRET_KEY` (required; long random string)
- `FLASK_ENV=production`
- `DATABASE_PATH=/app/instance/speak_in_canto.db`
- `GUNICORN_WORKERS=1` (recommended for low-memory VPS)
- `GUNICORN_THREADS=2` (recommended for low-memory VPS)
- `SESSION_LIFETIME_HOURS=12`
- `REMEMBER_COOKIE_DAYS=30`
- `SESSION_REFRESH_EACH_REQUEST=true`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=Lax`

### Google TTS Credentials
Use one of these methods:

1. File path (if mounting a secret file):
- `GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-sa.json`

2. Inline JSON in env:
- `GCP_SERVICE_ACCOUNT_JSON={...single-line-json...}`
- Keep `private_key` newline escapes as `\\n`.

### Grok Translation
- `GROK_API_KEY=...`
- `GROK_MODEL=grok-4-1-fast-non-reasoning`
- `GROK_BASE_URL=https://api.x.ai/v1`
- `TRANSLATION_TIMEOUT_SECONDS=20`
- `MAX_TRANSLATION_INPUT_CHARS=12000`

### Existing App Limits (recommended defaults)
- `MAX_INPUT_CHARS=12000`
- `TEMP_AUDIO_TTL_HOURS=4`
- `MAX_TEMP_AUDIO_FILES=120`
- `MAX_TEMP_AUDIO_BYTES=314572800`
- `TTS_TIMEOUT_SECONDS=20`
- `HQ_TEXT_TARGET_MAX_BYTES=350`
- `HQ_TEXT_HARD_MAX_BYTES=700`
- `HQ_MAX_SPLIT_DEPTH=8`
- `HQ_MAX_TTS_CALLS=128`
- `MONTHLY_QUOTA_CHARS=1000000`

### Dictionary Mode (optional but required for dictionary feature)
- `DICTIONARY_ENABLED=true`
- `DICTIONARY_CC_CEDICT_PATH=/app/dictionaries/cc-cedict.u8`
- `DICTIONARY_CC_CANTO_PATH=/app/dictionaries/cc-canto.u8`
- `MAX_DICTIONARY_INPUT_CHARS=12000`
- `MAX_DICTIONARY_ALTERNATIVES=3`
- `MAX_DICTIONARY_TERM_CHARS=64`

## Persistent Storage
Create persistent volumes and mount to:
- `/app/instance`
- `/app/secrets` (when using file-based Google credentials)
- `/app/dictionaries` (if dictionary source files are mounted instead of committed)

This preserves SQLite data across redeploys.

## First Deploy Checklist
1. Add all required env vars in Coolify.
2. Configure volume mount for `/app/instance`.
3. If using file-based Google creds, mount `/app/secrets` and set `GOOGLE_APPLICATION_CREDENTIALS`.
4. Deploy.
5. Verify app health endpoint: `/healthz` returns `{"status":"ok"}`.
6. Create first admin user:
   - Open terminal for the running container and run:
   - `flask create-admin --username <admin> --password '<strong-password>'`

## Notes
- Audio files are temporary and written to `/app/static/temp_audio`, then cleaned up by TTL/cap logic.
- If translation fails with `403/1010`, verify `GROK_API_KEY` in Coolify and redeploy so env changes are applied.
- High Quality TTS may fail on provider sentence-length limits if text is effectively one long sentence. Keep HQ guardrail defaults (`HQ_TEXT_TARGET_MAX_BYTES`, `HQ_TEXT_HARD_MAX_BYTES`, `HQ_MAX_SPLIT_DEPTH`, `HQ_MAX_TTS_CALLS`) unless you have measured reasons to tune them.

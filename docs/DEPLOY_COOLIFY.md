# Deploying to Coolify

## Runtime
- Build source: this repository (`Dockerfile` at repo root)
- Service type: Web app
- Port: `8000` (container)
- Health check path: `/healthz`

## Required Environment Variables
- `SECRET_KEY` (required; long random string)
- `FLASK_ENV=production`
- `DATABASE_PATH=/app/instance/speak_in_canto.db`

### Google TTS Credentials
Use one of these methods:

1. File path (if mounting a secret file):
- `GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-sa.json`

2. Inline JSON in env (recommended in Coolify):
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
- `MONTHLY_QUOTA_CHARS=1000000`

## Persistent Storage
Create a persistent volume and mount to:
- `/app/instance`

This preserves SQLite data across redeploys.

## First Deploy Checklist
1. Add all required env vars in Coolify.
2. Configure volume mount for `/app/instance`.
3. Deploy.
4. Verify app health endpoint: `/healthz` returns `{"status":"ok"}`.
5. Create first admin user:
   - Open terminal for the running container and run:
   - `flask create-admin --username <admin> --password '<strong-password>'`

## Notes
- Audio files are temporary and written to `/app/static/temp_audio`, then cleaned up by TTL/cap logic.
- If translation fails with `403/1010`, verify `GROK_API_KEY` in Coolify and redeploy so env changes are applied.

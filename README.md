# Speak-in-Canto

Cantonese reading app with:
- Google Cloud Text-to-Speech playback
- Character-level sync highlighting in Standard voice mode
- High Quality voice mode (no sync)
- English translation via Grok
- Auth + admin usage dashboard

## Features
- Login-protected reader
- Standard yue-HK voices with synchronized token highlighting
- High Quality Chirp3-HD yue-HK voices
- Per-user voice pinning
- Admin user management
- Monthly usage tracking
- Temp audio cleanup with TTL + file/size caps

## Tech Stack
- Python 3.12
- Flask + Flask-Login + Flask-SQLAlchemy
- SQLite
- Google Cloud Text-to-Speech
- Grok API
- Gunicorn (container runtime)

## Local Development
1. Create venv and install deps:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill secrets.

3. Run app:
```bash
.venv/bin/flask run
```

4. Create first admin:
```bash
.venv/bin/flask create-admin --username <admin> --password '<strong-password>'
```

## Deployment (Coolify)
Use the full deployment guide:
- `docs/DEPLOY_COOLIFY.md`

Quick essentials:
- Build from repo `Dockerfile`
- Expose container port `8000`
- Healthcheck: `/healthz`
- Persistent storage:
  - `/app/instance` (SQLite)
  - `/app/secrets` (if using mounted Google credential file)
- Set required env vars from:
  - `.env.example`
  - `docs/ENVIRONMENT.md`

## Environment Variables
Canonical variable reference:
- `docs/ENVIRONMENT.md`

Template for local env:
- `.env.example`

## Important Operational Notes
- High Quality voice mode uses provider text synthesis without SSML marks, so sync highlighting is intentionally disabled.
- Google HQ TTS can reject long sentences. The backend now proactively chunks HQ text and has bounded recursive split retries using:
  - `HQ_TEXT_TARGET_MAX_BYTES`
  - `HQ_TEXT_HARD_MAX_BYTES`
  - `HQ_MAX_SPLIT_DEPTH`
  - `HQ_MAX_TTS_CALLS`
- Keep these defaults unless you have measured evidence to change them.

## Testing
Run full suite:
```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

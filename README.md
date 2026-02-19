# Canto Reader

Cantonese reading app with:
- Google Cloud Text-to-Speech playback
- Character-level sync highlighting in Standard voice mode
- High Quality voice mode (no sync)
- English translation via Grok
- Local dictionary lookup mode (phrase-first, no AI)
- Dictionary popup + click-to-speak with cached term audio
- Auth + admin usage dashboard
- 30-day Remember Me login option

## Features
- Login-protected reader
- Standard yue-HK voices with synchronized token highlighting
- High Quality Chirp3-HD yue-HK voices
- Per-user voice pinning
- Admin user management
- Monthly usage tracking
- Temp audio cleanup with TTL + file/size caps
- Local dictionary data support via CC-CEDICT + CC-Canto source files
- Dictionary term audio cache in `static/temp_audio/` (same cleanup guardrails)

## Tech Stack
- Python 3.12
- Flask + Flask-Login + Flask-SQLAlchemy
- SQLite
- Google Cloud Text-to-Speech
- Grok API
- Gunicorn (container runtime)

## Frontend Structure
- `static/js/reader.js` (module orchestrator)
- `static/js/reader/sync.js` (token timing + highlight sync)
- `static/js/reader/voice.js` (voice mode/dropdown/pins)
- `static/js/reader/dictionary.js` (lookup popover + term speak)
- `static/js/reader/translation.js` (translation request/state)

Reader frontend now uses ES modules (`<script type="module">` in `templates/reader.html`).

## Local Development
1. Create venv and install deps:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill secrets.

3. Run app:
```bash
set -a; source .env; set +a; .venv/bin/flask run
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
  - `/app/dictionaries` (if using dictionary mode with mounted source files)
- Set required env vars from:
  - `.env.example`
  - `docs/ENVIRONMENT.md`

## Environment Variables
Canonical variable reference:
- `docs/ENVIRONMENT.md`

Template for local env:
- `.env.example`

## Dictionary Mode Setup
Dictionary mode now has backend + UI integration and expects local source files:
- `data/dictionaries/cc-cedict.u8`
- `data/dictionaries/cc-canto.u8`

If files are missing, dictionary lookup returns `503` with a clear error while the rest of the app continues to work.
Path overrides are available via:
- `DICTIONARY_CC_CEDICT_PATH`
- `DICTIONARY_CC_CANTO_PATH`

Setup guide:
- `docs/DICTIONARY_SETUP.md`

## Auth Behavior
- Login form supports `Remember me for 30 days`.
- Without remember-me, normal session expiration is controlled by:
  - `SESSION_LIFETIME_HOURS`
  - `SESSION_REFRESH_EACH_REQUEST`
- Cookie policy is controlled by:
  - `COOKIE_SECURE`
  - `COOKIE_SAMESITE`

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

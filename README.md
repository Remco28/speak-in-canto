# Canto Reader

A personal Cantonese reading app:
- Google Cloud Text-to-Speech playback
- Character-level sync highlighting in Standard voice mode
- High Quality voice mode (no sync)
- English translation via OpenRouter
- Local dictionary lookup mode (phrase-first, no AI)
- Dictionary popup + click-to-speak with cached term audio

It runs as a lightweight desktop app on an Ubuntu/Debian laptop and can also
run from source on a headless home server over the LAN. There is no Docker, no
authentication, and no cloud hosting.

## Features
- Standard yue-HK voices with synchronized token highlighting
- High Quality Chirp3-HD yue-HK voices
- Voice pinning stored in browser `localStorage`
- Temp audio cleanup with TTL + file/size caps
- Local dictionary data support via CC-CEDICT + CC-Canto source files
- Dictionary term audio cache in `static/temp_audio/` (same cleanup guardrails)

## Tech Stack
- Python 3.12+
- Flask + waitress (pure-Python WSGI server)
- pywebview (desktop window, GTK + WebKit2GTK on Linux)
- Google Cloud Text-to-Speech
- OpenRouter (OpenAI-compatible translation API)
- pycantonese (local Jyutping romanization)

## Frontend Structure
- `static/js/reader.js` (module orchestrator)
- `static/js/reader/sync.js` (token timing + highlight sync)
- `static/js/reader/voice.js` (voice mode/dropdown/pins)
- `static/js/reader/dictionary.js` (lookup popover + term speak)
- `static/js/reader/translation.js` (translation request/state)

Reader frontend uses ES modules (`<script type="module">` in `templates/reader.html`).

## Laptop Desktop App
Run the one-time installer:

```bash
./scripts/install_laptop.sh
```

It will:
1. Ensure Python 3.12+ is available.
2. Install GTK/WebKit2GTK system dependencies.
3. Create `.venv` and install dependencies.
4. Create `.env` from `.env.example` if missing.
5. Write a `.desktop` launcher ("Canto Reader") to your app menu.

Then fill in `.env` with your OpenRouter key and Google TTS credentials, and
launch **Canto Reader** from the app menu. Closing the window stops the server
and exits the process.

Full runbook: `docs/DEPLOY_LAPTOP.md`.

## Home Server (LAN-only)
Run from source behind waitress + systemd, reachable at
`http://<server-lan-ip>:8734`. Full runbook: `docs/DEPLOY_HOME_SERVER.md`.

> The app has no authentication, so keep it on the LAN only — do not forward
> the port from your router.

## Manual Local Development
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

Or use waitress directly:
```bash
.venv/bin/python -m waitress --host=127.0.0.1 --port=8734 --threads=4 app:app
```

## Environment Variables
Canonical variable reference:
- `docs/ENVIRONMENT.md`

Template for local env:
- `.env.example`

## Dictionary Mode Setup
Dictionary mode expects local source files:
- `data/dictionaries/cc-cedict.u8`
- `data/dictionaries/cc-canto.u8`

If files are missing, dictionary lookup returns `503` with a clear error while
the rest of the app continues to work. Path overrides are available via:
- `DICTIONARY_CC_CEDICT_PATH`
- `DICTIONARY_CC_CANTO_PATH`

Setup guide:
- `docs/DICTIONARY_SETUP.md`

## Important Operational Notes
- High Quality voice mode uses provider text synthesis without SSML marks, so
  sync highlighting is intentionally disabled.
- Google HQ TTS can reject long sentences. The backend proactively chunks HQ
  text and has bounded recursive split retries using:
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

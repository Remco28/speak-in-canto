# System Architecture: Canto Reader

## 1. Overview
A personal Cantonese TTS reader with Google Cloud TTS playback, character-level
sync (Standard voices), local dictionary lookup, and optional English
translation via OpenRouter. It runs as a desktop app on a laptop and can also
run from source on a headless home server. There is no authentication, no
database, and no cloud hosting.

## 2. Tech Stack
- **Language:** Python 3.12+
- **Framework:** Flask (Web)
- **WSGI Server:** waitress (pure-Python, threaded)
- **Desktop Window:** pywebview (GTK + WebKit2GTK on Linux)
- **Frontend:** Vanilla JS + CSS (responsive)
- **TTS Engine:** Google Cloud Text-to-Speech
  - Standard yue-HK voices with SSML marks + sync
  - Chirp3-HD yue-HK voices in high-quality mode (no SSML mark sync)
- **Translation Engine:** OpenRouter (OpenAI-compatible `/chat/completions`)
- **Dictionary Engine:** Local dictionary ingestion + phrase-first lookup (CC-CEDICT + CC-Canto)

## 3. Data Storage
- No database. The SQLite / Flask-SQLAlchemy stack was removed.
- Voice pins are stored in browser `localStorage` (per-browser).
- Temporary audio files are stored in `static/temp_audio/` and cleaned up by
  TTL + file-count + byte-cap policies.

## 4. TTS Implementation (SSML + Timepoints)
- **Payload Constraint:** Requests must be < 5,000 bytes (UTF-8, including SSML tags).
- **Mark Strategy:** Default to per-character marks for non-whitespace tokens.
- **Reliability Fallback:** If timepoints are sparse/missing, retry once with
  reduced mark density and return a `sync_mode` flag (`full` or `reduced`).
- **Voice Modes:**
    - **Standard:** synchronized highlighting supported.
    - **High Quality (Chirp3-HD):** no timestamp sync support from provider; highlighting disabled by design.
- **Response:** Backend returns JSON with `audio_url`, token/timepoint metadata,
  `sync_mode`, and `sync_supported`.
- **Jyutping Engine:** `pycantonese` library used on the backend to generate romanization per character.
- **Frontend:**
    - **Highlighting:** Wrap text in `<span>` tags with matching IDs. Display Jyutping as "ruby" text above the characters.
    - **Sync Player:** Sync `audio.currentTime` with timepoint data to highlight current character.
    - **Click-to-Seek:** Jump to the timestamp associated with a character span.
    - **Playback Speed:** Client-side `playbackRate` adjustment (0.5x to 2.0x) to ensure zero additional API costs.

## 5. Dictionary Implementation (No-AI)
- **Sources:** CC-CEDICT + CC-Canto local files.
- **Core Services:**
  - `services/dictionary_loader.py` parses dictionary entries into in-memory indexes.
  - `services/dictionary_lookup.py` performs phrase-first, longest-match lookup at a clicked token index.
- **API:**
  - `POST /api/dictionary/lookup`
    - Input: full rendered text + click index.
    - Output: `best` candidate + ranked `alternatives`.
  - `POST /api/dictionary/speak`
    - Input: matched term + voice settings.
    - Output: short audio URL for immediate playback.
- **UI Behavior:**
  - Reader has `Read` and `Dictionary` modes.
  - Dictionary mode click opens a floating popover near clicked text.
  - Popover shows best gloss + optional alternatives.
  - Matched span is highlighted in Reader.
  - Click auto-speaks the matched term.
- **Term Audio Cache:**
  - Persistent hash key cache by `(voice_mode, voice_name, text)`.
  - Stored in `static/temp_audio/` using existing TTL/size/file cleanup guardrails.

## 6. Auth & Voice Pins
- Authentication was removed entirely; the app is a single-user personal tool.
- Voice pinning moved from server-side per-user rows to browser `localStorage`
  (`canto-reader.voice-pins`). Pins are per-browser and survive page reloads but
  are not synced between devices.

## 7. File Management & Storage
- **Directory:** `static/temp_audio/`
- **Retention:** Files are stored as either unique synthesized output files or deterministic hash cache files.
- **Cleanup:** Request-time cleanup enforces TTL + max file count + max bytes.

## 8. Deployment
- **Laptop:** `run_app.py` starts waitress in a background thread on
  `127.0.0.1:8734`, then opens a pywebview window. Closing the window stops the
  server and exits. Installed via `scripts/install_laptop.sh` + a `.desktop`
  launcher. See `docs/DEPLOY_LAPTOP.md`.
- **Home server:** venv + waitress + systemd unit binding `0.0.0.0:8734` for LAN
  access. See `docs/DEPLOY_HOME_SERVER.md`.
- **Google Credentials:** Either mounted key file path via
  `GOOGLE_APPLICATION_CREDENTIALS`, or inline JSON via `GCP_SERVICE_ACCOUNT_JSON`.
- **Translation:** OpenRouter API key stored in environment (`OPENROUTER_API_KEY`).

## 9. Translation Integration
- **Route:** `POST /api/translate`.
- **Purpose:** Translate reader input text to English for comprehension support.
- **Flow:** Reader UI -> Flask translate route -> OpenRouter -> JSON translation response -> render below reader.
- **Guardrails:** Input length cap + upstream timeout + controlled error responses.
- **Default model:** `openrouter/free` (a router over free models); configurable
  via `OPENROUTER_MODEL`, including Grok models via OpenRouter slugs.

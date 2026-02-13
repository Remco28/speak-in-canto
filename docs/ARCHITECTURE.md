# System Architecture: Speak-in-Canto

## 1. Overview
A lightweight Cantonese TTS reader with authentication, Google Cloud TTS playback, character-level sync (Standard voices), and optional English translation via Grok.

## 2. Tech Stack
- **Language:** Python 3.x
- **Framework:** Flask (Web), Flask-Login (Auth), Flask-SQLAlchemy (ORM)
- **Database:** SQLite (Stored in a persistent volume)
- **Frontend:** Vanilla JS + CSS (responsive)
- **TTS Engine:** Google Cloud Text-to-Speech
  - Standard yue-HK voices with SSML marks + sync
  - Chirp3-HD yue-HK voices in high-quality mode (no SSML mark sync)
- **Translation Engine:** Grok API (English translation for reader text)

## 3. Data Model (SQLite)
- `User`: id, username, password_hash, is_admin (bool).
- `UsageLog`: id, user_id, char_count, voice_name, timestamp.
- `UserVoicePin`: id, user_id, voice_id, voice_mode, created_at (per-user pinned voices in UI).

## 4. TTS Implementation (SSML + Timepoints)
- **Payload Constraint:** Requests must be < 5,000 bytes (UTF-8, including SSML tags).
- **Mark Strategy:** Default to per-character marks for non-whitespace tokens.
- **Reliability Fallback:** If timepoints are sparse/missing, retry once with reduced mark density and return a `sync_mode` flag (`full` or `reduced`).
- **Voice Modes:**
    - **Standard:** synchronized highlighting supported.
    - **High Quality (Chirp3-HD):** no timestamp sync support from provider; highlighting disabled by design.
- **Response:** Backend returns JSON with `audio_url`, token/timepoint metadata, `sync_mode`, and `sync_supported`.
- **Jyutping Engine:** `pycantonese` library used on the backend to generate romanization per character.
- **Frontend:**
    - **Highlighting:** Wrap text in `<span>` tags with matching IDs. Display Jyutping as "ruby" text above the characters.
    - **Sync Player:** Sync `audio.currentTime` with timepoint data to highlight current character.
    - **Click-to-Seek:** Jump to the timestamp associated with a character span.
    - **Playback Speed:** Client-side `playbackRate` adjustment (0.5x to 2.0x) to ensure zero additional API costs.

## 5. File Management & Storage
- **Directory:** `static/temp_audio/`
- **Retention:** Files are stored with a timestamped name.
- **Cleanup:** A background task or scheduled function deletes files older than 4 hours.

## 6. Deployment (Coolify/VPS)
- **Google Credentials:** Either mounted key file path via `GOOGLE_APPLICATION_CREDENTIALS`, or inline JSON via `GCP_SERVICE_ACCOUNT_JSON`.
- **Additional Secrets:** Grok API key stored in environment (`GROK_API_KEY`).
- **Persistence:** SQLite database file must be mapped to a persistent volume.
- **HTTPS:** Managed by Coolify via Let's Encrypt.
- **Runtime:** Gunicorn in container (`Dockerfile`), with low-memory defaults configurable via env.

## 7. Translation Integration
- **Route:** `POST /api/translate` (auth required).
- **Purpose:** Translate reader input text to English for comprehension support.
- **Flow:** Reader UI -> Flask translate route -> Grok API -> JSON translation response -> render below reader.
- **Guardrails:** Input length cap + upstream timeout + controlled error responses.

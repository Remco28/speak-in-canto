# System Architecture: Speak-in-Canto

## 1. Overview
A lightweight Cantonese TTS reader designed for family use. Key features include user authentication, Google Cloud TTS integration, and character-level playback highlighting.

## 2. Tech Stack
- **Language:** Python 3.x
- **Framework:** Flask (Web), Flask-Login (Auth), Flask-SQLAlchemy (ORM)
- **Database:** SQLite (Stored in a persistent volume)
- **Frontend:** Vanilla JS / jQuery + Bootstrap 5 (Responsive)
- **TTS Engine:** Google Cloud Text-to-Speech (Neural2-yue-HK)
- **Translation Engine:** Grok API (English translation for reader text)

## 3. Data Model (SQLite)
- `User`: id, username, password_hash, is_admin (bool).
- `UsageLog`: id, user_id, char_count, timestamp (To track 1M free tier limit).

## 4. TTS Implementation (SSML + Timepoints)
- **Payload Constraint:** Requests must be < 5,000 bytes (UTF-8, including SSML tags).
- **Mark Strategy:** Default to per-character marks for non-whitespace tokens.
- **Reliability Fallback:** If timepoints are sparse/missing, retry once with reduced mark density and return a `sync_mode` flag (`full` or `reduced`).
- **Response:** Backend returns JSON with `audio_url`, `timepoints`, and `jyutping` data.
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
- **Secrets:** Google Service Account JSON stored as an environment variable (`GOOGLE_APPLICATION_CREDENTIALS_JSON`).
- **Additional Secrets:** Grok API key stored in environment (`GROK_API_KEY`).
- **Persistence:** SQLite database file must be mapped to a persistent volume.
- **HTTPS:** Managed by Coolify via Let's Encrypt.

## 7. Translation Integration
- **Route:** `POST /api/translate` (auth required).
- **Purpose:** Translate reader input text to English for comprehension support.
- **Flow:** Reader UI -> Flask translate route -> Grok API -> JSON translation response -> render below reader.
- **Guardrails:** Input length cap + upstream timeout + controlled error responses.

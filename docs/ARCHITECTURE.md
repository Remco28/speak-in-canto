# System Architecture: Canto Reader

## 1. Overview
A lightweight Cantonese TTS reader with authentication, Google Cloud TTS playback, character-level sync (Standard voices), local dictionary lookup, and optional English translation via Grok.

## 2. Tech Stack
- **Language:** Python 3.x
- **Framework:** Flask (Web), Flask-Login (Auth), Flask-SQLAlchemy (ORM)
- **Database:** SQLite (Stored in a persistent volume)
- **Frontend:** Vanilla JS + CSS (responsive)
- **TTS Engine:** Google Cloud Text-to-Speech
  - Standard yue-HK voices with SSML marks + sync
  - Chirp3-HD yue-HK voices in high-quality mode (no SSML mark sync)
- **Translation Engine:** Grok API (English translation for reader text)
- **Dictionary Engine:** Local dictionary ingestion + phrase-first lookup (CC-CEDICT + CC-Canto)

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

## 6. Auth & Session Strategy
- Login supports `Remember me for 30 days`.
- Session policy is env-driven:
  - `SESSION_LIFETIME_HOURS`
  - `REMEMBER_COOKIE_DAYS`
  - `SESSION_REFRESH_EACH_REQUEST`
  - `COOKIE_SECURE`
  - `COOKIE_SAMESITE`
- Redirect handling for `next` is restricted to local paths.

## 7. File Management & Storage
- **Directory:** `static/temp_audio/`
- **Retention:** Files are stored as either unique synthesized output files or deterministic hash cache files.
- **Cleanup:** Request-time cleanup enforces TTL + max file count + max bytes.

## 8. Deployment (Coolify/VPS)
- **Google Credentials:** Either mounted key file path via `GOOGLE_APPLICATION_CREDENTIALS`, or inline JSON via `GCP_SERVICE_ACCOUNT_JSON`.
- **Additional Secrets:** Grok API key stored in environment (`GROK_API_KEY`).
- **Persistence:** SQLite database file must be mapped to a persistent volume.
- **HTTPS:** Managed by Coolify via Let's Encrypt.
- **Runtime:** Gunicorn in container (`Dockerfile`), with low-memory defaults configurable via env.

## 9. Translation Integration
- **Route:** `POST /api/translate` (auth required).
- **Purpose:** Translate reader input text to English for comprehension support.
- **Flow:** Reader UI -> Flask translate route -> Grok API -> JSON translation response -> render below reader.
- **Guardrails:** Input length cap + upstream timeout + controlled error responses.

## 10. Refactor Kickoff (2026-02-18)
- **Status:** Active.
- **Branch:** `refactor/codebase-streamline-2026-02-18`
- **Goal:** Reduce bloat and improve maintainability without changing user-visible behavior.
- **Method:** Small, low-risk cleanup steps with verification after each step.
- **Initial sequence:**
  1. Inventory modules/files and identify dead or duplicate code.
  2. Trace core runtime paths (auth, TTS, dictionary, translation).
  3. Consolidate repeated backend logic (validation/error/config patterns).
  4. Simplify frontend state/event handling where safe.
  5. Remove stale docs/files and align tests/docs with final structure.
- **Non-goals (this phase):**
  - No product feature changes.
  - No UI redesign work.
  - No infra/provider changes unless required for correctness.

## 11. Refactor Findings (Inventory + Runtime Review)
- **Priority A (Safe cleanup first):**
  - Remove dead frontend hooks for inline play/pause controls no longer present in template.
  - Remove unused templates that are not rendered by any active route.
  - Remove empty legacy archive directories and stale references where applicable.
- **Priority B (Shared backend logic):**
  - Consolidate monthly usage aggregation logic shared across admin page and admin API.
  - Reduce repetitive config lookups by centralizing typed config access helpers.
  - Normalize repeated JSON payload validation patterns across route modules.
- **Priority C (Maintainability improvements):**
  - Split `static/js/reader.js` into smaller modules by responsibility (voice UI, player/sync, dictionary, translation).
  - Normalize test naming from task-era names to feature-oriented names.
  - Archive or modernize stale historical planning docs that no longer reflect current structure.

## 12. Refactor Execution Plan
1. **Phase 1: Dead-code and stale-file cleanup**
   - Target: no behavior changes, no API contract changes.
   - Validation: app boots; core pages render; targeted test run.
2. **Phase 2: Shared backend helper extraction**
   - Target: remove duplicated logic without changing responses.
   - Validation: admin/dashboard and admin usage API parity.
3. **Phase 3: Config/access cleanup**
   - Target: improve readability and reduce config drift risk.
   - Validation: full test run + manual smoke.
4. **Phase 4: Frontend module split**
   - Target: smaller maintainable JS units with same runtime behavior.
   - Validation: reader, dictionary, translation, and playback smoke checks.
5. **Phase 5: Test/doc alignment**
   - Target: naming cleanup + retired docs archive strategy.
   - Validation: full suite passing and docs cross-check.

## 13. Refactor Progress (Current Branch)
- **Completed:**
  - Phase 1 dead/stale cleanup (unused templates, dead JS hooks).
  - Phase 2 shared backend helper extraction (`usage_metrics`, `audio_policy`).
  - Phase 3 config/access cleanup (`runtime_config` + reduced app factory duplication).
  - Phase 4 frontend modularization of reader runtime:
    - `static/js/reader/sync.js`
    - `static/js/reader/voice.js`
    - `static/js/reader/dictionary.js`
    - `static/js/reader/translation.js`
    - thin orchestrator in `static/js/reader.js`
  - Phase 5 test naming normalization from task-era files to feature-oriented files.
- **Verification status:**
  - Full unit test suite passing after each major refactor step.

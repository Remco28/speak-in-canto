# Spec: Canto Reader — Laptop Desktop App + Home Server (Local Deployment)

Status: Draft (interview complete, no code changes made yet)

## 1. Context & Goals

Canto Reader is a personal Cantonese reading app (Flask, Google Cloud TTS, local dictionary, optional AI translation). It is currently deployed as a Docker container managed by Coolify on a VPS.

The user wants to:
1. **Run the app on their Linux (Ubuntu/Debian) laptop** as a lightweight desktop app — launcher icon, double-click to start, close the window to quit. No Docker ("too heavy").
2. **Eventually run the app on a home Ubuntu server** (headless, 8+ GB RAM, yet to be fully configured) reachable over the LAN, running from source with the simplest setup.
3. **Abandon the VPS / Coolify deployment entirely** — the home server replaces it; nothing is hosted remotely anymore.
4. **Remove authentication** — it's a personal tool, no other users. (Feature can be re-added later if ever needed.)
5. **Switch translation from the Grok API to OpenRouter** — still may use Grok models, but accessed via OpenRouter. Default should be a **free** OpenRouter model.

Non-goals:
- No Docker anywhere (laptop or home server).
- No public internet exposure (LAN only).
- No packaging as a `.deb`/AppImage/Flatpak (a setup script + `.desktop` launcher is enough).
- No production migration path from the VPS (fresh start everywhere).

## 2. Environment

### Laptop (primary target)
- **OS:** Ubuntu/Debian family (exact version TBD — affects WebKit2GTK package names, see §6.3).
- **Python:** 3.12+ required. User is unsure if installed — setup must check `python3 --version` and, if missing, install via `apt` (Ubuntu 24.04 ships 3.12; 22.04 needs deadsnakes PPA or pyenv).
- **sudo:** Allowed for `apt` installs of system dependencies.
- **GUI backend:** pywebview with **GTK + WebKit2GTK** (recommended; lighter than Qt, standard on Ubuntu GNOME).

### Home server (future)
- **OS:** Ubuntu (headless, no GUI).
- **Hardware:** 8+ GB RAM — no resource constraints; single user, so worker/thread counts can stay low.
- **Access:** LAN only, no domain/HTTPS (auth is removed, so it must NOT be exposed to the internet as-is).

### Ports
- One shared, uncommon port for both laptop and home server to avoid conflicts with 8000/8080/3000/5000 etc.
- **Recommended: `8734`** (chosen at implementation; user opted for "same unique port both" and "you recommend").

## 3. Architectural Decisions (from interview)

| Topic | Decision |
|---|---|
| Laptop run style | Native Python venv, wrapped in a pywebview native window; close window → server stops → process exits |
| Laptop packaging | Setup script (`install.sh`) + `.desktop` launcher entry with an icon; no `.deb` |
| Autostart at login | No — launch manually from the app menu/launcher |
| App data location | Inside the project folder (matches current layout; no XDG move) |
| Translation provider | OpenRouter (OpenAI-compatible `/chat/completions`), default free model, env-configurable |
| Auth | Full removal: login pages, Flask-Login, User model, admin dashboard/API, CLI user commands, auth tests |
| Usage quota/logging | Removed entirely (incl. `MONTHLY_QUOTA_CHARS`, `UsageLog`, `log_usage()`) |
| Voice pins | Moved from per-user DB rows to **browser localStorage** (per-browser, no server storage) |
| Admin usage stats | Removed entirely |
| Database | Entire SQLite / Flask-SQLAlchemy stack removed (nothing left to store) |
| Dictionary mode | Kept (core feature) — needs CC-CEDICT + CC-Canto data files, which are git-ignored (see §7) |
| Google Cloud TTS | Kept — needs service account credentials available locally (see §8) |
| Home server runtime | Run from source: venv + WSGI server + systemd unit, no Docker |
| WSGI server | **waitress** (pure-Python, threaded, same server for desktop + home server; gunicorn can be dropped or kept optional) |
| VPS/Coolify | Abandoned |

## 4. Laptop Desktop App

### 4.1 Experience
- App menu launcher entry "Canto Reader" with an icon (simple SVG/PNG asset created during implementation).
- Double-click → Python process starts → Flask app serves on `http://127.0.0.1:8734` → pywebview opens a native window loading that URL.
- Close the window (or Ctrl+C in terminal) → Flask server is shut down → process exits cleanly.
- No browser tab, no tray icon needed (manual launch only).

### 4.2 Process model
- Entry point: `run_app.py` (or a `desktop` package) at repo root:
  - Reads `.env` (or env vars) for config.
  - Starts the Flask app with waitress in a background thread (`serve(app, host="127.0.0.1", port=8734, threads=4)`).
  - Waits for the server to be up, then opens pywebview window (`webview.create_window("Canto Reader", url, width=…, height=…)`, `webview.start()`).
  - On window close, stop the waitress server and exit.

### 4.3 System dependencies (Ubuntu, pywebview GTK backend)
Approximate apt list (exact names verified at implementation per Ubuntu version):
- `python3-gi`, `python3-gi-cairo`, `libgtk-3-0`, `gir1.2-webkit2-4.1` (24.04) / `gir1.2-webkit2-4.0` (22.04), `python3-dev`, `build-essential`.
- `pip install pywebview[gtk]`.

### 4.4 Launcher packaging
- `scripts/install_laptop.sh`:
  1. Check/install Python 3.12+ (via apt/deadsnakes/pyenv if needed).
  2. Install apt system deps (§4.3).
  3. Create `.venv`, `pip install -r requirements.txt`.
  4. Create `.env` from `.env.example` if missing (user fills secrets).
  5. Write a `.desktop` file to `~/.local/share/applications/canto-reader.desktop` pointing at an executable launcher script (e.g., `scripts/canto-reader.sh` that activates the venv and runs `run_app.py`), with `Icon=` set to the app icon.
  6. Print next steps (create admin no longer needed; provide Google creds + OpenRouter key; dictionary data).

## 5. Auth Removal (Full)

Delete or neutralize the following:

| File / area | Action |
|---|---|
| `auth.py` | Delete (login blueprint) |
| `admin.py`, `routes_admin_api.py` | Delete (admin UI + usage API) |
| `routes_user.py` | Delete (per-user voice pins API) |
| `models.py` | Delete (User, UsageLog, UserVoicePin, `db`, `log_usage`) |
| `app.py` | Remove Flask-Login (`LoginManager`, `login_required`, `load_user`), `User` import, `db` init, `db.create_all()`, `create-admin`/`update-user` CLI commands, `@login_required` on `/` and `/reader` |
| `templates/login.html`, `templates/admin_dashboard.html` | Delete |
| `templates/reader.html` | Remove login/logout links and any `current_user` usage |
| `routes_tts.py`, `routes_translate.py`, `routes_dictionary.py` | Remove `@login_required`, `current_user`, and `log_usage()` calls |
| `static/js/reader/voice.js` (+ `reader.js`) | Voice pins: replace `/api/user/voice-pins` calls with localStorage read/write |
| `tests/test_auth_and_core.py`, `tests/test_admin_user_delete.py`, `tests/test_reader_and_admin_routes.py`, `tests/test_user_voice_pins.py` | Remove or rewrite for the no-auth app (see §11) |
| `requirements.txt` | Remove `Flask-Login`, `Flask-SQLAlchemy`; add `pywebview[gtk]`, `waitress` |
| `.env.example`, `docs/ENVIRONMENT.md` | Remove `DATABASE_PATH`, `SESSION_LIFETIME_HOURS`, `REMEMBER_COOKIE_DAYS`, `SESSION_REFRESH_EACH_REQUEST`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `MONTHLY_QUOTA_CHARS`; add OpenRouter vars (§6) |
| `README.md`, `docs/DEPLOY_COOLIFY.md`, `docs/ARCHITECTURE.md` | Update: no auth, no Docker/Coolify, new local/home deployment docs |

Notes:
- Flask's `SECRET_KEY` becomes effectively unused (no sessions/flash) — keep a default, drop the "required in production" check.
- `FLASK_ENV` can stay for dev mode convenience but is no longer load-bearing for auth.
- The app currently renders a voice catalog by calling Google's API at request time (cached 5 min). With no credentials it degrades to standard voices only — fine.

## 6. OpenRouter Translation

### 6.1 Why it's a small change
`services/translation_grok.py` already calls an OpenAI-compatible `POST {base_url}/chat/completions` with `messages` + `temperature`. OpenRouter exposes the identical contract at `https://openrouter.ai/api/v1`.

### 6.2 Changes
- Rename env vars:
  - `GROK_API_KEY` → `OPENROUTER_API_KEY`
  - `GROK_MODEL` → `OPENROUTER_MODEL`
  - `GROK_BASE_URL` → `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`)
- Rename the service class `GrokTranslationService` → `OpenRouterTranslationService` (file can be renamed `services/translation_openrouter.py`), update provider label to `openrouter`, and update the error message that mentions `GROK_API_KEY`.
- `routes_translate.py`: update config keys; keep timeouts/limits unchanged (`TRANSLATION_TIMEOUT_SECONDS`, `MAX_TRANSLATION_INPUT_CHARS`).
- Update tests that mock the Grok service to the new name/keys.

### 6.3 Default model (free)
- Default to a **free** OpenRouter model, configurable via `OPENROUTER_MODEL`.
- Free models rotate; at implementation, pick a current one (e.g., a `:free` Llama/Mistral/Qwen variant) or default to the **`openrouter/free` router** (random free model) as a robust zero-cost default.
- Note in `.env.example` that this is a free model and can be changed, including to Grok models via OpenRouter (e.g., `x-ai/…` slugs) if the user wants them back.
- The user **has** an OpenRouter API key — wire it into `.env` during setup.

## 7. Dictionary Mode

- Kept as-is: `services/dictionary_loader.py`, `services/dictionary_lookup.py`, routes `POST /api/dictionary/lookup` and `/speak` (minus auth).
- Data files `data/dictionaries/cc-cedict.u8` and `data/dictionaries/cc-canto.u8` are **git-ignored** and currently absent from the repo. They must be obtained (download per `docs/DICTIONARY_SETUP.md` / `docs/DICTIONARY_DATA_LICENSES.md`, or copied from the old VPS before it's decommissioned) and placed in `data/dictionaries/`, then validated with `scripts/prepare_dictionary_data.py`.
- Open item (see §12): user to confirm where to source these files.
- Same files needed on the home server at a later step.

## 8. Google Cloud TTS Credentials

- The app needs a GCP service account key. Two existing mechanisms stay:
  - File: `GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-sa.json` (path relative to repo; `secrets/` is git-ignored), or
  - Inline: `GCP_SERVICE_ACCOUNT_JSON` (single-line JSON).
- Assumption: the user has the service-account JSON from the Coolify deployment and can copy it to the laptop's `secrets/` (or paste inline). Flagged as a required input in §12.
- Without credentials, TTS API calls fail while the rest of the app (dictionary, UI) still works.

## 9. Home Server Deployment (from source, LAN-only)

### 9.1 Layout
- Clone/copy the repo to e.g. `/opt/canto-reader` (owned by a dedicated `canto` user or the login user).
- `python3 -m venv .venv` + `pip install -r requirements.txt` (no GUI deps needed on the server — no pywebview; waitress suffices).
- `.env` with:
  - `PORT=8734` (or hardcoded), `FLASK_ENV=production`
  - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
  - `GOOGLE_APPLICATION_CREDENTIALS=/opt/canto-reader/secrets/gcp-sa.json` (or inline JSON)
  - Dictionary paths (defaults point at `data/dictionaries/…` relative to repo — fine)
  - TTS/translation guardrails kept at defaults.
- Bind **`0.0.0.0:8734`** so LAN devices can reach it.

### 9.2 systemd unit
- `canto-reader.service`: `ExecStart=/opt/canto-reader/.venv/bin/python -m waitress --host=0.0.0.0 --port=8734 --threads=4 app:app` (or via the run script), `Restart=always`, `User=canto`, `WorkingDirectory=/opt/canto-reader`, `EnvironmentFile=/opt/canto-reader/.env`.
- `systemctl enable --now canto-reader`.
- Firewall note: allow TCP 8734 on the LAN interface only; since there is no auth, do not forward this port from the router.

### 9.3 Access
- From laptop/phone browser: `http://<server-lan-ip>:8734`.
- No TLS/domain needed for LAN. If the user later wants internet access, add a reverse proxy (Caddy) + reconsider protection, since the app has no login.

## 10. Configuration Surface (`.env.example` after changes)

```env
# Runtime
FLASK_ENV=development            # production on home server
PORT=8734
SECRET_KEY=dev-secret-key        # no longer security-critical

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-sa.json
GCP_SERVICE_ACCOUNT_JSON=

# OpenRouter translation (OpenAI-compatible)
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free   # free by default; change to any OpenRouter slug
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
TRANSLATION_TIMEOUT_SECONDS=20
MAX_TRANSLATION_INPUT_CHARS=12000

# TTS guardrails (unchanged)
MAX_INPUT_CHARS=12000
TEMP_AUDIO_DIR=static/temp_audio
TEMP_AUDIO_TTL_HOURS=4
MAX_TEMP_AUDIO_FILES=120
MAX_TEMP_AUDIO_BYTES=314572800
TTS_TIMEOUT_SECONDS=20
HQ_TEXT_TARGET_MAX_BYTES=350
HQ_TEXT_HARD_MAX_BYTES=700
HQ_MAX_SPLIT_DEPTH=8
HQ_MAX_TTS_CALLS=128

# Local dictionary mode (unchanged)
DICTIONARY_ENABLED=true
DICTIONARY_CC_CEDICT_PATH=data/dictionaries/cc-cedict.u8
DICTIONARY_CC_CANTO_PATH=data/dictionaries/cc-canto.u8
MAX_DICTIONARY_INPUT_CHARS=12000
MAX_DICTIONARY_ALTERNATIVES=3
MAX_DICTIONARY_TERM_CHARS=64
```

Removed: `DATABASE_PATH`, `SESSION_*`, `REMEMBER_*`, `COOKIE_*`, `GROK_*`, `MONTHLY_QUOTA_CHARS`.

## 11. Testing

- Update the suite to the no-auth app:
  - Delete/rewrite: `test_auth_and_core.py`, `test_admin_user_delete.py`, `test_reader_and_admin_routes.py`, `test_user_voice_pins.py`.
  - Keep + adapt: `test_tts_services.py`, `test_tts_route.py` (remove login/usage-log assertions), `test_dictionary_services.py`, `test_dictionary_route.py` (remove login), `test_translation_route.py` (mock OpenRouter service, new env keys).
- Canonical command stays: `.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v`.
- Manual smoke: desktop app boots to reader without login; TTS plays; dictionary popover works; translation returns via OpenRouter; close window exits cleanly.

## 12. Assumptions & Open Items (confirm before/while implementing)

1. **GCP service-account JSON** — user must supply it for the laptop (`secrets/gcp-sa.json` or inline). *Assumed available from the old Coolify setup.*
2. **Dictionary data files** — where to source `cc-cedict.u8` / `cc-canto.u8` (download fresh vs copy from VPS before decommission). *TBD — user to confirm.*
3. **Exact Ubuntu versions** — laptop and home server (affects `gir1.2-webkit2-*` package names and whether Python 3.12 is present or needs installing).
4. **OpenRouter free model** — pick at implementation time (free roster rotates); `openrouter/free` router is the safe default; user can switch to a Grok slug via OpenRouter.
5. **WSGI server** — waitress recommended for both desktop and home server; gunicorn may be removed from `requirements.txt` (user opted for "simplest implementation").
6. **Icon asset** — a simple icon will be created for the launcher; no brand requirements given.
7. **Voice pins via localStorage** — pins become per-browser; acceptable per user.
8. **No autostart** on laptop — confirmed.

## 13. Implementation Plan (later phase, not now)

1. Strip auth/admin/DB stack; update templates, routes, JS (pins → localStorage), CLI.
2. Add OpenRouter translation (rename service + env keys + tests).
3. Add waitress + pywebview desktop wrapper (`run_app.py`) and launcher script.
4. Create icon; write `scripts/install_laptop.sh` (deps, venv, `.env`, `.desktop`).
5. Update `.env.example`, README, docs (replace Coolify guide with laptop + home-server runbooks).
6. Update/rewrite tests; run full suite.
7. Add home-server runbook + systemd unit example.
8. Smoke-test desktop app on the laptop; verify dictionary/TTS/translation.

## 14. Reference Files
- `README.md` (current local dev + Coolify notes)
- `docs/DEPLOY_COOLIFY.md`, `docs/ENVIRONMENT.md`, `docs/ARCHITECTURE.md`, `docs/DICTIONARY_SETUP.md`
- `app.py`, `models.py`, `auth.py`, `admin.py`, `routes_*.py`
- `services/translation_grok.py`, `services/runtime_config.py`, `services/tts_google.py`
- `.env.example`, `requirements.txt`, `Dockerfile` (Dockerfile becomes obsolete once Docker is abandoned)

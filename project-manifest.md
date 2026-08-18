# Project Manifest: Canto Reader

This manifest is a lightweight index of active project artifacts.

## Project Meta
- **Name:** Canto Reader
- **Status:** Local desktop app + home-server (LAN) deployment; no auth, no Docker.

## Canonical Docs
- `README.md` - product summary, desktop/server setup, and testing.
- `docs/ARCHITECTURE.md` - runtime architecture.
- `docs/ENVIRONMENT.md` - env var reference.
- `docs/DEPLOY_LAPTOP.md` - laptop desktop app runbook.
- `docs/DEPLOY_HOME_SERVER.md` - home server (venv + waitress + systemd) runbook.
- `docs/DICTIONARY_SETUP.md` - dictionary data preparation.
- `docs/DICTIONARY_DATA_LICENSES.md` - dictionary licensing notes.
- `docs/COST_CONSTRAINTS.md` - TTS constraints and cost notes.

## Core Source Entrypoints
- `app.py` - app factory, config wiring, and route registration.
- `run_app.py` - desktop entry point (waitress + pywebview).
- `routes_tts.py` - synthesis API and HQ/standard handling.
- `routes_dictionary.py` - dictionary lookup + term speech API.
- `routes_translate.py` - English translation API (OpenRouter).
- `services/` - TTS, SSML, translation, dictionary, audio storage/policy helpers.
- `templates/reader.html` and `static/js/reader.js` - primary UI/runtime frontend logic.

## Deployment Assets
- `scripts/install_laptop.sh` - laptop installer + `.desktop` launcher writer.
- `scripts/canto-reader.sh` - desktop launcher.
- `scripts/prepare_dictionary_data.py` - dictionary data import/validation.
- `deploy/canto-reader.service` - home server systemd unit example.
- `requirements.txt` - core/server dependencies (no GUI).
- `requirements-desktop.txt` - adds pywebview for the desktop app.

## Test Coverage
- `tests/` contains TTS, dictionary, translation, and app route tests.
- Canonical command: `.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v`

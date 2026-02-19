# Project Manifest: Canto Reader

This manifest is a lightweight index of active project artifacts.

## Project Meta
- **Name:** Canto Reader
- **Status:** Production functional, active refactor in progress.
- **Refactor Branch:** `refactor/codebase-streamline-2026-02-18`

## Canonical Docs
- `README.md` - product summary, local setup, and testing.
- `docs/ARCHITECTURE.md` - runtime architecture and refactor plan/findings.
- `docs/ENVIRONMENT.md` - env var reference.
- `docs/DEPLOY_COOLIFY.md` - deployment/runbook for Coolify.
- `docs/DICTIONARY_SETUP.md` - dictionary data preparation and mounting.
- `docs/DICTIONARY_DATA_LICENSES.md` - dictionary licensing notes.
- `docs/COST_CONSTRAINTS.md` - cost and operational guardrails.

## Core Source Entrypoints
- `app.py` - app factory, config wiring, route registration, and CLI.
- `models.py` - SQLite models and usage logging.
- `routes_tts.py` - synthesis API and HQ/standard handling.
- `routes_dictionary.py` - dictionary lookup + term speech API.
- `routes_translate.py` - English translation API.
- `routes_user.py` - voice pin APIs.
- `admin.py` and `routes_admin_api.py` - admin page + usage API.
- `services/` - TTS, SSML, translation, dictionary, audio storage/policy helpers.
- `templates/reader.html` and `static/js/reader.js` - primary UI/runtime frontend logic.

## Test Coverage
- `tests/` contains auth, admin, TTS, dictionary, translation, and user voice-pin tests.
- Canonical command: `.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v`

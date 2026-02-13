# Project Manifest: Speak-in-Canto

This manifest is the single source of truth for the project's architecture, documentation, and critical entrypoints.

## Project Meta
- **Name:** Speak-in-Canto (Cantonese TTS Reader)
- **Status:** Tasks 01, 02, 03, and 07 implemented.
- **Objective:** Secure Cantonese reader with Google Cloud TTS, sync highlighting (Standard voices), and optional English translation.

## Key Pointers

### Architecture & Docs
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System-wide technical specs.
- [COST_CONSTRAINTS.md](docs/COST_CONSTRAINTS.md) - Critical billing and payload limits.
- [DEPLOY_COOLIFY.md](docs/DEPLOY_COOLIFY.md) - Deployment reference for container runtime on Coolify.
- [ENVIRONMENT.md](docs/ENVIRONMENT.md) - Canonical runtime environment variable reference.
- [TECHADVISOR.md](comms/roles/TECHADVISOR.md) - AI Technical Advisor role.

### Activity & Tasks
- [log.md](comms/log.md) - Unified activity log and Advisory Notes.
- [Task 01 (Detailed)](comms/tasks/2026-02-13-01-foundation-auth-and-data.md) - Foundation, Auth, Usage Data.
- [Task 02 (Detailed)](comms/tasks/2026-02-13-02-tts-pipeline-and-sync-metadata.md) - TTS Pipeline and Sync Metadata.
- [Task 03 (Detailed)](comms/tasks/2026-02-13-03-reader-ui-admin-usage-dashboard.md) - Reader UI and Admin Dashboard.
- [Task 07 (Detailed)](comms/tasks/2026-02-13-07-english-translation-grok.md) - Grok English translation panel and API.
- [Legacy Task Briefs (Archived)](comms/tasks/archive/legacy/) - Superseded by detailed specs.

### Source Code
- `app.py` - Flask app factory, auth, admin, and TTS route wiring.
- `models.py` - SQLite ORM models and usage logging utility.
- `routes_tts.py` - TTS synthesis API contract and fallback flow.
- `routes_translate.py` - English translation API (`/api/translate`).
- `routes_admin_api.py` - Admin usage aggregation API endpoints.
- `routes_user.py` - User voice pin APIs.
- `services/` - SSML builder, Google TTS wrapper, audio storage/cleanup.
- `templates/` - Login, reader, and admin dashboard pages.
- `static/js/reader.js` - Reader sync/player frontend logic.
- `static/css/reader.css` - Reader/admin UI styling.
- `tests/` - Unit/integration coverage for auth/admin, TTS pipeline, reader/admin routes, translation route, and voice pin APIs.
- `Dockerfile` - Production container runtime entrypoint (Gunicorn).

## Current Focus
- [x] Finalize tech stack and architecture.
- [x] Publish detailed implementation specs for Tasks 01-03.
- [x] Implement Task 01 detailed spec (`2026-02-13-01-foundation-auth-and-data.md`).
- [x] Implement Task 02 detailed spec (`2026-02-13-02-tts-pipeline-and-sync-metadata.md`).
- [x] Implement Task 03 detailed spec (`2026-02-13-03-reader-ui-admin-usage-dashboard.md`).
- [x] Implement Task 07 translation spec (`2026-02-13-07-english-translation-grok.md`).

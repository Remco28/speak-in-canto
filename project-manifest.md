# Project Manifest: Speak-in-Canto

This manifest is the single source of truth for the project's architecture, documentation, and critical entrypoints.

## Project Meta
- **Name:** Speak-in-Canto (Cantonese TTS Reader)
- **Status:** Tasks 01-02 Implemented / Task 03 Next
- **Objective:** Simple, secure web app for Cantonese Text-to-Speech using Google Cloud TTS.

## Key Pointers

### Architecture & Docs
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System-wide technical specs.
- [COST_CONSTRAINTS.md](docs/COST_CONSTRAINTS.md) - Critical billing and payload limits.
- [TECHADVISOR.md](comms/roles/TECHADVISOR.md) - AI Technical Advisor role.

### Activity & Tasks
- [log.md](comms/log.md) - Unified activity log and Advisory Notes.
- [Task 01 (Detailed)](comms/tasks/2026-02-13-01-foundation-auth-and-data.md) - Foundation, Auth, Usage Data.
- [Task 02 (Detailed)](comms/tasks/2026-02-13-02-tts-pipeline-and-sync-metadata.md) - TTS Pipeline and Sync Metadata.
- [Task 03 (Detailed)](comms/tasks/2026-02-13-03-reader-ui-admin-usage-dashboard.md) - Reader UI and Admin Dashboard.
- [Task 01 (Legacy Brief)](comms/tasks/01-data-model.md)
- [Task 02 (Legacy Brief)](comms/tasks/02-tts-engine.md)
- [Task 03 (Legacy Brief)](comms/tasks/03-frontend-ui.md)

### Source Code
- `app.py` - Flask app factory, auth, admin, and TTS route wiring.
- `models.py` - SQLite ORM models and usage logging utility.
- `routes_tts.py` - TTS synthesis API contract and fallback flow.
- `services/` - SSML builder, Google TTS wrapper, audio storage/cleanup.
- `templates/` - Login, index, and admin user pages.
- `tests/` - Task 01 and Task 02 verification coverage.

## Current Focus
- [x] Finalize tech stack and architecture.
- [x] Publish detailed implementation specs for Tasks 01-03.
- [x] Implement Task 01 detailed spec (`2026-02-13-01-foundation-auth-and-data.md`).
- [x] Implement Task 02 detailed spec (`2026-02-13-02-tts-pipeline-and-sync-metadata.md`).
- [ ] Implement Task 03 detailed spec (`2026-02-13-03-reader-ui-admin-usage-dashboard.md`).

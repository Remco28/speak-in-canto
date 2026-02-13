<!-- Example log -->
[2025-08-26 09:00] [Gemini]: SETUP: Initialized comms directory structure and logging protocol.

[2026-02-12] [TECHADVISOR]: ADVISORY NOTES (Feature Refinement)
- Good: Moving to a proper Login UI + Admin flag in DB. Much better UX than Basic Auth.
- Feature: **Character Tracking** is a "go." We will use Google TTS SSML `<mark>` tags to get timepoints.
- Complexity (High): Backend must convert raw text to SSML with marks and return both audio and timepoint metadata. Frontend needs a "Sync Player" logic.
- Storage: Use a `temp/` directory for MP3s with a TTL (Time-To-Live) cleanup strategy instead of strict session-based deletion.
- **Verification Logic**: Added Jyutping support (`pycantonese`) and client-side playback speed control to the roadmap.
- Action: Create `comms/tasks/01-data-model.md` and `comms/tasks/02-tts-engine.md`.

<!-- example log -->
[2026-02-12 22:35] [ARCHITECT]: SPEC IN_PROGRESS: Reviewing repository state, architecture, and existing task briefs for developer handoff.
[2026-02-12 22:35] [ARCHITECT]: SPEC READY: Added detailed implementation specs: 2026-02-13-01-foundation-auth-and-data.md, 2026-02-13-02-tts-pipeline-and-sync-metadata.md, 2026-02-13-03-reader-ui-admin-usage-dashboard.md.
[2026-02-12 22:36] [ARCHITECT]: SPEC UPDATE: Added mark-density reliability policy, byte-based chunking limits, and fallback sync_mode contract in Task 02 + architecture/cost docs.
[2026-02-12 22:37] [ARCHITECT]: SPEC UPDATE: Added Jyutping alignment safeguards, MAX_INPUT_CHARS=12000 guardrail, and strict temp-audio high-watermark cleanup caps (files/bytes + oldest-first eviction).
[2026-02-12 23:54] [CLAUDE]: IMPL IN_PROGRESS: Task 01 foundation/auth/data implementation started (app factory, models, auth/admin routes, tests).
[2026-02-12 23:57] [CLAUDE]: IMPL DONE: Completed Task 01 foundation/auth/data with app factory, SQLite models, login/logout, admin user management, create-admin CLI, and passing unit tests.
[2026-02-13 00:01] [CLAUDE]: IMPL DONE: Completed Task 02 backend (SSML chunking, mark fallback mode, Google TTS wrapper, /api/tts/synthesize, temp audio cleanup caps, and tests).
[2026-02-13 00:02] [ARCHITECT]: SPEC MAINTENANCE: Archived legacy task briefs to comms/tasks/archive/legacy; detailed dated specs remain the active implementation source.

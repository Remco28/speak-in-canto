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
[2026-02-13 00:06] [CLAUDE]: IMPL IN_PROGRESS: Task 03 reader UI, sync player behavior, and admin usage dashboard/API implementation.
[2026-02-13 00:06] [CLAUDE]: IMPL DONE: Completed Task 03 with reader page, sync JS, admin dashboard, monthly usage API, and passing tests.
[2026-02-13 00:40] [CLAUDE]: IMPL IN_PROGRESS: Added two-mode voice UX (Standard synced + High Quality Chirp no-sync), dynamic star-name voice list, and sync drift/click usability improvements.
[2026-02-13 00:51] [CLAUDE]: IMPL DONE: Added admin user deletion safeguards, per-user voice pin APIs/UI (pins at top), and smoother reader sync loop/click behavior.
[2026-02-13 04:42] [ARCHITECT]: SPEC READY: Added Task 07 spec `2026-02-13-07-english-translation-grok.md` for Grok-only English translation panel under Reader; updated architecture doc with translation integration point and `GROK_API_KEY` runtime secret.
[2026-02-13 04:53] [CLAUDE]: IMPL DONE: Implemented Task 07 Grok-only English translation (`/api/translate`), reader translation panel/UI states, env-driven Grok config, and translation route tests (full suite passing).
[2026-02-13 05:15] [CLAUDE]: IMPL DONE: Added Coolify deployment readiness assets (`Dockerfile`, `.dockerignore`, `docs/DEPLOY_COOLIFY.md`), switched production runtime to Gunicorn dependency, and improved Grok 403/1010 diagnostics.
[2026-02-13 14:42] [ARCHITECT]: DOCS UPDATE: Refreshed architecture, deployment, and project-manifest docs to match implemented voice modes, translation endpoint, data model additions, Coolify runtime env guidance, and current task status (including Task 07).
[2026-02-13 14:54] [CLAUDE]: IMPL DONE: Fixed High Quality TTS long-sentence failures by enforcing smaller HQ text chunk byte budgets (`HQ_TEXT_TARGET_MAX_BYTES` / `HQ_TEXT_HARD_MAX_BYTES`) and added regression test for punctuation-sparse input.
[2026-02-13 15:23] [CLAUDE]: IMPL DONE: Hardened High Quality TTS for scale by adding bounded recursive split retries (`HQ_MAX_SPLIT_DEPTH`, `HQ_MAX_TTS_CALLS`) and per-request HQ synthesis metrics logging.
[2026-02-13 15:57] [ARCHITECT]: DOCS UPDATE: Added repo `README.md`, `docs/ENVIRONMENT.md`, and deployment note capturing HQ sentence-length failure lesson + required guardrail envs to prevent repeat regressions.
[2026-02-13 17:11] [ARCHITECT]: DOCS CLEANUP: Removed obsolete reusable/legacy docs from repo and added `comms/VPS_SWAP_SETUP.md` with copy-friendly VPS swap setup instructions.
[2026-02-13 20:52] [CLAUDE]: IMPL DONE: Rebranded reader UI to `Canto Reader`, merged reader/media areas, moved admin/logout to low-emphasis footer links, and refreshed UI tests for updated branding copy.
[2026-02-18 19:24] [ARCHITECT]: REFACTOR IN_PROGRESS: Started systematic codebase streamlining on branch `refactor/codebase-streamline-2026-02-18` with inventory + runtime-path audit and phased execution plan.
[2026-02-18 19:24] [CLAUDE]: REFACTOR DONE: Removed dead frontend hooks and unused templates, extracted shared backend helpers (`services/usage_metrics.py`, `services/runtime_config.py`, `services/audio_policy.py`), and consolidated duplicated route logic without API behavior changes.
[2026-02-18 19:24] [CLAUDE]: REFACTOR DONE: Modularized reader frontend into ES modules (`sync`, `voice`, `dictionary`, `translation`) with `static/js/reader.js` as orchestrator; switched reader template script loading to `type=module`.
[2026-02-18 19:24] [CLAUDE]: REFACTOR DONE: Normalized test naming from task-era files to feature-oriented files, removed empty archive directory, refreshed architecture/environment/manifest docs, and re-validated full suite passing (44 tests).

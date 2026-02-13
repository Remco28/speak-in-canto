# Task: Reader UI, Sync Player, and Admin Usage Dashboard

## Rationale
The product succeeds or fails at the interaction layer: submit text, hear speech, and track characters in real time. We should deliver one clear screen for reading and one admin screen for lightweight operations, avoiding UI complexity that does not improve comprehension.

## Objective
Implement frontend and supporting backend routes for:
- Reader input and synthesis trigger
- Character + jyutping rendering
- Audio-timepoint synchronized highlighting
- Click-to-seek per character
- Playback speed and voice controls
- Admin usage dashboard and user management view hookup

## User Stories
- As a user, I can paste text and hear Cantonese playback quickly.
- As a user, I can follow highlighted characters while listening.
- As a user, I can click a character to jump playback.
- As an admin, I can monitor monthly usage and manage users.

## Scope
In scope:
- Browser UI and JS logic
- API integration with `/api/tts/synthesize`
- Admin usage summary endpoint + table rendering

Out of scope:
- Advanced design system
- Multi-tenant billing exports

## Required File Changes
- Create: `templates/reader.html`
- Create: `templates/admin_dashboard.html`
- Create: `static/js/reader.js`
- Create: `static/css/reader.css`
- Update: `app.py` or route modules to serve pages
- Create: `routes_admin_api.py`

## UI Requirements

### Reader Page
- Textarea for Cantonese input.
- Character counter under textarea (`current/MAX_INPUT_CHARS`).
- Voice selector driven by backend allowlist.
- Read button with loading/disabled state.
- Speed slider (`0.5-2.0`, step `0.1`) bound to `audio.playbackRate`.
- Render area where each token is a clickable span:
  - `data-token-id` and `data-mark`
  - ruby-like jyutping text above token

### Sync Logic (`static/js/reader.js`)
- Build an in-memory index from `timepoints` + `mark_to_token`.
- On `audio.timeupdate`:
  - Determine active mark by current time.
  - Highlight corresponding token span.
- On token click:
  - Seek `audio.currentTime` to token timestamp when available.
- Handle tokens without marks (e.g., whitespace) gracefully.

## Admin Dashboard Requirements
- `GET /admin/dashboard` page with:
  - User table (username, role, created_at)
  - Monthly usage progress bar and absolute count
- `GET /api/admin/usage/monthly` JSON response:
  - `month_start`, `month_end`, `used_chars`, `quota_chars`, `percent_used`
- Require admin auth for all admin pages and API routes.

## Error and Empty States
- Reader:
  - Empty input validation before request.
  - Over-limit input validation against `MAX_INPUT_CHARS`.
  - Inline error banner on API failure.
  - Clear state reset between requests.
- Admin:
  - Show `0` usage when no logs exist.
  - Render empty table state for no users.

## Constraints
- Keep dependencies minimal (vanilla JS + Bootstrap is enough).
- Avoid polling; all sync logic should be local after API response.
- Keep UI responsive for long text (use efficient DOM updates).
- Keep `MAX_INPUT_CHARS` sourced from backend-rendered config (single source of truth).

## Acceptance Criteria
- User can synthesize and play text end-to-end from reader page.
- Reader blocks over-limit submissions and shows a clear limit message.
- Highlight follows audio and updates smoothly.
- Click-to-seek jumps to expected audio position.
- Speed slider modifies playback rate immediately.
- Admin dashboard shows correct monthly usage aggregation.
- Non-admin receives `403` for admin page/API.

## Verification
- Manual checks:
  - Long paragraph synthesis + sync remains stable.
  - Rapid seeking does not break highlight state.
  - Voice change affects synthesized audio.
- Add frontend integration tests where practical (or documented manual test checklist if no framework is set up yet).

# Task: Foundation, Auth, and Usage Data

## Rationale
We need a minimal, correct foundation before any TTS work. If identity, persistence, and usage accounting are unclear, all downstream features become brittle. The simplest path is one Flask app, one SQLite DB, and session auth with explicit admin gating.

## Objective
Implement the backend foundation:
- Flask app bootstrap and config loading
- SQLite models and table creation
- Session login/logout
- Admin-only user management endpoints
- Usage logging primitives for future TTS integration

## User Stories
- As a parent/admin, I can create and manage user accounts.
- As a user, I can log in and access the reader page.
- As the system, I can record character usage events for billing visibility.

## Scope
In scope:
- Backend only (no finalized UI polish yet)
- Data model and auth flows
- Admin API and minimal HTML pages needed to verify behavior

Out of scope:
- Google TTS calls
- Character-level sync UI

## Required File Changes
- Create: `app.py`
- Create: `models.py`
- Create: `auth.py`
- Create: `admin.py`
- Create: `templates/login.html`
- Create: `templates/index.html`
- Create: `templates/admin_users.html`
- Update: `requirements.txt` (only if a strictly required dependency is missing)

## Required Interfaces

### `models.py`
- `db = SQLAlchemy()`
- `class User(UserMixin, db.Model)` with:
  - `id`, `username`, `password_hash`, `is_admin`, `created_at`
- `class UsageLog(db.Model)` with:
  - `id`, `user_id`, `char_count`, `timestamp`, optional `voice_name`
- `def log_usage(user_id: int, char_count: int, voice_name: str | None = None) -> None`

### `app.py`
- `def create_app() -> Flask`
- Load env config:
  - `SECRET_KEY` (required in non-dev)
  - `DATABASE_PATH` (default `instance/speak_in_canto.db`)
- Initialize:
  - `Flask-Login`
  - `Flask-SQLAlchemy`
- Enable SQLite WAL on startup.
- Register blueprints from `auth.py` and `admin.py`.
- Provide `@login_manager.user_loader`.

### `auth.py` blueprint
- `GET/POST /login`
- `POST /logout`
- Session-based auth via `werkzeug.security`.
- Redirect authenticated users away from login page.

### `admin.py` blueprint
- Guard every route with admin check.
- `GET /admin/users` list users.
- `POST /admin/users` create user with server-side validation.
- Reject duplicate usernames with a clear message.

## Bootstrap / CLI
- Add a CLI command:
  - `flask create-admin --username <u> --password <p>`
- Behavior:
  - Creates initial admin if username does not exist.
  - Fails safely with clear output if user already exists.

## Constraints
- Do not store plaintext passwords.
- Do not expose admin routes to non-admin users.
- Keep responses deterministic and explicit on error.
- Keep DB access in request thread only; no background worker yet.

## Acceptance Criteria
- New DB initializes with `users` and `usage_logs`.
- Admin user can be created via CLI.
- Login/logout works with session cookie.
- Non-admin users are denied `403` on `/admin/*`.
- Admin can create standard users from `/admin/users`.
- `log_usage(...)` inserts a row with correct `user_id` and `char_count`.

## Verification
- Add tests for:
  - Password hashing and verification.
  - Login success/failure.
  - Admin route protection.
  - Duplicate username handling.
  - `log_usage` insertion.


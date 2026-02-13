# Task 01: Data Model & Auth Setup

## Objective
Establish the SQLite database and basic authentication flow using Flask-Login.

## Schema Requirements
- `users` table:
    - `id` (INT, PK)
    - `username` (TEXT, Unique)
    - `password_hash` (TEXT)
    - `is_admin` (BOOLEAN)
    - `created_at` (DATETIME)
- `usage_logs` (To track Google TTS costs):
    - `id` (INT, PK)
    - `user_id` (INT, FK)
    - `char_count` (INT)
    - `timestamp` (DATETIME)

## Tasks
- [ ] Initialize Flask app with `Flask-SQLAlchemy`.
- [ ] Create User model with `UserMixin`.
- [ ] Implement `werkzeug.security` for password hashing.
- [ ] Create an initial "Super Admin" via a CLI command or a one-time script.
- [ ] Set up login/logout routes.

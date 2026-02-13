# Task: Reader English Translation (Grok API)

## Rationale
Users want a simple way to understand pasted Cantonese/Chinese passages without leaving the app. A lightweight translation panel under the Reader delivers this value with minimal product complexity and no disruption to the existing TTS + sync pipeline.

## Objective
Implement a single-purpose translation feature that translates user-provided reader text to English using Grok.

## User Stories
- As a user, I can translate the current passage to English from the Reader page.
- As a user, I can see translation results inline without leaving playback controls.
- As an operator, I can run this feature with simple configuration and clear failure behavior.

## Scope
In scope:
- One backend translation endpoint using Grok only
- One translation section in Reader UI under existing reader controls/output
- English-only translation output
- Basic reliability guardrails (input cap, timeout, errors, logs)

Out of scope:
- Multi-language output
- Multi-provider abstraction in UI
- Tone/style controls
- Copy button
- Per-user translation analytics dashboard

## Product Decisions (Locked)
- Provider: Grok API only
- Target language: English only
- Prompt behavior: minimal instruction; allow model to choose natural translation
- Mixed-language handling: rely on model behavior (no special preprocessing rules)
- Cost controls: keep simple; no quota throttling in v1

## Required File Changes
- Create: `services/translation_grok.py`
- Create: `routes_translate.py`
- Update: `app.py` (register translate blueprint)
- Update: `templates/reader.html` (add translation section under Reader)
- Update: `static/js/reader.js` (call translation endpoint + render states)
- Update: `requirements.txt` (add Grok/xAI SDK dependency or HTTP client dependency if not present)
- Create/Update tests:
  - `tests/test_translation_route.py`
  - Adjust reader UI integration tests/manual checklist docs as needed

## API Contract

### `POST /api/translate`
Request JSON:
- `text` (string, required)

Response JSON (success):
- `translation` (string)
- `provider` (string, always `grok`)
- `model` (string)

Error responses:
- `400` empty/malformed input
- `413` input exceeds `MAX_TRANSLATION_INPUT_CHARS`
- `502` upstream Grok failure
- `504` upstream timeout

## Backend Requirements
- Add `TranslationServiceError` typed exception in translation service module.
- Configuration (env-driven):
  - `GROK_API_KEY` (required in non-test runtime)
  - `GROK_MODEL` (default to a stable, generally available model)
  - `TRANSLATION_TIMEOUT_SECONDS` (default `20`)
  - `MAX_TRANSLATION_INPUT_CHARS` (default `12000`)
- Input handling:
  - Trim outer whitespace.
  - Reject empty text after trim.
  - Enforce max input chars before calling provider.
- Prompt policy:
  - System/developer prompt should request English translation output only.
  - Keep prompt short; no extra style transforms unless needed for correctness.
- Logging:
  - Log request size and latency at INFO.
  - Log provider failures with safe error details (no secret leakage).

## Reader UI Requirements
- Add section title: `English Translation`
- Add button: `Translate to English`
- Add output container under the button.
- Pending state:
  - Disable translate button
  - Show simple loading text (e.g., `Translating...`)
- Success state:
  - Render translated text in output container
- Error state:
  - Render inline error message in translation area
- Existing reader/TTS behavior must remain unaffected by translation failures.

## Constraints
- Do not send Google credentials or TTS data to Grok.
- Keep route auth consistent with current reader access model (logged-in users only).
- Set strict provider timeout; never allow indefinite waits.
- Keep implementation synchronous for v1 (no job queue).

## Acceptance Criteria
- Reader page displays translation section under existing reader content.
- Valid `POST /api/translate` request returns English text from Grok.
- Empty input returns `400`.
- Over-limit input returns `413`.
- Provider timeout returns controlled `504`.
- Provider non-timeout errors return controlled `502`.
- Translation button is disabled during request and re-enabled after completion/failure.
- Existing TTS synthesis flow remains functional and unchanged.

## Verification
- Unit/integration tests for route:
  - success path (mock provider)
  - empty input
  - over-limit input
  - timeout mapping to `504`
  - provider error mapping to `502`
- Manual checks:
  - Translate short Cantonese text
  - Translate mixed Cantonese/Chinese + English text
  - Confirm UI recovers after an error and can retry

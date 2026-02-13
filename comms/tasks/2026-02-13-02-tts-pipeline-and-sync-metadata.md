# Task: TTS Pipeline, SSML Marks, and Sync Metadata

## Rationale
Character-sync playback is the core product value. The system must map input text to audio timestamps reliably while staying within Google payload limits and free-tier usage constraints. The simplest robust design is: normalize text -> tokenize for display -> build SSML with deterministic marks -> synthesize -> return audio plus mapping metadata.

## Objective
Implement backend TTS generation with:
- SSML mark insertion
- Chunking for payload safety
- Audio file persistence with TTL cleanup
- Timepoint metadata packaging for frontend sync
- Usage logging on successful synthesis

## User Stories
- As a user, I can submit Cantonese text and receive playable audio.
- As a user, I can see per-character highlighting that matches playback.
- As an admin, I can track character usage for cost awareness.

## Scope
In scope:
- TTS service layer
- One API endpoint for synthesis
- Metadata contract for frontend
- Temp audio retention cleanup job

Out of scope:
- Final frontend rendering logic
- Long-term object storage/CDN

## Required File Changes
- Create: `services/ssml_builder.py`
- Create: `services/tts_google.py`
- Create: `services/audio_store.py`
- Create: `routes_tts.py`
- Update: `app.py` (register blueprint + startup cleanup hook)

## API Contract

### `POST /api/tts/synthesize`
Request JSON:
- `text` (string, required)
- `voice_name` (string, required, allowed set managed server-side)
- `speaking_rate` (number, optional, default `1.0`, clamp `0.5-2.0`)

Response JSON (success):
- `audio_url` (string)
- `duration_seconds` (number)
- `timepoints` (array of `{mark_name, seconds}`)
- `tokens` (array of `{token_id, char, raw_index, jyutping}`)
- `mark_to_token` (object mapping `mark_name -> token_id`)
- `sync_mode` (string: `full` or `reduced`)

Error responses:
- `400` invalid input or empty text
- `413` input exceeds `MAX_INPUT_CHARS` guardrail
- `413` exceeds supported size after chunking attempts
- `502` upstream TTS failure

## SSML and Token Rules
- Normalize line endings and trim outer whitespace.
- Build `tokens` from user-visible characters in order.
- Insert `<mark name="c_<token_id>"/>` before each non-whitespace token in SSML.
- Preserve punctuation tokens for highlighting.
- Whitespace tokens:
  - Keep in rendered `tokens` list
  - Do not emit marks for pure whitespace
- Create `mark_to_token` only for emitted marks.

## Mark Density Reliability Rules
- Default mode: mark every non-whitespace token.
- Validate chunk timepoint quality after synthesis:
  - If emitted marks exist but returned timepoints are missing/sparse, classify as degraded.
- On degraded chunk, retry once with reduced marks:
  - Mark Han characters and sentence-ending punctuation only.
  - Keep token IDs and `mark_to_token` stable for surviving marks.
- If reduced mode fails again, return controlled `502` with a user-safe error.

## Chunking Rules
- Hard limit: keep each SSML chunk safely below Google 5,000-byte payload.
- Target range: 3,500-4,200 UTF-8 bytes per SSML chunk.
- Split on sentence boundaries first (`。！？!?`), then commas, then hard split as last resort.
- Maintain global token index across chunks so frontend uses one continuous timeline.
- Merge chunk timepoints by adding cumulative duration offset from previous chunks.
- Enforce configurable request cap: `MAX_INPUT_CHARS` (default `12000`).

## Jyutping Rules
- Generate jyutping from the full normalized input first, then align to token indices.
- Alignment policy:
  - Han/CJK token: best-effort jyutping syllable mapped by source index order.
  - Punctuation/whitespace/symbol/Latin token: `jyutping=""`.
  - If a token cannot be confidently aligned, set `jyutping=""` (never shift neighboring token mappings).
- If jyutping generation fails for the whole input, continue synthesis with empty jyutping values (do not fail request).
- Add optional debug logging counters per request: `jyutping_mapped`, `jyutping_unmapped`.

## Audio Storage and Cleanup
- Store generated files in `static/temp_audio/`.
- Use collision-safe filename: timestamp + random suffix.
- Implement cleanup function deleting files older than 4 hours.
- Implement high-watermark cleanup guards:
  - `MAX_TEMP_AUDIO_FILES` default `120`
  - `MAX_TEMP_AUDIO_BYTES` default `300MB`
  - Delete oldest files until both limits are satisfied.
- Run cleanup:
  - Before synthesis starts
  - At app startup
  - Opportunistically after successful synthesis

## Usage Logging
- On successful synthesis only, insert one `usage_logs` row:
  - `user_id`, `char_count` (count of non-whitespace tokens), `voice_name`, `timestamp`

## Constraints
- Validate `voice_name` against an allowlist on server.
- Never trust client-provided usage counts.
- Keep all Google credentials server-side only.
- Set upstream timeout and return controlled error on timeout.

## Acceptance Criteria
- Valid request returns audio + aligned token/timepoint metadata.
- Chunked requests still produce monotonic timepoints and correct token mapping.
- Response includes `sync_mode` and reports `reduced` if fallback mode was used.
- Jyutping values never shift to the wrong token on partial mapping failure.
- Invalid voice is rejected with `400`.
- Input above `MAX_INPUT_CHARS` returns `413`.
- Oversized unchunkable payload returns `413`.
- Successful calls write audio file and usage row.
- Cleanup removes files older than 4 hours and enforces file/size high-watermark caps.

## Verification
- Add tests for:
  - Chunking boundary behavior.
  - Mark naming continuity across chunks.
  - Monotonic merged timestamps.
  - Fallback transition from `full` to `reduced` mode when marks are sparse.
  - Jyutping alignment for mixed input (Han + punctuation + Latin + whitespace).
  - Unmappable jyutping tokens remain empty without index drift.
  - Usage logging only on success.
  - Cleanup deletion logic (TTL and high-watermark enforcement).
  - Voice allowlist enforcement.

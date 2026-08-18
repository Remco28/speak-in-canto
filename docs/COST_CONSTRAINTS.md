# TTS Constraints & Cost Notes

This documents the Google Cloud TTS constraints the app is built around. The
app no longer enforces a monthly quota or usage dashboard; these are reference
limits and guardrails.

## 1. Google Cloud TTS Free Tier
- The free tier is 1,000,000 characters per month.
- What counts as a "character" for billing:
    - The actual Cantonese text.
    - Spaces, newlines, and punctuation.
    - SSML tags like `<speak>`, `<voice>`, and `<break>`.
- `<mark>` tags are EXEMPT from billing, so the app uses them freely for
  character tracking.

## 2. Technical Payload Limits (The 5K Ceiling)
- A single Google request cannot exceed 5,000 bytes of total input length.
- `<mark>` tags are free for billing but DO count toward this technical limit.
- The backend splits input by UTF-8 byte budget, not char count:
  - Conservative target: 3,500–4,200 bytes per SSML chunk.
  - Chunk by sentence first, then clause, then hard split as a last resort.

## 2.1 Mark Density Reliability Policy
- **Default mode:** Per-character `<mark>` on all non-whitespace tokens.
- **Skip mode:** No marks for pure whitespace tokens.
- **Fallback mode (automatic):** If returned timepoints are sparse/missing for a
  chunk, re-synthesize that chunk once with reduced marks:
    - Keep marks on Han characters and sentence-ending punctuation only.
    - Keep token IDs stable so frontend mapping remains deterministic.
- **Last-resort behavior:** If fallback still fails, return a controlled error
  with guidance to shorten input.

## 2.2 Input Size Guardrail
- No file uploads are supported; text is pasted directly into the reader.
- `MAX_INPUT_CHARS` (default 12,000) is enforced per request, returning `413`
  when exceeded.

## 3. Audio Regeneration (No-Double-Dip)
- Playback speed is handled via the browser's `audio.playbackRate`; never
  re-request audio for a different speed.
- Changing the voice triggers a new billed request. The UI reflects the current
  selection before reading.

## 4. Local Resource Management
- Generated MP3s are stored in `static/temp_audio/` with a TTL (default 4 hours).
- Hard cleanup caps:
    - `MAX_TEMP_AUDIO_FILES=120`
    - `MAX_TEMP_AUDIO_BYTES=300MB`
  Cleanup runs before and after synthesis; oldest files are evicted first.
- Jyutping uses the local `pycantonese` library (no external API calls).

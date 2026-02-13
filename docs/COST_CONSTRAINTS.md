# Developer Guide: Cost Constraints & Quotas

To keep this project within the **Google Cloud TTS Free Tier** (1M characters/month) and the **$5/mo VPS** budget, developers MUST adhere to the following constraints.

## 1. Google Cloud TTS Billing (Neural2-yue-HK)
- **Free Limit:** 1,000,000 characters per month.
- **What counts as a "Character" for billing:**
    - The actual Cantonese text.
    - Spaces, newlines, and punctuation.
    - SSML tags like `<speak>`, `<voice>`, and `<break>`.
- **The "Free" Tag:** 
    - **`<mark>` tags are EXEMPT from billing.** 
    - Developers should use `<mark>` tags aggressively for character tracking without fear of increasing the bill.

## 2. Technical Payload Limits (The 5K Ceiling)
- **The Constraint:** A single API request to Google cannot exceed **5,000 bytes** in total input length.
- **The Conflict:** While `<mark>` tags are free for *billing*, they **do** count toward this 5,000-byte technical limit.
- **The Requirement:** 
    - The backend MUST implement a chunking strategy. 
    - If a user pastes a large document, split by **UTF-8 byte budget**, not char count.
    - Use a conservative target: **3,500-4,200 bytes per SSML chunk** to avoid boundary failures.
    - Chunk by sentence first, then clause, then hard split as a last resort.

## 2.1 Mark Density Reliability Policy
- **Default mode:** Per-character `<mark>` on all non-whitespace tokens.
- **Skip mode:** No marks for pure whitespace tokens.
- **Fallback mode (automatic):** If returned timepoints are sparse or missing for a chunk, re-synthesize that chunk once with reduced marks:
    - Keep marks on Han characters and sentence-ending punctuation only.
    - Keep token IDs stable so frontend mapping remains deterministic.
- **Last-resort behavior:** If fallback still fails, return a controlled error for that request with guidance to shorten input.

## 2.2 Input Size Guardrail (Product Scope)
- No file uploads are supported.
- Text is pasted directly into the reader.
- Enforce `MAX_INPUT_CHARS` (default **12,000** chars) per request.
- Return `413` with a clear message when exceeded.

## 3. Audio Regeneration (The "No-Double-Dip" Rule)
- **Constraint:** Never call the Google TTS API more than once for the same block of text in a single session.
- **Implementation:**
    - **Playback Speed:** MUST be handled via the browser's `audio.playbackRate`. **Do not** re-request audio from Google for different speeds.
    - **Voice Selection:** Changing the voice (Male vs. Female) **will** trigger a new billed request. UI should warn the user if they are switching voices on a very large text.

## 4. Local Resource Management (VPS)
- **Storage:** To prevent disk space overages on the $5 VPS, all generated MP3s must be stored in a `temp` directory with a **4-hour TTL (Time-To-Live)**.
- **CPU/RAM:** Use `pycantonese` for Jyutping. It is a local Python library and costs $0 to run. Do not use external APIs for romanization.
- **Hard cleanup caps (required):**
    - `MAX_TEMP_AUDIO_FILES=120`
    - `MAX_TEMP_AUDIO_BYTES=300MB`
    - Run cleanup before synthesis, after synthesis, and at startup.
    - If over cap, delete oldest files first until within limits.

## 5. Usage Monitoring
- **Requirement:** Every successful TTS call must be logged in the `usage_logs` SQLite table.
- **Admin Alert:** The Admin dashboard must display the current month's aggregate character count to ensure the 1M limit is not exceeded.

## 6. Budget Guardrails
- Add a soft warning at **80%** monthly usage.
- Add a hard warning at **95%** monthly usage.
- If monthly usage exceeds configured quota, disable new synthesis by default for non-admin users.

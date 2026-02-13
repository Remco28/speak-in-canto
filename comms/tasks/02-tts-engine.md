# Task 02: TTS Engine & SSML Mapping

## Objective
Convert raw Cantonese text into SSML with timepoint marks, call Google TTS, and handle the response metadata.

## Core Logic
1. **Text Chunking**: Handle strings > 5,000 chars by splitting on sentence boundaries.
2. **SSML Generation**: 
   - Wrap text in `<speak>` tags.
   - Insert `<mark name="c_{index}"/>` before each character.
3. **Google API Call**: 
   - Use `yue-HK` language code.
   - **Voice Selection**: Support a dropdown for available Neural2 voices (e.g., `yue-HK-Neural2-A`, `yue-HK-Neural2-B`).
   - Set `enable_time_pointing=True`.
4. **Response Packaging**:
   - Save Audio Content to `static/temp_audio/`.
   - Return a JSON object containing the `audio_url`, the `timepoints` array, and `jyutping` strings.
5. **Usage Tracking**: Increment the `usage_logs` table after every successful API call.

## Tasks
- [ ] Research the optimal "mark" density for performance.
- [ ] Implement the `SSMLBuilder` utility class with `pycantonese` integration.
- [ ] Implement the `GoogleTTSWrapper` service with voice selection support.
- [ ] Create a cleanup task for `static/temp_audio/`.

# Task 03: Frontend Reader & Sync Player

## Objective
Create a responsive web interface for reading text, displaying Jyutping, and playing audio with synchronized highlighting.

## Requirements
1. **Reader Interface**:
    - A large text area for inputting Cantonese text.
    - A "Read" button that triggers the TTS process.
    - A display area that renders characters with "ruby" text (Jyutping) above them.
2. **Sync Player**:
    - Use the HTML5 `<audio>` element.
    - Implement a `timeupdate` listener to highlight the corresponding `<span>` based on Google's timepoints.
    - **Click-to-Seek**: Clicking any character span updates `audio.currentTime` to the mark's timestamp.
3. **Controls**:
    - **Speed Slider**: Adjust `audio.playbackRate` between 0.5x and 2.0x.
    - **Voice Toggle**: Select between Male/Female Neural2 voices.
4. **Admin View**:
    - A simple table to see/add users.
    - A progress bar showing monthly character usage (queried from `usage_logs`).

## Tasks
- [ ] Build the layout using Bootstrap 5.
- [ ] Implement the `Reader` JS class to handle audio/text sync.
- [ ] Create the Admin usage dashboard.

# Dictionary Setup (No-AI)

This feature expects two local source files:
- `data/dictionaries/cc-cedict.u8`
- `data/dictionaries/cc-canto.u8`

## 1. Download source files
Download CC-CEDICT and CC-Canto from their official channels and save them somewhere on your machine.

Reference pages:
- https://cc-cedict.org/wiki/
- https://cantonese.org/

## 2. Copy and validate into project paths
Use the helper script:

```bash
.venv/bin/python scripts/prepare_dictionary_data.py \
  --cedict /path/to/your/cedict-file.u8 \
  --cccanto /path/to/your/cccanto-file.u8
```

What it does:
- Copies the files into `data/dictionaries/`
- Renames them to expected runtime names
- Parses both files and validates that each has a reasonable number of terms

## 3. Verify app env
In `.env` (or deployment env vars):

```env
DICTIONARY_ENABLED=true
DICTIONARY_CC_CEDICT_PATH=data/dictionaries/cc-cedict.u8
DICTIONARY_CC_CANTO_PATH=data/dictionaries/cc-canto.u8
MAX_DICTIONARY_INPUT_CHARS=12000
MAX_DICTIONARY_ALTERNATIVES=3
MAX_DICTIONARY_TERM_CHARS=64
```

## 4. Quick functional check
1. Start app and log in.
2. Paste Cantonese text and press `Read` once (to populate Reader tokens).
3. Switch Reader mode toggle to `Dictionary`.
4. Tap on a word/phrase in Reader.

Expected:
- Floating definition popover appears near clicked term.
- Alternatives appear under collapsed details when available.
- Term is spoken automatically using current voice mode/voice selection.
- If files are missing/invalid, API returns `503` and UI shows the error.

## 5. Deployment note (Coolify)
If dictionary files are not committed to Git, mount them into the container and point env vars to mounted paths, for example:

- `DICTIONARY_CC_CEDICT_PATH=/app/dictionaries/cc-cedict.u8`
- `DICTIONARY_CC_CANTO_PATH=/app/dictionaries/cc-canto.u8`

Then add persistent storage mount to `/app/dictionaries`.

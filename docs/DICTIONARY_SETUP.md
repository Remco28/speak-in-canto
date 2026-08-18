# Dictionary Setup (No-AI)

This feature expects two local source files:
- `data/dictionaries/cc-cedict.u8`
- `data/dictionaries/cc-canto.u8`

## 1. Download source files

### CC-CEDICT
Download the latest release from MDBG:
- Page: https://www.mdbg.net/chinese/dictionary?page=cc-cedict
- File: `cedict_1_0_ts_utf-8_mdbg.zip` (UTF-8, traditional + simplified)
- Extract `cedict_ts.u8` from the zip and use that as the `--cedict` input.

### CC-Canto
Download the latest CC-Canto data:
- Page: https://cantonese.org/download.html
  (the link "The latest version of CC-Canto can be downloaded here")
- File: `cccanto-webdist.txt` (CC-CEDICT format, with Jyutping readings in `{}`)

Both sources are CC BY-SA licensed; see `docs/DICTIONARY_DATA_LICENSES.md` for
the attribution record to fill in.

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
1. Start app (no login required).
2. Paste Cantonese text and press `Read` once (to populate Reader tokens).
3. Switch Reader mode toggle to `Dictionary`.
4. Tap on a word/phrase in Reader.

Expected:
- Floating definition popover appears near clicked term.
- Alternatives appear under collapsed details when available.
- Term is spoken automatically using current voice mode/voice selection.
- If files are missing/invalid, API returns `503` and UI shows the error.

## 5. Deployment notes
Dictionary files are git-ignored and must be copied into `data/dictionaries/`
on each machine (laptop and home server). Use `scripts/prepare_dictionary_data.py`
on each machine, or copy the prepared files from your laptop to the server.

If you place the files elsewhere, override the paths via:

- `DICTIONARY_CC_CEDICT_PATH=/absolute/path/to/cc-cedict.u8`
- `DICTIONARY_CC_CANTO_PATH=/absolute/path/to/cc-canto.u8`

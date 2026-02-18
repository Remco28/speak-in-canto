# Dictionary Data Licenses

This project's dictionary mode is designed for local, no-AI lookup and expects these data sources:

- CC-CEDICT
- CC-Canto

## Required Attribution and License Tracking
Before shipping dictionary data in production, maintain:

1. Source URL for each file
2. Retrieved date
3. Version or snapshot identifier
4. Full license text or official license link
5. Attribution text included in this file and user-facing legal docs (if needed)

## Source Pointers
- CC-CEDICT project wiki: https://cc-cedict.org/wiki/
- CC-Canto project site: https://cantonese.org/

## Attribution Record (Fill Before Release)
- CC-CEDICT source URL:
- CC-CEDICT retrieved date:
- CC-CEDICT version/snapshot:
- CC-CEDICT license:

- CC-Canto source URL:
- CC-Canto retrieved date:
- CC-Canto version/snapshot:
- CC-Canto license:

## Repository Policy
- Do not add third-party dictionary files without validating license terms.
- Keep raw source files in `data/dictionaries/`.
- If files are absent, dictionary mode remains non-fatal and returns `503` from `/api/dictionary/lookup`.

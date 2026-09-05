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

## Attribution Record
- CC-CEDICT source URL: https://www.mdbg.net/chinese/dictionary?page=cc-cedict
- CC-CEDICT retrieved date: 2026-08-18
- CC-CEDICT version/snapshot: latest release 2026-08-18 (124,871 entries)
- CC-CEDICT license: Creative Commons Attribution-ShareAlike 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)

- CC-Canto source URL: https://cantonese.org/download.html
- CC-Canto retrieved date: 2026-08-18
- CC-Canto version/snapshot: 2017-02-02
- CC-Canto license: Creative Commons Attribution-ShareAlike 3.0 (https://creativecommons.org/licenses/by-sa/3.0/)

## Repository Policy
- Do not add third-party dictionary files without validating license terms.
- Keep raw source files in `data/dictionaries/`.
- If files are absent, dictionary mode remains non-fatal and returns `503` from `/api/dictionary/lookup`.

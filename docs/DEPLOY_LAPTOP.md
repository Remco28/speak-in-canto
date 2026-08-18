# Deploying the Laptop Desktop App

Canto Reader runs as a native window on Ubuntu/Debian via pywebview
(GTK + WebKit2GTK). No Docker, no browser tab, no tray icon.

## Prerequisites
- Ubuntu/Debian laptop.
- Python 3.12+ (Ubuntu 24.04 ships 3.12; Ubuntu 22.04 needs deadsnakes PPA or pyenv).
- `sudo` access for `apt` package installs.

## One-time install

```bash
./scripts/install_laptop.sh
```

The script:
1. Ensures Python 3.12+ is available (installs via apt if missing).
2. Installs GTK/WebKit2GTK system dependencies. It auto-selects
   `gir1.2-webkit2-4.1` on Ubuntu 24.04+ and `gir1.2-webkit2-4.0` on 22.04.
3. Creates `.venv` and installs `requirements-desktop.txt`.
4. Creates `.env` from `.env.example` if missing.
5. Writes a `.desktop` entry to `~/.local/share/applications/canto-reader.desktop`
   with the app icon.

## Configure secrets

Edit `.env`:
- `OPENROUTER_API_KEY` — your OpenRouter API key.
- Google TTS credentials, one of:
  - `GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-sa.json` (copy the service-account
    JSON into `secrets/gcp-sa.json`), or
  - `GCP_SERVICE_ACCOUNT_JSON=<single-line JSON>`.

Without Google credentials, TTS calls fail while the dictionary and UI still work.

## Dictionary data (optional)

```bash
.venv/bin/python scripts/prepare_dictionary_data.py \
  --cedict /path/to/cc-cedict.u8 \
  --cccanto /path/to/cc-canto.u8
```

See `docs/DICTIONARY_SETUP.md`.

## Launch

- App menu: **Canto Reader**, or
- Terminal: `./scripts/canto-reader.sh`.

The process starts waitress on `http://127.0.0.1:8734`, opens a native window,
and exits cleanly when you close the window (or press Ctrl+C in the terminal).

## Update

Re-run the installer to pull in dependency changes; your `.env` is preserved.

```bash
./scripts/install_laptop.sh
```

## Troubleshooting
- **Window does not open:** confirm the WebKit package for your Ubuntu version is
  installed (`gir1.2-webkit2-4.1` on 24.04+, `gir1.2-webkit2-4.0` on 22.04).
- **TTS fails:** verify Google credentials in `.env` and that the service account
  has Text-to-Speech enabled.
- **Translation fails:** verify `OPENROUTER_API_KEY`; a free account is limited to
  a daily request count.
- **Port conflict:** change `PORT` in `.env` to another uncommon port.

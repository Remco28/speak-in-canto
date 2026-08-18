from __future__ import annotations

import os
import threading
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import webview
from waitress import serve

from app import app

HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "8734"))
URL = f"http://{HOST}:{PORT}"
ICON_PATH = str(Path(__file__).resolve().parent / "assets" / "canto-reader.svg")


def _wait_until_ready(timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/healthz", timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - poll until the server is up
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Canto Reader server did not become ready: {last_error}")


def main() -> None:
    # pywebview's GTK backend disables file downloads unless explicitly enabled.
    webview.settings["ALLOW_DOWNLOADS"] = True

    server_thread = threading.Thread(
        target=serve,
        kwargs={"app": app, "host": HOST, "port": PORT, "threads": 4},
        name="canto-reader-server",
        daemon=True,
    )
    server_thread.start()

    _wait_until_ready()

    webview.create_window("Canto Reader", URL, width=1100, height=800)
    webview.start(icon=ICON_PATH)


if __name__ == "__main__":
    main()

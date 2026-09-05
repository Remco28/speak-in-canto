from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import webview
from waitress import serve

from app import app


def _env_port() -> int:
    try:
        return int(os.getenv("PORT", "8734"))
    except ValueError:
        return 8734


HOST = "127.0.0.1"
PORT = _env_port()
URL = f"http://{HOST}:{PORT}"
PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = str(PROJECT_ROOT / "assets" / "canto-reader.png")
STORAGE_PATH = str(PROJECT_ROOT / "instance" / "webview_profile")


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


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def main() -> None:
    if _port_in_use(HOST, PORT):
        print(f"Canto Reader is already running on {URL}.", file=sys.stderr)
        return

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

    # Persist localStorage (voice pins/selection) across launches.
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    webview.create_window("Canto Reader", URL, width=1100, height=800)
    webview.start(icon=ICON_PATH, private_mode=False, storage_path=STORAGE_PATH)


if __name__ == "__main__":
    main()

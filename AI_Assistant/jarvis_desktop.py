"""Native desktop launcher for the JARVIS Neural Grid.

The full UI still talks to the local Python service, but users see a dedicated
desktop window rather than having to manage a browser tab and server process.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import webview


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
HOST = os.getenv("JARVIS_HOST", "localhost")
PORT = int(os.getenv("JARVIS_PORT", "7890"))
APP_URL = f"http://{HOST}:{PORT}"
READY_URL = f"{APP_URL}/health/ready"
UI_FILE = APP_DIR / "neural_grid_ui" / "index.html"


def _window_url() -> str:
    """Cache-bust UI code updates without clearing the user's local storage."""
    version = int(UI_FILE.stat().st_mtime) if UI_FILE.exists() else int(time.time())
    return f"{APP_URL}/?ui={version}"

_server_process: Optional[subprocess.Popen] = None
_log_handles = []


def _backend_python() -> str:
    """Select a Python runtime that has the JARVIS backend dependencies."""
    explicit = os.getenv("JARVIS_SERVER_PYTHON", "").strip()
    candidates = [explicit, sys.executable]

    if os.name == "nt" and shutil.which("py"):
        try:
            resolved = subprocess.check_output(
                ["py", "-3.11", "-c", "import sys; print(sys.executable)"],
                text=True,
                timeout=10,
            ).strip()
            candidates.append(resolved)
        except (OSError, subprocess.SubprocessError):
            pass

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen or not Path(candidate).is_file():
            continue
        seen.add(candidate)
        probe = subprocess.run(
            [
                candidate,
                "-c",
                "import groq, speech_recognition, sounddevice, edge_tts, pygame",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        if probe.returncode == 0:
            return candidate

    raise RuntimeError(
        "No compatible JARVIS backend Python found. Install project requirements under Python 3.11."
    )


def _server_ready(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(READY_URL, timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _start_server() -> bool:
    """Start the local service if needed; return whether this process owns it."""
    global _server_process
    if _server_ready():
        return False

    stdout = open(PROJECT_DIR / "jarvis-app.stdout.log", "a", encoding="utf-8")
    stderr = open(PROJECT_DIR / "jarvis-app.stderr.log", "a", encoding="utf-8")
    _log_handles.extend((stdout, stderr))
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    server_python = _backend_python()
    _server_process = subprocess.Popen(
        [server_python, "-u", "jarvis_grid_server.py"],
        cwd=APP_DIR,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )

    # Importing the AI stack and initializing audio can take 30+ seconds on a
    # cold Windows start, especially while antivirus scans native modules.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if _server_process.poll() is not None:
            _cleanup()
            raise RuntimeError("JARVIS service stopped during startup; check jarvis-app.stderr.log")
        if _server_ready():
            return True
        time.sleep(0.25)
    _cleanup()
    raise TimeoutError("JARVIS service did not become ready within 60 seconds")


def _cleanup() -> None:
    global _server_process
    if _server_process and _server_process.poll() is None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
    _server_process = None
    for handle in _log_handles:
        if not handle.closed:
            handle.close()
    _log_handles.clear()


def run() -> None:
    _start_server()
    atexit.register(_cleanup)
    webview.create_window(
        "JARVIS",
        _window_url(),
        width=1280,
        height=820,
        min_size=(900, 650),
        resizable=True,
        background_color="#f5f7fb",
    )
    webview.start(debug=False, private_mode=False)


if __name__ == "__main__":
    run()

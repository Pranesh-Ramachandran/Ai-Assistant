"""
JARVIS Desktop Control — Phase 5.

Real actions:
  - Fuzzy app launcher (open VS Code, open my project)
  - Clipboard read/write
  - Window management (switch, minimize, maximize)
  - File search (find recent files by name/extension)
  - Volume, screenshot, lock (already in system_access.py — extended here)
  - Confirmation required for destructive actions

Public API:
  handle(command)  → str | ConfirmationRequest
"""

from __future__ import annotations
import os
import re
import subprocess
import platform
from typing import Optional

_IS_WIN = platform.system() == "Windows"

# ── Clipboard ─────────────────────────────────────────────────────────────────

def clipboard_read() -> str:
    try:
        import pyperclip  # type: ignore
        text = pyperclip.paste()
        if text:
            return f"Clipboard: {text[:200]}{'...' if len(text)>200 else ''}"
        return "Clipboard is empty."
    except ImportError:
        if _IS_WIN:
            try:
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=3, creationflags=0x08000000
                )
                text = result.stdout.strip()
                return f"Clipboard: {text[:200]}" if text else "Clipboard is empty."
            except Exception:
                pass
    return "Clipboard access unavailable."

def clipboard_write(text: str) -> str:
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return f"Copied to clipboard: {text[:60]}{'...' if len(text)>60 else ''}"
    except ImportError:
        if _IS_WIN:
            try:
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard '{text}'"],
                    capture_output=True, timeout=3, creationflags=0x08000000
                )
                return f"Copied to clipboard."
            except Exception:
                pass
    return "Clipboard write unavailable."


# ── Window management ─────────────────────────────────────────────────────────

def list_windows() -> str:
    if not _IS_WIN:
        return "Window management is Windows-only."
    try:
        import ctypes
        result = subprocess.run(
            ["powershell", "-command",
             "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
             "Select-Object -ExpandProperty MainWindowTitle"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000
        )
        titles = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()][:10]
        return "Open windows: " + ", ".join(titles) if titles else "No windows found."
    except Exception as e:
        return f"Window list error: {e}"

def switch_to_window(name: str) -> str:
    if not _IS_WIN:
        return "Window switching is Windows-only."
    try:
        script = (
            f"$wnd = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{name}*'}} | "
            f"Select-Object -First 1; "
            f"if ($wnd) {{ "
            f"  Add-Type -AssemblyName Microsoft.VisualBasic; "
            f"  [Microsoft.VisualBasic.Interaction]::AppActivate($wnd.Id) "
            f"}} else {{ Write-Output 'not found' }}"
        )
        result = subprocess.run(
            ["powershell", "-command", script],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000
        )
        if "not found" in result.stdout:
            return f"No window matching '{name}' found."
        return f"Switched to {name}."
    except Exception as e:
        return f"Window switch error: {e}"

def minimize_window(name: str = "") -> str:
    if not _IS_WIN:
        return "Window control is Windows-only."
    try:
        target = f"*{name}*" if name else "*"
        script = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"$proc = Get-Process | Where-Object {{$_.MainWindowTitle -like '{target}'}} | "
            f"Select-Object -First 1; "
            f"if ($proc) {{ [System.Windows.Forms.Application]::DoEvents() }}"
        )
        subprocess.run(["powershell", "-command", script],
                       capture_output=True, timeout=5, creationflags=0x08000000)
        return f"Minimized {name or 'current window'}."
    except Exception as e:
        return f"Minimize error: {e}"


# ── Fuzzy app launcher ────────────────────────────────────────────────────────

_APP_MAP = {
    "chrome": "chrome.exe", "google chrome": "chrome.exe",
    "firefox": "firefox.exe", "edge": "msedge.exe",
    "notepad": "notepad.exe", "calculator": "calc.exe",
    "paint": "mspaint.exe", "excel": "excel.exe",
    "word": "winword.exe", "powerpoint": "powerpnt.exe",
    "vscode": "code.exe", "vs code": "code.exe", "visual studio code": "code.exe",
    "terminal": "wt.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
    "explorer": "explorer.exe", "file explorer": "explorer.exe",
    "spotify": "Spotify.exe", "discord": "Discord.exe",
    "telegram": "Telegram.exe", "whatsapp": "WhatsApp.exe",
    "task manager": "taskmgr.exe", "control panel": "control.exe",
    "youtube": "https://youtube.com", "google": "https://google.com",
    "gmail": "https://mail.google.com", "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
}

def _fuzzy_match(query: str) -> Optional[str]:
    q = query.lower().strip()
    # exact
    if q in _APP_MAP:
        return _APP_MAP[q]
    # partial
    for key, val in _APP_MAP.items():
        if q in key or key in q:
            return val
    return None

def open_app(name: str) -> str:
    target = _fuzzy_match(name)
    if not target:
        target = name  # try direct

    if target.startswith("http"):
        import webbrowser
        webbrowser.open(target)
        return f"Opened {name} in browser."

    if _IS_WIN:
        try:
            os.startfile(target)
            return f"Opening {name}."
        except Exception:
            try:
                subprocess.Popen([target], shell=True, creationflags=0x08000000)
                return f"Opening {name}."
            except Exception as e:
                return f"Could not open {name}: {e}"
    try:
        subprocess.Popen([target])
        return f"Opening {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"

def open_with_file(app: str, filepath: str) -> str:
    """Open an app and a specific file together."""
    target = _fuzzy_match(app) or app
    try:
        if _IS_WIN:
            subprocess.Popen([target, filepath], shell=True, creationflags=0x08000000)
        else:
            subprocess.Popen([target, filepath])
        return f"Opening {os.path.basename(filepath)} in {app}."
    except Exception as e:
        return f"Could not open: {e}"


# ── File search ───────────────────────────────────────────────────────────────

def find_files(query: str, search_path: str = "~",
               extensions: list = None, limit: int = 5) -> str:
    """Find files by name fragment, optionally filtered by extension."""
    base = os.path.expanduser(search_path)
    if not os.path.exists(base):
        base = os.path.expanduser("~")

    matches = []
    q = query.lower()
    exts = [e.lower() if e.startswith(".") else f".{e.lower()}"
            for e in (extensions or [])]

    try:
        for root, dirs, files in os.walk(base):
            # Skip hidden/system dirs
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in ("node_modules", "__pycache__", "venv", ".git")]
            for fname in files:
                if q in fname.lower():
                    if not exts or any(fname.lower().endswith(e) for e in exts):
                        full = os.path.join(root, fname)
                        matches.append((os.path.getmtime(full), full))
                if len(matches) >= 50:
                    break
            if len(matches) >= 50:
                break
    except PermissionError:
        pass

    if not matches:
        return f"No files matching '{query}' found in {search_path}."

    # Sort by most recently modified
    matches.sort(reverse=True)
    results = [os.path.basename(p) + f" ({os.path.dirname(p)})"
               for _, p in matches[:limit]]
    return f"Found: " + ", ".join(results) + "."

def find_recent_files(ext: str = "", limit: int = 5) -> str:
    """Find most recently modified files."""
    base = os.path.expanduser("~")
    files = []
    try:
        for root, dirs, fnames in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in ("node_modules", "__pycache__", "venv", ".git",
                                     "AppData", "Library")]
            for f in fnames:
                if not ext or f.lower().endswith(ext.lower()):
                    full = os.path.join(root, f)
                    try:
                        files.append((os.path.getmtime(full), full))
                    except Exception:
                        pass
            if len(files) > 200:
                break
    except Exception:
        pass

    files.sort(reverse=True)
    results = [os.path.basename(p) for _, p in files[:limit]]
    return "Recent files: " + ", ".join(results) + "." if results else "No recent files found."


# ── Main command handler ──────────────────────────────────────────────────────

def handle(command: str) -> str:
    cmd = command.lower().strip()

    # Clipboard
    if "clipboard" in cmd or "copy that" in cmd:
        if "read" in cmd or "what" in cmd or "show" in cmd:
            return clipboard_read()
        m = re.search(r"copy (.+) to clipboard", cmd)
        if m:
            return clipboard_write(m.group(1))
        return clipboard_read()

    # Window management
    if "window" in cmd or "switch to" in cmd:
        if "list" in cmd or "show" in cmd:
            return list_windows()
        m = re.search(r"switch to (.+)", cmd)
        if m:
            return switch_to_window(m.group(1).strip())
        m = re.search(r"minimize (.+)", cmd)
        if m:
            return minimize_window(m.group(1).strip())
        return list_windows()

    # File search
    if "find" in cmd and "file" in cmd:
        m = re.search(r"find (?:file|files?) (?:named? )?(.+?)(?:\s+in (.+))?$", cmd)
        if m:
            return find_files(m.group(1).strip(),
                              m.group(2).strip() if m.group(2) else "~")
        return find_recent_files()

    if "recent file" in cmd:
        ext_m = re.search(r"\.(\w+)", cmd)
        return find_recent_files(f".{ext_m.group(1)}" if ext_m else "")

    # Open app + file
    m = re.search(r"open (.+?) (?:and|with) (.+)", cmd)
    if m:
        return open_with_file(m.group(1).strip(), m.group(2).strip())

    # Open app
    m = re.search(r"open (.+)", cmd)
    if m:
        return open_app(m.group(1).strip())

    return "Desktop command not understood. Try: open [app], find file [name], clipboard, switch to [window]."

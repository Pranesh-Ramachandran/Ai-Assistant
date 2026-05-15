"""
JARVIS System Access — Full Windows + Android system control.
Exposes safe, AI-callable tools for system interaction.
Sensitive ops (delete, send SMS) require confirmation flag.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any, Optional

_IS_WINDOWS = platform.system() == "Windows"
_IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_ROOT" in os.environ

# ─── Optional imports ─────────────────────────────────────────────────────────
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import ctypes
    _CTYPES = True
except ImportError:
    _CTYPES = False


# ═══════════════════════════════════════════════════════════════════════════════
# System Info
# ═══════════════════════════════════════════════════════════════════════════════

def get_battery() -> str:
    """Return battery percentage and charging status."""
    if _PSUTIL:
        try:
            batt = psutil.sensors_battery()
            if batt:
                status = "charging" if batt.power_plugged else "discharging"
                return f"Battery is at {int(batt.percent)}%, {status}."
        except Exception:
            pass
    if _IS_ANDROID:
        try:
            from android_access import get_battery_info  # type:ignore
            return get_battery_info()
        except Exception:
            pass
    return "Battery info unavailable."


def get_cpu_usage() -> str:
    """Return current CPU usage percentage."""
    if _PSUTIL:
        try:
            pct = psutil.cpu_percent(interval=0.5)
            return f"CPU usage: {pct:.1f}%"
        except Exception:
            pass
    return "CPU info unavailable."


def get_ram_usage() -> str:
    """Return RAM usage."""
    if _PSUTIL:
        try:
            mem = psutil.virtual_memory()
            used_gb  = mem.used  / 1e9
            total_gb = mem.total / 1e9
            return f"RAM: {used_gb:.1f} GB used of {total_gb:.1f} GB ({mem.percent:.0f}%)"
        except Exception:
            pass
    return "RAM info unavailable."


def get_disk_usage(path: str = "/") -> str:
    """Return disk usage for a path."""
    if _IS_WINDOWS:
        path = "C:\\"
    if _PSUTIL:
        try:
            disk = psutil.disk_usage(path)
            free_gb  = disk.free  / 1e9
            total_gb = disk.total / 1e9
            return f"Disk: {free_gb:.1f} GB free of {total_gb:.1f} GB ({disk.percent:.0f}% used)"
        except Exception:
            pass
    return "Disk info unavailable."


def get_system_info() -> str:
    """Return a summary of system stats."""
    parts = []
    try:
        parts.append(get_battery())
        parts.append(get_cpu_usage())
        parts.append(get_ram_usage())
        parts.append(get_disk_usage())
    except Exception:
        pass
    if not parts:
        return "System info unavailable."
    return " | ".join(p for p in parts if "unavailable" not in p)


def get_wifi_info() -> str:
    """Return current WiFi SSID (Windows)."""
    if _IS_WINDOWS:
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=5, creationflags=0x08000000
            )
            for line in result.stdout.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":", 1)[-1].strip()
                    if ssid:
                        return f"Connected to WiFi: {ssid}"
        except Exception:
            pass
    return "WiFi info unavailable."


# ═══════════════════════════════════════════════════════════════════════════════
# Volume Control
# ═══════════════════════════════════════════════════════════════════════════════

def set_volume(level: int) -> str:
    """Set system volume (0-100). Windows only."""
    level = max(0, min(100, int(level)))
    if _IS_WINDOWS:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL          # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return f"Volume set to {level}%."
        except Exception:
            # Fallback: nircmd
            try:
                vol_nircmd = int(level * 65535 / 100)
                subprocess.run(["nircmd", "setsysvolume", str(vol_nircmd)],
                               capture_output=True, timeout=3)
                return f"Volume set to {level}%."
            except Exception:
                pass
    return "Volume control not available on this system."


def get_volume() -> str:
    """Get current system volume."""
    if _IS_WINDOWS:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            pct = int(volume.GetMasterVolumeLevelScalar() * 100)
            return f"Current volume: {pct}%."
        except Exception:
            pass
    return "Volume info unavailable."


# ═══════════════════════════════════════════════════════════════════════════════
# App Control
# ═══════════════════════════════════════════════════════════════════════════════

# Known app name → Windows executable mapping
_APP_MAP: dict[str, str] = {
    "chrome":      "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox":     "firefox.exe",
    "notepad":     "notepad.exe",
    "calculator":  "calc.exe",
    "paint":       "mspaint.exe",
    "excel":       "excel.exe",
    "word":        "winword.exe",
    "powerpoint":  "powerpnt.exe",
    "vscode":      "code.exe",
    "vs code":     "code.exe",
    "cmd":         "cmd.exe",
    "terminal":    "wt.exe",
    "explorer":    "explorer.exe",
    "spotify":    "Spotify.exe",
    "discord":    "Discord.exe",
    "telegram":   "Telegram.exe",
    "whatsapp":   "WhatsApp.exe",
    "youtube":    "https://youtube.com",
    "google":     "https://google.com",
    "gmail":      "https://mail.google.com",
}

def open_app(name: str) -> str:
    """Open an application by name."""
    key = name.lower().strip()
    exe = _APP_MAP.get(key, "")

    if not exe:
        # Try direct open
        exe = key

    if exe.startswith("http"):
        try:
            import webbrowser
            webbrowser.open(exe)
            return f"Opened {name} in your browser."
        except Exception as e:
            return f"Could not open {name}: {e}"

    if _IS_WINDOWS:
        try:
            os.startfile(exe)  # type: ignore[attr-defined]
            return f"Opening {name}."
        except Exception:
            try:
                subprocess.Popen([exe], shell=True, creationflags=0x08000000)
                return f"Opening {name}."
            except Exception as e:
                return f"Could not open {name}: {e}"

    try:
        subprocess.Popen([exe])
        return f"Opening {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"


def list_running_apps() -> str:
    """List currently running applications."""
    if _PSUTIL:
        try:
            apps = set()
            for proc in psutil.process_iter(["name"]):
                name = proc.info.get("name", "")
                if name and not name.lower().endswith(("svchost.exe", "system", "registry")):
                    apps.add(name)
            sorted_apps = sorted(apps)[:20]
            return "Running: " + ", ".join(sorted_apps)
        except Exception:
            pass
    return "App list unavailable."


def take_screenshot(savepath: str = "") -> str:
    """Take a screenshot and save it."""
    try:
        import datetime
        if not savepath:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            savepath = os.path.join(desktop, f"jarvis_screenshot_{ts}.png")

        try:
            import PIL.ImageGrab  # type: ignore
            img = PIL.ImageGrab.grab()
            img.save(savepath)
            return f"Screenshot saved to {savepath}."
        except ImportError:
            pass

        if _IS_WINDOWS:
            subprocess.run(
                ["powershell", "-command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"[System.Windows.Forms.Screen]::PrimaryScreen | "
                 f"ForEach-Object {{ $img = [System.Drawing.Bitmap]::new($_.Bounds.Width, $_.Bounds.Height); "
                 f"[System.Windows.Forms.Screen]::PrimaryScreen }}; "
                 f"[System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}')"],
                capture_output=True, timeout=5
            )
            return "Screenshot captured (check clipboard)."

    except Exception as e:
        return f"Screenshot failed: {e}"
    return "Screenshot unavailable."


def lock_screen() -> str:
    """Lock the screen."""
    if _IS_WINDOWS:
        try:
            ctypes.windll.user32.LockWorkStation()  # type: ignore
            return "Screen locked."
        except Exception:
            pass
    return "Screen lock unavailable."


# ═══════════════════════════════════════════════════════════════════════════════
# File System
# ═══════════════════════════════════════════════════════════════════════════════

def list_files(path: str = "~") -> str:
    """List files in a directory."""
    try:
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return f"Path not found: {path}"
        items = os.listdir(expanded)
        dirs  = [f + "/" for f in items if os.path.isdir(os.path.join(expanded, f))]
        files = [f for f in items if os.path.isfile(os.path.join(expanded, f))]
        result = dirs[:10] + files[:10]
        return f"Contents of {path}: " + ", ".join(result[:20])
    except PermissionError:
        return f"Permission denied to access {path}."
    except Exception as e:
        return f"Could not list {path}: {e}"


def open_file(path: str) -> str:
    """Open a file with its default application."""
    try:
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return f"File not found: {path}"
        if _IS_WINDOWS:
            os.startfile(expanded)  # type: ignore
        else:
            subprocess.Popen(["xdg-open", expanded])
        return f"Opened {os.path.basename(path)}."
    except Exception as e:
        return f"Could not open {path}: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Notifications (Windows toast)
# ═══════════════════════════════════════════════════════════════════════════════

def send_notification(title: str, body: str) -> str:
    """Send a desktop notification."""
    if _IS_WINDOWS:
        try:
            from win10toast import ToastNotifier  # type: ignore
            toaster = ToastNotifier()
            toaster.show_toast(title, body, duration=5, threaded=True)
            return f"Notification sent: {title}"
        except ImportError:
            try:
                # PowerShell toast fallback
                script = (
                    f"[Windows.UI.Notifications.ToastNotificationManager,"
                    f"Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                    f"$t=[Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
                    f"$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
                    f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('{title}'))|Out-Null;"
                    f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{body}'))|Out-Null;"
                    f"$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                    f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('JARVIS').Show($n)"
                )
                subprocess.run(["powershell", "-command", script],
                               capture_output=True, timeout=5, creationflags=0x08000000)
                return f"Notification sent: {title}"
            except Exception:
                pass
    return "Notifications unavailable."


# ═══════════════════════════════════════════════════════════════════════════════
# Tool registry for AI brain
# ═══════════════════════════════════════════════════════════════════════════════

TOOLS = {
    "get_battery":       get_battery,
    "get_system_info":   get_system_info,
    "get_wifi_info":     get_wifi_info,
    "get_cpu_usage":     get_cpu_usage,
    "get_ram_usage":     get_ram_usage,
    "get_disk_usage":    get_disk_usage,
    "open_app":          open_app,
    "list_running_apps": list_running_apps,
    "set_volume":        set_volume,
    "get_volume":        get_volume,
    "take_screenshot":   take_screenshot,
    "lock_screen":       lock_screen,
    "list_files":        list_files,
    "open_file":         open_file,
    "send_notification": send_notification,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_battery",
            "description": "Get the device battery percentage and charging status",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get system stats: CPU, RAM, disk, battery summary",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wifi_info",
            "description": "Get the current WiFi network name and connection status",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application by name (e.g. Chrome, Spotify, Notepad)",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Application name"}},
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system volume level (0-100)",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer", "description": "Volume 0-100"}},
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot and save it to the desktop",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path (default: home)"}},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Open a file with its default application",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path to open"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the computer screen",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_apps",
            "description": "List currently running applications and processes",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


def execute_tool(name: str, args: dict) -> str:
    """Execute a system tool by name with given arguments."""
    fn = TOOLS.get(name)
    if fn is None:
        return f"Unknown system tool: {name}"
    try:
        return fn(**args) if args else fn()
    except TypeError:
        return fn()
    except Exception as e:
        return f"Tool '{name}' error: {e}"


if __name__ == "__main__":
    print("=== JARVIS System Access Test ===")
    print(get_battery())
    print(get_cpu_usage())
    print(get_ram_usage())
    print(get_disk_usage())
    print(get_wifi_info())
    print(list_files("~"))

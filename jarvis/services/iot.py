"""
JARVIS IoT Service — local smart home device control.
"""

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_DEVICE_FILE = str(Path(__file__).resolve().parent.parent.parent / "data" / "devices.json")
_BULB_FILE   = str(Path(__file__).resolve().parent.parent.parent / "data" / "smart_bulbs.json")

_COLOR_MAP = {
    "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
    "yellow": "#FFFF00", "purple": "#800080", "orange": "#FFA500",
    "pink": "#FFC0CB", "white": "#FFFFFF", "cyan": "#00FFFF", "magenta": "#FF00FF",
}

# ── File cache — avoids re-reading disk on every command ──────────────────────
_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 30.0  # seconds
_cache_lock = threading.Lock()


def _load_json(path: str) -> dict:
    import time
    with _cache_lock:
        entry = _cache.get(path)
        if entry and (time.time() - entry[1]) < _CACHE_TTL:
            return entry[0]
    data: dict = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load %s: %s", path, e)
    import time as _t
    with _cache_lock:
        _cache[path] = (data, _t.time())
    return data


def _invalidate_cache(path: str) -> None:
    with _cache_lock:
        _cache.pop(path, None)


def _save_json(path: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _invalidate_cache(path)
    except OSError as e:
        logger.error("Could not save %s: %s", path, e)


def _send_local(ip: str, action: str) -> bool:
    for endpoint in (f"http://{ip}/api/v1/power/{action}", f"http://{ip}/{action}"):
        try:
            r = requests.get(endpoint, timeout=3)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            continue
    return False


class IoTAssistant:
    def handle_iot_command(self, command: str) -> str:
        cmd = (command or "").lower()

        if any(w in cmd for w in ("bulb", "light", "lamp")):
            return self._handle_bulb(cmd)
        if any(c in cmd for c in _COLOR_MAP):
            return self._handle_bulb(cmd)
        if any(w in cmd for w in ("bright", "dim", "brightness", "%")):
            return self._handle_bulb(cmd)

        return self._handle_generic(cmd)

    def _handle_bulb(self, cmd: str) -> str:
        bulbs = _load_json(_BULB_FILE)
        matched = next((name for name in bulbs if name in cmd), None)

        if not matched:
            return "I couldn't identify which bulb you want to control."

        cfg = bulbs[matched]
        ip = cfg.get("ip")

        if "off" in cmd:
            if ip:
                _send_local(ip, "off")
            return f"{matched.title()} turned off."

        if "on" in cmd:
            if ip:
                _send_local(ip, "on")
            return f"{matched.title()} turned on."

        for color in _COLOR_MAP:
            if color in cmd:
                if ip:
                    try:
                        hex_c = _COLOR_MAP[color][1:]
                        requests.get(f"http://{ip}/color?hex={hex_c}", timeout=3)
                    except requests.RequestException:
                        pass
                return f"{matched.title()} color set to {color}."

        m = re.search(r"(\d+)%", cmd)
        if m:
            pct = int(m.group(1))
            if ip:
                try:
                    requests.get(f"http://{ip}/brightness?level={pct}", timeout=3)
                except requests.RequestException:
                    pass
            return f"{matched.title()} brightness set to {pct}%."

        return f"Please specify on, off, a color, or brightness for {matched}."

    def _handle_generic(self, cmd: str) -> str:
        devices = _load_json(_DEVICE_FILE)
        matched = next((kw for kw in devices if kw in cmd), None)
        if not matched:
            return "No matching device found."

        action = "ON" if "on" in cmd else ("OFF" if "off" in cmd else None)
        if not action:
            return "Please say 'on' or 'off' in your command."

        ip = devices[matched].get("ip", "")
        if ip:
            _send_local(ip, action.lower())
        return f"{matched.title()} turned {action}."

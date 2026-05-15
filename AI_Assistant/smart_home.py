"""
JARVIS Smart Home — Phase 4.

Supports:
  - Local HTTP devices (ESP8266/Tasmota, Shelly, generic REST)
  - Tuya local protocol (tinytuya, optional)
  - Scenes: movie_mode, sleep_mode, work_mode, morning_mode
  - Schedules: stored in .jarvis_memory.json, checked by alarm thread
  - Device registry: devices.json

Public API:
  control(command)          → str  (voice command handler)
  set_scene(name)           → str
  add_device(name, ip, type)→ str
  list_devices()            → str
  get_status()              → dict
"""

from __future__ import annotations
import json
import os
import re
import threading
import time
from typing import Optional

_BASE        = os.path.dirname(os.path.abspath(__file__))
_DEVICE_FILE = os.path.join(_BASE, "smart_devices.json")

# ── Device registry ───────────────────────────────────────────────────────────

def _load_devices() -> dict:
    try:
        if os.path.exists(_DEVICE_FILE):
            with open(_DEVICE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_devices(d: dict):
    with open(_DEVICE_FILE, "w") as f:
        json.dump(d, f, indent=2)

def add_device(name: str, ip: str, device_type: str = "tasmota",
               tuya_id: str = "", tuya_key: str = "") -> str:
    devs = _load_devices()
    devs[name.lower()] = {
        "ip": ip, "type": device_type,
        "tuya_id": tuya_id, "tuya_key": tuya_key,
        "state": "unknown"
    }
    _save_devices(devs)
    return f"Device '{name}' added ({device_type} at {ip})."

def remove_device(name: str) -> str:
    devs = _load_devices()
    if name.lower() in devs:
        del devs[name.lower()]
        _save_devices(devs)
        return f"Device '{name}' removed."
    return f"Device '{name}' not found."

def list_devices() -> str:
    devs = _load_devices()
    if not devs:
        return "No smart devices configured. Say 'add device' to set one up."
    lines = [f"{n} ({d['type']} @ {d['ip']}) — {d.get('state','?')}"
             for n, d in devs.items()]
    return "Devices: " + ", ".join(lines) + "."


# ── Device control ────────────────────────────────────────────────────────────

# ── Home Assistant bridge ────────────────────────────────────────────────────

def _hass_url() -> str:
    return os.getenv("HASS_URL", "http://homeassistant.local:8123")

def _hass_token() -> str:
    return os.getenv("HASS_TOKEN", "")

def _send_hass(entity_id: str, action: str, brightness: int = None,
               color: str = None) -> bool:
    """Call Home Assistant REST API to control any entity."""
    token = _hass_token()
    if not token:
        return False
    import requests
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    domain = entity_id.split(".")[0]  # light, switch, fan, etc.
    if action == "off":
        service = "turn_off"
        body: dict = {"entity_id": entity_id}
    else:
        service = "turn_on"
        body = {"entity_id": entity_id}
        if brightness is not None:
            body["brightness_pct"] = brightness
        if color:
            # convert #RRGGBB to [r, g, b]
            h = color.lstrip("#")
            body["rgb_color"] = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    try:
        url = f"{_hass_url()}/api/services/{domain}/{service}"
        r = requests.post(url, json=body, headers=headers, timeout=2)
        return r.status_code in (200, 201)
    except Exception:
        return False


def _send_tasmota(ip: str, action: str) -> bool:
    """Tasmota/Shelly/generic REST control."""
    import requests
    cmd = "Power%20On" if action == "on" else "Power%20Off"
    urls = [
        f"http://{ip}/cm?cmnd={cmd}",          # Tasmota
        f"http://{ip}/relay/0?turn={action}",   # Shelly
        f"http://{ip}/{action}",                # Generic
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            continue
    return False

def _send_tasmota_brightness(ip: str, pct: int) -> bool:
    import requests
    try:
        r = requests.get(f"http://{ip}/cm?cmnd=Dimmer%20{pct}", timeout=1)
        return r.status_code == 200
    except Exception:
        return False

def _send_tasmota_color(ip: str, hex_color: str) -> bool:
    import requests
    try:
        r = requests.get(f"http://{ip}/cm?cmnd=Color%20{hex_color.lstrip('#')}", timeout=1)
        return r.status_code == 200
    except Exception:
        return False

def _send_tuya(device_id: str, device_key: str, action: str) -> bool:
    try:
        import tinytuya  # type: ignore
        d = tinytuya.OutletDevice(device_id, "auto", device_key)
        d.set_version(3.3)
        if action == "on":
            d.turn_on()
        else:
            d.turn_off()
        return True
    except Exception:
        return False

def _control_device(name: str, action: str, brightness: int = None,
                    color: str = None) -> str:
    devs = _load_devices()
    dev  = devs.get(name.lower())
    if not dev:
        return f"Device '{name}' not found. Say 'add device {name}' to set it up."

    ip   = dev.get("ip", "")
    dtype = dev.get("type", "tasmota")
    ok   = False

    if dtype in ("tasmota", "shelly", "generic"):
        if color:
            ok = _send_tasmota_color(ip, color)
        elif brightness is not None:
            ok = _send_tasmota_brightness(ip, brightness)
        else:
            ok = _send_tasmota(ip, action)
    elif dtype == "tuya":
        ok = _send_tuya(dev.get("tuya_id",""), dev.get("tuya_key",""), action)
    elif dtype == "hass":
        entity = dev.get("hass_entity") or f"light.{name.lower().replace(' ','_')}"
        ok = _send_hass(entity, action, brightness, color)

    # Update state
    devs[name.lower()]["state"] = action if ok else devs[name.lower()]["state"]
    _save_devices(devs)

    if ok:
        if color:   return f"{name.title()} color set to {color}."
        if brightness is not None: return f"{name.title()} brightness set to {brightness}%."
        return f"{name.title()} turned {action}."
    return f"Sent {action} to {name.title()} (no confirmation from device)."


# ── Scenes ────────────────────────────────────────────────────────────────────

_SCENES = {
    "movie":   [("light", "dim", 20, None), ("tv", "on", None, None)],
    "sleep":   [("light", "off", None, None), ("fan", "on", None, None)],
    "work":    [("light", "on", 80, None), ("fan", "on", None, None)],
    "morning": [("light", "on", 100, None), ("fan", "on", None, None)],
    "relax":   [("light", "on", 40, "#FF8C00"), ("fan", "on", None, None)],
}

def set_scene(name: str) -> str:
    scene = _SCENES.get(name.lower())
    if not scene:
        available = ", ".join(_SCENES.keys())
        return f"Unknown scene '{name}'. Available: {available}."

    results = []
    for device, action, brightness, color in scene:
        r = _control_device(device, action, brightness, color)
        results.append(r)

    return f"{name.title()} mode activated. " + " ".join(results)


# ── Voice command parser ──────────────────────────────────────────────────────

_COLOR_MAP = {
    "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
    "yellow": "#FFFF00", "purple": "#800080", "orange": "#FFA500",
    "pink": "#FFC0CB", "white": "#FFFFFF", "warm white": "#FFE4B5",
    "cyan": "#00FFFF", "magenta": "#FF00FF",
}

def control(command: str) -> str:
    """Parse and execute a voice command for smart home control."""
    cmd = command.lower().strip()

    # Scene detection
    for scene in _SCENES:
        if scene in cmd and ("mode" in cmd or "scene" in cmd or "activate" in cmd):
            return set_scene(scene)

    # List devices
    if "list" in cmd and "device" in cmd:
        return list_devices()

    # Add device: "add device bedroom light ip 192.168.1.100"
    m = re.search(r"add device (.+?) (?:at |ip )?(\d+\.\d+\.\d+\.\d+)", cmd)
    if m:
        return add_device(m.group(1).strip(), m.group(2).strip())

    # Find device name in command
    devs = _load_devices()
    matched = None
    for dname in devs:
        if dname in cmd:
            matched = dname
            break

    # Fallback: generic keywords
    if not matched:
        for kw in ("light", "fan", "bulb", "lamp", "ac", "tv", "plug"):
            if kw in cmd:
                matched = kw
                break

    if not matched:
        return "Which device? Say the device name or add one first."

    # Color
    for color_name, hex_val in _COLOR_MAP.items():
        if color_name in cmd:
            return _control_device(matched, "on", color=hex_val)

    # Brightness
    pct_m = re.search(r"(\d+)\s*%", cmd)
    if pct_m:
        return _control_device(matched, "on", brightness=int(pct_m.group(1)))
    if "dim" in cmd or "low" in cmd:
        return _control_device(matched, "on", brightness=20)
    if "bright" in cmd or "full" in cmd or "max" in cmd:
        return _control_device(matched, "on", brightness=100)
    if "half" in cmd or "medium" in cmd:
        return _control_device(matched, "on", brightness=50)

    # On/Off
    if "off" in cmd:
        return _control_device(matched, "off")
    if "on" in cmd or "turn" in cmd or "switch" in cmd:
        return _control_device(matched, "on")

    return f"What should I do with {matched}? Say on, off, dim, or a color."


def get_status() -> dict:
    devs = _load_devices()
    return {
        "device_count": len(devs),
        "devices": {n: d.get("state", "unknown") for n, d in devs.items()},
        "scenes": list(_SCENES.keys()),
    }


# Global shim for iot_assistant backward compat
class _IoTShim:
    def handle_iot_command(self, cmd): return control(cmd)
    def list_devices(self): return list_devices()

iot = _IoTShim()

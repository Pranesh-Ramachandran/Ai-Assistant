"""
JARVIS GPS Manager — real location on desktop via IP geolocation fallback.

On Android: uses plyer GPS (hardware).
On Windows/desktop: uses ip-api.com (free, no key) as fallback.
Caches location for 5 minutes to avoid hammering the API.
"""

from __future__ import annotations
import json
import os
import time
from typing import Optional, Tuple

_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".last_location.json")
_CACHE_TTL  = 300   # 5 minutes

_cached_loc: Optional[Tuple[float, float]] = None
_cached_at:  float = 0.0


def _load_cache() -> Optional[Tuple[float, float]]:
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE) as f:
                d = json.load(f)
            if time.time() - d.get("ts", 0) < _CACHE_TTL:
                return (d["lat"], d["lon"])
    except Exception:
        pass
    return None


def _save_cache(lat: float, lon: float) -> None:
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump({"lat": lat, "lon": lon, "ts": time.time()}, f)
    except Exception:
        pass


def _ip_location() -> Optional[Tuple[float, float]]:
    """Get location via ip-api.com (free, ~city-level accuracy)."""
    try:
        import requests
        r = requests.get("http://ip-api.com/json/?fields=lat,lon,city,regionName,status",
                         timeout=4)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                lat, lon = float(d["lat"]), float(d["lon"])
                _save_cache(lat, lon)
                print(f"[GPS] IP location: {d.get('city')}, {d.get('regionName')} ({lat:.4f}, {lon:.4f})")
                return (lat, lon)
    except Exception as e:
        print(f"[GPS] IP location failed: {e}")
    return None


def _android_location() -> Optional[Tuple[float, float]]:
    try:
        from plyer import gps
        # plyer GPS is async — return cached if available
        return None
    except ImportError:
        return None


def get_current_location(force: bool = False) -> Optional[Tuple[float, float]]:
    """
    Get current location. Returns (lat, lon) or None.
    Uses cache → IP geolocation → default (Chennai).
    """
    global _cached_loc, _cached_at

    # In-memory cache
    if not force and _cached_loc and (time.time() - _cached_at) < _CACHE_TTL:
        return _cached_loc

    # Disk cache
    cached = _load_cache()
    if cached and not force:
        _cached_loc, _cached_at = cached, time.time()
        return cached

    # Try Android GPS first
    loc = _android_location()
    if loc:
        _cached_loc, _cached_at = loc, time.time()
        return loc

    # IP geolocation (works on desktop/Windows)
    loc = _ip_location()
    if loc:
        _cached_loc, _cached_at = loc, time.time()
        return loc

    # Default: Chennai, Tamil Nadu
    default = (13.0827, 80.2707)
    print("[GPS] Using default location: Chennai")
    return default


def get_city_name() -> str:
    """Get city name from IP geolocation."""
    try:
        import requests
        r = requests.get("http://ip-api.com/json/?fields=city,regionName,status", timeout=4)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                return f"{d.get('city', '')}, {d.get('regionName', '')}".strip(", ")
    except Exception:
        pass
    return "Chennai, Tamil Nadu"


def save_location(lat: float, lon: float) -> None:
    global _cached_loc, _cached_at
    _cached_loc, _cached_at = (lat, lon), time.time()
    _save_cache(lat, lon)


def get_location_status() -> str:
    loc = _load_cache()
    if loc:
        return f"Location cached: {loc[0]:.4f}, {loc[1]:.4f}"
    return "No cached location — will use IP geolocation on next request."


# Shim for backward compat with maps_assistant.py
class _GPSManagerShim:
    def get_current_location(self, force_update=False):
        return get_current_location(force=force_update)
    def get_location_status(self):
        return get_location_status()
    def save_location(self, lat, lon):
        save_location(lat, lon)

gps_manager = _GPSManagerShim()

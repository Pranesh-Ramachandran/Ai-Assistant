"""
Android camera capture for JARVIS vision.

Tier:  LOCAL — no cloud, no API key.
Used only when running on Android (is_android() == True).

Two strategies, tried in order:
  1. plyer.camera  — takes a photo to a temp file, reads it back
  2. Kivy XCamera  — grabs the texture buffer directly (no file I/O)

Public API:
  capture_frame_android() -> Optional[bytes]   JPEG bytes or None
"""

from __future__ import annotations
import io
import os
import tempfile
import threading
import time
from typing import Optional


def capture_frame_android() -> Optional[bytes]:
    """Return JPEG bytes from the Android rear camera, or None on failure."""
    data = _capture_via_plyer()
    if data:
        return data
    return _capture_via_kivy_texture()


# ── Strategy 1: plyer.camera ──────────────────────────────────────────────────

def _capture_via_plyer() -> Optional[bytes]:
    try:
        from plyer import camera  # type: ignore
        tmp = os.path.join(tempfile.gettempdir(), "jarvis_capture.jpg")
        # plyer camera.take_picture is async on Android; we block with an event
        done = threading.Event()

        def _on_complete(filename):
            done.set()

        camera.take_picture(filename=tmp, on_complete=_on_complete)
        done.wait(timeout=10)

        if os.path.exists(tmp):
            with open(tmp, "rb") as f:
                data = f.read()
            try:
                os.unlink(tmp)
            except Exception:
                pass
            return data if data else None
    except Exception as e:
        print(f"[AndroidCamera] plyer failed: {e}")
    return None


# ── Strategy 2: Kivy XCamera texture grab ────────────────────────────────────

def _capture_via_kivy_texture() -> Optional[bytes]:
    """
    Grab a frame from a running Kivy XCamera widget.
    Works only if the app already has a Camera widget in the tree.
    """
    try:
        from kivy.app import App  # type: ignore
        from kivy.uix.camera import Camera  # type: ignore
        from PIL import Image as _PILImage  # type: ignore

        app = App.get_running_app()
        if not app:
            return None

        cam_widget = _find_camera_widget(app.root)
        if not cam_widget:
            # Spin up a headless camera widget for one frame
            cam_widget = Camera(index=0, resolution=(640, 480), play=True)
            time.sleep(1.5)          # let camera warm up
            data = _texture_to_jpeg(cam_widget.texture)
            cam_widget.play = False
            return data

        return _texture_to_jpeg(cam_widget.texture)

    except Exception as e:
        print(f"[AndroidCamera] kivy texture grab failed: {e}")
    return None


def _find_camera_widget(widget):
    """Depth-first search for a Camera widget in the Kivy tree."""
    try:
        from kivy.uix.camera import Camera  # type: ignore
        if isinstance(widget, Camera):
            return widget
        for child in getattr(widget, "children", []):
            found = _find_camera_widget(child)
            if found:
                return found
    except Exception:
        pass
    return None


def _texture_to_jpeg(texture) -> Optional[bytes]:
    """Convert a Kivy texture to JPEG bytes via PIL."""
    try:
        from PIL import Image as _PILImage  # type: ignore
        if not texture:
            return None
        pixels = texture.pixels          # raw RGBA bytes
        img = _PILImage.frombytes("RGBA", texture.size, pixels)
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception as e:
        print(f"[AndroidCamera] texture→JPEG failed: {e}")
    return None

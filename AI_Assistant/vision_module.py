"""
JARVIS Vision — Phase 7.

Real capabilities:
  - Webcam capture on demand
  - OCR via pytesseract or RapidOCR (reads text from screen/image)
  - QR code scanning via pyzbar
  - Object/scene description via Gemini Vision API
  - Screen region capture

Public API:
  capture_and_describe()   → str  (what's in front of camera)
  read_screen()            → str  (OCR current screen)
  scan_qr()                → str  (scan QR from camera)
  describe_image(path)     → str  (describe any image file)
  handle(command)          → str
"""

from __future__ import annotations
import base64
import io
import os
import tempfile
from typing import Optional

_BASE = os.path.dirname(os.path.abspath(__file__))
_RAPIDOCR = None


def _get_rapidocr():
    """Lazily construct RapidOCR once, or return None if unavailable."""
    global _RAPIDOCR
    if _RAPIDOCR is False:
        return None
    if _RAPIDOCR is not None:
        return _RAPIDOCR
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
        _RAPIDOCR = RapidOCR()
        return _RAPIDOCR
    except Exception:
        _RAPIDOCR = False
        return None


def _rapidocr_text(result) -> str:
    """Extract readable text from RapidOCR output in a tolerant way."""
    texts = []

    def _push(value):
        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")
        if isinstance(value, str):
            value = value.strip()
            if value:
                texts.append(value)

    def _walk(node):
        if node is None:
            return
        if isinstance(node, (str, bytes)):
            _push(node)
            return
        if isinstance(node, (list, tuple)):
            if len(node) >= 2 and isinstance(node[1], (str, bytes)):
                _push(node[1])
                return
            for item in node:
                _walk(item)

    _walk(result)

    deduped = []
    seen = set()
    for item in texts:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return " ".join(deduped).strip()


# ── Camera capture ────────────────────────────────────────────────────────────

def _capture_frame() -> Optional[bytes]:
    """Capture one frame from camera. Returns JPEG bytes."""
    # Android: use plyer / Kivy camera (cv2 and ImageGrab don't work on Android)
    try:
        from android_access import is_android
        if is_android():
            from android_camera import capture_frame_android
            return capture_frame_android()
    except Exception:
        pass

    # Desktop: cv2 webcam
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        _, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes()
    except ImportError:
        pass
    except Exception as e:
        print(f"[Vision] Camera error: {e}")

    # Desktop fallback: PIL screen grab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        return None


def _screen_capture(region=None) -> Optional[bytes]:
    """Capture screen or region. Returns JPEG bytes."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=region)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        try:
            import subprocess
            tmp = tempfile.mktemp(suffix=".png")
            subprocess.run(
                ["powershell", "-command",
                 f"Add-Type -AssemblyName System.Windows.Forms; "
                 f"$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                 f"$b=New-Object System.Drawing.Bitmap($s.Width,$s.Height); "
                 f"$g=[System.Drawing.Graphics]::FromImage($b); "
                 f"$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size); "
                 f"$b.Save('{tmp}')"],
                capture_output=True, timeout=5, creationflags=0x08000000
            )
            if os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    data = f.read()
                os.unlink(tmp)
                return data
        except Exception:
            pass
    except Exception as e:
        print(f"[Vision] Screen capture error: {e}")
    return None


# ── OCR ───────────────────────────────────────────────────────────────────────

def read_image_text(image_bytes: bytes) -> str:
    """Extract text from image bytes using pytesseract, then RapidOCR."""
    img = None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return f"OCR error: {e}"

    try:
        import pytesseract  # type: ignore
        text = pytesseract.image_to_string(img).strip()
        if text:
            return text
    except Exception:
        pass

    rapidocr = _get_rapidocr()
    if rapidocr is not None:
        try:
            import numpy as np  # type: ignore
            arr = np.array(img)
            result = rapidocr(arr)
            text = _rapidocr_text(result)
            if text:
                return text
        except Exception as e:
            return f"OCR error: {e}"

    return "OCR unavailable. Install pytesseract+tesseract or rapidocr-onnxruntime."


def read_screen() -> str:
    """Capture screen and extract text via OCR."""
    data = _screen_capture()
    if not data:
        return "Screen capture failed."
    text = read_image_text(data)
    if len(text) > 500:
        text = text[:500] + "..."
    return f"Screen text: {text}"


def analyze_image_bytes(image_bytes: bytes, prompt: str = "", use_cloud: bool = False) -> str:
    """Analyze image bytes.
    use_cloud=False  → OCR + QR only, zero network calls.
    use_cloud=True   → Gemini Vision (only when explicitly requested).
    """
    if use_cloud:
        desc = _describe_with_gemini(
            image_bytes,
            prompt or "Describe what you see in this image concisely."
        )
        return desc or "Gemini couldn't describe the image. Check GEMINI_API_KEY."

    # Free tier: QR first (fast), then OCR
    qr = _scan_qr_bytes(image_bytes)
    if qr:
        return f"QR code: {qr}"

    text = read_image_text(image_bytes)
    if text and text not in ("No text found in image.",):
        return f"Text found: {text[:300]}"

    return "No text or QR code found. Tap \u2728 Analyze to use Gemini for a full description."


# ── QR Code ───────────────────────────────────────────────────────────────────

def _scan_qr_bytes(image_bytes: bytes) -> str:
    """Decode QR from raw bytes. Returns decoded string or empty string."""
    try:
        from pyzbar import pyzbar  # type: ignore
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        codes = pyzbar.decode(img)
        return ", ".join(c.data.decode("utf-8") for c in codes) if codes else ""
    except Exception:
        return ""


def scan_qr_from_camera() -> str:
    """Scan QR code from webcam."""
    try:
        from pyzbar import pyzbar  # type: ignore
        from PIL import Image
        data = _capture_frame()
        if not data:
            return "Camera not available."
        img = Image.open(io.BytesIO(data))
        codes = pyzbar.decode(img)
        if not codes:
            return "No QR code detected. Hold it closer to the camera."
        results = [c.data.decode("utf-8") for c in codes]
        return "QR code: " + ", ".join(results)
    except ImportError:
        return "QR scanning unavailable. Install: pip install pyzbar pillow"
    except Exception as e:
        return f"QR scan error: {e}"


def scan_qr_from_screen() -> str:
    """Scan QR code from current screen."""
    try:
        from pyzbar import pyzbar  # type: ignore
        from PIL import Image
        data = _screen_capture()
        if not data:
            return "Screen capture failed."
        img = Image.open(io.BytesIO(data))
        codes = pyzbar.decode(img)
        if not codes:
            return "No QR code found on screen."
        results = [c.data.decode("utf-8") for c in codes]
        return "QR code: " + ", ".join(results)
    except ImportError:
        return "QR scanning unavailable. Install: pip install pyzbar pillow"
    except Exception as e:
        return f"QR scan error: {e}"


# ── Gemini Vision ─────────────────────────────────────────────────────────────

def _describe_with_gemini(image_bytes: bytes, prompt: str = "Describe what you see in this image concisely.") -> Optional[str]:
    """Send image to Gemini Vision for description."""
    try:
        import google.genai as genai  # type: ignore
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            return None
        client = genai.Client(api_key=key)
        b64 = base64.b64encode(image_bytes).decode()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"role": "user", "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                    {"text": prompt}
                ]}
            ]
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        print(f"[Vision] Gemini error: {e}")
        return None


def capture_and_describe(use_cloud: bool = False) -> str:
    """Capture from webcam and describe it. Free by default, cloud on request."""
    data = _capture_frame()
    if not data:
        return "Camera not available. Make sure a webcam is connected."

    return analyze_image_bytes(
        data,
        "What do you see? Be concise, 2-3 sentences.",
        use_cloud=use_cloud
    )


def describe_image(path: str, use_cloud: bool = False) -> str:
    """Describe an image file. Free OCR by default, Gemini only when requested."""
    if not os.path.exists(path):
        return f"File not found: {path}"
    try:
        with open(path, "rb") as f:
            data = f.read()
        return analyze_image_bytes(data, use_cloud=use_cloud)
    except Exception as e:
        return f"Could not read image: {e}"


def read_screen_and_describe(use_cloud: bool = False) -> str:
    """Capture screen and describe it. Free OCR by default, cloud on request."""
    data = _screen_capture()
    if not data:
        return "Screen capture failed."
    if use_cloud:
        desc = _describe_with_gemini(data, "What is on this screen? Summarize briefly.")
        if desc:
            return desc
    return read_image_text(data)


# ── Main handler ──────────────────────────────────────────────────────────────

def handle(command: str) -> str:
    cmd = command.lower().strip()
    explicit_cloud = any(w in cmd for w in ("analyze", "gemini", "detailed", "full detail"))

    if any(w in cmd for w in ("what's in front", "what do you see", "look", "camera", "see")):
        return capture_and_describe(use_cloud=explicit_cloud)

    if any(w in cmd for w in ("read screen", "what's on screen", "ocr screen", "screen text")):
        return read_screen_and_describe(use_cloud=explicit_cloud)

    if any(w in cmd for w in ("read text", "ocr", "extract text")):
        if "screen" in cmd:
            return read_screen()
        return capture_and_describe(use_cloud=explicit_cloud)

    if "qr" in cmd:
        if "screen" in cmd:
            return scan_qr_from_screen()
        return scan_qr_from_camera()

    if "describe" in cmd:
        import re
        m = re.search(r"describe (.+)", cmd)
        if m:
            return describe_image(m.group(1).strip(), use_cloud=explicit_cloud)
        return capture_and_describe(use_cloud=explicit_cloud)

    return "Vision commands: 'what do you see', 'read screen', 'scan QR', 'describe [image path]'"

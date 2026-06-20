"""
JARVIS Vision Service — Camera capture, OCR, QR scanning, and AI vision analysis.

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

import base64
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_RAPIDOCR = None

# Optional dependencies with fallbacks
try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False

try:
    from pyzbar import pyzbar
    _PYZBAR_AVAILABLE = True
except ImportError:
    _PYZBAR_AVAILABLE = False


def _get_rapidocr():
    """Lazily construct RapidOCR once, or return None if unavailable."""
    global _RAPIDOCR
    if _RAPIDOCR is False:
        return None
    if _RAPIDOCR is not None:
        return _RAPIDOCR
    try:
        from rapidocr_onnxruntime import RapidOCR
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
    if not _CV2_AVAILABLE and not _PIL_AVAILABLE:
        return None
    
    # Desktop: cv2 webcam
    if _CV2_AVAILABLE:
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.warning("Camera not accessible via cv2")
            else:
                ret, frame = cap.read()
                cap.release()
                if ret:
                    _, buf = cv2.imencode(".jpg", frame)
                    return buf.tobytes()
        except Exception as e:
            logger.warning(f"cv2 camera error: {e}")

    # Desktop fallback: PIL screen grab (as camera substitute)
    if _PIL_AVAILABLE:
        try:
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return buf.getvalue()
        except Exception as e:
            logger.warning(f"Screen grab error: {e}")

    return None


def _screen_capture(region=None) -> Optional[bytes]:
    """Capture screen or region. Returns JPEG bytes."""
    if not _PIL_AVAILABLE:
        return None
        
    try:
        img = ImageGrab.grab(bbox=region)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Screen capture error: {e}")
        return None


# ── OCR ───────────────────────────────────────────────────────────────────────

def read_image_text(image_bytes: bytes) -> str:
    """Extract text from image bytes using pytesseract, then RapidOCR."""
    if not _PIL_AVAILABLE:
        return "PIL not available for image processing"
        
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return f"Image processing error: {e}"

    # Try pytesseract first
    if _TESSERACT_AVAILABLE:
        try:
            text = pytesseract.image_to_string(img).strip()
            if text:
                return text
        except Exception as e:
            logger.warning(f"Tesseract OCR error: {e}")

    # Fallback to RapidOCR
    rapidocr = _get_rapidocr()
    if rapidocr is not None:
        try:
            import numpy as np
            arr = np.array(img)
            result = rapidocr(arr)
            text = _rapidocr_text(result)
            if text:
                return text
        except Exception as e:
            logger.warning(f"RapidOCR error: {e}")

    return "No text found in image. Install pytesseract+tesseract or rapidocr-onnxruntime for OCR."


def read_screen() -> str:
    """Capture screen and extract text via OCR."""
    data = _screen_capture()
    if not data:
        return "Screen capture failed. PIL package required."
    
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
    if text and "No text found" not in text:
        return f"Text found: {text[:300]}"

    return "No text or QR code found. Use 'analyze image' for AI description (requires GEMINI_API_KEY)."


# ── QR Code ───────────────────────────────────────────────────────────────────

def _scan_qr_bytes(image_bytes: bytes) -> str:
    """Decode QR from raw bytes. Returns decoded string or empty string."""
    if not _PYZBAR_AVAILABLE or not _PIL_AVAILABLE:
        return ""
        
    try:
        img = Image.open(io.BytesIO(image_bytes))
        codes = pyzbar.decode(img)
        return ", ".join(c.data.decode("utf-8") for c in codes) if codes else ""
    except Exception as e:
        logger.warning(f"QR decode error: {e}")
        return ""


def scan_qr_from_camera() -> str:
    """Scan QR code from webcam."""
    if not _PYZBAR_AVAILABLE:
        return "QR scanning unavailable. Install: pip install pyzbar"
    
    data = _capture_frame()
    if not data:
        return "Camera not available. Install opencv-python or ensure webcam is connected."
    
    qr = _scan_qr_bytes(data)
    if not qr:
        return "No QR code detected. Hold it closer to the camera."
    
    return f"QR code: {qr}"


def scan_qr_from_screen() -> str:
    """Scan QR code from current screen."""
    if not _PYZBAR_AVAILABLE:
        return "QR scanning unavailable. Install: pip install pyzbar"
    
    data = _screen_capture()
    if not data:
        return "Screen capture failed."
    
    qr = _scan_qr_bytes(data)
    if not qr:
        return "No QR code found on screen."
    
    return f"QR code: {qr}"


# ── Gemini Vision ─────────────────────────────────────────────────────────────

def _describe_with_gemini(image_bytes: bytes, prompt: str = "Describe what you see in this image concisely.") -> Optional[str]:
    """Send image to Gemini Vision for description. ONLY for explicit vision analysis."""
    
    # Check if Gemini should be used conservatively
    vision_only = os.getenv("GEMINI_VISION_ONLY", "false").lower() == "true"
    if vision_only:
        # Only use for explicit analysis requests
        analysis_keywords = ["analyze", "detailed", "describe", "what is", "identify"]
        if not any(keyword in prompt.lower() for keyword in analysis_keywords):
            logger.info("Skipping Gemini call - not an analysis request")
            return None
    
    # Rate limiting check
    try:
        from jarvis.core.rate_guard import can_call
        allowed, reason = can_call("gemini")
        if not allowed:
            logger.warning(f"Gemini vision blocked: {reason}")
            return None
    except ImportError:
        pass
    
    # Cooldown check
    cooldown = int(os.getenv("GEMINI_VISION_COOLDOWN", "10"))
    global _last_gemini_call
    if not hasattr(_describe_with_gemini, '_last_call'):
        _describe_with_gemini._last_call = 0
    
    import time
    now = time.time()
    if now - _describe_with_gemini._last_call < cooldown:
        logger.info(f"Gemini vision cooldown: {cooldown}s")
        return None
    
    try:
        # Try using existing AI brain first (may use Groq instead)
        from jarvis.core.ai_brain import ask as ai_ask
        
        # Only use direct Gemini for image analysis
        b64 = base64.b64encode(image_bytes).decode()
        if len(b64) > 1000:  # Only for actual images
            _describe_with_gemini._last_call = now
            
    except ImportError:
        pass
    
    # Direct Gemini API (last resort)
    try:
        import google.genai as genai
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            return None
            
        _describe_with_gemini._last_call = now
        client = genai.Client(api_key=key)
        b64 = base64.b64encode(image_bytes).decode()
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # Use cheaper model
            contents=[
                {"role": "user", "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                    {"text": prompt + " (Be concise - 1-2 sentences)"}
                ]}
            ]
        )
        
        # Record the API call
        try:
            from jarvis.core.rate_guard import record_call
            record_call("gemini")
        except ImportError:
            pass
            
        return response.text.strip() if response.text else None
        
    except Exception as e:
        logger.warning(f"Gemini Vision error: {e}")
        return None


def capture_and_describe(use_cloud: bool = False) -> str:
    """Capture from webcam and describe it. Free by default, cloud on request."""
    data = _capture_frame()
    if not data:
        return "Camera not available. Make sure a webcam is connected or install opencv-python."

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
        return "Screen capture failed. Install Pillow package."
    
    if use_cloud:
        desc = _describe_with_gemini(data, "What is on this screen? Summarize briefly.")
        if desc:
            return desc
    
    return read_image_text(data)


# ── Main handler ──────────────────────────────────────────────────────────────

def handle_vision_command(command: str) -> str:
    """Handle vision-related commands from the main brain."""
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


def get_vision_capabilities() -> str:
    """Get available vision capabilities based on installed packages."""
    caps = []
    
    if _CV2_AVAILABLE:
        caps.append("📹 Camera capture (opencv)")
    elif _PIL_AVAILABLE:
        caps.append("📹 Screen capture (PIL)")
    
    if _TESSERACT_AVAILABLE:
        caps.append("📝 OCR (Tesseract)")
    elif _get_rapidocr():
        caps.append("📝 OCR (RapidOCR)")
    
    if _PYZBAR_AVAILABLE:
        caps.append("📱 QR scanning")
    
    if os.getenv("GEMINI_API_KEY"):
        caps.append("🤖 AI Vision (Gemini)")
    
    if not caps:
        return "Vision features unavailable. Install: pip install opencv-python pillow pytesseract pyzbar"
    
    return "Available vision capabilities:\n" + "\n".join(f"• {cap}" for cap in caps)
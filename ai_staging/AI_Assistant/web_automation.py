"""
JARVIS Web Automation — Phase 6.

Real actions (no mock data):
  - Product search on Flipkart/Amazon India (opens browser with results)
  - Google search
  - Form fill via pyautogui (types saved profile data)
  - Confirmation required before any form submission

Confirmation flow:
  Every risky action returns a ConfirmationRequest.
  Server holds it pending, user says "yes/confirm" → executes.
  User says "no/cancel" → discards.

Public API:
  search_product(query, site, max_price) → str
  google_search(query)                   → str
  fill_form(field_map)                   → ConfirmationRequest
  handle(command)                        → str | ConfirmationRequest
"""

from __future__ import annotations
import re
import webbrowser
from dataclasses import dataclass, field
from typing import Callable, Optional


# ── Confirmation system ───────────────────────────────────────────────────────

@dataclass
class ConfirmationRequest:
    prompt: str                    # what JARVIS says to the user
    action: Callable               # callable to execute on confirm
    action_label: str = ""         # short description for logging
    confirmed: bool = False

    def confirm(self) -> str:
        self.confirmed = True
        try:
            return self.action()
        except Exception as e:
            return f"Action failed: {e}"

    def cancel(self) -> str:
        return "Cancelled."


# Global pending confirmation (one at a time)
_pending: Optional[ConfirmationRequest] = None

def set_pending(req: ConfirmationRequest):
    global _pending
    _pending = req

def get_pending() -> Optional[ConfirmationRequest]:
    return _pending

def clear_pending():
    global _pending
    _pending = None

def resolve(user_says: str) -> Optional[str]:
    """Call this when user responds to a confirmation prompt."""
    global _pending
    if not _pending:
        return None
    s = user_says.lower().strip()
    if any(w in s for w in ("yes", "confirm", "do it", "go ahead", "sure", "ok", "okay")):
        result = _pending.confirm()
        _pending = None
        return result
    if any(w in s for w in ("no", "cancel", "stop", "don't", "nope", "abort")):
        _pending = None
        return "Cancelled."
    return None  # not a confirmation response


# ── Product search ────────────────────────────────────────────────────────────

def search_product(query: str, site: str = "flipkart",
                   max_price: int = 0) -> str:
    """Open product search in browser. Returns confirmation of action."""
    q = query.strip().replace(" ", "+")
    price_filter = ""

    if site.lower() in ("flipkart", "fk"):
        url = f"https://www.flipkart.com/search?q={q}"
        if max_price:
            url += f"&p%5B%5D=facets.price_range.from%3DMin&p%5B%5D=facets.price_range.to%3D{max_price}"
        site_name = "Flipkart"
    elif site.lower() in ("amazon", "amz"):
        url = f"https://www.amazon.in/s?k={q}"
        if max_price:
            url += f"&rh=p_36%3A-{max_price * 100}"
        site_name = "Amazon India"
    elif site.lower() in ("meesho",):
        url = f"https://www.meesho.com/search?q={q}"
        site_name = "Meesho"
    else:
        url = f"https://www.google.com/search?q={q}+buy+online+india"
        site_name = "Google Shopping"

    webbrowser.open(url)
    result = f"Opened {site_name} search for '{query}'"
    if max_price:
        result += f" under ₹{max_price:,}"
    return result + "."


def google_search(query: str) -> str:
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching Google for '{query}'."


# ── Form fill ─────────────────────────────────────────────────────────────────

def fill_form_with_profile() -> str:
    """
    Type saved profile data into the currently focused form field.
    Uses pyautogui to type. Requires user confirmation first.
    """
    try:
        from user_memory import get_profile, get_preference
        profile = get_profile()
        name    = profile.get("name", "")
        city    = profile.get("city", "")
        phone   = get_preference("phone", "")
        email   = get_preference("email", "")

        if not any([name, city, phone, email]):
            return "No profile data saved. Go to Memory tab and fill in your details first."

        def _do_fill():
            try:
                import pyautogui  # type: ignore
                import time
                fields = []
                if name:  fields.append(name)
                if email: fields.append(email)
                if phone: fields.append(phone)
                if city:  fields.append(city)

                for i, val in enumerate(fields):
                    pyautogui.typewrite(val, interval=0.05)
                    if i < len(fields) - 1:
                        pyautogui.press("tab")
                        time.sleep(0.2)
                return f"Filled {len(fields)} fields with your profile data."
            except ImportError:
                return "pyautogui not installed. Run: pip install pyautogui"
            except Exception as e:
                return f"Form fill error: {e}"

        summary = f"I'll type: {', '.join(filter(None, [name, email, phone, city]))}. Confirm?"
        req = ConfirmationRequest(
            prompt=summary,
            action=_do_fill,
            action_label="fill_form"
        )
        set_pending(req)
        return summary

    except Exception as e:
        return f"Form fill error: {e}"


def type_text(text: str) -> str:
    """Type arbitrary text at current cursor position. Requires confirmation."""
    def _do_type():
        try:
            import pyautogui  # type: ignore
            pyautogui.typewrite(text, interval=0.04)
            return f"Typed: {text[:50]}{'...' if len(text)>50 else ''}"
        except ImportError:
            return "pyautogui not installed."
        except Exception as e:
            return f"Type error: {e}"

    prompt = f"I'll type '{text[:60]}{'...' if len(text)>60 else ''}' at the cursor. Confirm?"
    req = ConfirmationRequest(prompt=prompt, action=_do_type, action_label="type_text")
    set_pending(req)
    return prompt


# ── Main command handler ──────────────────────────────────────────────────────

def handle(command: str) -> str:
    cmd = command.lower().strip()

    # Check for pending confirmation first
    resolved = resolve(cmd)
    if resolved is not None:
        return resolved

    # Product search
    m = re.search(r"(?:search|find|look for|buy)\s+(.+?)(?:\s+on\s+(flipkart|amazon|meesho))?(?:\s+under\s+(?:rs\.?|₹|inr)?\s*(\d+))?$", cmd)
    if m and any(w in cmd for w in ("buy", "search", "find", "price", "shop", "order")):
        query     = m.group(1).strip()
        site      = m.group(2) or "flipkart"
        max_price = int(m.group(3)) if m.group(3) else 0
        return search_product(query, site, max_price)

    # Google search
    if cmd.startswith("google ") or "search google" in cmd or "search for" in cmd:
        q = re.sub(r"^(google|search google for?|search for?)\s+", "", cmd).strip()
        return google_search(q)

    # Form fill
    if "fill form" in cmd or "fill my details" in cmd or "autofill" in cmd:
        return fill_form_with_profile()

    # Type text
    m = re.search(r"type (.+)", cmd)
    if m:
        return type_text(m.group(1).strip())

    return "Web command not understood. Try: search [product] on flipkart, google [query], fill form."

"""
JARVIS Call & SMS Assistant — Phase 8.

On Windows:
  - Reads notifications from Windows Action Center (toast)
  - Announces incoming calls via TTS
  - Drafts SMS replies (opens messaging app or WhatsApp Web)

On Android (future):
  - Uses android_event_bridge for real SMS/call events

Confirmation required before sending any message.

Public API:
  announce_call(caller)         → str
  handle_sms(sender, body)      → str
  draft_reply(contact, message) → ConfirmationRequest
  handle(command)               → str
"""

from __future__ import annotations
import os
import re
import webbrowser
from typing import Optional

# ── Call announcement ─────────────────────────────────────────────────────────

def announce_call(caller: str, number: str = "") -> str:
    """Announce incoming call via TTS and desktop notification."""
    display = caller or number or "Unknown"
    msg = f"Incoming call from {display}."

    # Desktop notification
    try:
        import subprocess
        script = (
            f"[Windows.UI.Notifications.ToastNotificationManager,"
            f"Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
            f"$t=[Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
            f"$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
            f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('Incoming Call'))|Out-Null;"
            f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{display}'))|Out-Null;"
            f"$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('JARVIS').Show($n)"
        )
        subprocess.run(["powershell", "-command", script],
                       capture_output=True, timeout=3, creationflags=0x08000000)
    except Exception:
        pass

    return msg


# ── SMS handling ──────────────────────────────────────────────────────────────

def handle_sms(sender: str, body: str) -> str:
    """Process incoming SMS — announce and offer reply."""
    preview = body[:80] + ("..." if len(body) > 80 else "")
    return f"Message from {sender}: {preview}. Say 'reply to {sender}' to respond."


def draft_reply(contact: str, message: str) -> str:
    """
    Draft a reply. Opens WhatsApp Web or SMS with pre-filled message.
    Returns confirmation prompt.
    """
    from web_automation import ConfirmationRequest, set_pending

    def _send():
        # Try WhatsApp Web (works on desktop)
        encoded = message.replace(" ", "%20")
        url = f"https://wa.me/?text={encoded}"
        webbrowser.open(url)
        return f"Opened WhatsApp Web with message to {contact}."

    prompt = f"Send to {contact}: '{message[:60]}{'...' if len(message)>60 else ''}' — confirm?"
    req = ConfirmationRequest(prompt=prompt, action=_send, action_label="send_message")
    set_pending(req)
    return prompt


# ── Contact lookup ────────────────────────────────────────────────────────────

def _lookup_contact(name: str) -> Optional[str]:
    """Look up contact from user_memory."""
    try:
        from user_memory import get_contact
        return get_contact(name)
    except Exception:
        return None


# ── Android bridge (no-op on Windows) ────────────────────────────────────────

_bridge_active = False

def start_android_bridge(on_call=None, on_sms=None) -> bool:
    """Start Android event bridge if on Android."""
    global _bridge_active
    try:
        from android_event_bridge import AndroidEventBridge
        bridge = AndroidEventBridge()

        def _on_sms(data):
            sender = data.get("address", "Unknown")
            body   = data.get("body", "")
            msg    = handle_sms(sender, body)
            try:
                from fast_tts import speak
                speak(msg)
            except Exception:
                pass

        def _on_call(data):
            caller = data.get("caller", data.get("address", "Unknown"))
            msg    = announce_call(caller)
            try:
                from fast_tts import speak
                speak(msg)
            except Exception:
                pass

        ok = bridge.start(
            on_sms=on_sms or _on_sms,
            on_notification=on_call
        )
        _bridge_active = ok
        return ok
    except Exception:
        return False


# ── Main handler ──────────────────────────────────────────────────────────────

def handle(command: str) -> str:
    cmd = command.lower().strip()

    # Reply to contact
    m = re.search(r"reply to (.+?)(?:\s+saying?\s+(.+))?$", cmd)
    if m:
        contact = m.group(1).strip()
        message = m.group(2).strip() if m.group(2) else ""
        if not message:
            return f"What would you like to say to {contact}?"
        # Check memory for contact details
        detail = _lookup_contact(contact)
        if detail:
            return draft_reply(contact, message) + f" (Contact: {detail})"
        return draft_reply(contact, message)

    # Send message
    m = re.search(r"(?:send|message|text|whatsapp)\s+(.+?)\s+(?:saying?|:)\s+(.+)", cmd)
    if m:
        return draft_reply(m.group(1).strip(), m.group(2).strip())

    # Call announcement test
    m = re.search(r"(?:announce|incoming) call from (.+)", cmd)
    if m:
        return announce_call(m.group(1).strip())

    # Open WhatsApp
    if "whatsapp" in cmd:
        webbrowser.open("https://web.whatsapp.com")
        return "Opening WhatsApp Web."

    # Open messages
    if "messages" in cmd or "sms" in cmd:
        if os.name == "nt":
            try:
                import subprocess
                subprocess.Popen(["explorer", "ms-chat:"], shell=True, creationflags=0x08000000)
                return "Opening Messages app."
            except Exception:
                pass
        webbrowser.open("https://messages.google.com/web")
        return "Opening Google Messages Web."

    return "Call/SMS commands: 'reply to [name] saying [message]', 'open whatsapp', 'open messages'"

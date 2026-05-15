"""
Android event bridge for SMS, notification, and accessibility broadcasts.
Safe no-op on non-Android platforms.
"""

from android_access import is_android

try:
    from android.broadcast import BroadcastReceiver
except Exception:
    BroadcastReceiver = None

try:
    from kivy.clock import Clock
except Exception:
    Clock = None


def _dispatch(callback, data):
    if callback is None:
        return
    if Clock:
        Clock.schedule_once(lambda dt: callback(data), 0)
    else:
        callback(data)


def _get_extra(intent, key, default=None):
    try:
        value = intent.getStringExtra(key)
        return value if value is not None else default
    except Exception:
        return default


def _get_long_extra(intent, key, default=0):
    try:
        return int(intent.getLongExtra(key, default))
    except Exception:
        return default


class AndroidEventBridge:
    def __init__(self):
        self.receivers = []

    def start(self, on_sms=None, on_mms=None, on_notification=None, on_accessibility=None):
        if not is_android() or BroadcastReceiver is None:
            return False

        if on_sms:
            def _sms_receiver(context, intent):
                data = {
                    "address": _get_extra(intent, "address", ""),
                    "body": _get_extra(intent, "body", ""),
                    "timestamp": _get_long_extra(intent, "timestamp", 0)
                }
                _dispatch(on_sms, data)
            r = BroadcastReceiver(_sms_receiver, actions=[
                "org.pranesh.jarvis_ai.SMS_EVENT"
            ])
            r.start()
            self.receivers.append(r)

        if on_mms:
            def _mms_receiver(context, intent):
                data = {
                    "action": _get_extra(intent, "action", "")
                }
                _dispatch(on_mms, data)
            r = BroadcastReceiver(_mms_receiver, actions=[
                "org.pranesh.jarvis_ai.MMS_EVENT"
            ])
            r.start()
            self.receivers.append(r)

        if on_notification:
            def _notif_receiver(context, intent):
                data = {
                    "package": _get_extra(intent, "package", ""),
                    "title": _get_extra(intent, "title", ""),
                    "text": _get_extra(intent, "text", "")
                }
                _dispatch(on_notification, data)
            r = BroadcastReceiver(_notif_receiver, actions=[
                "org.pranesh.jarvis_ai.NOTIFICATION_EVENT"
            ])
            r.start()
            self.receivers.append(r)

        if on_accessibility:
            def _access_receiver(context, intent):
                data = {
                    "event_type": _get_extra(intent, "event_type", ""),
                    "package": _get_extra(intent, "package", ""),
                    "text": _get_extra(intent, "text", "")
                }
                _dispatch(on_accessibility, data)
            r = BroadcastReceiver(_access_receiver, actions=[
                "org.pranesh.jarvis_ai.ACCESSIBILITY_EVENT"
            ])
            r.start()
            self.receivers.append(r)

        return True

    def stop(self):
        for r in self.receivers:
            try:
                r.stop()
            except Exception:
                pass
        self.receivers = []

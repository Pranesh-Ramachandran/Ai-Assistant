"""
Android data access helpers (contacts, call logs, SMS).
Safe no-op on non-Android platforms.
"""

from android_access import is_android


def _get_activity():
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity


def list_contacts(limit=50):
    if not is_android():
        return []
    try:
        from jnius import autoclass
        Contacts = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
        resolver = _get_activity().getContentResolver()
        cursor = resolver.query(Contacts.CONTENT_URI, None, None, None, None)
        results = []
        if cursor:
            name_col = cursor.getColumnIndex(Contacts.DISPLAY_NAME)
            number_col = cursor.getColumnIndex(Contacts.NUMBER)
            count = 0
            while cursor.moveToNext() and count < limit:
                name = cursor.getString(name_col)
                number = cursor.getString(number_col)
                results.append({"name": name, "number": number})
                count += 1
            cursor.close()
        return results
    except Exception:
        return []


def list_call_logs(limit=50):
    if not is_android():
        return []
    try:
        from jnius import autoclass
        Calls = autoclass("android.provider.CallLog$Calls")
        resolver = _get_activity().getContentResolver()
        cursor = resolver.query(Calls.CONTENT_URI, None, None, None, Calls.DATE + " DESC")
        results = []
        if cursor:
            num_col = cursor.getColumnIndex(Calls.NUMBER)
            type_col = cursor.getColumnIndex(Calls.TYPE)
            date_col = cursor.getColumnIndex(Calls.DATE)
            dur_col = cursor.getColumnIndex(Calls.DURATION)
            count = 0
            while cursor.moveToNext() and count < limit:
                results.append({
                    "number": cursor.getString(num_col),
                    "type": cursor.getInt(type_col),
                    "date": cursor.getLong(date_col),
                    "duration": cursor.getLong(dur_col)
                })
                count += 1
            cursor.close()
        return results
    except Exception:
        return []


def list_sms_inbox(limit=50):
    if not is_android():
        return []
    try:
        from jnius import autoclass
        SmsInbox = autoclass("android.provider.Telephony$Sms$Inbox")
        resolver = _get_activity().getContentResolver()
        cursor = resolver.query(SmsInbox.CONTENT_URI, None, None, None, "date DESC")
        results = []
        if cursor:
            body_col = cursor.getColumnIndex("body")
            addr_col = cursor.getColumnIndex("address")
            date_col = cursor.getColumnIndex("date")
            count = 0
            while cursor.moveToNext() and count < limit:
                results.append({
                    "address": cursor.getString(addr_col),
                    "body": cursor.getString(body_col),
                    "date": cursor.getLong(date_col)
                })
                count += 1
            cursor.close()
        return results
    except Exception:
        return []


def send_sms(number, message):
    if not is_android():
        return False
    try:
        from jnius import autoclass
        SmsManager = autoclass("android.telephony.SmsManager")
        SmsManager.getDefault().sendTextMessage(number, None, message, None, None)
        return True
    except Exception:
        return False

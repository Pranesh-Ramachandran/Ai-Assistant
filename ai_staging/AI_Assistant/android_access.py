"""
Android access helpers for permissions and system settings shortcuts.
Safe no-op on non-Android platforms.
"""

def is_android():
    try:
        from kivy.utils import platform
        return platform == "android"
    except Exception:
        return False


def request_runtime_permissions(perms):
    """Request runtime permissions (Android only)."""
    if not is_android():
        return False
    try:
        from android.permissions import request_permissions
        request_permissions(perms)
        return True
    except Exception:
        return False


def has_permission(permission):
    if not is_android():
        return False
    try:
        from jnius import autoclass
        ContextCompat = autoclass("androidx.core.content.ContextCompat")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        PackageManager = autoclass("android.content.pm.PackageManager")
        current = PythonActivity.mActivity
        result = ContextCompat.checkSelfPermission(current, permission)
        return result == PackageManager.PERMISSION_GRANTED
    except Exception:
        return False


def has_all_files_access():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        return bool(Environment.isExternalStorageManager())
    except Exception:
        return False


def get_default_sms_package():
    if not is_android():
        return None
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Telephony = autoclass("android.provider.Telephony$Sms")
        current = PythonActivity.mActivity
        return Telephony.getDefaultSmsPackage(current)
    except Exception:
        return None


def is_notification_listener_enabled():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        SettingsSecure = autoclass("android.provider.Settings$Secure")
        current = PythonActivity.mActivity
        enabled = SettingsSecure.getString(current.getContentResolver(), "enabled_notification_listeners")
        if not enabled:
            return False
        package_name = current.getPackageName()
        return package_name in enabled
    except Exception:
        return False


def is_accessibility_enabled():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        SettingsSecure = autoclass("android.provider.Settings$Secure")
        current = PythonActivity.mActivity
        enabled = SettingsSecure.getString(current.getContentResolver(), "enabled_accessibility_services")
        if not enabled:
            return False
        package_name = current.getPackageName()
        return package_name in enabled
    except Exception:
        return False

def _start_activity(intent):
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        current = PythonActivity.mActivity
        current.startActivity(intent)
        return True
    except Exception:
        return False


def open_app_settings():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        current = PythonActivity.mActivity
        package_name = current.getPackageName()
        uri = Uri.fromParts("package", package_name, None)
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, uri)
        return _start_activity(intent)
    except Exception:
        return False


def open_all_files_access_settings():
    """Open Manage All Files Access for this app."""
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        current = PythonActivity.mActivity
        package_name = current.getPackageName()
        uri = Uri.fromParts("package", package_name, None)
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, uri)
        return _start_activity(intent)
    except Exception:
        # Fallback to app settings
        return open_app_settings()


def open_accessibility_settings():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        return _start_activity(intent)
    except Exception:
        return False


def open_notification_listener_settings():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        return _start_activity(intent)
    except Exception:
        return False


def open_default_sms_settings():
    if not is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        # Open default apps settings (user can set SMS default)
        intent = Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS)
        return _start_activity(intent)
    except Exception:
        return open_app_settings()

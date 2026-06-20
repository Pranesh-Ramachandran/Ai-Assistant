[app]
title = JARVIS
package.name = jarvis
package.domain = com.jarvis.assistant

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,env,txt,mp3

version = 1.0.0

# Entry point — the Kivy app file
entrypoint = jarvis_grid_app.py

# ── Python dependencies (pip packages for Android) ───────────────────────────
requirements =
    python3,
    kivy==2.3.0,
    plyer,
    requests,
    beautifulsoup4,
    pillow,
    numpy,
    pyzbar,
    edge-tts,
    gtts,
    google-generativeai,
    certifi

# ── Android permissions ───────────────────────────────────────────────────────
android.permissions =
    CAMERA,
    RECORD_AUDIO,
    INTERNET,
    ACCESS_NETWORK_STATE,
    ACCESS_FINE_LOCATION,
    ACCESS_COARSE_LOCATION,
    READ_EXTERNAL_STORAGE,
    WRITE_EXTERNAL_STORAGE,
    READ_CONTACTS,
    READ_CALL_LOG,
    READ_SMS,
    RECEIVE_SMS,
    SEND_SMS,
    CALL_PHONE,
    VIBRATE,
    RECEIVE_BOOT_COMPLETED,
    FOREGROUND_SERVICE,
    POST_NOTIFICATIONS

# ── Android build settings ────────────────────────────────────────────────────
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = False
android.fullscreen = 0

# Needed for camera + mic on Android 12+
android.add_activities = org.kivy.android.PythonActivity

# ── Orientation ───────────────────────────────────────────────────────────────
orientation = portrait

# ── Icons / Presplash ─────────────────────────────────────────────────────────
# icon.filename = %(source.dir)s/design-assets/icon.png
# presplash.filename = %(source.dir)s/design-assets/splash.png

# ── Buildozer internals ───────────────────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1

# Lazy imports — only load when actually used to avoid crashing
# if optional dependencies (pygame, pyttsx3, etc.) are missing.

def __getattr__(name):
    if name in ("speak", "EnhancedTTS"):
        from .tts import speak, EnhancedTTS
        return speak if name == "speak" else EnhancedTTS
    if name == "listen":
        from .stt import listen
        return listen
    if name == "get_weather":
        from .data_collector import get_weather
        return get_weather
    if name == "get_information":
        from .data_collector import get_information
        return get_information
    if name == "IoTAssistant":
        from .iot import IoTAssistant
        return IoTAssistant
    raise AttributeError(f"module 'jarvis.services' has no attribute {name!r}")

__all__ = ["speak", "EnhancedTTS", "listen", "get_weather", "get_information", "IoTAssistant"]

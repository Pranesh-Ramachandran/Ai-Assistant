#!/usr/bin/env python3
import sys
import os
sys.path.append('AI_Assistant')

from AI_Assistant.tts import AdvancedTTS

def test_tts():
    print("Testing TTS system...")
    tts = AdvancedTTS()

    print("Testing basic speak function...")
    result = tts.speak("Hello, this is a test of the TTS system.")
    print(f"Speak result: {result}")

    print("Testing voice info...")
    try:
        info = tts.get_voice_info()
        print(f"Voice info: {info}")
    except Exception as e:
        print(f"Voice info error: {e}")

    print("Testing speech history...")
    history = tts.get_history()
    print(f"Speech history: {history}")

    print("TTS test completed!")

if __name__ == "__main__":
    test_tts()

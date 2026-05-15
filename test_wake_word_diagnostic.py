"""
Wake Word Detection Diagnostic Test
Run this to debug wake word detection issues
"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

print("=" * 70)
print("JARVIS Wake Word Detection Diagnostic")
print("=" * 70)

# Test 1: Check if speech_recognition is available
print("\n[1] Checking speech_recognition library...")
try:
    import speech_recognition as sr
    print("    ✓ speech_recognition OK")
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Check if Google API is accessible
print("\n[2] Testing Google Speech Recognition API...")
try:
    recognizer = sr.Recognizer()
    recognizer.recognize_google(b'', language="en-US")
except sr.RequestError as e:
    if "Connection" in str(e) or "API" in str(e):
        print(f"    ✗ FAILED: Google API unreachable: {e}")
        print("    → Check your internet connection")
    else:
        print(f"    ⚠ Warning: {e}")
except sr.UnknownValueError:
    print("    ✓ Google API accessible (no audio provided, as expected)")
except Exception as e:
    print(f"    ? Unexpected: {e}")

# Test 3: Check microphone
print("\n[3] Testing microphone...")
try:
    mic = sr.Microphone()
    with mic as source:
        print("    Listening for 2 seconds... please speak 'hey jarvis'")
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 200
        try:
            audio = recognizer.listen(source, timeout=2.0)
            print(f"    ✓ Audio captured ({len(audio.get_raw_data())} bytes)")
            
            # Try to recognize it
            try:
                text = recognizer.recognize_google(audio, language="en-US")
                print(f"    recognized: '{text}'")
                if "jarvis" in text.lower() or "aria" in text.lower():
                    print("    ✓ Wake word DETECTED!")
                else:
                    print(f"    ✗ Not a wake word, got: {text}")
            except sr.UnknownValueError:
                print("    ✗ Could not understand audio")
            except sr.RequestError as e:
                print(f"    ✗ API error: {e}")
        except sr.RequestError as e:
            print(f"    ✗ Mic error: {e}")
except Exception as e:
    print(f"    ✗ FAILED: {e}")

# Test 4: Check EfficientWakeWordSystem
print("\n[4] Testing EfficientWakeWordSystem...")
try:
    from wake_word_detector import EfficientWakeWordSystem
    
    wake_triggered = False
    def trigger_callback():
        global wake_triggered
        wake_triggered = True
        print("    ✓✓✓ WAKE WORD DETECTED ✓✓✓")
    
    system = EfficientWakeWordSystem(wake_phrase="hey jarvis")
    print(f"    Created system with phrase: '{system.wake_phrase}'")
    print("    Starting listener... speak 'hey jarvis' within next 10 seconds")
    
    system.start(wake_callback=trigger_callback)
    
    for i in range(10):
        time.sleep(1)
        if wake_triggered:
            print("    ✓ Detection successful!")
            break
        print(f"    Waiting... ({i+1}/10)")
    
    system.stop()
    
    if not wake_triggered:
        print("    ✗ No wake word detected after 10 seconds")
except Exception as e:
    print(f"    ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Diagnostic complete")
print("=" * 70)

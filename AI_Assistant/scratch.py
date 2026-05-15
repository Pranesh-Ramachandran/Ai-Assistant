import threading, time, sys, traceback
import jarvis_ai_brain

def dump():
    time.sleep(5)
    print("dumping stack")
    for tid, frame in sys._current_frames().items():
        print(f"Thread {tid}:")
        traceback.print_stack(frame)

threading.Thread(target=dump, daemon=True).start()
print("testing ask...")
jarvis_ai_brain.ask('What is 2+2?')

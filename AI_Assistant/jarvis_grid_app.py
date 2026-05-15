"""
JARVIS Neural Grid — Desktop App
Wraps neural_grid_ui/index.html in a native frameless window via pywebview.
Starts the grid API server in a background thread.
"""
import sys, os, threading, time
sys.path.insert(0, os.path.dirname(__file__))

import webview
from jarvis_grid_server import JarvisHandler
from http.server import ThreadingHTTPServer

HOST = "localhost"
PORT = 7890

def start_server():
    server = ThreadingHTTPServer((HOST, PORT), JarvisHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Start API + file server in background
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(0.5)  # Let server bind

    webview.create_window(
        title="JARVIS",
        url=f"http://{HOST}:{PORT}",
        width=480,
        height=820,
        resizable=True,
        frameless=False,
        on_top=False,
        background_color="#F8FAFF",
    )
    webview.start()

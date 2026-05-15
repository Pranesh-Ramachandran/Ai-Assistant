# JARVIS Neural Grid - Setup & Deployment Guide

This guide covers everything needed to set up and deploy the JARVIS AI Assistant. JARVIS is built with a Python backend and a lightweight HTML/JS frontend (Neural Grid).

## Prerequisites
- Python 3.10 or 3.11
- A microphone and speakers
- Windows OS (recommended)

## 1. Installation

1. **Create a virtual environment:**
   ```cmd
   python -m venv venv311
   ```

2. **Activate the environment:**
   ```cmd
   venv311\Scripts\activate
   ```

3. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```
   *(Note: The system automatically detects whether to use `venv311` or global Python when launching.)*

## 2. API Keys

JARVIS uses external cloud APIs for LLM intelligence (free tiers available). You must configure them in the `jarvis.env` file.

1. Create a file named `jarvis.env` in the `AI_Assistant` folder if it doesn't exist.
2. Add your keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Optional configurations:
   JARVIS_TTS_MODE=hq          # 'fast' (pyttsx3) or 'hq' (edge-tts)
   JARVIS_STT_ENGINE=google    # 'google' or 'azure'
   JARVIS_AI_MODE=hybrid       # 'hybrid' | 'groq' | 'gemini' | 'offline'
   ```
   *Note: Never commit `jarvis.env` to version control. Keep it private.*

## 3. Running JARVIS

The easiest way to start JARVIS is to use the provided launch scripts.

**Option A: Developer Mode (Shows Console)**
Double click `run_jarvis.bat`. This will start the Python backend and automatically open the Neural Grid UI in your default web browser after a brief delay.

**Option B: Stealth / Deployment Mode**
Double click `start_jarvis.bat`.

Alternatively, you can manually run:
```cmd
python jarvis_grid_server.py
```
And open your browser to `http://localhost:7890`.

## 4. Testing Core Features

Once running, verify these components in the UI (`http://localhost:7890`):
- **Microphone**: Click the mic icon or press `Ctrl+M` and say "Hello".
- **Wake Word**: Open the hamburger menu and toggle the Wake Word to ON. Say "Aria" (default wake word) followed by a command.
- **Dark Mode**: Toggle Dark Mode in the menu to test the UI responsive design.

## 5. Troubleshooting

- **No audio output**: Ensure `JARVIS_TTS_MODE=hq` in your `.env` and that `edge-tts` is installed. Check system volume.
- **Double responses / Messages**: Make sure you have the latest `index.html` UI file. Stale browser caches can cause this; force refresh (`Ctrl+F5`).
- **Wake word not responding**: Wake word processing requires the `SpeechRecognition` library and a relatively quiet background environment.

## 6. Going to Production

For a permanent home network deployment:
1. Run the server on a dedicated machine.
2. Update `jarvis_grid_server.py` `HOST` from `"localhost"` to `"0.0.0.0"`.
3. Access the UI from any device on your local network (e.g., `http://192.168.1.50:7890`).
*(Note: Browser microphone access requires HTTPS or localhost. If using on mobile via local network, you may need to use a reverse proxy like Ngrok or configure local SSL certificates.)*

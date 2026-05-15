# JARVIS AI Assistant

## Project Structure

```
jarvis/
├── core/
│   ├── brain.py        # Authoritative brain — intent + response routing
│   ├── nlp.py          # NLP engine — intent classification
│   ├── ai_brain.py     # Groq + Gemini hybrid LLM routing
│   ├── cache.py        # SQLite response cache with fuzzy matching
│   └── rate_guard.py   # API rate limit tracking
├── services/
│   ├── tts.py          # Text-to-speech (pyttsx3 → gTTS fallback)
│   ├── stt.py          # Speech-to-text (Azure → Google → Vosk fallback)
│   ├── data_collector.py  # Weather (wttr.in) + Wikipedia
│   └── iot.py          # Local smart device control
├── ui/
│   └── app.py          # Flask web UI
├── tests/
│   └── test_jarvis.py  # Consolidated test suite
└── main.py             # Single entry point
data/                   # Runtime files (gitignored)
models/                 # Vosk STT model (gitignored)
.env                    # Secrets (gitignored — copy from .env.example)
.env.example            # Template — safe to commit
requirements.txt        # Single pinned requirements file
```

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env       # Windows
cp .env.example .env         # Linux/macOS
# Edit .env and fill in GROQ_API_KEY, GEMINI_API_KEY, FLASK_SECRET_KEY

# 4. Run
python -m jarvis.main              # Voice mode
python -m jarvis.main --text       # Text mode (no mic)
python -m jarvis.main --web        # Web UI at http://localhost:5000
```

## Running Tests

```bash
pytest jarvis/tests/ -v --cov=jarvis
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq LLM API key | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `FLASK_SECRET_KEY` | Flask session secret | — |
| `JARVIS_AI_MODE` | `hybrid` / `groq` / `gemini` / `offline` | `hybrid` |
| `JARVIS_STT_ENGINE` | `auto` / `google` / `azure` / `vosk` | `google` |
| `JARVIS_TTS_MODE` | `fast` (pyttsx3) / `hq` (edge-tts) | `fast` |
| `VOSK_MODEL_PATH` | Path to Vosk model directory | `models/vosk-model-small-en-us-0.15` |

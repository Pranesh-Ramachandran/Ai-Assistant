@echo off
set FLASK_SECRET_KEY=jarvis-dev-secret-2024
set JARVIS_AI_MODE=hybrid
cd /d d:\ai
start "" venv311\Scripts\pythonw.exe -m jarvis.main

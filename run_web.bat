@echo off
set FLASK_SECRET_KEY=jarvis-dev-secret-2024
echo Starting JARVIS Web UI at http://localhost:5000
echo Press Ctrl+C to stop
d:\ai\venv311\Scripts\python.exe -c "import os; os.environ['FLASK_SECRET_KEY']='jarvis-dev-secret-2024'; from jarvis.ui.app import app; app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)"
pause

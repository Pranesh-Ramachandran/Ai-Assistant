@echo off
title JARVIS Neural Grid
color 0B

echo ========================================
echo    JARVIS AI ASSISTANT
echo ========================================
echo.

set PYTHON=python
if exist "d:\ai\venv311\Scripts\python.exe" (
    set PYTHON=d:\ai\venv311\Scripts\python.exe
)

echo Python: %PYTHON%
echo.
echo Starting JARVIS server...
echo Open browser at: http://localhost:7890
echo.
echo Press Ctrl+C to stop.
echo ========================================
echo.

cd /d d:\ai\AI_Assistant
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:7890"
%PYTHON% jarvis_grid_server.py

pause

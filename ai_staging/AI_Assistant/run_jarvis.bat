@echo off
title JARVIS AI Assistant
color 0B

echo ========================================
echo    JARVIS AI ASSISTANT — Neural Grid
echo ========================================
echo.

REM Clean up stale tmp files from previous sessions
del /q "%~dp0tmp*.json" 2>nul

REM Use venv311 if it exists (has all packages), else fallback to system python
set PYTHON=python
if exist "d:\ai\venv311\Scripts\python.exe" (
    set PYTHON=d:\ai\venv311\Scripts\python.exe
    echo Using venv311 Python environment
) else if exist "..\venv311\Scripts\python.exe" (
    set PYTHON=..\venv311\Scripts\python.exe
    echo Using venv311 Python environment
) else (
    echo Using system Python
)

echo.
%PYTHON% --version
echo.

REM Launch JARVIS Grid Server
echo Starting JARVIS Neural Grid Server...
echo   URL: http://localhost:7890
echo   Press Ctrl+C to stop
echo.
echo ========================================
echo.

REM Launch browser after a brief delay so server has time to start
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:7890"

REM Start the server in foreground
%PYTHON% jarvis_grid_server.py

echo.
echo JARVIS closed.
pause
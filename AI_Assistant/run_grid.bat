@echo off
title JARVIS Neural Grid
color 0B

echo ========================================
echo    JARVIS — Neural Grid Desktop App
echo ========================================
echo.

set PYTHON=python
if exist "d:\ai\venv311\Scripts\python.exe" (
    set PYTHON=d:\ai\venv311\Scripts\python.exe
)

echo Python: %PYTHON%
echo Starting JARVIS Neural Grid...
echo.

cd /d d:\ai\AI_Assistant
%PYTHON% jarvis_grid_app.py

pause

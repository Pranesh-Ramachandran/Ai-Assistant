#!/bin/bash

# Jarvis AI Assistant - Launcher Script for Linux/Mac
# Make executable with: chmod +x run_jarvis.sh

echo "========================================"
echo "   JARVIS AI ASSISTANT - LAUNCHER"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ ERROR: Python is not installed"
        echo "Please install Python 3.8+ from python.org"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "✅ Python found: $($PYTHON_CMD --version)"
echo

# Check if main file exists
if [ ! -f "jarvis_welcome_ui.py" ]; then
    echo "⚠️ Welcome UI not found. Running fallback..."
    if [ -f "jarvis_refined.py" ]; then
        $PYTHON_CMD jarvis_refined.py
    else
        $PYTHON_CMD quick_start.py
    fi
    exit 0
fi

# Try to run Jarvis Welcome UI
echo "🚀 Starting Jarvis AI Assistant with Welcome UI..."
echo
echo "Controls:"
echo "- Follow the welcome setup process"
echo "- Say 'Hey Jarvis' to activate voice"
echo "- Use the GUI buttons and text input"
echo "- Close window to exit"
echo
echo "========================================"
echo

$PYTHON_CMD jarvis_welcome_ui.py

echo
echo "👋 Jarvis AI Assistant closed."
echo "Press Enter to exit..."
read
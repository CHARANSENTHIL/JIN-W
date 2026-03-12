@echo off
title JARVIS - Autonomous AI PC Assistant
color 0B

echo.
echo  ==========================================
echo   JARVIS - Autonomous AI PC Assistant
echo  ==========================================
echo.
echo  Starting JARVIS...
echo  Make sure Ollama is running: ollama serve
echo.

cd /d "%~dp0"

echo Starting Python Backend...
set PYTHONPATH=%~dp0
.\venv\Scripts\python.exe -m jarvis.main %*

pause

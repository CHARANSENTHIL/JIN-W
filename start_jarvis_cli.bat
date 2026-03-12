@echo off
title JARVIS CLI Mode
color 0A
cd /d "%~dp0"
echo Starting JARVIS in CLI mode...
python jarvis/main.py cli
pause

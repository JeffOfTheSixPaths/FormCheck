@echo off
title FormCheck - Biomechanical AI Training Platform
cd /d "%~dp0"
echo =======================================================
echo   Launching FormCheck Desktop Application
echo =======================================================
call .venv\Scripts\activate
python main.py
pause

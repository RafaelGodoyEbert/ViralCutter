@echo off
setlocal
title ViralCutter

cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main_improved.py
echo.
pause
@echo off
setlocal
title ViralCutter - Visual Opus Quality
echo ==========================================
echo  ViralCutter - Visual Opus Quality WebUI
echo ==========================================
echo.
echo  Pipeline: Denoise - Auto Illumination - Color Grading - Unsharp
echo  Blur Background + YOLO Talking-Head disponiveis!
echo.
echo ==========================================

cd /d "%~dp0"
call .venv\Scripts\activate.bat

echo Iniciando WebUI...
echo.
python webui\app.py

echo.
pause

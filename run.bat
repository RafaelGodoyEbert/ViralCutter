@echo off
setlocal
title ViralCutter - Visual Opus Quality
echo ==========================================
echo  ViralCutter - Visual Opus Quality (CLI)
echo ==========================================
echo.
echo  Pipeline: Denoise - Auto Illumination - Color Grading - Unsharp
echo  Use --no-face-mode blur para Blur Background!
echo.
echo ==========================================

cd /d "%~dp0"
call .venv\Scripts\activate.bat

echo Iniciando ViralCutter...
echo.
python main_improved.py %*

echo.
pause
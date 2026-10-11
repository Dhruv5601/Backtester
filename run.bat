@echo off
cd /d "%~dp0"
title Quant Backtester

echo ========================================
echo       Quant Backtester
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Running initial setup...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo Checking and installing required libraries...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Starting Quant Backtester...
echo Your dashboard will open in your browser.
echo Keep this window open while using the app.
echo.

start "" powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000'"

".venv\Scripts\python.exe" app.py

echo.
echo Backtester stopped.
pause

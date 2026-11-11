@echo off
title NeuroPredict Local Assessment Platform
echo ===================================================================
echo   Starting NeuroPredict Local Assessment Platform
echo ===================================================================
echo.

cd /d "%~dp0backend"
echo [1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...
start "NeuroPredict Backend API" uvicorn main:app --host 127.0.0.1 --port 8000 --reload

timeout /t 2 >nul

cd /d "%~dp0frontend"
echo [2/2] Opening NeuroPredict Web Interface...
start "" index.html

echo.
echo ===================================================================
echo   Backend running at: http://127.0.0.1:8000
echo   Health check URL:   http://127.0.0.1:8000/health
echo   API Documentation:  http://127.0.0.1:8000/docs
echo   Frontend launched in your default browser.
echo ===================================================================
echo.
pause

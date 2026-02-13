@echo off
chcp 65001 >nul
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1
timeout /t 2 /nobreak >nul
echo Starting OpenCode server...
start /MIN python run_server.py
timeout /t 6 /nobreak >nul
echo Testing connection...
curl -s http://localhost:8088/
echo.
echo Server should be running now.

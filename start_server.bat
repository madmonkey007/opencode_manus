@echo off
echo ========================================
echo OpenCode Server Starting...
echo ========================================
echo.
echo [1/2] Stopping old services...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo Done.
echo.
echo [2/2] Starting server...
echo.
echo URL: http://localhost:8088
echo New API: http://localhost:8088?use_new_api=true
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.
cd /d D:\Manus\opencode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info
pause

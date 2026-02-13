@echo off
echo ========================================
echo Starting OpenCode Server
echo ========================================
echo.
cd /d D:\Manus\opencode
echo Current directory: %CD%
echo.
echo Starting uvicorn on port 8088...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info
echo.
echo ========================================
echo Server stopped. Press any key to exit.
echo ========================================
pause

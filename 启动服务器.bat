@echo off
REM ============================================================
REM OpenCode 服务器启动脚本（前台运行）
REM ============================================================
chcp 65001 >nul

echo ============================================================
echo   OpenCode 服务器启动脚本
echo ============================================================
echo.

REM 停止旧服务
echo [1/2] 清理旧服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo 完成.
echo.

REM 启动服务器（前台运行）
echo [2/2] 启动服务器...
echo.
echo ============================================================
echo   服务器正在启动...
echo   地址: http://localhost:8088
echo   新 API: http://localhost:8088?use_new_api=true
echo ============================================================
echo.
echo 按 Ctrl+C 停止服务器
echo.

cd /d "%~dp0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info

pause

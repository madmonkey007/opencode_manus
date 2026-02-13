@echo off
echo ============================================================
echo 完全重启OpenCode服务器
echo ============================================================
echo.

echo [1/2] 停止所有Python进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo 完成.

echo.
echo [2/2] 启动新的服务器（使用修复后的代码）...
cd /d "%~dp0"
start "OpenCode Server" python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info

echo.
echo ============================================================
echo 服务器已在新窗口启动
echo 请访问 http://localhost:8088 测试
echo ============================================================
echo.
pause

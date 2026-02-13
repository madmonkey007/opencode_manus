@echo off
echo ============================================================
echo 启动OpenCode本地服务器
echo ============================================================
echo.

echo [1/3] 停止所有Python进程...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo 完成.

echo.
echo [2/3] 启动服务器...
cd /d D:\Manus\opencode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8088
echo.

echo ============================================================
echo 服务器已在新窗口启动
echo 浏览器访问: http://localhost:8088
echo.
echo 如需停止服务器，关闭此窗口或按 Ctrl+C
echo ============================================================
pause

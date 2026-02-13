@echo off
REM ============================================================
REM OpenCode服务器启动脚本（修复版）
REM ============================================================

echo OpenCode服务器启动脚本（修复版）
echo ============================================================
echo.

REM 停止旧服务
echo [1/2] 清理旧服务...
taskkill /F /IM python.exe /T 2>nul
timeout /t 1 /nobreak >nul
echo 完成.

echo.
REM 启动服务器（后台运行）
echo [2/2] 启动服务器（后台运行）...
echo.

cd /d "%~dp0"
start /B opencode-server.exe /MIN opencode-server.exe -LogToLogs --OpenAPIServerToken=your_token_here --ProxyUrl

REM 如果需要前台运行，注释下面两行，取消上面的后台运行
REM python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info

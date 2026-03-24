@echo off
echo ========================================
echo OpenCode 服务修复脚本
echo ========================================
echo.

echo 1. 查找占用8089端口的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8089') do (
    set PID=%%a
    goto :found
)

echo 没有找到占用8089端口的进程
goto :start

:found
echo 发现占用8089端口的进程: !PID!
echo 进程详情:
wmic process where processid=!PID! get processid,name,commandline
echo.
echo 正在终止进程...
taskkill /F /PID !PID!
if errorlevel 1 (
    echo 终止进程失败
) else (
    echo 进程已终止
)
echo.

:start
echo 2. 清理旧的Python进程...
taskkill /F /IM python.exe >nul 2>&1
echo.

echo 3. 启动OpenCode服务...
cd /d D:\manus\opencode
start /B python -m app.main > logs\service.log 2>&1

echo.
echo 4. 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo 5. 检查服务状态...
tasklist | findstr python.exe
echo.

echo 6. 检查端口...
netstat -ano | findstr :8089
echo.

echo ========================================
echo 服务启动完成！
echo ========================================
echo.
echo 查看日志:
echo   tail -f logs/app.err.log
echo.
echo 或访问:
echo   http://localhost:8089
echo.
pause

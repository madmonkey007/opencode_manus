@echo off
chcp 65001 >nul
echo ========================================
echo   验证所有前端修复
echo ========================================
echo.

REM 1. 停止旧服务
echo [1/3] 停止旧服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM 2. 启动服务器
echo [2/3] 启动服务器...
start /MIN python run_server.py
timeout /t 6 /nobreak >nul

REM 3. 测试连接
echo [3/3] 测试服务器连接...
curl -s http://localhost:8088/ >nul
if errorlevel 1 (
    echo [ERROR] 服务器启动失败
    pause
    exit /b 1
)

echo [OK] 服务器运行中
echo.
echo ========================================
echo   浏览器测试地址
echo ========================================
echo.
echo 主页:    http://localhost:8088
echo 新 API:  http://localhost:8088?use_new_api=true
echo.
echo 打开浏览器控制台（F12）验证以下错误已消失：
echo   1. 无限循环的 [NewAPI] submitTask not found
echo   2. Uncaught SyntaxError: Unexpected string
echo   3. window.timelineProgress.onStepClick is not a function
echo.
echo 停止服务: taskkill /F /IM python.exe
echo.
pause

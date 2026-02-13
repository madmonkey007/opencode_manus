@echo off
chcp 65001 >nul
echo ============================================================
echo   OpenCode 服务器一键启动和验证
echo ============================================================
echo.

REM 1. 停止旧服务
echo [步骤 1/3] 停止旧服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo 完成.
echo.

REM 2. 启动服务器
echo [步骤 2/3] 启动服务器...
echo 在新窗口中启动 OpenCode 服务器...
start "OpenCode Server" cmd /k "cd /d D:\manus\opencode && python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --log-level info"
echo 服务器已在新窗口中启动！
echo.

REM 3. 等待并测试
echo [步骤 3/3] 等待服务器启动...
timeout /t 8 /nobreak >nul
echo.
echo 测试服务器连接...
curl -s http://localhost:8088/ >nul
if errorlevel 1 (
    echo [警告] 服务器可能还在启动中，请稍后手动测试
    echo.
) else (
    echo [成功] 服务器已就绪！
    echo.
)

echo ============================================================
echo   测试地址
echo ============================================================
echo.
echo 主页:    http://localhost:8088
echo 新 API:  http://localhost:8088?use_new_api=true
echo.
echo 验证步骤：
echo   1. 打开上面的地址
echo   2. 按 F12 打开控制台
echo   3. 确认以下错误已消失：
echo      - 无限循环的 [NewAPI] submitTask not found
echo      - Uncaught SyntaxError: Unexpected string
echo      - window.timelineProgress.onStepClick is not a function
echo.
echo 停止服务: taskkill /F /IM python.exe
echo.
echo ============================================================
echo.
pause

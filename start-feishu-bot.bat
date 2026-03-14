@echo off
chcp 65001 >nul
echo ============================================================
echo  OpenCode Feishu Bot - Event Listener
echo ============================================================
echo.

echo [START] Starting Feishu Event Listener...
echo.

REM 启动飞书事件接收服务器
start "Feishu Event Listener" cmd /k "node feishu-event-listener.js"

echo.
echo [WAIT] Waiting for server to start (3 seconds)...
timeout /t 3 /nobreak > nul

echo [TEST] Checking server status...
curl -s http://localhost:3000/health >nul 2>&1

if errorlevel 1 (
    echo [!] Server not responding
    echo.
    echo Please check:
    echo   1. Feishu Event Listener window started properly
    echo   2. Port 3000 is not occupied
    echo.
) else (
    echo [OK] Server is running
)

echo.
echo ============================================================
echo  Setup Complete!
echo ============================================================
echo.
echo Services running:
echo   1. Feishu Event Listener (port 3000) - Receives @mentions
echo   2. IM Bridge (port 18080) - Sends results to Feishu
echo.
echo Next steps:
echo   1. Create Feishu app at https://open.feishu.cn/
echo   2. Get AppID and AppSecret
echo   3. Update configs/feishu-config.json
echo   4. Restart this server
echo   5. Test: @opencode 创建一个Python脚本计算1+1
echo.

pause

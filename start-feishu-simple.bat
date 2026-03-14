@echo off
chcp 65001 >nul
echo ============================================================
echo  OpenCode Feishu Bot - Start
echo ============================================================
echo.

echo [START] Starting IM Bridge Server with Feishu...
echo.

REM Load environment variables from .env.feishu
for /f "tokens=1,2 delims==" %%a in (.env.feishu) do (
    set %%a=%%b
)

REM Set environment variables
set IM_PLATFORM=feishu
set FEISHU_ENABLE=true
set FEISHU_WEBHOOK_URL=%FEISHU_WEBHOOK_URL%
set FEISHU_ENABLED_EVENTS=complete,error,phase
set IM_BRIDGE_PORT=18080

echo [INFO] Configuration:
echo   Platform: Feishu
echo   Webhook: %FEISHU_WEBHOOK_URL:~0,50%...
echo   Port: %IM_BRIDGE_PORT%
echo.

echo [START] Launching IM Bridge Server...
start "IM Bridge - Feishu" cmd /k "node im-bridge-server.js"

echo [OK] IM Bridge Server started!
echo.
echo You can now submit OpenCode tasks.
echo Notifications will be sent to your Feishu group.
echo.
echo To stop: Close the IM Bridge window
echo.

timeout /t 2 >nul
exit

@echo off
chcp 65001 >nul
echo ============================================================
echo  OpenCode Feishu Bot - Quick Setup
echo ============================================================
echo.

REM Check if .env.feishu exists
if exist .env.feishu (
    echo [INFO] Found existing .env.feishu file
    echo.
    set /p RELOAD="Reconfigure? (y/n): "
    if /i not "%RELOAD%"=="y" (
        echo.
        echo [SKIP] Using existing configuration
        goto :start
    )
)

echo.
echo ============================================================
echo  Feishu Bot Configuration Wizard
echo ============================================================
echo.
echo Please get your Feishu Webhook URL:
echo.
echo Steps:
echo   1. Open your Feishu group chat
echo   2. Click Group Settings → Group Bots → Add Bot
echo   3. Choose "Custom Bot"
echo   4. Copy the Webhook URL
echo.

REM Input Webhook URL
echo [CONFIG] Enter Feishu Webhook URL:
set /p FEISHU_WEBHOOK_URL=""

if "%FEISHU_WEBHOOK_URL%"=="" (
    echo [ERROR] Webhook URL cannot be empty
    pause
    exit /b 1
)

REM Validate Webhook URL format
echo %FEISHU_WEBHOOK_URL% | findstr /C:"https://open.feishu.cn" >nul
if errorlevel 1 (
    echo.
    echo [WARNING] URL doesn't look like a Feishu webhook
    echo Expected format: https://open.feishu.cn/open-apis/bot/v2/hook/...
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" (
        pause
        exit /b 1
    )
)

REM Create config file
echo.
echo [WRITE] Creating .env.feishu configuration file...

(
    echo # Feishu Bot Configuration
    echo # Generated: %date% %time%
    echo.
    echo FEISHU_ENABLE=true
    echo IM_PLATFORM=feishu
    echo FEISHU_WEBHOOK_URL=%FEISHU_WEBHOOK_URL%
    echo FEISHU_ENABLED_EVENTS=complete,error,phase
    echo IM_BRIDGE_PORT=18080
) > .env.feishu

echo [OK] Configuration file created
echo.

:start
REM Load configuration and start server
echo ============================================================
echo  Starting IM Bridge Server
echo ============================================================
echo.

echo [LOAD] Loading configuration from .env.feishu...
for /f "tokens=1,2 delims==" %%a in (.env.feishu) do (
    set %%a=%%b
)

echo [OK] Configuration loaded
echo.
echo   Platform: Feishu
echo   Webhook: %FEISHU_WEBHOOK_URL:~0,50%...
echo   Port: %IM_BRIDGE_PORT%
echo.

echo [START] IM Bridge Server...
echo.

REM Set environment variables
set IM_PLATFORM=feishu
set FEISHU_ENABLE=true
set FEISHU_WEBHOOK_URL=%FEISHU_WEBHOOK_URL%
set FEISHU_ENABLED_EVENTS=complete,error,phase
set IM_BRIDGE_PORT=18080

start "IM Bridge" cmd /k "node im-bridge-server.js"

echo.
echo [WAIT] Waiting for server to start (3 seconds)...
timeout /t 3 /nobreak > nul

echo [TEST] Checking server status...
curl -s http://localhost:18080/health >nul 2>&1

if errorlevel 1 (
    echo.
    echo [!] Server not responding
    echo.
    echo Please check:
    echo   1. IM Bridge window started properly
    echo   2. Port 18080 is not occupied
    echo.
    echo Press any key to exit...
    pause > nul
    exit /b 1
)

echo [OK] IM Bridge server is running
echo.

REM Display summary
echo ============================================================
echo  Setup Complete!
echo ============================================================
echo.
echo Configuration:
echo   Platform: Feishu (Webhook)
echo   Status: Ready
echo.
echo Next steps:
echo   1. Submit an OpenCode task
echo   2. Check if Feishu group receives notification
echo.
echo Test command:
echo   curl -X POST http://localhost:18080/test/event ^
echo     -H "Content-Type: application/json" ^
echo     -d "{\"event_type\":\"complete\",\"data\":{\"result\":\"success\"}}"
echo.
echo To stop: Close the IM Bridge window
echo.

pause

@echo off
echo ============================================================
echo  OpenCode QQ Official Bot - Quick Setup
echo ============================================================
echo.

REM Check if .env exists
if exist .env (
    echo [INFO] Found existing .env file
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
echo  QQ Official Bot Configuration Wizard
echo ============================================================
echo.
echo Please prepare:
echo   1. QQ Bot AppID (from https://bot.q.qq.com)
echo   2. QQ Bot Token (from https://bot.q.qq.com)
echo   3. Your OpenID (user ID to receive notifications)
echo.

REM Input AppID
echo [CONFIG] Enter QQ Bot AppID:
set /p QQ_APP_ID=""

if "%QQ_APP_ID%"=="" (
    echo [ERROR] AppID cannot be empty
    pause
    exit /b 1
)

REM Input Token
echo.
echo [CONFIG] Enter QQ Bot Token:
set /p QQ_TOKEN=""

if "%QQ_TOKEN%"=="" (
    echo [ERROR] Token cannot be empty
    pause
    exit /b 1
)

REM Input OpenID
echo.
echo [CONFIG] Enter your OpenID (user to receive notifications):
set /p QQ_OPENID=""

if "%QQ_OPENID%"=="" (
    echo [ERROR] OpenID cannot be empty
    pause
    exit /b 1
)

REM Environment selection
echo.
echo [CONFIG] Select environment:
echo   1. Production
echo   2. Sandbox (for testing)
set /p ENV_CHOICE="Choose (1/2): "

if "%ENV_CHOICE%"=="2" (
    set QQ_SANDBOX=true
) else (
    set QQ_SANDBOX=false
)

REM Create config file
echo.
echo [WRITE] Creating .env configuration file...

(
    echo # QQ Official Bot Configuration
    echo # Generated: %date% %time%
    echo.
    echo QQ_ENABLE=true
    echo QQ_BOT_TYPE=official
    echo QQ_APP_ID=%QQ_APP_ID%
    echo QQ_TOKEN=%QQ_TOKEN%
    echo QQ_SANDBOX=%QQ_SANDBOX%
    echo QQ_TARGETS=user:%QQ_OPENID%
    echo QQ_ENABLED_EVENTS=complete,error,phase
    echo IM_BRIDGE_PORT=18080
) > .env

echo [OK] Configuration file created
echo.

:start
REM Start IM Bridge server
echo ============================================================
echo  Starting IM Bridge Server
echo ============================================================
echo.

echo [START] IM Bridge server (port 18080)...
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

REM Display configuration summary
echo ============================================================
echo  Configuration Complete!
echo ============================================================
echo.
echo Running services:
echo   1. IM Bridge (port 18080) - Message forwarding
echo.
echo Configuration:
echo   Bot Type: QQ Official Bot
echo   AppID: %QQ_APP_ID%
echo   Environment: %QQ_SANDBOX%
echo   Target: user:%QQ_OPENID%
echo.
echo Next steps:
echo   1. Submit an OpenCode task
echo   2. Check if you receive QQ notification
echo.
echo Test command:
echo   curl -X POST http://localhost:18080/test/event ^
echo     -H "Content-Type: application/json" ^
echo     -d "{\"event_type\":\"complete\",\"data\":{\"result\":\"success\"}}"
echo.
echo To stop: Close the IM Bridge window
echo.

pause

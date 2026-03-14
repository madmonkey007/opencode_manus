@echo off
chcp 65001 >nul
echo ============================================================
echo  Start IM Bridge with QQ Bot Support
echo ============================================================
echo.

REM Load QQ configuration from .env.qq if exists
if exist .env.qq (
    echo [INFO] Loading QQ configuration from .env.qq
    for /f "tokens=1,2 delims==" %%a in (.env.qq) do (
        set %%a=%%b
    )
    echo [OK] Configuration loaded
    echo.
)

REM Check if QQ is enabled
if "%QQ_ENABLE%"=="true" (
    echo [QQ Bot] Status: ENABLED
    echo [QQ Bot] Type: %QQ_BOT_TYPE%
    echo [QQ Bot] AppID: %QQ_APP_ID%
    echo [QQ Bot] Target: %QQ_TARGETS%
    echo.
) else (
    echo [QQ Bot] Status: NOT CONFIGURED
    echo.
    echo Please configure .env.qq file first:
    echo   1. Edit .env.qq
    echo   2. Set QQ_APP_ID and QQ_TOKEN
    echo   3. Set QQ_TARGETS to your OpenID
    echo.
    pause
    exit /b 1
)

REM Start IM Bridge server
echo [START] IM Bridge Server (port 18080)...
echo.

REM Pass environment variables to the server
set QQ_ENABLE=%QQ_ENABLE%
set QQ_BOT_TYPE=%QQ_BOT_TYPE%
set QQ_APP_ID=%QQ_APP_ID%
set QQ_TOKEN=%QQ_TOKEN%
set QQ_SANDBOX=%QQ_SANDBOX%
set QQ_TARGETS=%QQ_TARGETS%
set QQ_ENABLED_EVENTS=%QQ_ENABLED_EVENTS%
set IM_BRIDGE_PORT=%IM_BRIDGE_PORT%

start "IM Bridge" cmd /k "node im-bridge-server.js"

echo [OK] IM Bridge started
echo.
echo Test: curl -X POST http://localhost:18080/test/event -H "Content-Type: application/json" -d "{\"event_type\":\"complete\",\"data\":{\"result\":\"success\"}}"
echo.

pause

@echo off
REM OpenCode IM Bridge Server 启动脚本

echo.
echo ========================================
echo OpenCode IM Bridge Server Launcher
echo ========================================
echo.

REM 检查Node.js是否安装
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到Node.js，请先安装Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Node.js已安装
node --version

echo.
echo [1/3] 检查依赖...
if not exist node_modules (
    echo [!] 依赖未安装，正在安装...
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [OK] 依赖已安装
)

echo.
echo [2/3] 配置环境变量...
set IM_BRIDGE_PORT=18080
echo [OK] IM Bridge端口: %IM_BRIDGE_PORT%

echo.
echo [3/3] 启动服务器...
echo.
node im-bridge-server.js

pause

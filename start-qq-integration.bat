@echo off
REM OpenCode QQ Bot 一键启动脚本

echo.
echo ============================================================
echo  OpenCode QQ Bot 一键启动
echo ============================================================
echo.

REM ============================================================================
REM 检查go-cqhttp
REM ============================================================================

echo [检查] go-cqhttp安装...
if not exist go-cqhttp (
    echo [!] go-cqhttp未安装
    echo.
    echo 正在运行安装脚本...
    call install-go-cqhttp.bat

    if errorlevel 1 (
        echo [错误] 安装失败，请手动安装
        pause
        exit /b 1
    )
)

echo [OK] go-cqhttp已安装
echo.

REM ============================================================================
REM 配置环境变量
REM ============================================================================

echo [配置] QQ Bot环境变量...

REM 提示用户输入QQ号
echo.
echo 请输入你的QQ号（用于接收通知）:
set /p YOUR_QQ="QQ号: "

if "%YOUR_QQ%"=="" (
    echo [错误] QQ号不能为空
    pause
    exit /b 1
)

REM 设置环境变量
set QQ_ENABLE=true
set QQ_TARGETS=user:%YOUR_QQ%
set QQ_ENABLED_EVENTS=complete,error,phase
set QQ_API_URL=http://localhost:3000

echo [OK] 环境变量已配置:
echo   QQ_ENABLE=%QQ_ENABLE%
echo   QQ_TARGETS=%QQ_TARGETS%
echo   QQ_ENABLED_EVENTS=%QQ_ENABLED_EVENTS%
echo   QQ_API_URL=%QQ_API_URL%
echo.

REM ============================================================================
REM 启动服务
REM ============================================================================

echo [启动] go-cqhttp...
echo.
echo 提示: 如果是首次运行，请用手机QQ扫码登录
echo.

start "go-cqhttp" cmd /k "cd go-cqhttp && echo go-cqhttp运行中... && go-cqhttp.exe"

REM 等待go-cqhttp启动
echo.
echo 等待go-cqhttp启动...
timeout /t 5 /nobreak > nul

REM ============================================================================
REM 检查go-cqhttp状态
REM ============================================================================

echo [检查] go-cqhttp运行状态...
curl -s http://localhost:3000/get_login_info > nul 2>&1

if errorlevel 1 (
    echo.
    echo [!] go-cqhttp启动失败或未登录
    echo.
    echo 请检查:
    echo   1. 是否已用手机QQ扫码登录
    echo   2. go-cqhttp窗口是否有错误信息
    echo.
    pause
    exit /b 1
)

echo [OK] go-cqhttp运行正常
echo.

REM ============================================================================
REM 启动IM Bridge服务器
REM ============================================================================

echo [启动] IM Bridge服务器（带QQ配置）...
echo.

start "IM Bridge" cmd /k "echo IM Bridge服务器运行中... && set QQ_ENABLE=true && set QQ_TARGETS=user:%YOUR_QQ% && set QQ_ENABLED_EVENTS=complete,error,phase && set QQ_API_URL=http://localhost:3000 && node im-bridge-server.js"

REM 等待IM Bridge启动
echo 等待IM Bridge启动...
timeout /t 3 /nobreak > nul

echo.
echo ============================================================
echo  启动完成！
echo ============================================================
echo.
echo 运行的服务:
echo   1. go-cqhttp - QQ Bot框架 (端口3000)
echo   2. IM Bridge - 消息转发服务器 (端口18080)
echo.
echo 下一步:
echo   1. 确保已用手机QQ扫码登录go-cqhttp
echo   2. 运行测试: python tests\test_qq_integration.py
echo   3. 或手动测试: curl -X POST http://localhost:18080/test/event
echo.
echo 停止服务: 直接关闭对应窗口即可
echo.
pause

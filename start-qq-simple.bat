@echo off
chcp 65001 >nul
echo ============================================================
echo  OpenCode QQ Bot - 简化启动
echo ============================================================
echo.

REM ============================================================================
REM 检查go-cqhttp
REM ============================================================================

if exist go-cqhttp\go-cqhttp.exe (
    echo [OK] go-cqhttp已安装
    echo.
) else (
    echo [ERROR] go-cqhttp未找到
    echo.
    echo 请先安装go-cqhttp:
    echo   1. 访问 https://github.com/Mrs4s/go-cqhttp/releases
    echo   2. 下载 go-cqhttp_windows_amd64.zip
    echo   3. 解压到当前目录
    echo   4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM 配置环境变量
REM ============================================================================

echo [配置] 请输入你的QQ号:
set /p YOUR_QQ=""

if "%YOUR_QQ%"=="" (
    echo [ERROR] QQ号不能为空
    pause
    exit /b 1
)

set QQ_ENABLE=true
set QQ_TARGETS=user:%YOUR_QQ%
set QQ_ENABLED_EVENTS=complete,error,phase
set QQ_API_URL=http://localhost:3000

echo.
echo [OK] 配置完成:
echo   QQ_ENABLE=%QQ_ENABLE%
echo   QQ_TARGETS=%QQ_TARGETS%
echo   QQ_ENABLED_EVENTS=%QQ_ENABLED_EVENTS%
echo.

REM ============================================================================
REM 启动服务
REM ============================================================================

echo [启动] go-cqhttp...
start "go-cqhttp" cmd /k "cd go-cqhttp && echo go-cqhttp正在运行... && go-cqhttp.exe"

echo.
echo [等待] 等待go-cqhttp启动（5秒）...
timeout /t 5 /nobreak > nul

echo [检查] 检查go-cqhttp状态...
curl -s http://localhost:3000/get_login_info >nul 2>&1

if errorlevel 1 (
    echo.
    echo [!] go-cqhttp未就绪
    echo.
    echo 请检查:
    echo   1. go-cqhttp窗口是否显示二维码
    echo   2. 用手机QQ扫码登录
    echo   3. 完成设备验证
    echo.
    echo 登录成功后，按任意键继续...
    pause > nul
)

echo [OK] go-cqhttp运行正常
echo.

REM ============================================================================
REM 启动IM Bridge
REM ============================================================================

echo [启动] IM Bridge服务器...
start "IM Bridge" cmd /k "echo IM Bridge服务器运行中... && set QQ_ENABLE=true && set QQ_TARGETS=user:%YOUR_QQ% && set QQ_ENABLED_EVENTS=complete,error,phase && node im-bridge-server.js"

echo.
echo [等待] 等待IM Bridge启动（3秒）...
timeout /t 3 /nobreak > nul

REM ============================================================================
REM 完成提示
REM ============================================================================

echo.
echo ============================================================
echo  启动完成！
echo ============================================================
echo.
echo 运行的服务:
echo   1. go-cqhttp (端口3000) - QQ Bot框架
echo   2. IM Bridge (端口18080) - 消息转发
echo.
echo 下一步:
echo   1. 检查go-cqhttp窗口，确保已扫码登录
echo   2. 运行测试: python tests\test_qq_integration.py
echo   3. 或手动测试: curl -X POST http://localhost:18080/test/event
echo.
echo 停止服务: 关闭对应窗口即可
echo.

pause

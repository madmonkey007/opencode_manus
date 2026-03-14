@echo off
chcp 65001 >nul
echo ============================================================
echo  OpenCode QQ Bot - 官方机器人快速配置
echo ============================================================
echo.

REM 检查是否已有配置
if exist .env (
    echo [提示] 发现现有 .env 配置文件
    echo.
    set /p RELOAD="是否重新配置？(y/n): "
    if /i not "%RELOAD%"=="y" (
        echo.
        echo [跳过] 使用现有配置
        goto :start
    )
)

echo.
echo ============================================================
echo  QQ官方机器人配置向导
echo ============================================================
echo.
echo 请准备以下信息：
echo   1. QQ机器人AppID（从 https://bot.q.qq.com 获取）
echo   2. QQ机器人Token（从 https://bot.q.qq.com 获取）
echo   3. 你的OpenID（机器人的用户ID）
echo.

REM 输入AppID
echo [配置] 请输入QQ机器人AppID:
set /p QQ_APP_ID=""

if "%QQ_APP_ID%"=="" (
    echo [错误] AppID不能为空
    pause
    exit /b 1
)

REM 输入Token
echo.
echo [配置] 请输入QQ机器人Token:
set /p QQ_TOKEN=""

if "%QQ_TOKEN%"=="" (
    echo [错误] Token不能为空
    pause
    exit /b 1
)

REM 输入OpenID
echo.
echo [配置] 请输入你的OpenID（接收通知的QQ号）:
set /p QQ_OPENID=""

if "%QQ_OPENID%"=="" (
    echo [错误] OpenID不能为空
    pause
    exit /b 1
)

REM 环境选择
echo.
echo [配置] 选择运行环境:
echo   1. 生产环境
echo   2. 沙箱环境（测试）
set /p ENV_CHOICE="请选择 (1/2): "

if "%ENV_CHOICE%"=="2" (
    set QQ_SANDBOX=true
) else (
    set QQ_SANDBOX=false
)

REM 创建配置文件
echo.
echo [写入] 创建 .env 配置文件...

(
    echo # QQ官方机器人配置
    echo # 生成时间: %date% %time%
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

echo [OK] 配置文件已创建
echo.

:start
REM 启动IM Bridge服务器
echo ============================================================
echo  启动IM Bridge服务器
echo ============================================================
echo.

echo [启动] IM Bridge服务器（端口18080）...
start "IM Bridge" cmd /k "node im-bridge-server.js"

echo.
echo [等待] 等待服务器启动（3秒）...
timeout /t 3 /nobreak > nul

echo [测试] 检查服务器状态...
curl -s http://localhost:18080/health >nul 2>&1

if errorlevel 1 (
    echo.
    echo [!] 服务器未响应
    echo.
    echo 请检查:
    echo   1. IM Bridge窗口是否正常启动
    echo   2. 端口18080是否被占用
    echo.
    echo 按任意键退出...
    pause > nul
    exit /b 1
)

echo [OK] IM Bridge服务器运行正常
echo.

REM 显示配置摘要
echo ============================================================
echo  配置完成！
echo ============================================================
echo.
echo 运行的服务:
echo   1. IM Bridge (端口18080) - 消息转发
echo.
echo 配置信息:
echo   机器人类型: QQ官方机器人
echo   AppID: %QQ_APP_ID%
echo   环境: %QQ_SANDBOX%
echo   推送目标: user:%QQ_OPENID%
echo.
echo 下一步:
echo   1. 提交一个OpenCode任务
echo   2. 检查QQ是否收到通知
echo.
echo 测试命令:
echo   curl -X POST http://localhost:18080/test/event ^
echo     -H "Content-Type: application/json" ^
echo     -d "{\"event_type\":\"complete\",\"data\":{\"result\":\"success\"}}"
echo.
echo 停止服务: 关闭IM Bridge窗口即可
echo.

pause

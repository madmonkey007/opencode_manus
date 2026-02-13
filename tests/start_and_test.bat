@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   OpenCode 完整测试脚本
echo   1. 停止旧服务
echo   2. 启动新服务
echo   3. 运行测试
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [WARNING] 建议以管理员身份运行此脚本
    echo           右键点击 - 以管理员身份运行
    echo.
)

REM 1. 停止所有 Python 进程
echo [步骤 1/4] 停止旧服务进程...
taskkill /F /IM python.exe >nul 2>&1
if errorlevel 1 (
    echo [INFO] 没有运行的 Python 进程
) else (
    echo [SUCCESS] 已停止旧服务
)

REM 等待端口释放
echo [INFO] 等待端口释放...
timeout /t 2 /nobreak >nul

REM 2. 检查依赖
echo.
echo [步骤 2/4] 检查 Python 依赖...
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 requests...
    pip install requests -q
)

python -c "import sseclient" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 sseclient-py...
    pip install sseclient-py -q
)

echo [SUCCESS] 依赖检查完成

REM 3. 启动服务器（后台）
echo.
echo [步骤 3/4] 启动 OpenCode 服务...
start /B python -m app.main >server_output.log 2>&1

REM 等待服务启动
echo [INFO] 等待服务启动（5秒）...
timeout /t 5 /nobreak >nul

REM 检查服务是否启动成功
curl -s http://localhost:8088 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    echo.
    echo 请查看 server_output.log 了解详情
    pause
    exit /b 1
)

echo [SUCCESS] 服务启动成功

REM 4. 运行测试
echo.
echo [步骤 4/4] 运行测试...
echo.

REM 选择测试类型
echo 请选择测试类型:
echo.
echo   1. 快速验证（推荐）
echo   2. 完整测试（约 30 秒）
echo   3. 浏览器测试
echo.

set /p test_type="请输入选项 (1-3): "

if "%test_type%"=="1" goto quick_test
if "%test_type%"=="2" goto full_test
if "%test_type%"=="3" goto browser_test
goto default

:quick_test
echo.
echo ========================================
echo   运行快速验证测试
echo ========================================
echo.
python tests\quick_verify.py
goto finish

:full_test
echo.
echo ========================================
echo   运行完整测试
echo ========================================
echo.
python tests\automated_test.py --skip-slow
goto finish

:browser_test
echo.
echo ========================================
echo   打开浏览器
echo ========================================
echo.
echo 测试地址：
echo.
echo   主页面: http://localhost:8088
echo   新 API:  http://localhost:8088?use_new_api=true
echo   旧 API:  http://localhost:8088?use_new_api=false
echo.
start http://localhost:8088?use_new_api=true
goto finish

:default
echo.
echo 运行默认测试...
python tests\quick_verify.py

:finish
echo.
echo ========================================
echo   测试完成
echo ========================================
echo.
echo 提示:
echo   - 服务器日志: server_output.log
echo   - 如需停止服务: taskkill /F /IM python.exe
echo.

pause

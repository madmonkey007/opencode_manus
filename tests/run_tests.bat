@echo off
REM OpenCode Web Interface - 测试脚本
REM 使用方法: run_tests.bat

chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   OpenCode Web Interface - 测试工具
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.11+
    pause
    exit /b 1
)

echo ✓ Python 已安装
echo.

REM 检查依赖
echo 正在检查依赖...

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo ❌ 缺少依赖: requests
    echo 正在安装: pip install requests
    pip install requests
    if errorlevel 1 (
        echo 安装失败，请手动执行: pip install requests
        pause
        exit /b 1
    )
)

python -c "import sseclient" >nul 2>&1
if errorlevel 1 (
    echo ❌ 缺少依赖: sseclient-py
    echo 正在安装: pip install sseclient-py
    pip install sseclient-py
    if errorlevel 1 (
        echo 安装失败，请手动执行: pip install sseclient-py
        pause
        exit /b 1
    )
)

echo ✓ 所有依赖已安装
echo.

REM 菜单选择
echo 请选择测试类型:
echo.
echo   1. 快速验证（推荐，约 10 秒）
echo   2. 完整测试（包含耗时测试，约 1 分钟）
echo   3. 详细测试（包含日志输出）
echo   4. 退出
echo.

set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" goto quick
if "%choice%"=="2" goto full
if "%choice%"=="3" goto verbose
if "%choice%"=="4" goto end
echo 无效选项，退出
goto end

:quick
echo.
echo ========================================
echo   运行快速验证测试
echo ========================================
echo.
python tests\quick_verify.py
goto end

:full
echo.
echo ========================================
echo   运行完整测试（跳过耗时测试）
echo ========================================
echo.
python tests\automated_test.py --skip-slow
goto end

:verbose
echo.
echo ========================================
echo   运行详细测试（包含日志输出）
echo ========================================
echo.
python tests\automated_test.py --verbose
goto end

:end
echo.
echo ========================================
echo   测试完成
echo ========================================
echo.
pause

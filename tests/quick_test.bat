@echo off
chcp 65001 >nul

echo ========================================
echo   OpenCode 一键测试
echo ========================================
echo.

REM 切换到项目目录
cd /d "%~dp0.."

REM 1. 停止旧服务
echo [1/4] 停止旧服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 /nobreak >nul

REM 2. 启动服务器（后台窗口）
echo [2/4] 启动服务器...
start /B python -m app.main >nul 2>&1
timeout /t 5 /nobreak >nul

REM 3. 检查服务
echo [3/4] 检查服务状态...
curl -s http://localhost:8088 >nul
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)
echo [OK] 服务运行中

REM 4. 运行测试
echo [4/4] 运行快速测试...
echo.
python tests\quick_verify.py

echo.
echo ========================================
echo   测试完成
echo ========================================
echo.
echo 提示:
echo   - 服务器仍在运行
echo   - 访问: http://localhost:8088
echo   - 停止: taskkill /F /IM python.exe
echo.

@echo off
echo === 启动OpenCode服务 ===
setlocal

REM 设置环境变量
set CORS_ORIGINS=http://localhost:3000,http://localhost:8089
set PYTHONIOENCODING=utf-8

echo 环境变量设置完成:
echo CORS_ORIGINS=%CORS_ORIGINS%
echo PYTHONIOENCODING=%PYTHONIOENCODING%
echo.

echo 启动服务...
python -m app.main

pause
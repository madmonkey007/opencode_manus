@echo off
chcp 65001 >nul
echo ========================================
echo   测试修复后的服务器
echo ========================================
echo.

REM 1. 停止所有 Python 进程
echo [1/3] 停止旧服务...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM 2. 启动服务器
echo [2/3] 启动服务器...
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8088 >server.log 2>&1
timeout /t 6 /nobreak >nul

REM 3. 测试 API
echo [3/3] 测试 API...
echo.
curl -s -X POST "http://localhost:8088/opencode/session" -H "Content-Type: application/json" -d "{\"title\": \"Test\"}"
echo.
echo.

REM 检查结果
curl -s "http://localhost:8088/openapi.json" | python -c "import sys,json; d=json.load(sys.stdin); print(f'总路由数: {len(d[\"paths\"])}'); print('/opencode/session 存在:', '/opencode/session' in d['paths'])"
echo.

echo ========================================
echo   测试完成
echo ========================================
echo.
echo 服务器日志: server.log
echo 停止服务: taskkill /F /IM python.exe
echo.
pause

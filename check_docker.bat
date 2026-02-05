@echo off
echo ========================================
echo OpenCode Docker 诊断工具
echo ========================================
echo.

echo [1/5] 检查Docker是否运行...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Docker正在运行
) else (
    echo [ERROR] Docker未运行！请启动Docker Desktop
    pause
    exit /b 1
)

echo.
echo [2/5] 检查opencode容器状态...
docker ps -a --filter "name=opencode" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo [3/5] 停止并删除旧容器...
docker-compose down 2>nul

echo.
echo [4/5] 构建Docker镜像...
docker-compose build

echo.
echo [5/5] 启动容器...
docker-compose up -d

echo.
echo ========================================
echo 查看容器日志...
echo ========================================
docker logs opencode-container

echo.
echo ========================================
echo 检查端口监听...
echo ========================================
netstat -ano | findstr ":8088"
netstat -ano | findstr ":6081"

echo.
echo ========================================
echo 诊断完成！
echo ========================================
echo.
echo 访问 http://localhost:8088 打开OpenCode
pause

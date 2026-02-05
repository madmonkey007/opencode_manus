@echo off
echo 启动OpenCode Docker容器...
cd /d D:\manus\opencode
docker-compose up -d
echo.
echo 容器已启动！
echo 访问地址: http://localhost:8088
echo VNC地址: http://localhost:6081/vnc.html
echo.
echo 查看日志: docker logs -f opencode-container
echo 停止容器: docker-compose down
pause

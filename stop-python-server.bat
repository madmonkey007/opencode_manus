@echo off
echo Stopping Python HTTP Server on port 8088...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8088" ^| find "LISTENING"') do (
    echo Killing process %%a
    taskkill /F /PID %%a
)
echo Port 8088 is now free. You can start Docker now.
pause

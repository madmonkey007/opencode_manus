@echo off
REM go-cqhttp 快速下载和安装脚本

echo.
echo ========================================
echo go-cqhttp 快速安装
echo ========================================
echo.

REM 设置版本号
set VERSION=v1.2.0
set ARCH=amd64

REM 选择下载镜像
echo 请选择下载镜像:
echo 1. GitHub官方 (可能较慢)
echo 2. 镜像站 (推荐)
echo.
set /p CHOICE="请输入选择 (1 或 2): "

if "%CHOICE%"=="1" (
    set DOWNLOAD_URL=https://github.com/Mrs4s/go-cqhttp/releases/download/%VERSION%/go-cqhttp_windows_%ARCH%.zip
) else (
    set DOWNLOAD_URL=https://ghproxy.com/https://github.com/Mrs4s/go-cqhttp/releases/download/%VERSION%/go-cqhttp_windows_%ARCH%.zip
)

echo.
echo [1/4] 下载go-cqhttp...
echo 从: %DOWNLOAD_URL%
echo.

REM 使用PowerShell下载
powershell -Command "& {Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile 'go-cqhttp.zip'}"

if not exist go-cqhttp.zip (
    echo [错误] 下载失败，请检查网络连接
    pause
    exit /b 1
)

echo [OK] 下载完成
echo.

echo [2/4] 解压文件...
REM 创建目录
if not exist go-cqhttp (
    mkdir go-cqhttp
)

REM 使用PowerShell解压
powershell -Command "& {Expand-Archive -Path 'go-cqhttp.zip' -DestinationPath 'go-cqhttp' -Force}"

echo [OK] 解压完成
echo.

echo [3/4] 清理临时文件...
del go-cqhttp.zip

echo [OK] 清理完成
echo.

echo [4/4] 下载完成！
echo.
echo 安装目录: %CD%\go-cqhttp
echo.
echo 下一步:
echo   1. cd go-cqhttp
echo   2. 双击运行 go-cqhttp.exe
echo   3. 使用手机QQ扫码登录
echo.

pause

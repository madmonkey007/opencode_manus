#!/bin/bash
# go-cqhttp 快速下载和安装脚本

echo ""
echo "========================================"
echo "go-cqhttp 快速安装"
echo "========================================"
echo ""

# 版本配置
VERSION="v1.2.0"
ARCH="amd64"

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "检测到Linux系统"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="darwin"
    echo "检测到macOS系统"
    ARCH="arm64"  # Mac M1/M2使用arm64
else
    echo "不支持的系统: $OSTYPE"
    exit 1
fi

# 选择下载镜像
echo ""
echo "请选择下载镜像:"
echo "1. GitHub官方 (可能较慢)"
echo "2. 镜像站 (推荐)"
echo ""
read -p "请输入选择 (1 或 2): " CHOICE

if [ "$CHOICE" == "1" ]; then
    DOWNLOAD_URL="https://github.com/Mrs4s/go-cqhttp/releases/download/${VERSION}/go-cqhttp_${OS}_${ARCH}.tar.gz"
else
    DOWNLOAD_URL="https://ghproxy.com/https://github.com/Mrs4s/go-cqhttp/releases/download/${VERSION}/go-cqhttp_${OS}_${ARCH}.tar.gz"
fi

echo ""
echo "[1/4] 下载go-cqhttp..."
echo "从: $DOWNLOAD_URL"
echo ""

# 下载
if command -v wget &> /dev/null; then
    wget -O go-cqhttp.tar.gz "$DOWNLOAD_URL"
elif command -v curl &> /dev/null; then
    curl -L -o go-cqhttp.tar.gz "$DOWNLOAD_URL"
else
    echo "错误: 需要wget或curl"
    exit 1
fi

if [ ! -f "go-cqhttp.tar.gz" ]; then
    echo "错误: 下载失败"
    exit 1
fi

echo "[OK] 下载完成"
echo ""

echo "[2/4] 解压文件..."
mkdir -p go-cqhttp
tar -xzf go-cqhttp.tar.gz -C go-cqhttp
echo "[OK] 解压完成"
echo ""

echo "[3/4] 清理临时文件..."
rm go-cqhttp.tar.gz
echo "[OK] 清理完成"
echo ""

echo "[4/4] 安装完成！"
echo ""
echo "安装目录: $(pwd)/go-cqhttp"
echo ""
echo "下一步:"
echo "  1. cd go-cqhttp"
echo "  2. ./go-cqhttp"
echo "  3. 使用手机QQ扫码登录"
echo ""

# 询问是否立即运行
read -p "是否立即运行go-cqhttp? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd go-cqhttp
    chmod +x go-cqhttp
    ./go-cqhttp
fi

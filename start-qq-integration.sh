#!/bin/bash
# OpenCode QQ Bot 一键启动脚本

echo ""
echo "============================================================"
echo " OpenCode QQ Bot 一键启动"
echo "============================================================"
echo ""

# ============================================================================
# 检查go-cqhttp
# ============================================================================

echo "[检查] go-cqhttp安装..."
if [ ! -d "go-cqhttp" ]; then
    echo "[!] go-cqhttp未安装"
    echo ""
    echo "正在运行安装脚本..."
    chmod +x install-go-cqhttp.sh
    ./install-go-cqhttp.sh

    if [ $? -ne 0 ]; then
        echo "[错误] 安装失败"
        exit 1
    fi
fi

echo "[OK] go-cqhttp已安装"
echo ""

# ============================================================================
# 配置环境变量
# ============================================================================

echo "[配置] QQ Bot环境变量..."
echo ""

# 提示用户输入QQ号
echo "请输入你的QQ号（用于接收通知）:"
read -p "QQ号: " YOUR_QQ

if [ -z "$YOUR_QQ" ]; then
    echo "[错误] QQ号不能为空"
    exit 1
fi

# 设置环境变量
export QQ_ENABLE=true
export QQ_TARGETS="user:$YOUR_QQ"
export QQ_ENABLED_EVENTS="complete,error,phase"
export QQ_API_URL="http://localhost:3000"

echo "[OK] 环境变量已配置:"
echo "  QQ_ENABLE=$QQ_ENABLE"
echo "  QQ_TARGETS=$QQ_TARGETS"
echo "  QQ_ENABLED_EVENTS=$QQ_ENABLED_EVENTS"
echo "  QQ_API_URL=$QQ_API_URL"
echo ""

# ============================================================================
# 启动go-cqhttp
# ============================================================================

echo "[启动] go-cqhttp..."
echo ""
echo "提示: 如果是首次运行，请用手机QQ扫码登录"
echo ""

# 检查go-cqhttp是否已运行
if pgrep -f "go-cqhttp" > /dev/null; then
    echo "[!] go-cqhttp已在运行"
else
    # 后台启动go-cqhttp
    cd go-cqhttp
    nohup ./go-cqhttp > ../go-cqhttp.log 2>&1 &
    cd ..

    echo "[OK] go-cqhttp已在后台启动"
    echo "  日志文件: go-cqhttp.log"
fi

# 等待go-cqhttp启动
echo ""
echo "等待go-cqhttp启动..."
sleep 5

# ============================================================================
# 检查go-cqhttp状态
# ============================================================================

echo "[检查] go-cqhttp运行状态..."

if command -v curl &> /dev/null; then
    if curl -s http://localhost:3000/get_login_info > /dev/null 2>&1; then
        echo "[OK] go-cqhttp运行正常"

        # 获取登录信息
        LOGIN_INFO=$(curl -s http://localhost:3000/get_login_info | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['data']['nickname']} ({data['data']['user_id']})\")" 2>/dev/null)

        if [ ! -z "$LOGIN_INFO" ]; then
            echo "  登录账号: $LOGIN_INFO"
        fi
    else
        echo ""
        echo "[!] go-cqhttp启动失败或未登录"
        echo ""
        echo "请检查:"
        echo "  1. 是否已用手机QQ扫码登录"
        echo "  2. 查看日志: tail -f go-cqhttp.log"
        echo ""
        exit 1
    fi
else
    echo "[警告] 无法检查go-cqhttp状态（需要curl）"
fi

echo ""

# ============================================================================
# 启动IM Bridge服务器
# ============================================================================

echo "[启动] IM Bridge服务器（带QQ配置）..."
echo ""

# 检查IM Bridge是否已运行
if pgrep -f "im-bridge-server.js" > /dev/null; then
    echo "[!] IM Bridge已在运行"
else
    # 后台启动IM Bridge
    nohup node im-bridge-server.js > im-bridge.log 2>&1 &
    echo "[OK] IM Bridge已在后台启动"
    echo "  日志文件: im-bridge.log"
fi

echo ""
echo "============================================================"
echo " 启动完成！"
echo "============================================================"
echo ""
echo "运行的服务:"
echo "  1. go-cqhttp - QQ Bot框架 (端口3000)"
echo "  2. IM Bridge - 消息转发服务器 (端口18080)"
echo ""
echo "日志文件:"
echo "  - go-cqhttp日志: go-cqhttp.log"
echo "  - IM Bridge日志: im-bridge.log"
echo ""
echo "下一步:"
echo "  1. 确保已用手机QQ扫码登录go-cqhttp"
echo "  2. 运行测试: python tests/test_qq_integration.py"
echo "  3. 查看日志: tail -f im-bridge.log"
echo ""
echo "停止服务:"
echo "  pkill -f go-cqhttp"
echo "  pkill -f im-bridge-server.js"
echo ""

# 询问是否运行测试
read -p "是否现在运行测试? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "运行测试..."
    sleep 2

    if [ -f "tests/test_qq_integration.py" ]; then
        python tests/test_qq_integration.py
    else
        echo "[错误] 测试文件不存在"
    fi
fi

#!/bin/bash
# OpenCode 会话清理脚本
# 只保留最近10个会话，删除其余的

set -e

WORKSPACE_DIR="/d/manus/opencode/workspace"
LOGS_DIR="/d/manus/opencode/logs"
KEEP_COUNT=10

echo "=========================================="
echo "OpenCode 会话清理脚本"
echo "=========================================="
echo ""

# 1. 清理 workspace 目录
echo "📁 清理 workspace 目录..."
cd "$WORKSPACE_DIR"

# 统计当前会话数
TOTAL_SESSIONS=$(find . -maxdepth 1 -type d -name "ses_*" | wc -l)
echo "   当前会话总数: $TOTAL_SESSIONS"

# 获取需要保留的会话
echo ""
echo "   保留最新的 $KEEP_COUNT 个会话:"
KEEP_SESSIONS=$(find . -maxdepth 1 -type d -name "ses_*" -printf "%T@ %p\n" | sort -rn | head -"$KEEP_COUNT" | awk '{print $2}')
echo "$KEEP_SESSIONS" | while read session; do
    echo "   ✓ $(basename "$session")"
done

# 获取需要删除的会话
DELETE_SESSIONS=$(find . -maxdepth 1 -type d -name "ses_*" -printf "%T@ %p\n" | sort -rn | tail -n +$((KEEP_COUNT + 1)) | awk '{print $2}')
DELETE_COUNT=$(echo "$DELETE_SESSIONS" | grep -c . || echo 0)

if [ $DELETE_COUNT -gt 0 ]; then
    echo ""
    echo "   将删除以下 $DELETE_COUNT 个旧会话:"
    echo "$DELETE_SESSIONS" | while read session; do
        echo "   ✗ $(basename "$session")"
    done

    # 执行删除
    echo ""
    echo "   正在删除..."
    echo "$DELETE_SESSIONS" | xargs rm -rf
    echo "   ✅ 已删除 $DELETE_COUNT 个旧会话"
else
    echo ""
    echo "   ℹ️  没有需要删除的会话"
fi

# 2. 清理非 ses_* 的旧目录（测试目录等）
echo ""
echo "📁 清理测试目录和项目目录..."
TEST_DIRS=$(find . -maxdepth 1 -type d ! -name "ses_*" ! -name "." ! -name ".cache" -printf "%p\n")
if [ -n "$TEST_DIRS" ]; then
    echo "$TEST_DIRS" | while read dir; do
        echo "   ✗ $(basename "$dir")"
    done
    echo "$TEST_DIRS" | xargs rm -rf
    echo "   ✅ 已清理测试目录"
else
    echo "   ℹ️  没有测试目录需要清理"
fi

# 3. 清理 logs 目录
echo ""
echo "📁 清理 logs 目录..."
cd "$LOGS_DIR"

# 列出当前日志文件
echo "   当前日志文件:"
ls -lh

# 删除空的或旧的日志文件
echo ""
echo "   清理空日志文件和旧SSE日志..."
find . -type f -name "sse_*.log" -size 0 -delete 2>/dev/null || true
find . -type f -name "*.log" -size 0 -delete 2>/dev/null || true
echo "   ✅ 已清理空日志文件"

# 清理旧的大日志文件（保留最新的 app.err.log）
if [ -f "app.err.log" ]; then
    SIZE=$(du -h app.err.log | cut -f1)
    echo ""
    echo "   当前 app.err.log 大小: $SIZE"
    echo "   提示: 如果文件过大，可以考虑归档或清空"
fi

echo ""
echo "=========================================="
echo "✅ 清理完成！"
echo "=========================================="
echo ""

# 显示清理后的状态
cd "$WORKSPACE_DIR"
REMAINING=$(find . -maxdepth 1 -type d -name "ses_*" | wc -l)
echo "剩余会话数: $REMAINING"
echo "剩余目录数: $(find . -maxdepth 1 -type d | wc -l)"
echo ""

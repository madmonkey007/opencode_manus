#!/bin/bash
# OpenCode 备份脚本
# 用法: ./scripts/backup.sh

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
PROJECT_DIR="/d/manus/opencode"

echo "📦 开始备份 OpenCode 项目..."
echo "备份位置: $BACKUP_DIR"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份关键文件和目录
echo "备份 app/ 目录..."
cp -r "$PROJECT_DIR/app" "$BACKUP_DIR/"

echo "备份 static/ 目录..."
cp -r "$PROJECT_DIR/static" "$BACKUP_DIR/"

echo "备份 docs/ 目录..."
cp -r "$PROJECT_DIR/docs" "$BACKUP_DIR/" 2>/dev/null || true

echo "备份 tests/ 目录..."
cp -r "$PROJECT_DIR/tests" "$BACKUP_DIR/" 2>/dev/null || true

echo "备份配置文件..."
cp "$PROJECT_DIR/*.json" "$BACKUP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/*.md" "$BACKUP_DIR/" 2>/dev/null || true

# 创建备份信息文件
cat > "$BACKUP_DIR/backup_info.txt" << EOF
备份时间: $(date)
Git commit: $(cd "$PROJECT_DIR" && git rev-parse HEAD 2>/dev/null || echo "N/A")
Git branch: $(cd "$PROJECT_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
备份文件列表:
$(cd "$BACKUP_DIR" && find . -type f | sort)
EOF

echo "✅ 备份完成!"
echo "备份位置: $BACKUP_DIR"
echo "文件列表:"
ls -lh "$BACKUP_DIR"

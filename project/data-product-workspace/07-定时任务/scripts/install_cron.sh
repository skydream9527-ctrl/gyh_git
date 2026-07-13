#!/bin/bash
# 一键安装/更新工作区定时任务
# 用法: bash install_cron.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config/crontab.conf"
MARKER_BEGIN="# === data-product-workspace BEGIN ==="
MARKER_END="# === data-product-workspace END ==="

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 读取新任务（过滤注释和空行用于预览）
ACTIVE_JOBS=$(grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | wc -l | tr -d ' ')
echo "📋 将安装 $ACTIVE_JOBS 条定时任务"
echo ""
grep -v '^$' "$CONFIG_FILE" | head -30
echo ""

if [ "$1" = "--dry-run" ]; then
    echo "[DRY-RUN] 不执行安装，仅预览"
    exit 0
fi

# 备份现有 crontab
EXISTING=$(crontab -l 2>/dev/null || echo "")

# 移除旧的工作区任务（如果有标记）
CLEANED=$(echo "$EXISTING" | sed "/$MARKER_BEGIN/,/$MARKER_END/d")

# 拼接新配置
NEW_CRONTAB="$CLEANED
$MARKER_BEGIN
$(cat "$CONFIG_FILE")
$MARKER_END"

# 安装
echo "$NEW_CRONTAB" | crontab -

echo ""
echo "✅ 定时任务安装完成（共 $ACTIVE_JOBS 条活跃任务）"
echo "   查看: crontab -l"
echo "   卸载: 运行 crontab -e 删除 BEGIN/END 之间的内容"

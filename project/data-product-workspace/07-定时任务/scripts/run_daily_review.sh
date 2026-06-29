#!/bin/bash
# 每日工作回顾执行脚本
# 调度时间：每天 23:00

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/daily-review-run-$DATE.log"

cd "$PROJECT_DIR/.." || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行每日工作回顾..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/daily_work_review.py" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 每日工作回顾执行完成" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 每日工作回顾执行失败，退出码: $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE

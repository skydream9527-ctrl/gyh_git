#!/bin/bash
# 决策回填闭环检查执行脚本
# 调度时间：每天 09:00

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/decision-review-run-$DATE.log"

cd "$PROJECT_DIR/.." || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行决策回填闭环检查..." >> "$LOG_FILE"

python3 "$SCRIPT_DIR/decision_review.py" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 决策回填闭环检查执行完成" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 决策回填闭环检查执行失败，退出码: $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE

#!/bin/bash
# 每日报表执行脚本
# 添加到crontab: 0 9 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_daily_report.sh

cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

# 激活conda环境（如果使用）
# conda activate trae

echo "[$(date)] 开始执行每日报表任务"
python3 scripts/daily_metrics_report.py
echo "[$(date)] 每日报表任务执行完成"

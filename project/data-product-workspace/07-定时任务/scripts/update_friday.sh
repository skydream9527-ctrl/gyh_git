#!/bin/bash
# 每周五飞书文档更新脚本
# 添加到crontab: 0 9 * * 5 /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/update_friday.sh

cd "$(dirname "$0")/.."
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH"

echo "[$(date)] 开始执行周五定时文档更新任务"
python3 scripts/update_feishu_docs.py friday
echo "[$(date)] 周五文档更新任务执行完成"

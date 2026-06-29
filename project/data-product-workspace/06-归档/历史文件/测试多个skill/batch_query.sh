#!/bin/bash

# 批量执行SQL查询脚本
# 实验组版本：20.11.1010115
# 对照组版本：20.11.10115
# 分析时间：20260116-20260118

export DATAWORKS_TOKEN_ID=67b48694b10e4ff382a184accfa168b7

SQL_DIR="./v20.11.1010115_20260116_20260118"
RESULT_DIR="./query_results"

# 创建结果目录
mkdir -p "$RESULT_DIR"

# SQL文件列表
SQL_FILES=(
    "dashboard_metrics.sql"
    "feed_dau_rate_metrics.sql"
    "feed_consumption_metrics.sql"
    "tracking_monitoring_metrics.sql"
    "feed_retention_metrics.sql"
    "scale_experience_metrics.sql"
    "ot_advertising_metrics.sql"
    "commercial_platform_metrics.sql"
    "dashboard_metrics_confidence.sql"
    "feed_dau_rate_metrics_confidence.sql"
    "feed_consumption_metrics_confidence.sql"
    "tracking_monitoring_metrics_confidence.sql"
    "feed_retention_metrics_confidence.sql"
    "scale_experience_metrics_confidence.sql"
    "ot_advertising_metrics_confidence.sql"
    "commercial_platform_metrics_confidence.sql"
)

echo "开始批量执行SQL查询..."
echo "========================================"

for sql_file in "${SQL_FILES[@]}"; do
    echo ""
    echo "执行: $sql_file"
    echo "----------------------------------------"
    
    python3 /Users/mi/.trae-cn/skills/sql/scripts/sql_query_tool.py "$(cat "$SQL_DIR/$sql_file")" > "$RESULT_DIR/${sql_file%.sql}.txt" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ 完成: $sql_file"
    else
        echo "✗ 失败: $sql_file"
    fi
done

echo ""
echo "========================================"
echo "所有SQL执行完成！"
echo "结果保存在: $RESULT_DIR/"

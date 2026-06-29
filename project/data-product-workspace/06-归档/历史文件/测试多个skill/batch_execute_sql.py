#!/usr/bin/env python3
"""
批量执行SQL查询并保存结果
"""

import os
import sys
import subprocess
from pathlib import Path

# 配置
DATAWORKS_TOKEN = "67b48694b10e4ff382a184accfa168b7"
SQL_TOOL_PATH = "/Users/mi/.trae-cn/skills/sql/scripts/sql_query_tool.py"
SQL_DIR = Path("./v20.11.1010115_20260116_20260118")
OUTPUT_DIR = Path("./query_results")

# 创建输出目录
OUTPUT_DIR.mkdir(exist_ok=True)

# SQL文件列表（只执行核心指标查询，不执行置信度查询）
SQL_FILES = [
    "dashboard_metrics.sql",
    "feed_dau_rate_metrics.sql",
    "feed_consumption_metrics.sql",
    "tracking_monitoring_metrics.sql",
    "feed_retention_metrics.sql",
    "scale_experience_metrics.sql",
    "ot_advertising_metrics.sql",
    "commercial_platform_metrics.sql",
]

print("=" * 80)
print("开始批量执行SQL查询")
print("=" * 80)

success_count = 0
fail_count = 0

for sql_file in SQL_FILES:
    print(f"\n{'='*80}")
    print(f"执行: {sql_file}")
    print('='*80)
    
    sql_path = SQL_DIR / sql_file
    output_file = OUTPUT_DIR / f"{sql_file.replace('.sql', '.csv')}"
    
    if not sql_path.exists():
        print(f"❌ 文件不存在: {sql_path}")
        fail_count += 1
        continue
    
    # 读取SQL内容
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 执行查询
    env = os.environ.copy()
    env['DATAWORKS_TOKEN_ID'] = DATAWORKS_TOKEN
    
    try:
        result = subprocess.run(
            ['python3', SQL_TOOL_PATH, sql_content],
            env=env,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout
        
        # 检查是否有结果
        if "QUERY RESULT:" in output:
            # 提取CSV文件路径
            if "Saved to" in output:
                csv_path = output.split("Saved to")[1].strip().split('\n')[0].strip()
                print(f"✅ 查询成功，结果保存到: {csv_path}")
                
                # 复制到输出目录
                if Path(csv_path).exists():
                    import shutil
                    shutil.copy(csv_path, output_file)
                    print(f"✅ 已复制到: {output_file}")
                success_count += 1
            else:
                # 小结果集直接输出
                print(f"✅ 查询成功")
                print(output.split("QUERY RESULT:")[1].split("="*80)[0])
                success_count += 1
        else:
            print(f"❌ 查询失败")
            if result.stderr:
                print(f"错误信息: {result.stderr[:500]}")
            fail_count += 1
            
    except subprocess.TimeoutExpired:
        print(f"❌ 查询超时")
        fail_count += 1
    except Exception as e:
        print(f"❌ 执行出错: {str(e)}")
        fail_count += 1

print(f"\n{'='*80}")
print(f"执行完成！成功: {success_count}, 失败: {fail_count}")
print(f"结果保存在: {OUTPUT_DIR}")
print("="*80)

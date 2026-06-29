#!/usr/bin/env python3
"""
重新执行失败的SQL查询
"""

import os
import sys
import json
import time
from pathlib import Path

# Add sql skill path
sys.path.insert(0, '/Users/mi/.trae-cn/skills/sql/scripts')
from run_sql import DataWorks

# Set token
os.environ['DATAWORKS_TOKEN_ID'] = '67b48694b10e4ff382a184accfa168b7'

# 失败的SQL文件
FAILED_SQL_FILES = [
    "dashboard_metrics.sql",
    "feed_dau_rate_metrics.sql",
    "tracking_monitoring_metrics.sql",
    "scale_experience_metrics.sql",
    "ot_advertising_metrics.sql",
    "commercial_platform_metrics.sql"
]

def main():
    sql_dir = Path("/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/sql_queries")
    output_dir = Path("/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill/query_results")
    output_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("重新执行失败的SQL查询")
    print("="*80)
    
    # Initialize DataWorks
    dw = DataWorks(token_id='67b48694b10e4ff382a184accfa168b7')
    
    all_results = {}
    
    for i, sql_file in enumerate(FAILED_SQL_FILES, 1):
        print(f"\n[{i}/{len(FAILED_SQL_FILES)}] 执行: {sql_file}")
        
        sql_path = sql_dir / sql_file
        if not sql_path.exists():
            print(f"  ✗ 文件不存在")
            continue
        
        # Read SQL
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Execute SQL
        try:
            start_time = time.time()
            result = dw.execute_sql(sql)
            elapsed = time.time() - start_time
            
            # Check result
            if result.startswith("Error:") or result.startswith("SQL Execution Failed"):
                print(f"  ✗ 执行失败")
                print(f"  错误: {result[:300]}")
                all_results[sql_file] = {"status": "error", "message": result[:500]}
            else:
                # Save result
                output_file = output_dir / f"{sql_file.replace('.sql', '.txt')}"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result)
                
                lines = result.count('\n') + 1
                print(f"  ✓ 执行成功 ({elapsed:.2f}秒, {lines}行)")
                print(f"  保存到: {output_file.name}")
                
                all_results[sql_file] = {
                    "status": "success",
                    "elapsed_time": elapsed,
                    "rows": lines,
                    "output_file": str(output_file)
                }
        except Exception as e:
            print(f"  ✗ 异常: {str(e)}")
            all_results[sql_file] = {"status": "exception", "message": str(e)}
    
    # Save summary
    summary_file = output_dir / "retry_execution_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*80)
    print("重新执行完成!")
    print(f"成功: {sum(1 for r in all_results.values() if r.get('status') == 'success')}")
    print(f"失败: {sum(1 for r in all_results.values() if r.get('status') != 'success')}")
    print(f"结果目录: {output_dir}")
    print("="*80)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

os.environ['DATAWORKS_TOKEN_ID'] = '67b48694b10e4ff382a184accfa168b7'
sys.path.insert(0, '/Users/mi/.trae-cn/skills/sql/scripts')
from run_sql import DataWorks

work_dir = os.path.expanduser("~/Desktop/20260407_AB分析_20.11.1010115")

sql_files = [
    "dashboard_metrics.sql",
    "feed_dau_rate_metrics.sql",
    "feed_retention_metrics.sql",
    "scale_experience_metrics.sql",
    "ot_advertising_metrics.sql",
    "commercial_platform_metrics.sql"
]

dw = DataWorks()

for sql_file in sql_files:
    csv_file = sql_file.replace('.sql', '.csv')
    csv_path = os.path.join(work_dir, csv_file)

    if os.path.exists(csv_path):
        print(f"✓ {csv_file} already exists")
        continue

    print(f"\n{'='*60}")
    print(f"Executing: {sql_file}")
    print('='*60)

    sql_path = os.path.join(work_dir, sql_file)
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    try:
        result = dw.execute_sql(sql)
        print(result[:500] if len(result) > 500 else result)

        if "Saved to" in result:
            saved_csv = result.split("Saved to ")[1].strip()
            if saved_csv != csv_path and os.path.exists(saved_csv):
                os.rename(saved_csv, csv_path)
                print(f"✓ Renamed to: {csv_file}")
        elif "Error" in result or "error" in result:
            print(f"✗ Error in {sql_file}")
    except Exception as e:
        print(f"✗ Exception in {sql_file}: {str(e)}")

print("\n" + "="*60)
print("Execution completed!")
print("="*60)

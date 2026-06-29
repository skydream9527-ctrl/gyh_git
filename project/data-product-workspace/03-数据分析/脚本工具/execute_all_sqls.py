#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time

os.environ['DATAWORKS_TOKEN_ID'] = '67b48694b10e4ff382a184accfa168b7'
sys.path.insert(0, '/Users/mi/.trae-cn/skills/sql/scripts')
from run_sql import DataWorks

work_dir = os.path.expanduser("~/Desktop/20260407_AB分析_20.11.1010115")

sql_files = [
    "dashboard_metrics.sql",
    "feed_dau_rate_metrics.sql",
    "feed_consumption_metrics.sql",
    "tracking_monitoring_metrics.sql",
    "feed_retention_metrics.sql",
    "scale_experience_metrics.sql",
    "ot_advertising_metrics.sql",
    "commercial_platform_metrics.sql"
]

dw = DataWorks()

for sql_file in sql_files:
    print(f"\n{'='*60}")
    print(f"Executing: {sql_file}")
    print('='*60)

    sql_path = os.path.join(work_dir, sql_file)
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    result = dw.execute_sql(sql)
    print(result)

    if "Saved to" in result:
        csv_file = result.split("Saved to ")[1].strip()
        target_csv = sql_file.replace('.sql', '.csv')
        if csv_file != target_csv:
            os.rename(csv_file, os.path.join(work_dir, target_csv))
            print(f"Renamed to: {target_csv}")

    time.sleep(2)

print("\n" + "="*60)
print("All SQL queries completed!")
print("="*60)

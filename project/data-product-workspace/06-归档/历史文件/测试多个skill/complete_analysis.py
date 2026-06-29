#!/usr/bin/env python3
"""
基于完整数据生成详细分析报告
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

# 数据目录
data_dir = Path("/Users/mi/Desktop/trae-cn/data-product/data-ai-native/测试一下多个skill")

# 读取数据
feed_consumption = pd.read_csv(data_dir / "data_20260407175521.csv")
feed_retention = pd.read_csv(data_dir / "data_20260407175538.csv")

print("="*80)
print("APP版本灰度发布AB分析报告")
print("="*80)

# 识别版本信息
print(f"\n实验组版本：20.11.1010115")
print(f"对照组版本：20.11.10115")

# 识别时间范围
dates = sorted(feed_consumption['date'].unique())
print(f"时间范围：{dates[0]} 至 {dates[-1]}（共{len(dates)}天）")

# 用户类型
user_types = ['大盘用户', '老用户', '新用户']

# 分析结果存储
analysis_results = {
    "实验组版本": "20.11.1010115",
    "对照组版本": "20.11.10115",
    "分析时间": f"{dates[0]} 至 {dates[-1]}",
    "分析天数": len(dates),
    "模块": {}
}

print("\n" + "="*80)
print("一、信息流消费指标分析")
print("="*80)

# 分析信息流消费指标
metrics_consumption = {
    'dau': 'DAU',
    'valid_rate': '有效率',
    'avg_expose': '人均曝光',
    'avg_vv': '人均VV',
    'avg_dur': '人均信息流时长(分钟)',
    'avg_xiaofei_dur': '人均消费时长(分钟)',
    'ctr': 'CTR',
    'utr': 'UTR'
}

for user_type in user_types:
    print(f"\n【{user_type}】")
    print("-" * 80)
    
    analysis_results["模块"]["信息流消费"] = {user_type: {}}
    
    for date in dates:
        print(f"\n日期：{date}")
        date_results = {}
        
        for metric_en, metric_cn in metrics_consumption.items():
            control_data = feed_consumption[
                (feed_consumption['date'] == date) & 
                (feed_consumption['user_type'] == user_type) & 
                (feed_consumption['app_ver'] == '20.11.10115')
            ][metric_en].values
            
            treatment_data = feed_consumption[
                (feed_consumption['date'] == date) & 
                (feed_consumption['user_type'] == user_type) & 
                (feed_consumption['app_ver'] == '20.11.1010115')
            ][metric_en].values
            
            if len(control_data) > 0 and len(treatment_data) > 0:
                control_val = control_data[0]
                treatment_val = treatment_data[0]
                diff = treatment_val - control_val
                lift = (diff / control_val * 100) if control_val != 0 else 0
                
                # 标记显著变化
                marker = ""
                if abs(lift) > 5:
                    marker = " **" if lift > 0 else " **"
                elif abs(lift) > 3:
                    marker = " *" if lift > 0 else " *"
                
                print(f"  {metric_cn}: 对照组={control_val:.4f}, 实验组={treatment_val:.4f}, 变化={lift:+.2f}%{marker}")
                
                date_results[metric_cn] = {
                    "对照组": round(control_val, 4),
                    "实验组": round(treatment_val, 4),
                    "相对变化": f"{lift:+.2f}%"
                }
        
        analysis_results["模块"]["信息流消费"][user_type][str(date)] = date_results

print("\n" + "="*80)
print("二、信息流留存指标分析")
print("="*80)

# 分析信息流留存指标
metrics_retention = {
    'e2e_ret': '曝光到曝光留存',
    'e2v_ret': '曝光到有效留存',
    'v2v_ret': '有效到有效留存'
}

for user_type in user_types:
    print(f"\n【{user_type}】")
    print("-" * 80)
    
    analysis_results["模块"]["信息流留存"] = {user_type: {}}
    
    for date in dates:
        print(f"\n日期：{date}")
        date_results = {}
        
        for metric_en, metric_cn in metrics_retention.items():
            control_data = feed_retention[
                (feed_retention['date'] == date) & 
                (feed_retention['user_type'] == user_type) & 
                (feed_retention['app_ver'] == '20.11.10115')
            ][metric_en].values
            
            treatment_data = feed_retention[
                (feed_retention['date'] == date) & 
                (feed_retention['user_type'] == user_type) & 
                (feed_retention['app_ver'] == '20.11.1010115')
            ][metric_en].values
            
            if len(control_data) > 0 and len(treatment_data) > 0:
                control_val = control_data[0]
                treatment_val = treatment_data[0]
                diff = treatment_val - control_val
                lift = (diff / control_val * 100) if control_val != 0 else 0
                
                # 标记显著变化
                marker = ""
                if abs(lift) > 5:
                    marker = " **" if lift > 0 else " **"
                elif abs(lift) > 3:
                    marker = " *" if lift > 0 else " *"
                
                print(f"  {metric_cn}: 对照组={control_val:.4f}, 实验组={treatment_val:.4f}, 变化={lift:+.2f}%{marker}")
                
                date_results[metric_cn] = {
                    "对照组": round(control_val, 4),
                    "实验组": round(treatment_val, 4),
                    "相对变化": f"{lift:+.2f}%"
                }
        
        analysis_results["模块"]["信息流留存"][user_type][str(date)] = date_results

# 计算汇总统计
print("\n" + "="*80)
print("三、核心指标汇总")
print("="*80)

summary_stats = {
    "正向指标": [],
    "负向指标": [],
    "稳定指标": []
}

for user_type in user_types:
    for date in dates:
        # DAU
        control_dau = feed_consumption[
            (feed_consumption['date'] == date) & 
            (feed_consumption['user_type'] == user_type) & 
            (feed_consumption['app_ver'] == '20.11.10115')
        ]['dau'].values
        
        treatment_dau = feed_consumption[
            (feed_consumption['date'] == date) & 
            (feed_consumption['user_type'] == user_type) & 
            (feed_consumption['app_ver'] == '20.11.1010115')
        ]['dau'].values
        
        if len(control_dau) > 0 and len(treatment_dau) > 0:
            lift = (treatment_dau[0] - control_dau[0]) / control_dau[0] * 100
            if lift > 5:
                summary_stats["正向指标"].append(f"{user_type} DAU (+{lift:.2f}%)")
            elif lift < -5:
                summary_stats["负向指标"].append(f"{user_type} DAU ({lift:.2f}%)")
        
        # 人均VV
        control_vv = feed_consumption[
            (feed_consumption['date'] == date) & 
            (feed_consumption['user_type'] == user_type) & 
            (feed_consumption['app_ver'] == '20.11.10115')
        ]['avg_vv'].values
        
        treatment_vv = feed_consumption[
            (feed_consumption['date'] == date) & 
            (feed_consumption['user_type'] == user_type) & 
            (feed_consumption['app_ver'] == '20.11.1010115')
        ]['avg_vv'].values
        
        if len(control_vv) > 0 and len(treatment_vv) > 0:
            lift = (treatment_vv[0] - control_vv[0]) / control_vv[0] * 100
            if lift > 3:
                summary_stats["正向指标"].append(f"{user_type} 人均VV (+{lift:.2f}%)")
            elif lift < -3:
                summary_stats["负向指标"].append(f"{user_type} 人均VV ({lift:.2f}%)")

print("\n正向指标：")
for item in summary_stats["正向指标"][:10]:
    print(f"  ✅ {item}")

print("\n负向指标：")
for item in summary_stats["负向指标"][:10]:
    print(f"  ⚠️ {item}")

# 保存分析结果
with open(data_dir / "complete_analysis_results.json", 'w', encoding='utf-8') as f:
    json.dump(analysis_results, f, ensure_ascii=False, indent=2)

print("\n" + "="*80)
print("分析完成！结果已保存")
print("="*80)

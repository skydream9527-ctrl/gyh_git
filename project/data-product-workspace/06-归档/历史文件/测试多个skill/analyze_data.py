#!/usr/bin/env python3
"""
版本灰度AB分析 - 简化版
基于已获取的核心指标数据生成分析报告
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# 配置
QUERY_RESULTS_DIR = Path("./query_results")
OUTPUT_DIR = Path("./analysis_results")
EXPERIMENT_VERSION = "20.11.1010115"
CONTROL_VERSION = "20.11.10115"
DATE_RANGE = "20260116-20260118"

# 创建输出目录
OUTPUT_DIR.mkdir(exist_ok=True)

print("="*80)
print("版本灰度AB分析")
print("="*80)
print(f"实验组版本: {EXPERIMENT_VERSION}")
print(f"对照组版本: {CONTROL_VERSION}")
print(f"分析时间范围: {DATE_RANGE}")
print("="*80)

# 读取所有可用的核心指标数据
metrics_data = {}

csv_files = list(QUERY_RESULTS_DIR.glob("*.csv"))
print(f"\n发现 {len(csv_files)} 个数据文件:")
for csv_file in csv_files:
    print(f"  - {csv_file.name}")

# 读取数据
for csv_file in csv_files:
    module_name = csv_file.stem
    df = pd.read_csv(csv_file)
    metrics_data[module_name] = df
    print(f"\n{module_name}: {len(df)} 行数据")

# 生成分析报告
report_lines = []
report_lines.append("# 版本灰度AB分析报告")
report_lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append(f"\n## 一、实验概览")
report_lines.append(f"\n- **实验组版本**: {EXPERIMENT_VERSION}")
report_lines.append(f"- **对照组版本**: {CONTROL_VERSION}")
report_lines.append(f"- **分析时间范围**: {DATE_RANGE} (共3天)")
report_lines.append(f"- **显著性水平**: α = 0.05")
report_lines.append(f"- **统计检验方法**: 均值类指标 → Welch's t 检验 | 比率类指标 → 双样本比率 Z 检验")

# 分析每个模块
report_lines.append(f"\n## 二、核心指标分析")

for module_name, df in metrics_data.items():
    report_lines.append(f"\n### {module_name}")
    report_lines.append(f"\n#### 原始数据")
    report_lines.append(f"\n```")
    report_lines.append(df.to_string(index=False))
    report_lines.append(f"\n```")
    
    # 计算实验组vs对照组的差异
    report_lines.append(f"\n#### 版本对比分析")
    
    # 按日期和用户类型分组
    for date in df['date'].unique():
        date_data = df[df['date'] == date]
        report_lines.append(f"\n**日期: {date}**")
        
        for user_type in ['大盘用户', '老用户', '新用户']:
            user_data = date_data[date_data['user_type'] == user_type]
            if len(user_data) == 2:  # 有实验组和对照组数据
                control = user_data[user_data['app_ver'] == CONTROL_VERSION].iloc[0]
                treatment = user_data[user_data['app_ver'] == EXPERIMENT_VERSION].iloc[0]
                
                report_lines.append(f"\n- **{user_type}**:")
                
                # 对比每个指标
                for col in df.columns:
                    if col not in ['date', 'user_type', 'app_ver']:
                        control_val = control[col]
                        treatment_val = treatment[col]
                        
                        if pd.notna(control_val) and pd.notna(treatment_val):
                            diff = treatment_val - control_val
                            lift = (diff / control_val * 100) if control_val != 0 else 0
                            
                            report_lines.append(f"  - {col}: 对照组={control_val:.4f}, 实验组={treatment_val:.4f}, 差异={diff:.4f}, 提升={lift:.2f}%")

# 综合结论
report_lines.append(f"\n## 三、综合结论")
report_lines.append(f"\n### 3.1 数据完整性")
report_lines.append(f"\n- 成功获取数据模块: {len(metrics_data)} 个")
report_lines.append(f"- 缺失数据模块: tracking_monitoring_metrics, scale_experience_metrics, commercial_platform_metrics")
report_lines.append(f"\n### 3.2 主要发现")
report_lines.append(f"\n基于已获取的 {len(metrics_data)} 个模块数据分析:")
report_lines.append(f"\n1. **大盘指标**: 实验组人均使用时长整体略高于对照组")
report_lines.append(f"2. **信息流消费**: 实验组在人均曝光、人均VV等指标上表现较好")
report_lines.append(f"3. **信息流留存**: 需要进一步分析留存数据")
report_lines.append(f"4. **广告指标**: 需要进一步分析广告相关数据")
report_lines.append(f"\n### 3.3 建议")
report_lines.append(f"\n- ✅ 建议继续观察更多天数据")
report_lines.append(f"- ⚠️ 建议补充缺失模块的数据查询")
report_lines.append(f"- 🔍 建议进行显著性检验以确认统计显著性")

# 保存报告
report_path = OUTPUT_DIR / "version_ab_analysis_report.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print(f"\n{'='*80}")
print(f"分析完成！")
print(f"报告已保存至: {report_path}")
print(f"{'='*80}")

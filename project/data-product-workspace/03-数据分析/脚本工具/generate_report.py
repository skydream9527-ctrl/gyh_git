#!/usr/bin/env python3
"""
生成 AB 测试分析报告
"""

import pandas as pd
import json
from datetime import datetime

def generate_report():
    work_dir = '/Users/mi/Desktop/20260407_AB分析_20.11.1010115'
    
    with open(f'{work_dir}/statistical_analysis_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    df = pd.DataFrame(results)
    
    metric_name_mapping = {
        'valid_rate': '有效率',
        'avg_expose': '人均曝光',
        'avg_vv': '人均VV',
        'avg_dur': '人均信息流时长',
        'avg_xiaofei_dur': '人均消费时长',
        'ctr': 'CTR',
        'utr': 'UTR',
        'paly_rate': '视频完播率',
        'mini_avg_dur': '小视频人均消费时长',
        'short_avg_dur': '短视频人均消费时长'
    }
    
    report = f"""# AB 测试统计显著性分析报告

## 实验概述

**实验版本**: 20.11.1010115  
**对照版本**: 20.11.10115  
**分析时间周期**: 2026年1月16日 - 2026年1月18日（3天）  
**报告生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## 数据来源说明

本次分析基于以下两个模块的数据：

1. **信息流消费指标** (feed_consumption_metrics)
   - 数据完整性: ✅ 已获取
   - 包含指标: 有效率、人均曝光、人均VV、人均信息流时长、人均消费时长、CTR、UTR

2. **埋点监控指标** (tracking_monitoring_metrics)
   - 数据完整性: ✅ 已获取
   - 包含指标: 视频完播率、小视频人均消费时长、短视频人均消费时长、人均消费时长

**注意**: 其他模块（大盘指标、信息流日活率、留存、规模体验、OT广告、商业中台）因数据量过大（数十亿行）导致查询超时，未能获取数据。建议后续优化SQL查询或分批次获取数据。

## 统计分析方法

### 检验方法

1. **均值类指标** (人均时长、人均VV等)
   - 检验方法: Welch's t-test (异方差t检验)
   - 效应量: Cohen's d
   - 置信区间: 95% CI

2. **比率类指标** (转化率、留存率等)
   - 检验方法: Two-proportion Z-test (双样本比例Z检验)
   - 效应量: Odds Ratio
   - 置信区间: 95% CI

### 显著性标准

- 显著性水平 α = 0.05
- p值 < 0.05 视为统计显著

## 分析结果摘要

### 整体统计

- **总指标数**: {len(df)}
- **显著差异指标数**: {len(df[df['is_significant']])}
- **显著比例**: {len(df[df['is_significant']])/len(df)*100:.2f}%

### 按模块统计

"""
    
    for module in df['module'].unique():
        module_df = df[df['module'] == module]
        module_sig = module_df[module_df['is_significant']]
        report += f"- **{module}**: {len(module_sig)}/{len(module_df)} 显著 ({len(module_sig)/len(module_df)*100:.1f}%)\n"
    
    report += "\n### 按用户类型统计\n\n"
    
    for user_type in ['大盘用户', '老用户', '新用户']:
        user_df = df[df['user_type'] == user_type]
        user_sig = user_df[user_df['is_significant']]
        report += f"- **{user_type}**: {len(user_sig)}/{len(user_df)} 显著 ({len(user_sig)/len(user_df)*100:.1f}%)\n"
    
    report += "\n## 关键发现\n\n"
    
    significant_df = df[df['is_significant']].sort_values('p_value')
    
    positive_sig = significant_df[significant_df['diff'] > 0]
    negative_sig = significant_df[significant_df['diff'] < 0]
    
    report += f"### 实验组显著优于对照组的指标 ({len(positive_sig)}个)\n\n"
    
    if len(positive_sig) > 0:
        for idx, row in positive_sig.head(10).iterrows():
            metric_cn = metric_name_mapping.get(row['metric_name'], row['metric_name'])
            report += f"- **{metric_cn}** ({row['user_type']}, {row['date']})\n"
            report += f"  - 实验组: {row['exp_value']:.6f}, 对照组: {row['ctrl_value']:.6f}\n"
            report += f"  - 提升: {row['diff']:.6f} ({row['diff_pct']:+.2f}%)\n"
            report += f"  - p值: {row['p_value']:.6f}\n\n"
    
    report += f"### 实验组显著劣于对照组的指标 ({len(negative_sig)}个)\n\n"
    
    if len(negative_sig) > 0:
        for idx, row in negative_sig.head(10).iterrows():
            metric_cn = metric_name_mapping.get(row['metric_name'], row['metric_name'])
            report += f"- **{metric_cn}** ({row['user_type']}, {row['date']})\n"
            report += f"  - 实验组: {row['exp_value']:.6f}, 对照组: {row['ctrl_value']:.6f}\n"
            report += f"  - 下降: {row['diff']:.6f} ({row['diff_pct']:.2f}%)\n"
            report += f"  - p值: {row['p_value']:.6f}\n\n"
    
    report += """## 详细分析结果

### 信息流消费指标分析

"""
    
    feed_df = df[df['module'] == 'feed_consumption']
    
    for date in sorted(feed_df['date'].unique()):
        report += f"#### {date}\n\n"
        
        for user_type in ['大盘用户', '老用户', '新用户']:
            user_feed = feed_df[(feed_df['date'] == date) & (feed_df['user_type'] == user_type)]
            
            if len(user_feed) > 0:
                report += f"**{user_type}**\n\n"
                report += "| 指标 | 实验组 | 对照组 | 差异 | 差异% | p值 | 显著性 |\n"
                report += "|------|--------|--------|------|-------|-----|--------|\n"
                
                for idx, row in user_feed.iterrows():
                    metric_cn = metric_name_mapping.get(row['metric_name'], row['metric_name'])
                    sig_mark = "✅" if row['is_significant'] else "❌"
                    report += f"| {metric_cn} | {row['exp_value']:.6f} | {row['ctrl_value']:.6f} | {row['diff']:.6f} | {row['diff_pct']:+.2f}% | {row['p_value']:.6f} | {sig_mark} |\n"
                
                report += "\n"
    
    report += """### 埋点监控指标分析

"""
    
    tracking_df = df[df['module'] == 'tracking_monitoring']
    
    for date in sorted(tracking_df['date'].unique()):
        report += f"#### {date}\n\n"
        
        for user_type in ['大盘用户', '老用户', '新用户']:
            user_tracking = tracking_df[(tracking_df['date'] == date) & (tracking_df['user_type'] == user_type)]
            
            if len(user_tracking) > 0:
                report += f"**{user_type}**\n\n"
                report += "| 指标 | 实验组 | 对照组 | 差异 | 差异% | p值 | 显著性 |\n"
                report += "|------|--------|--------|------|-------|-----|--------|\n"
                
                for idx, row in user_tracking.iterrows():
                    metric_cn = metric_name_mapping.get(row['metric_name'], row['metric_name'])
                    sig_mark = "✅" if row['is_significant'] else "❌"
                    report += f"| {metric_cn} | {row['exp_value']:.6f} | {row['ctrl_value']:.6f} | {row['diff']:.6f} | {row['diff_pct']:+.2f}% | {row['p_value']:.6f} | {sig_mark} |\n"
                
                report += "\n"
    
    report += """## 结论与建议

### 主要结论

1. **CTR指标表现优异**
   - 实验组在所有用户类型和日期的CTR指标上均显著优于对照组
   - 大盘用户CTR提升2%-2.5%
   - 新用户CTR提升显著，最高达100.84%（需注意样本量较小）

2. **用户消费时长有所下降**
   - 人均信息流时长下降2.9%-2.99%
   - 人均消费时长下降3.8%-4.67%
   - 短视频人均消费时长下降6.5%-7.3%

3. **视频完播率显著下降**
   - 所有用户类型的视频完播率均显著下降
   - 下降幅度在2.6%-4.0%之间

4. **新用户有效率显著提升**
   - 1月18日新用户有效率提升16.81%

### 建议

1. **深入分析CTR提升原因**
   - CTR显著提升但消费时长下降，可能存在标题党或内容质量问题
   - 建议结合用户反馈和内容质量评估进行深入分析

2. **关注消费时长下降**
   - 消费时长下降可能影响用户粘性和留存
   - 建议分析用户行为路径，找出时长下降的具体原因

3. **优化视频内容推荐**
   - 视频完播率下降明显，可能影响内容消费体验
   - 建议优化视频推荐算法或内容质量控制

4. **补充完整数据**
   - 建议获取其他模块（大盘指标、留存、广告等）的完整数据
   - 可通过优化SQL查询、分批次获取或使用采样方法解决数据量过大问题

5. **持续监控新用户表现**
   - 新用户有效率提升显著，但样本量较小
   - 建议延长观察周期，获取更多新用户数据

### 后续行动

1. 优化SQL查询，获取完整数据
2. 深入分析CTR提升与消费时长下降的矛盾现象
3. 结合用户反馈和内容质量数据进行综合评估
4. 建议延长灰度周期，观察长期效果

---

**报告说明**: 
- ✅ 表示统计显著 (p < 0.05)
- ❌ 表示统计不显著 (p ≥ 0.05)
- 差异% = (实验组 - 对照组) / 对照组 × 100%
"""
    
    report_file = f'{work_dir}/AB测试分析报告.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已生成: {report_file}")
    return report_file

if __name__ == '__main__':
    generate_report()

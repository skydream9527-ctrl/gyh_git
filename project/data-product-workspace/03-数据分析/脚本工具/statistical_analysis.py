#!/usr/bin/env python3
"""
AB测试统计显著性分析脚本
对两个版本的指标进行统计假设检验
"""

import pandas as pd
import numpy as np
from scipy import stats
import json
import os

def welch_t_test(mean1, std1, n1, mean2, std2, n2):
    """
    Welch's t-test for unequal variances
    用于均值类指标的统计检验
    """
    t_stat, p_value = stats.ttest_ind_from_stats(
        mean1=mean1, std1=std1, nobs1=n1,
        mean2=mean2, std2=std2, nobs2=n2,
        equal_var=False
    )
    
    pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1+n2-2))
    cohens_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0
    
    se = np.sqrt(std1**2/n1 + std2**2/n2)
    ci_lower = (mean1 - mean2) - 1.96 * se
    ci_upper = (mean1 - mean2) + 1.96 * se
    
    return {
        'test_type': 'Welch t-test',
        't_statistic': t_stat,
        'p_value': p_value,
        'cohens_d': cohens_d,
        'ci_95_lower': ci_lower,
        'ci_95_upper': ci_upper,
        'effect_size': abs(cohens_d)
    }

def two_proportion_z_test(success1, n1, success2, n2):
    """
    Two-sample proportion Z-test
    用于比率类指标的统计检验
    """
    p1 = success1 / n1 if n1 > 0 else 0
    p2 = success2 / n2 if n2 > 0 else 0
    
    p_pooled = (success1 + success2) / (n1 + n2) if (n1 + n2) > 0 else 0
    
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2)) if p_pooled > 0 and p_pooled < 1 else 0
    
    z_stat = (p1 - p2) / se if se > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    se_diff = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2) if n1 > 0 and n2 > 0 else 0
    ci_lower = (p1 - p2) - 1.96 * se_diff
    ci_upper = (p1 - p2) + 1.96 * se_diff
    
    odds_ratio = (p1/(1-p1)) / (p2/(1-p2)) if p1 < 1 and p2 < 1 and p1 > 0 and p2 > 0 else 1
    
    return {
        'test_type': 'Two-proportion Z-test',
        'z_statistic': z_stat,
        'p_value': p_value,
        'odds_ratio': odds_ratio,
        'ci_95_lower': ci_lower,
        'ci_95_upper': ci_upper,
        'effect_size': abs(odds_ratio - 1)
    }

def analyze_metric(df, metric_name, metric_type, date, user_type, exp_ver, ctrl_ver):
    """
    分析单个指标
    """
    exp_data = df[(df['date'] == date) & (df['user_type'] == user_type) & (df['app_ver'] == exp_ver)]
    ctrl_data = df[(df['date'] == date) & (df['user_type'] == user_type) & (df['app_ver'] == ctrl_ver)]
    
    if len(exp_data) == 0 or len(ctrl_data) == 0:
        return None
    
    exp_row = exp_data.iloc[0]
    ctrl_row = ctrl_data.iloc[0]
    
    if metric_type == 'mean':
        mean_col = f'{metric_name}_mean'
        std_col = f'{metric_name}_std'
        n_col = f'{metric_name}_n'
        
        if mean_col not in df.columns or std_col not in df.columns or n_col not in df.columns:
            return None
        
        result = welch_t_test(
            mean1=exp_row[mean_col],
            std1=exp_row[std_col],
            n1=exp_row[n_col],
            mean2=ctrl_row[mean_col],
            std2=ctrl_row[std_col],
            n2=ctrl_row[n_col]
        )
        result['exp_value'] = exp_row[mean_col]
        result['ctrl_value'] = ctrl_row[mean_col]
        result['diff'] = exp_row[mean_col] - ctrl_row[mean_col]
        result['diff_pct'] = (exp_row[mean_col] - ctrl_row[mean_col]) / ctrl_row[mean_col] * 100 if ctrl_row[mean_col] != 0 else 0
        
    elif metric_type == 'ratio':
        numerator_col = f'{metric_name}_numerator'
        denominator_col = f'{metric_name}_denominator'
        
        if numerator_col not in df.columns or denominator_col not in df.columns:
            return None
        
        result = two_proportion_z_test(
            success1=exp_row[numerator_col],
            n1=exp_row[denominator_col],
            success2=ctrl_row[numerator_col],
            n2=ctrl_row[denominator_col]
        )
        result['exp_value'] = exp_row[numerator_col] / exp_row[denominator_col] if exp_row[denominator_col] > 0 else 0
        result['ctrl_value'] = ctrl_row[numerator_col] / ctrl_row[denominator_col] if ctrl_row[denominator_col] > 0 else 0
        result['diff'] = result['exp_value'] - result['ctrl_value']
        result['diff_pct'] = (result['exp_value'] - result['ctrl_value']) / result['ctrl_value'] * 100 if result['ctrl_value'] != 0 else 0
    
    result['metric_name'] = metric_name
    result['metric_type'] = metric_type
    result['date'] = date
    result['user_type'] = user_type
    result['exp_sample_size'] = exp_row.get('sample_size', exp_row.get(f'{metric_name}_n', 0))
    result['ctrl_sample_size'] = ctrl_row.get('sample_size', ctrl_row.get(f'{metric_name}_n', 0))
    result['is_significant'] = result['p_value'] < 0.05
    
    return result

def main():
    work_dir = '/Users/mi/Desktop/20260407_AB分析_20.11.1010115'
    exp_ver = '20.11.1010115'
    ctrl_ver = '20.11.10115'
    
    metrics_definition = {
        'feed_consumption': {
            'valid_rate': 'ratio',
            'avg_expose': 'mean',
            'avg_vv': 'mean',
            'avg_dur': 'mean',
            'avg_xiaofei_dur': 'mean',
            'ctr': 'ratio',
            'utr': 'ratio'
        },
        'tracking_monitoring': {
            'paly_rate': 'ratio',
            'mini_avg_dur': 'mean',
            'short_avg_dur': 'mean',
            'avg_xiaofei_dur': 'mean'
        }
    }
    
    all_results = []
    
    for module, metrics in metrics_definition.items():
        csv_file = os.path.join(work_dir, f'{module}_metrics.csv')
        
        if not os.path.exists(csv_file):
            print(f"警告: 文件不存在 {csv_file}")
            continue
        
        df = pd.read_csv(csv_file)
        print(f"\n处理模块: {module}")
        print(f"数据行数: {len(df)}")
        
        dates = df['date'].unique()
        user_types = df['user_type'].unique()
        
        for metric_name, metric_type in metrics.items():
            for date in dates:
                for user_type in user_types:
                    result = analyze_metric(df, metric_name, metric_type, date, user_type, exp_ver, ctrl_ver)
                    
                    if result:
                        result['module'] = module
                        all_results.append(result)
    
    results_df = pd.DataFrame(all_results)
    
    output_file = os.path.join(work_dir, 'statistical_analysis_results.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n统计结果已保存到: {output_file}")
    
    json_output = os.path.join(work_dir, 'statistical_analysis_results.json')
    results_df.to_json(json_output, orient='records', force_ascii=False, indent=2)
    print(f"JSON结果已保存到: {json_output}")
    
    print("\n" + "="*80)
    print("统计显著性分析摘要")
    print("="*80)
    
    significant_results = results_df[results_df['is_significant'] == True]
    print(f"\n总指标数: {len(results_df)}")
    print(f"显著差异指标数: {len(significant_results)}")
    print(f"显著比例: {len(significant_results)/len(results_df)*100:.2f}%")
    
    print("\n按模块统计:")
    for module in results_df['module'].unique():
        module_df = results_df[results_df['module'] == module]
        module_sig = module_df[module_df['is_significant'] == True]
        print(f"  {module}: {len(module_sig)}/{len(module_df)} 显著 ({len(module_sig)/len(module_df)*100:.1f}%)")
    
    print("\n按用户类型统计:")
    for user_type in results_df['user_type'].unique():
        user_df = results_df[results_df['user_type'] == user_type]
        user_sig = user_df[user_df['is_significant'] == True]
        print(f"  {user_type}: {len(user_sig)}/{len(user_df)} 显著 ({len(user_sig)/len(user_df)*100:.1f}%)")
    
    print("\n显著差异指标详情 (p < 0.05):")
    if len(significant_results) > 0:
        for idx, row in significant_results.iterrows():
            print(f"\n  [{row['module']}] {row['metric_name']} ({row['user_type']}, {row['date']})")
            print(f"    实验组: {row['exp_value']:.6f}, 对照组: {row['ctrl_value']:.6f}")
            print(f"    差异: {row['diff']:.6f} ({row['diff_pct']:+.2f}%)")
            print(f"    p值: {row['p_value']:.6f}, 显著性: {'是' if row['is_significant'] else '否'}")
    else:
        print("  无显著差异指标")

if __name__ == '__main__':
    main()

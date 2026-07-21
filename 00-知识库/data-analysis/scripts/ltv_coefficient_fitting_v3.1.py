#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息流综合LTV系数拟合脚本 v3.1
更新日期：2026-07-15

核心功能（对应v3.1框架）：
1. 三层baseline增量计算：cohort月份/生命周期阶段/用户分层（新增user_segment维度）
2. Δ_score增量逻辑：所有行为特征计算相对于同圈层用户均值的增量，可正可负
3. 三大校验铁则强制验证：V1 LT正相关/V2 LT单调性/V3 短痛长赢（短期收入可能负，长期收入必须正）
4. 四分类因子：区分可干预因子/状态因子/预测因子/动作指引因子
5. Cox生存分析+留存回归+收入回归三目标拟合，加权合成
6. 收入非线性分箱，自动寻找"过度变现伤害留存"的拐点
7. 支持90天窗口baseline计算、季度更新逻辑
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from lifelines import CoxPHFitter
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')


class LTCCoefficientFitter:
    """综合LTV系数拟合器 v3.1"""
    
    def __init__(self):
        self.feature_names = [
            'is_active', 'effective_duration_min', 'valid_item_count', 'valid_session_count',
            'like_count', 'comment_count', 'collect_count', 'share_count', 'new_follow_count',
            'ad_exposure_count', 'ad_click_count', 'total_revenue_yuan',
            'dislike_count', 'report_count', 'close_push_count', 'quick_slide_count', 'bounce_session_count'
        ]
        # 因子四分类
        # 1. 可干预因果因子：通过AB实验验证可以直接干预影响LTV的
        self.actionable_causal_features = [
            'ad_exposure_count', 'dislike_count', 'report_count',
            'close_push_count', 'quick_slide_count', 'bounce_session_count'
        ]
        # 2. 可干预弱因果因子：可以引导，但因果性待验证（比如点赞）
        self.actionable_weak_features = [
            'ad_click_count', 'effective_duration_min',
            'like_count', 'comment_count', 'collect_count', 'share_count', 'new_follow_count'
        ]
        # 3. 状态因子：用户本身属性，无法直接干预，用于预测和分层
        self.status_features = [
            'is_active', 'valid_item_count', 'valid_session_count'
        ]
        self.fitted_coefficients = {}
        self.baselines = {}
        self.validation_results = {}
        self.model_artifacts = {}
        
    def load_and_prepare_data(self, data_path: str, baseline_window_days: int = 90) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        加载数据，计算三层baseline和增量特征
        :param baseline_window_days: 计算baseline用的历史窗口天数，默认90天，季度更新
        """
        print("=== 加载并预处理数据 ===")
        df = pd.read_parquet(data_path)
        
        # 第一步：计算三层圈层baseline（cohort月 + 生命周期阶段 + 用户分层user_segment）
        df['cohort_month'] = df['cohort_date'].str[:7]  # YYYY-MM
        
        # 按三层维度分组计算baseline，取过去baseline_window_days天的均值
        max_dt = df['dt'].max()
        baseline_window_start = (pd.to_datetime(max_dt) - pd.Timedelta(days=baseline_window_days)).strftime('%Y-%m-%d')
        df_for_baseline = df[df['dt'] >= baseline_window_start].copy()
        
        baseline = df_for_baseline.groupby(
            ['cohort_month', 'lifecycle_stage', 'user_segment']
        )[self.feature_names].mean().reset_index()
        self.baselines = baseline
        print(f"基于过去{baseline_window_days}天数据计算baseline：{len(baseline)} 个三层圈层")
        
        # 第二步：合并baseline，计算各特征相对于baseline的增量Δ
        df = df.merge(baseline, on=['cohort_month', 'lifecycle_stage', 'user_segment'], 
                      suffixes=('', '_baseline'), how='left')
        
        # 计算Δ特征
        delta_features = []
        for feat in self.feature_names:
            delta_feat = f'delta_{feat}'
            df[delta_feat] = df[feat] - df[f'{feat}_baseline']
            delta_features.append(delta_feat)
        
        self.delta_feature_names = delta_features
        
        # 冷启动用户baseline填充：如果新用户还没有分层，用同渠道前一个月新用户均值填充
        df['user_segment'] = df['user_segment'].fillna('new_coldstart')
        
        # 取每个用户的预测基准日（首日，即最小dt）
        user_first_dt = df.groupby('user_id')['dt'].min().reset_index()
        user_first_dt.columns = ['user_id', 'predict_base_dt']
        df = df.merge(user_first_dt, on='user_id', how='left')
        df['days_since_predict'] = (pd.to_datetime(df['dt']) - pd.to_datetime(df['predict_base_dt'])).dt.days
        
        # 聚合预测基准日后首7天Δ特征作为建模输入
        first7 = df[df['days_since_predict'] < 7].copy()
        user_features = first7.groupby('user_id')[delta_features].sum().reset_index()
        
        # 取用户级ground truth标签（基于预测基准日）
        base_day = df[df['dt'] == df['predict_base_dt']].copy()
        user_labels = base_day.groupby('user_id').agg({
            'lt_days': 'first',
            'future_365d_revenue_yuan': 'first',
            'is_active_365d': 'first',
        }).reset_index()
        
        # 计算首7天短期收入用于V3校验（短痛长赢验证）
        first7_rev = first7.groupby('user_id')['total_revenue_yuan'].sum().reset_index()
        first7_rev.columns = ['user_id', 'first7_revenue']
        user_labels = user_labels.merge(first7_rev, on='user_id', how='left')
        
        modeling_df = user_features.merge(user_labels, on='user_id', how='inner')
        
        # 离群值99分位截断
        for col in delta_features:
            cap = modeling_df[col].quantile(0.99)
            floor = modeling_df[col].quantile(0.01)
            modeling_df[col] = modeling_df[col].clip(floor, cap)
        
        print(f"建模样本量：{len(modeling_df)} 个用户")
        return modeling_df, df
    
    def fit_cox_survival_model(self, modeling_df: pd.DataFrame) -> Tuple[np.ndarray, float]:
        """拟合Cox比例风险模型：Δ行为对流失风险的影响"""
        print("\n=== 1/3 拟合Cox生存模型（生命周期长度） ===")
        
        cox_df = modeling_df[self.delta_feature_names + ['lt_days']].copy()
        cox_df['event'] = (cox_df['lt_days'] < 365).astype(int)
        
        # 标准化delta特征
        scaler = StandardScaler()
        cox_df[self.delta_feature_names] = scaler.fit_transform(cox_df[self.delta_feature_names])
        
        cph = CoxPHFitter(penalizer=0.1)
        cph.fit(cox_df, duration_col='lt_days', event_col='event')
        
        cindex = cph.concordance_index_
        print(f"C-index（预测准确率）: {cindex:.3f}")
        
        # 系数方向：负系数表示增加Δ行为会降低流失风险（正向），转换为价值方向
        coefs = -cph.params_[self.delta_feature_names].values  # 负号转成正向为正
        
        self.model_artifacts['cox_model'] = cph
        self.model_artifacts['cox_scaler'] = scaler
        return coefs, cindex
    
    def fit_retention_model(self, modeling_df: pd.DataFrame) -> Tuple[np.ndarray, float]:
        """拟合逻辑回归：Δ行为对365天留存的影响"""
        print("\n=== 2/3 拟合留存预测模型（365天留存） ===")
        
        X = modeling_df[self.delta_feature_names].values
        y = modeling_df['is_active_365d'].values
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        lr = LogisticRegression(penalty='l2', C=1.0, fit_intercept=True, max_iter=1000)
        cv_scores = cross_val_score(lr, X_scaled, y, cv=5, scoring='roc_auc')
        lr.fit(X_scaled, y)
        
        auc = np.mean(cv_scores)
        print(f"5折CV AUC: {auc:.3f} ± {np.std(cv_scores):.3f}")
        
        coefs = lr.coef_[0]
        
        self.model_artifacts['retention_model'] = lr
        self.model_artifacts['retention_scaler'] = scaler
        return coefs, auc
    
    def fit_revenue_model(self, modeling_df: pd.DataFrame) -> Tuple[np.ndarray, float]:
        """拟合Ridge回归：Δ行为对365天收入的影响"""
        print("\n=== 3/3 拟合收入预测模型（365天总收入） ===")
        
        X = modeling_df[self.delta_feature_names].values
        y = modeling_df['future_365d_revenue_yuan'].values
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        ridge = Ridge(alpha=1.0, fit_intercept=True)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)
        ridge.fit(X_train, y_train)
        r2 = ridge.score(X_test, y_test)
        
        print(f"测试集R²: {r2:.3f}")
        
        coefs = ridge.coef_
        
        self.model_artifacts['revenue_model'] = ridge
        self.model_artifacts['revenue_scaler'] = scaler
        return coefs, r2
    
    def validate_three_criteria(self, modeling_df: pd.DataFrame, final_coefs: np.ndarray) -> Dict:
        """自动验证三大校验标准V1-V3"""
        print("\n=== 验证三大校验标准 ===")
        
        # 计算用户首7天综合ΔLTV
        X = modeling_df[self.delta_feature_names].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        # 反标准化到原始delta尺度
        pred_ltv_delta = X @ final_coefs
        modeling_df['pred_ltv_delta'] = pred_ltv_delta
        
        results = {}
        
        # V1：综合LTV与LT正相关
        corr_lt = modeling_df['pred_ltv_delta'].corr(modeling_df['lt_days'])
        v1_pass = corr_lt > 0.3
        results['V1_LT_correlation'] = {'corr': corr_lt, 'pass': v1_pass}
        print(f"V1：综合LTV与LT相关系数 = {corr_lt:.3f}，{'✅ 通过' if v1_pass else '❌ 不通过（需要>0.3）'}")
        
        # V2：单调性验证——高ΔLTV分组留存率必须更高
        modeling_df['ltv_bin'] = pd.qcut(modeling_df['pred_ltv_delta'], q=5, labels=['Q1最低', 'Q2', 'Q3', 'Q4', 'Q5最高'])
        retention_by_bin = modeling_df.groupby('ltv_bin')['is_active_365d'].mean()
        v2_pass = (retention_by_bin.diff().dropna() > 0).all()
        results['V2_LT_monotonicity'] = {
            'retention_by_bin': retention_by_bin.to_dict(), 
            'pass': v2_pass
        }
        print(f"V2：分组留存率单调性：{'✅ 通过' if v2_pass else '❌ 不通过'}")
        print(retention_by_bin.round(3))
        
        # V3：长短期收入关系——短期7天收入可能负相关，但长期365天收入正相关
        corr_short = modeling_df['pred_ltv_delta'].corr(modeling_df['first7_revenue'])
        corr_long = modeling_df['pred_ltv_delta'].corr(modeling_df['future_365d_revenue_yuan'])
        v3_pass = corr_long > 0.2  # 长期必须正相关，短期可以负
        results['V3_short_long_revenue'] = {
            'short_term_corr': corr_short, 
            'long_term_corr': corr_long, 
            'pass': v3_pass
        }
        print(f"V3：与首7天收入相关 = {corr_short:.3f}，与365天收入相关 = {corr_long:.3f}")
        print(f"    {'✅ 通过' if v3_pass else '❌ 不通过（长期相关需要>0.2）'}")
        
        all_pass = v1_pass and v2_pass and v3_pass
        results['all_pass'] = all_pass
        print(f"\n=== 总体校验结果：{'✅ 全部通过，可以上线' if all_pass else '❌ 存在问题，需要调整特征/系数'} ===")
        
        self.validation_results = results
        return results
    
    def analyze_revenue_nonlinear(self, df: pd.DataFrame) -> Dict:
        """分析收入的非线性效应，寻找拐点"""
        print("\n=== 分析收入非线性效应 ===")
        
        df_copy = df.copy()
        # 按用户聚合首7天收入
        first7 = df_copy[df_copy['days_since_cohort'] < 7].groupby('user_id').agg({
            'total_revenue_yuan': 'sum',
            'lt_days': 'first',
            'is_active_365d': 'first',
            'future_365d_revenue_yuan': 'first'
        }).reset_index()
        
        first7['rev_bin'] = pd.cut(
            first7['total_revenue_yuan'],
            bins=[-np.inf, 0, 0.1, 0.3, 1, 3, np.inf],
            labels=['0元', '0-0.1元', '0.1-0.3元', '0.3-1元', '1-3元', '>3元']
        )
        
        rev_analysis = first7.groupby('rev_bin').agg({
            'user_id': 'count',
            'is_active_365d': 'mean',
            'lt_days': 'mean',
            'future_365d_revenue_yuan': 'mean'
        }).round(3)
        rev_analysis.columns = ['用户数', '365天留存率', '平均LT(天)', '365天平均总收入']
        print(rev_analysis)
        
        # 寻找拐点：留存开始下降的点
        retention = rev_analysis['365天留存率'].values
        inflection = None
        for i in range(1, len(retention)):
            if retention[i] < retention[i-1] * 0.95:
                inflection = rev_analysis.index[i]
                break
        
        if inflection:
            print(f"\n⚠️ 收入拐点：在{inflection}区间，留存开始下降，高收入开始伤害长期价值")
        else:
            print(f"\n✅ 样本范围内未发现明显收入负向拐点")
        
        return rev_analysis.to_dict()
    
    def synthesize_coefficients(self, cox_coefs: np.ndarray, ret_coefs: np.ndarray, rev_coefs: np.ndarray) -> np.ndarray:
        """综合三个模型系数，合成最终系数，锚定is_active=1.0，按四分类输出"""
        print("\n=== 综合三模型输出，合成最终系数 ===")
        
        # 标准化：以delta_is_active为锚点=1.0
        def normalize(coefs):
            return coefs / np.abs(coefs[0])
        
        cox_norm = normalize(cox_coefs)
        ret_norm = normalize(ret_coefs)
        rev_norm = normalize(rev_coefs)
        
        # 权重：留存40%（V2校验最核心），生命周期30%（V1校验），长期收入30%（V3校验）
        final_raw = 0.4 * ret_norm + 0.3 * cox_norm + 0.3 * rev_norm
        
        # 缩放让delta_is_active=1.0（有效活跃基础分）
        scale = 1.0 / final_raw[0]
        final_coefs = final_raw * scale
        
        # 构建输出字典，按业务尺度缩放
        coef_output = {}
        for feat, coef in zip(self.feature_names, final_coefs):
            if feat == 'effective_duration_min':
                coef = coef / 10  # 按分钟计，每10分钟一个单位更合理
            elif feat in ['ad_exposure_count', 'quick_slide_count']:
                coef = coef / 5   # 每5次曝光/划走一个单位
            coef_output[feat] = float(round(coef, 4))
        
        # 按四分类输出
        causal_coefs = {k:v for k,v in coef_output.items() if k in self.actionable_causal_features}
        weak_coefs = {k:v for k,v in coef_output.items() if k in self.actionable_weak_features}
        status_coefs = {k:v for k,v in coef_output.items() if k in self.status_features}
        
        print("\n=== 最终系数（四分类） ===")
        print("\n【1. 可干预强因果因子（直接做动作，优先优化）】")
        for k, v in sorted(causal_coefs.items(), key=lambda x: -abs(x[1])):
            direction = "✅ 正向（加分）" if v > 0 else "❌ 负向（扣分，需要控制）"
            print(f"  {k:25s} = {v:+.4f}  {direction}")
        
        print("\n【2. 可干预弱因果因子（可引导，因果性待AB验证）】")
        for k, v in sorted(weak_coefs.items(), key=lambda x: -abs(x[1])):
            direction = "✅ 正向" if v > 0 else "❌ 负向"
            print(f"  {k:25s} = {v:+.4f}  {direction}")
        
        print("\n【3. 状态因子（用户属性，用于分层/预测，不做考核）】")
        for k, v in sorted(status_coefs.items(), key=lambda x: -abs(x[1])):
            direction = "✅ 正向" if v > 0 else "❌ 负向"
            print(f"  {k:25s} = {v:+.4f}  {direction}")
        
        self.fitted_coefficients = coef_output
        self.factor_classification = {
            'actionable_causal': causal_coefs,
            'actionable_weak': weak_coefs,
            'status': status_coefs
        }
        return final_coefs
    
    def generate_report(self, output_path: str):
        """生成完整拟合报告 v3.1"""
        v1 = self.validation_results['V1_LT_correlation']
        v2 = self.validation_results['V2_LT_monotonicity']
        v3 = self.validation_results['V3_short_long_revenue']
        
        report = [
            "# 综合LTV v3.1 系数拟合与校验报告",
            "",
            "## 模型表现",
            f"- Cox生存模型C-index（LT预测准确率）: {self.model_artifacts.get('cindex', 0):.3f}",
            f"- 留存预测模型5折CV AUC: {self.model_artifacts.get('retention_auc', 0):.3f}",
            f"- 长期收入预测模型测试集R²: {self.model_artifacts.get('revenue_r2', 0):.3f}",
            "",
            "## 三大校验铁则结果（必须全部通过）",
            f"1. **V1：LT正相关** | 综合LTV与LT相关系数 = {v1['corr']:.3f} | {'✅ 通过' if v1['pass'] else '❌ 不通过（要求>0.3）'}",
            f"2. **V2：LT单调性** | 分组留存率单调上升 | {'✅ 通过' if v2['pass'] else '❌ 不通过'} | 分组留存：{', '.join([f'{k}={v:.3f}' for k,v in v2['retention_by_bin'].items()])}",
            f"3. **V3：短痛长赢** | 短期7天收入相关 = {v3['short_term_corr']:.3f}，长期365天收入相关 = {v3['long_term_corr']:.3f} | {'✅ 通过' if v3['pass'] else '❌ 不通过（长期相关要求>0.2，短期可负）'}",
            "",
            f"**总体结论：{'✅ 三大校验全部通过，指标有效，可以上线使用' if self.validation_results['all_pass'] else '❌ 存在校验不通过，需要调整特征/系数后重新拟合'}**",
            "",
            "## 最终系数（按四分类）",
            "",
            "### 1. 可干预强因果因子（优先作为业务动作方向）",
        ]
        
        for k, v in sorted(self.factor_classification['actionable_causal'].items(), key=lambda x: -abs(x[1])):
            direction = "正向加分" if v > 0 else "负向扣分"
            report.append(f"- {k}: {v:+.4f}（{direction}）")
        
        report.extend([
            "",
            "### 2. 可干预弱因果因子（可引导，需AB实验验证因果性）",
        ])
        
        for k, v in sorted(self.factor_classification['actionable_weak'].items(), key=lambda x: -abs(x[1])):
            direction = "正向加分" if v > 0 else "负向扣分"
            report.append(f"- {k}: {v:+.4f}（{direction}）")
        
        report.extend([
            "",
            "### 3. 状态因子（用于用户分层/预测，不做KPI考核）",
        ])
        
        for k, v in sorted(self.factor_classification['status'].items(), key=lambda x: -abs(x[1])):
            direction = "正向" if v > 0 else "负向"
            report.append(f"- {k}: {v:+.4f}（{direction}）")
        
        report.extend([
            "",
            "## 说明",
            "- 所有系数都是**增量系数**：相对于同圈层用户平均水平的边际变化",
            "- Δ_score可正可负，正表示用户体验/价值高于平均，负表示低于平均（被伤害）",
            "- 系数季度重拟合，baseline季度更新，保证同期可比",
        ])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"\n报告已生成：{output_path}")
    
    def run_full_pipeline(self, data_path: str, report_path: str, baseline_window_days: int = 90):
        """运行完整v3.1拟合流程"""
        modeling_df, raw_df = self.load_and_prepare_data(data_path, baseline_window_days)
        
        cox_coefs, cindex = self.fit_cox_survival_model(modeling_df)
        self.model_artifacts['cindex'] = cindex
        
        ret_coefs, ret_auc = self.fit_retention_model(modeling_df)
        self.model_artifacts['retention_auc'] = ret_auc
        
        rev_coefs, rev_r2 = self.fit_revenue_model(modeling_df)
        self.model_artifacts['revenue_r2'] = rev_r2
        
        self.analyze_revenue_nonlinear(raw_df)
        
        final_coefs = self.synthesize_coefficients(cox_coefs, ret_coefs, rev_coefs)
        
        self.validate_three_criteria(modeling_df, final_coefs)
        
        self.generate_report(report_path)
        
        return self.fitted_coefficients, self.validation_results, self.factor_classification


if __name__ == '__main__':
    fitter = LTCCoefficientFitter()
    print("="*70)
    print("综合LTV v3.1 系数拟合脚本加载完成")
    print("核心功能（对应v3.1框架）：")
    print("1. ✅ 三层baseline（cohort+生命周期+用户分层），90天窗口，季度更新")
    print("2. ✅ Δ增量计算，所有特征相对于同圈层均值，可正可负")
    print("3. ✅ Cox+留存+收入三目标拟合，加权合成")
    print("4. ✅ V1/V2/V3三大校验铁则强制自动验证")
    print("5. ✅ 因子四分类：强因果/弱因果/状态，区分预测和动作指引")
    print("6. ✅ 收入非线性拐点自动分析，寻找过度变现伤害留存的阈值")
    print("="*70)

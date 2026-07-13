# 报告 HTML 模板参考

> 本文件包含版本灰度分析报告中各章节的 HTML 模板，供 SKILL.md 引用。

---

## 一、实验概览模板

```html
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; border-radius: 12px; color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <h2 style="margin: 0 0 16px 0; font-size: 24px;">📊 版本灰度实验概览</h2>
  <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <tr><td style="padding: 8px 0; color: rgba(255,255,255,0.7);">实验组版本</td><td style="padding: 8px 0; font-weight: 600;">{实验组版本号}</td></tr>
    <tr><td style="padding: 8px 0; color: rgba(255,255,255,0.7);">对照组版本</td><td style="padding: 8px 0; font-weight: 600;">{对照组版本号}</td></tr>
    <tr><td style="padding: 8px 0; color: rgba(255,255,255,0.7);">分析时间范围</td><td style="padding: 8px 0; font-weight: 600;">{开始日期} ~ {结束日期}（共{N}天）</td></tr>
    <tr><td style="padding: 8px 0; color: rgba(255,255,255,0.7);">显著性水平</td><td style="padding: 8px 0; font-weight: 600;">α = 0.05</td></tr>
    <tr><td style="padding: 8px 0; color: rgba(255,255,255,0.7);">检验方法</td><td style="padding: 8px 0; font-weight: 600;">均值类 → Welch's t 检验 | 比率类 → Z 检验</td></tr>
  </table>
</div>
```

---

## 二、整体结论模板

### 2.1 核心发现摘要

```html
<div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 16px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <h3 style="margin: 0 0 16px 0; color: #1e293b; font-size: 18px;">🎯 核心发现</h3>
  <div style="display: flex; gap: 16px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 200px; background: #dcfce7; border-left: 4px solid #22c55e; padding: 16px; border-radius: 8px;">
      <div style="font-size: 32px; font-weight: 700; color: #16a34a;">{N}</div>
      <div style="color: #166534; font-size: 14px; margin-top: 4px;">✅ 显著正向指标</div>
      <div style="color: #15803d; font-size: 12px; margin-top: 8px; line-height: 1.6;">{列出所有显著正向的指标名称}</div>
    </div>
    <div style="flex: 1; min-width: 200px; background: #fee2e2; border-left: 4px solid #ef4444; padding: 16px; border-radius: 8px;">
      <div style="font-size: 32px; font-weight: 700; color: #dc2626;">{N}</div>
      <div style="color: #991b1b; font-size: 14px; margin-top: 4px;">❌ 显著负向指标</div>
      <div style="color: #b91c1c; font-size: 12px; margin-top: 8px; line-height: 1.6;">{列出所有显著负向的指标名称}</div>
    </div>
    <div style="flex: 1; min-width: 200px; background: #f1f5f9; border-left: 4px solid #94a3b8; padding: 16px; border-radius: 8px;">
      <div style="font-size: 32px; font-weight: 700; color: #64748b;">{N}</div>
      <div style="color: #475569; font-size: 14px; margin-top: 4px;">➡️ 不显著指标</div>
      <div style="color: #64748b; font-size: 12px; margin-top: 8px; line-height: 1.6;">{列出所有不显著的指标名称}</div>
    </div>
  </div>
</div>
```

### 2.2 发布建议

```html
<div style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); border-radius: 12px; padding: 20px; margin: 16px 0; color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <h3 style="margin: 0 0 12px 0; font-size: 18px;">📢 发布建议</h3>
  <div style="font-size: 20px; font-weight: 600; margin-bottom: 12px;">✅ 建议全量发布 / ⚠️ 建议延长观察 / ❌ 建议终止实验</div>
  <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; font-size: 14px; line-height: 1.6;"><strong>理由：</strong>{详细说明建议理由}</div>
</div>
```

### 2.3 风险提示

```html
<div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 12px; padding: 16px; margin: 16px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
    <span style="font-size: 20px;">⚠️</span>
    <span style="font-weight: 600; color: #92400e; font-size: 16px;">风险提示</span>
  </div>
  <ul style="margin: 0; padding-left: 20px; color: #78350f; font-size: 14px; line-height: 1.8;">
    <li>{如有显著负向指标，列出具体风险}</li>
    <li>{如样本量不足，列出具体指标}</li>
    <li>{如存在异常波动天，说明具体情况}</li>
  </ul>
</div>
```

---

## 三、指标差异对比模板

### 3.1 按模块指标差异对比表

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0;">
  <h3 style="color: #1e293b; font-size: 18px; margin-bottom: 16px;">📊 {模块名称} — 指标差异对比（{用户类型}）</h3>
  <table style="width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <thead>
      <tr style="background: #f1f5f9;">
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569;">指标名称</th>
        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569;">指标类型</th>
        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">对照组均值</th>
        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">实验组均值</th>
        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">绝对差异</th>
        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">相对提升</th>
        <th style="padding: 12px; text-align: center; border-bottom: 2px solid #e2e8f0; color: #475569;">趋势</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0;">{指标中文名}</td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0;"><span style="background: #dbeafe; color: #1d4ed8; padding: 2px 6px; border-radius: 4px; font-size: 11px;">mean</span> 或 <span style="background: #fce7f3; color: #be185d; padding: 2px 6px; border-radius: 4px; font-size: 11px;">ratio</span></td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">{对照组值}</td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">{实验组值}</td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">{绝对差异}</td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: right;"><span style="color: #16a34a; font-weight: 600;">🟢 +X.XX%</span> 或 <span style="color: #dc2626; font-weight: 600;">🔴 -X.XX%</span></td>
        <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">📈 或 📉 或 ➡️</td>
      </tr>
    </tbody>
  </table>
</div>
```

### 3.2 逐日指标差异对比表

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0;">
  <h3 style="color: #1e293b; font-size: 16px; margin-bottom: 12px;">📅 {指标中文名} — 逐日差异对比（{用户类型}）</h3>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <thead>
      <tr style="background: #f1f5f9;">
        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #e2e8f0; color: #475569;">日期</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">对照组</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">实验组</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">绝对差异</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">相对提升</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{日期}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{对照组值}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{实验组值}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{绝对差异}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;"><span style="color: #16a34a;">+X.XX%</span> 或 <span style="color: #dc2626;">-X.XX%</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 四、置信度计算原理与过程模板

### 4.1 均值类指标（Welch's t 检验）计算过程

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0; background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
  <div style="background: #eff6ff; padding: 16px 20px; border-bottom: 1px solid #bfdbfe;">
    <h4 style="margin: 0; color: #1e40af; font-size: 16px;">🔬 {指标中文名} — Welch's t 检验计算过程</h4>
    <div style="font-size: 12px; color: #3b82f6; margin-top: 4px;">日期: {date} | 用户类型: {user_type} | 检验方法: Welch's t-test</div>
  </div>
  <div style="padding: 20px;">
    <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 14px;">① 输入数据</h5>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px;">
      <tr style="background: #f8fafc;"><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">参数</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">对照组</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">实验组</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">样本量 n</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{n₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{n₁}</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">均值 x̄</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{x̄₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{x̄₁}</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">标准差 s</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{s₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{s₁}</td></tr>
    </table>
    <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 14px;">② 计算步骤</h5>
    <div style="background: #f8fafc; border-radius: 8px; padding: 16px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 2; color: #334155;">
      <div>SE = √(s₀²/n₀ + s₁²/n₁) = √({s₀}²/{n₀} + {s₁}²/{n₁}) = √({s₀²/n₀} + {s₁²/n₁}) = <strong>{SE}</strong></div>
      <div>Δ = x̄₁ - x̄₀ = {x̄₁} - {x̄₀} = <strong>{Δ}</strong></div>
      <div>t = Δ / SE = {Δ} / {SE} = <strong>{t}</strong></div>
      <div>df = (s₀²/n₀ + s₁²/n₁)² / [(s₀²/n₀)²/(n₀-1) + (s₁²/n₁)²/(n₁-1)] = <strong>{df}</strong></div>
      <div>p = 2 × P(T<sub>df={df}</sub> > |{t}|) = <strong>{p_value}</strong></div>
      <div>95% CI = [Δ - t<sub>α/2,df</sub> × SE, Δ + t<sub>α/2,df</sub> × SE] = <strong>[{ci_lower}, {ci_upper}]</strong></div>
      <div>Cohen's d = Δ / s<sub>pooled</sub> = {Δ} / {s_pooled} = <strong>{cohen_d}</strong></div>
    </div>
  </div>
</div>
```

### 4.2 比率类指标（Z 检验）计算过程

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0; background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
  <div style="background: #fdf4ff; padding: 16px 20px; border-bottom: 1px solid #e9d5ff;">
    <h4 style="margin: 0; color: #7e22ce; font-size: 16px;">🔬 {指标中文名} — 双样本比率 Z 检验计算过程</h4>
    <div style="font-size: 12px; color: #a855f7; margin-top: 4px;">日期: {date} | 用户类型: {user_type} | 检验方法: Two-proportion Z-test</div>
  </div>
  <div style="padding: 20px;">
    <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 14px;">① 输入数据</h5>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px;">
      <tr style="background: #f8fafc;"><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">参数</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">对照组</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0; font-weight: 600;">实验组</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">总数量 n</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{n₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{n₁}</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">成功数量 x</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{x₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{x₁}</td></tr>
      <tr><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">比率 p̂</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{p̂₀}</td><td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{p̂₁}</td></tr>
    </table>
    <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 14px;">② 计算步骤</h5>
    <div style="background: #f8fafc; border-radius: 8px; padding: 16px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 2; color: #334155;">
      <div>p̂₀ = x₀/n₀ = {x₀}/{n₀} = <strong>{p̂₀}</strong></div>
      <div>p̂₁ = x₁/n₁ = {x₁}/{n₁} = <strong>{p̂₁}</strong></div>
      <div>p̂ = (x₀ + x₁) / (n₀ + n₁) = ({x₀} + {x₁}) / ({n₀} + {n₁}) = <strong>{p̂}</strong></div>
      <div>SE_pooled = √[p̂(1-p̂)(1/n₀ + 1/n₁)] = √[{p̂}×{1-p̂}×(1/{n₀} + 1/{n₁})] = <strong>{SE_pooled}</strong></div>
      <div>Z = (p̂₁ - p̂₀) / SE_pooled = ({p̂₁} - {p̂₀}) / {SE_pooled} = <strong>{Z}</strong></div>
      <div>p = 2 × Φ(-|Z|) = 2 × Φ(-{|Z|}) = <strong>{p_value}</strong></div>
      <div>SE_unpooled = √[p̂₁(1-p̂₁)/n₁ + p̂₀(1-p̂₀)/n₀] = <strong>{SE_unpooled}</strong></div>
      <div>95% CI = [(p̂₁-p̂₀) - Z<sub>α/2</sub>×SE_unpooled, (p̂₁-p̂₀) + Z<sub>α/2</sub>×SE_unpooled] = <strong>[{ci_lower}, {ci_upper}]</strong></div>
      <div>Odds Ratio = [p̂₁/(1-p̂₁)] / [p̂₀/(1-p̂₀)] = <strong>{OR}</strong></div>
    </div>
  </div>
</div>
```

---

## 五、置信度计算结果汇总模板

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0;">
  <h3 style="color: #1e293b; font-size: 18px; margin-bottom: 16px;">📊 置信度计算结果汇总（{用户类型}）</h3>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <thead>
      <tr style="background: #f1f5f9;">
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569;">模块</th>
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569;">指标</th>
        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e2e8f0; color: #475569;">检验方法</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">统计量</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">p 值</th>
        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #e2e8f0; color: #475569;">95% CI</th>
        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e2e8f0; color: #475569;">效应量</th>
        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #e2e8f0; color: #475569;">结论</th>
      </tr>
    </thead>
    <tbody>
      <tr style="background: #f0fdf4;">
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0;">{模块名}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0;">{指标中文名}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0;">t-test / Z-test</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">t={值} / Z={值}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">{p值}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">[{下限}, {上限}]</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">d={值} / OR={值}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: center;"><span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-size: 11px;">✅ 显著正向</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 六、各模块详细分析模板

### 单指标详细分析卡片

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0; background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
  <div style="background: {背景色}; padding: 16px 20px; border-bottom: 1px solid {边框色};">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h4 style="margin: 0; color: {标题色}; font-size: 16px;">{指标中文名} ({英文字段名})</h4>
        <div style="font-size: 12px; color: {副标题色}; margin-top: 4px;">{模块名} | {metric_type} | {检验方法}</div>
      </div>
      <span style="background: {标签背景}; color: {标签色}; padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: 600;">{结论标签}</span>
    </div>
  </div>
  <div style="padding: 20px;">
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px;">
      <div style="background: #f8fafc; padding: 16px; border-radius: 8px; text-align: center;">
        <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">对照组</div>
        <div style="font-size: 24px; font-weight: 700; color: #1e293b;">{对照组值}</div>
      </div>
      <div style="background: #f8fafc; padding: 16px; border-radius: 8px; text-align: center;">
        <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">实验组</div>
        <div style="font-size: 24px; font-weight: 700; color: #1e293b;">{实验组值}</div>
      </div>
      <div style="background: {差异背景}; padding: 16px; border-radius: 8px; text-align: center;">
        <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">相对提升</div>
        <div style="font-size: 24px; font-weight: 700; color: {差异色};">{+X.XX% / -X.XX%}</div>
      </div>
    </div>
    <h5 style="margin: 0 0 8px 0; color: #1e293b; font-size: 14px;">📊 结论</h5>
    <div style="font-size: 14px; color: #1e293b; line-height: 1.8;">
      <span style="background: {标签背景}; color: {标签色}; padding: 2px 8px; border-radius: 4px; font-weight: 600;">{结论标签}</span><br><br>
      • 实验组{指标中文名}比对照组{高/低} <strong>{绝对差异}</strong><br>
      • p = {p值} {</>/>=} 0.05，差异{具有/不具有}统计显著性<br>
      • 95%置信区间 <strong>[{下限}, {上限}]</strong> {包含/不包含}0，结果{不可靠/可靠}
    </div>
  </div>
</div>
```

---

## 七、附录：统计方法说明模板

```html
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 16px 0;">
  <h3 style="color: #1e293b; font-size: 18px; margin-bottom: 16px;">📚 统计方法说明</h3>
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
      <h4 style="color: #3b82f6; font-size: 14px; margin: 0 0 12px 0;">🔬 检验方法选择</h4>
      <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
        <tr style="background: #f8fafc;"><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">类型</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">方法</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">均值类</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">Welch's t</td></tr>
        <tr><td style="padding: 8px;">比率类</td><td style="padding: 8px;">Z 检验</td></tr>
      </table>
    </div>
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
      <h4 style="color: #8b5cf6; font-size: 14px; margin: 0 0 12px 0;">📏 效应量解读</h4>
      <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
        <tr style="background: #f8fafc;"><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">大小</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">Cohen's d</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">OR</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">小</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">0.2</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">1.5</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">中</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">0.5</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">2.5</td></tr>
        <tr><td style="padding: 8px;">大</td><td style="padding: 8px;">0.8</td><td style="padding: 8px;">4.3</td></tr>
      </table>
    </div>
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
      <h4 style="color: #f59e0b; font-size: 14px; margin: 0 0 12px 0;">⚖️ 决策规则</h4>
      <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
        <tr style="background: #f8fafc;"><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">p值</td><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">决策</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">&lt;0.01</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9; color: #16a34a;">强烈采纳</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">&lt;0.05</td><td style="padding: 8px; border-bottom: 1px solid #f1f5f9; color: #3b82f6;">建议采纳</td></tr>
        <tr><td style="padding: 8px;">≥0.05</td><td style="padding: 8px; color: #64748b;">不显著</td></tr>
      </table>
    </div>
  </div>
</div>
```

# STL 周期剥离 / 时序分解

适用范式 3（波动分析）+ 范式 6（趋势分析）。

## 何时用

- 用户问"这是真异常还是周末效应 / 月初效应"
- 想剥离日 / 周 / 月周期，看真趋势 + 真噪声
- 趋势分析里 R² 很低，怀疑被周期性带噪

`statsmodels.tsa.seasonal.STL` 是首选（鲁棒、支持任意周期、支持 robust 模式）。

---

## 输入 schema

```
data/T1_dau.csv
date,dau
```

时间索引必须是连续日期（用 pandas asfreq 补 NaN）。

## 模板

```python
"""T{n}: STL 分解 + 周期剥离 + 异常检测"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

df = pd.read_csv('data/T1_dau.csv', parse_dates=['date']).sort_values('date')
y = df.set_index('date')['dau'].asfreq('D')
assert len(y) >= 14, "STL 至少 2 个周期"

# 周周期（period=7）；如果业务有月周期，可以 period=30 或叠两层 STL
stl = STL(y, period=7, robust=True)
res = stl.fit()

trend, seasonal, resid = res.trend, res.seasonal, res.resid

# 1. 落 CSV：每天的分解
out = pd.DataFrame({
    'date': y.index,
    'observed': y.values,
    'trend': trend.values,
    'seasonal': seasonal.values,
    'resid': resid.values,
})
out.to_csv('data/T{n}_decomposition.csv', index=False)

# 2. 残差异常点：|resid| > 2σ_resid
sigma_resid = float(np.nanstd(resid.values))
anomaly_mask = np.abs(resid.values) > 2 * sigma_resid
anomalies = pd.DataFrame({
    'date': y.index[anomaly_mask],
    'observed': y.values[anomaly_mask],
    'resid': resid.values[anomaly_mask],
    'resid_in_sigma': resid.values[anomaly_mask] / max(sigma_resid, 1e-9),
})
anomalies.to_csv('data/T{n}_anomalies.csv', index=False)

# 3. 四宫格图
fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
axes[0].plot(y.index, y.values, color='k'); axes[0].set_ylabel('observed')
axes[1].plot(trend.index, trend.values, color='C0'); axes[1].set_ylabel('trend')
axes[2].plot(seasonal.index, seasonal.values, color='C1'); axes[2].set_ylabel('seasonal (period=7)')
axes[3].plot(resid.index, resid.values, color='C3'); axes[3].set_ylabel('resid')
axes[3].axhline(2 * sigma_resid, color='gray', linestyle=':', alpha=0.5)
axes[3].axhline(-2 * sigma_resid, color='gray', linestyle=':', alpha=0.5)
# 高亮异常点
if anomaly_mask.any():
    axes[3].scatter(y.index[anomaly_mask], resid.values[anomaly_mask],
                    color='red', zorder=5, s=20)
axes[0].set_title(f"STL 分解（period=7, robust=True）")
fig.tight_layout()
fig.savefig('charts/T{n}_stl.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# 4. 关键统计 → stdout
total_var = float(np.var(y.values))
trend_var = float(np.var(trend.values))
seasonal_var = float(np.var(seasonal.values))
resid_var = float(np.var(resid.values))
print(f"variance breakdown:")
print(f"  trend     {trend_var/total_var:.1%}")
print(f"  seasonal  {seasonal_var/total_var:.1%}")
print(f"  resid     {resid_var/total_var:.1%}")
print(f"resid std = {sigma_resid:.2f}")
print(f"anomalies (|resid| > 2σ): {len(anomalies)} days")
if not anomalies.empty:
    print(anomalies.to_string(index=False))
```

---

## 输出契约

| 文件 | schema |
|---|---|
| `data/T{n}_decomposition.csv` | `date,observed,trend,seasonal,resid` |
| `data/T{n}_anomalies.csv` | `date,observed,resid,resid_in_sigma` |
| `charts/T{n}_stl.png` | 四宫格：observed / trend / seasonal / resid |

## 必打 stdout

```
variance breakdown: trend X.X%, seasonal X.X%, resid X.X%
resid std = ...
anomalies (|resid| > 2σ): N days
```

## 反模式

- ❌ period 写死成 7（业务有月度的要 period=30）
- ❌ 不开 robust=True：异常值会污染 trend
- ❌ 不算 variance breakdown：不知道周期到底贡献了多少
- ❌ 异常点用 |resid| > 1σ 太敏感，按 2σ

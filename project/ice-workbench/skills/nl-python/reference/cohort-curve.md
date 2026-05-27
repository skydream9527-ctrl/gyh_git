# 留存曲线拟合 + LT-DAU 外推

适用范式 8e（留存曲线拟合 + 外推）+ 范式 7（留存分析的延伸）。

## 适用条件

- 已有 ≥ 2 个 cohort，每个 cohort 至少观测到 D7（D14 更稳）
- 想从早期留存（D1/D7/D30）外推到 LT-DAU（D60+ / D90+）
- SQL 不能拟合，必须 Python

## 模型选择

| 数据形态 | 模型 | 公式 | 适用场景 |
|---|---|---|---|
| 缓降、长尾 | **幂律** | `r(d) = a · d^(-b)` | 中长尾内容产品 |
| 陡降、最终趋稳 | **指数 + 截距** | `r(d) = a · exp(-b·d) + c` | 高活产品 / 工具类 |
| 多段斜率 | **双段** | 早期指数 + 长尾幂律拼接 | 复杂用户结构 |

至少试 2 个，对比 R²，选高的。R² < 0.8 不允许外推到 D60+。

---

## 输入 CSV schema

```
data/T1_cohort_retention.csv
cohort,day_n,retention
2026-04-01,1,0.62
2026-04-01,3,0.45
2026-04-01,7,0.32
...
```

---

## 模板（双模型对比）

```python
"""T{n}: 留存曲线拟合 + LT 外推"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

df = pd.read_csv('data/T1_cohort_retention.csv')
assert {'cohort', 'day_n', 'retention'}.issubset(df.columns), "schema 不符"

# 模型族
def power(d, a, b):
    return a * np.power(d, -b)
def exp_with_floor(d, a, b, c):
    return a * np.exp(-b * d) + c

results = []
fig, axes = plt.subplots(1, len(df['cohort'].unique()), figsize=(5 * len(df['cohort'].unique()), 4),
                         sharey=True, squeeze=False)
axes = axes.ravel()

for i, (cohort, g) in enumerate(df.groupby('cohort')):
    g = g.sort_values('day_n')
    d, r = g['day_n'].values.astype(float), g['retention'].values
    # 拟合幂律
    try:
        p_power, _ = curve_fit(power, d, r, p0=[1.0, 0.5], maxfev=5000)
        r_hat_power = power(d, *p_power)
        ss_res = np.sum((r - r_hat_power) ** 2)
        ss_tot = np.sum((r - np.mean(r)) ** 2)
        r2_power = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    except Exception as e:
        p_power, r2_power = None, np.nan
        print(f"cohort {cohort} 幂律拟合失败：{e}")

    # 拟合指数 + 截距
    try:
        p_exp, _ = curve_fit(exp_with_floor, d, r, p0=[0.5, 0.1, 0.1],
                             bounds=([0, 0, 0], [1, 5, 1]), maxfev=5000)
        r_hat_exp = exp_with_floor(d, *p_exp)
        r2_exp = 1 - np.sum((r - r_hat_exp) ** 2) / ss_tot if ss_tot > 0 else 0
    except Exception as e:
        p_exp, r2_exp = None, np.nan
        print(f"cohort {cohort} 指数拟合失败：{e}")

    # 选 R² 高的
    if not np.isnan(r2_power) and (np.isnan(r2_exp) or r2_power >= r2_exp):
        chosen, params, r2 = 'power', p_power, r2_power
        predict = lambda dd: power(np.array(dd, dtype=float), *params)
    else:
        chosen, params, r2 = 'exp', p_exp, r2_exp
        predict = lambda dd: exp_with_floor(np.array(dd, dtype=float), *params)

    if r2 < 0.8:
        warning = f"WARN R²={r2:.3f} < 0.8，外推到 D60+ 不可靠"
    else:
        warning = ""

    # 外推到 D90
    days_full = np.arange(1, 91)
    r_full = predict(days_full)

    # LT-DAU 积分（trapezoidal，从 D1 到 D90）
    lt_d90 = float(np.trapz(r_full, days_full))

    results.append({
        'cohort': cohort,
        'model': chosen,
        'r2': float(r2),
        'd1_actual': float(g[g['day_n'] == 1]['retention'].iloc[0]) if (g['day_n'] == 1).any() else np.nan,
        'd7_actual': float(g[g['day_n'] == 7]['retention'].iloc[0]) if (g['day_n'] == 7).any() else np.nan,
        'd30_pred': float(predict([30])[0]),
        'd60_pred': float(predict([60])[0]),
        'd90_pred': float(predict([90])[0]),
        'lt_to_d90': lt_d90,
        'warning': warning,
    })

    ax = axes[i]
    ax.scatter(d, r, label='观测', color='k', zorder=3)
    ax.plot(days_full, r_full, '-', label=f'{chosen} (R²={r2:.3f})')
    ax.set_title(f'{cohort}'); ax.set_xlabel('day_n'); ax.set_ylabel('retention')
    ax.legend(); ax.grid(True, alpha=0.3)

fig.savefig('charts/T{n}_cohort_curve_fit.png', dpi=120, bbox_inches='tight')
plt.close(fig)

out = pd.DataFrame(results)
out.to_csv('data/T{n}_cohort_lt.csv', index=False)
print(out[['cohort', 'model', 'r2', 'd30_pred', 'd60_pred', 'd90_pred', 'lt_to_d90']]
      .to_string(index=False))
```

---

## 必落字段（Phase 5 引用）

| 字段 | 含义 |
|---|---|
| `model` | power / exp，每 cohort 一个 |
| `r2` | 拟合优度（< 0.8 不允许外推到 D60+）|
| `d30_pred / d60_pred / d90_pred` | 外推留存 |
| `lt_to_d90` | LT 积分（DAU/UV 的 D90 累计贡献因子）|
| `warning` | 低置信告警 |

## 反模式

- ❌ R² < 0.8 还外推到 D90 不写 warning
- ❌ 只拟合一种函数族
- ❌ 拟合后不画散点对比，看不到拟合质量
- ❌ LT 用单一 day 值乘以 N 天估计（不是积分）

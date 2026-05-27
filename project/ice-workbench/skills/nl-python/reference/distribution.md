# 分布分析的 Python 增强

适用范式 5（分布分析）。SQL 算分位数容易，但**形态判定 / 双峰检测 / 集中度 / 分布拟合**要 Python。

## 模板

```python
"""T{n}: 分布分析"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

df = pd.read_csv('data/T1_user_consumption.csv')   # 列：user_id,value
x = df['value'].dropna().values.astype(float)
assert len(x) > 30, "至少 30 个样本"

# 描述性
desc = {
    'n': len(x),
    'mean': float(np.mean(x)),
    'median': float(np.median(x)),
    'std': float(np.std(x)),
    'p10': float(np.percentile(x, 10)),
    'p50': float(np.percentile(x, 50)),
    'p90': float(np.percentile(x, 90)),
    'p99': float(np.percentile(x, 99)),
    'max': float(np.max(x)),
    'cv': float(np.std(x) / np.mean(x)) if np.mean(x) != 0 else np.nan,
    'skew': float(stats.skew(x)),
    'kurtosis': float(stats.kurtosis(x)),
}

# 形态判定（启发式）
p90_p50_ratio = desc['p90'] / max(desc['p50'], 1e-9)
if p90_p50_ratio > 5:
    shape = '长尾（P90/P50 > 5）'
elif desc['skew'] < 0.5 and abs(desc['kurtosis']) < 1:
    shape = '近正态'
else:
    shape = '中度偏斜'

# 双峰检测：simple kmeans on 1D
from sklearn.cluster import KMeans
km = KMeans(n_clusters=2, n_init=10, random_state=42).fit(x.reshape(-1, 1))
centers = sorted(km.cluster_centers_.flatten())
within_inertia = km.inertia_
# 比对 1-cluster (variance * n)
single_inertia = np.var(x) * len(x)
ratio = within_inertia / single_inertia if single_inertia > 0 else 1
bimodal = ratio < 0.6   # k=2 显著降惯性 → 双峰
print(f"双峰检测：centers={centers}, ratio={ratio:.3f}, "
      f"判定={'双峰' if bimodal else '单峰'}")

# 头/腰/尾占比
sorted_x = np.sort(x)[::-1]
total = sorted_x.sum()
top1pct_n = max(1, int(len(x) * 0.01))
top10pct_n = max(1, int(len(x) * 0.10))
top1pct_share = float(sorted_x[:top1pct_n].sum() / total) if total > 0 else 0
top10pct_share = float(sorted_x[:top10pct_n].sum() / total) if total > 0 else 0

# 基尼系数
def gini(arr):
    arr = np.sort(arr.astype(float))
    n = len(arr)
    if n == 0 or arr.sum() == 0:
        return 0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(arr) / (n * arr.sum()))
g = gini(x)

summary = {**desc, 'shape': shape, 'bimodal': bimodal,
           'top1pct_share': top1pct_share, 'top10pct_share': top10pct_share,
           'gini': g}
pd.DataFrame([summary]).to_csv('data/T{n}_distribution.csv', index=False)

# 双图：直方图 + CDF
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(x, bins=50, color='C0', alpha=0.7)
axes[0].axvline(desc['mean'], color='r', linestyle='--', label=f"mean={desc['mean']:.1f}")
axes[0].axvline(desc['median'], color='g', linestyle='--', label=f"median={desc['median']:.1f}")
axes[0].legend(); axes[0].set_title(f'直方图 ({shape})')
sorted_x_asc = np.sort(x)
axes[1].plot(sorted_x_asc, np.arange(1, len(x) + 1) / len(x))
axes[1].set_title(f'CDF (gini={g:.3f}, top1%={top1pct_share:.1%})')
fig.savefig('charts/T{n}_distribution.png', dpi=120, bbox_inches='tight')
plt.close(fig)
print(pd.DataFrame([summary]).T.to_string(header=False))
```

## 必打 stdout

```
descriptive (n / mean / median / p10/p50/p90/p99 / std / cv / skew / kurtosis)
shape: 长尾 / 近正态 / 偏斜
双峰检测：单峰 / 双峰
top1% share, top10% share, gini
```

## 反模式

- ❌ 只看 mean → 长尾被中位数误导
- ❌ 不报 gini → 没法量化集中度
- ❌ 用 KS test 判正态（KS 对正态太敏感）→ 用 skew/kurtosis 启发式更稳
- ❌ 双峰判据用肉眼 → 用 KMeans inertia 比值

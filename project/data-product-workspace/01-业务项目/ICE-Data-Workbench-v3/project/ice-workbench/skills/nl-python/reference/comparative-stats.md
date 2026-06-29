# 对比分析的统计方法

适用范式 1（对比分析）。SQL 给不了置信区间和显著性；这里补齐。

## 三种工具

| 工具 | 何时用 | 库 |
|---|---|---|
| **Bootstrap CI** | 给指标差值置信区间（不假设分布）| `numpy.random` |
| **Permutation test** | 检验 A vs B 的差异是否显著（非参）| 自实现 |
| **Welch's t-test** | A/B 都是正态/近似正态，要快速 p-value | `scipy.stats.ttest_ind` |
| **KS test** | 两分布形态是否相同（非参）| `scipy.stats.ks_2samp` |
| **Chi-square** | 类别频次比对（漏斗 / 留存桶）| `scipy.stats.chi2_contingency` |

---

## 输入 schema（A/B 两列）

```
data/T1_compare.csv
group,value
A,123
A,145
B,98
B,110
...
```

或宽表两个 CSV：`data/T1_a.csv` 和 `data/T1_b.csv`，各一列 `value`。

---

## 模板：bootstrap + permutation + 两类 test 全跑

```python
"""T{n}: 对比分析 - bootstrap + permutation + KS"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# 输入：长表 group,value
df = pd.read_csv('data/T1_compare.csv')
a = df[df['group'] == 'A']['value'].dropna().values.astype(float)
b = df[df['group'] == 'B']['value'].dropna().values.astype(float)
print(f"n_A = {len(a)}, n_B = {len(b)}")
print(f"mean_A = {a.mean():.3f}, mean_B = {b.mean():.3f}")
print(f"observed diff (B - A) = {b.mean() - a.mean():.3f}")

# --- Bootstrap CI for B - A ---
rng = np.random.default_rng(42)
B = 5000
boot_diffs = np.empty(B)
for i in range(B):
    sa = rng.choice(a, size=len(a), replace=True)
    sb = rng.choice(b, size=len(b), replace=True)
    boot_diffs[i] = sb.mean() - sa.mean()
ci_lo, ci_hi = np.percentile(boot_diffs, [2.5, 97.5])
print(f"bootstrap 95% CI for (B - A) mean diff: [{ci_lo:.3f}, {ci_hi:.3f}]")

# --- Permutation test ---
combined = np.concatenate([a, b])
n_a = len(a)
observed = b.mean() - a.mean()
n_perm = 5000
perm_diffs = np.empty(n_perm)
for i in range(n_perm):
    rng.shuffle(combined)
    perm_diffs[i] = combined[n_a:].mean() - combined[:n_a].mean()
p_perm = float(np.mean(np.abs(perm_diffs) >= np.abs(observed)))
print(f"permutation p-value (two-sided): {p_perm:.4f}")

# --- Welch's t (parametric, fast) ---
t_stat, p_t = stats.ttest_ind(a, b, equal_var=False)
print(f"Welch's t = {t_stat:.3f}, p = {p_t:.4f}")

# --- KS test (distribution shape) ---
ks_stat, p_ks = stats.ks_2samp(a, b)
print(f"KS stat = {ks_stat:.3f}, p = {p_ks:.4f} "
      f"({'同分布' if p_ks > 0.05 else '分布显著不同'})")

# --- 落表 ---
out = pd.DataFrame([{
    'group_A_n': len(a), 'group_B_n': len(b),
    'mean_A': a.mean(), 'mean_B': b.mean(), 'std_A': a.std(), 'std_B': b.std(),
    'diff_B_minus_A': observed,
    'bootstrap_ci_low': ci_lo, 'bootstrap_ci_high': ci_hi,
    'permutation_p': p_perm,
    'welch_t': float(t_stat), 'welch_p': float(p_t),
    'ks_stat': float(ks_stat), 'ks_p': float(p_ks),
}])
out.to_csv('data/T{n}_comparison.csv', index=False)

# --- 可视化：分布 + bootstrap diff ---
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(a, bins=30, alpha=0.5, label=f'A (n={len(a)})', density=True)
axes[0].hist(b, bins=30, alpha=0.5, label=f'B (n={len(b)})', density=True)
axes[0].set_title('分布对比'); axes[0].legend(); axes[0].set_xlabel('value')

axes[1].hist(boot_diffs, bins=50, color='gray', alpha=0.7)
axes[1].axvline(observed, color='red', label=f'观测 diff={observed:.3f}', linewidth=2)
axes[1].axvspan(ci_lo, ci_hi, color='blue', alpha=0.15, label=f'95% CI')
axes[1].axvline(0, color='black', linestyle='--', alpha=0.5)
axes[1].set_title(f'Bootstrap diff (B-A) | perm p={p_perm:.4f}')
axes[1].set_xlabel('B mean - A mean'); axes[1].legend()

fig.savefig('charts/T{n}_comparison.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# --- 显著性结论 ---
if ci_lo > 0 or ci_hi < 0:
    sig = "差异显著（95% CI 不跨 0）"
elif p_perm < 0.05:
    sig = f"差异显著（perm p={p_perm:.4f} < 0.05）"
else:
    sig = f"差异不显著（CI 跨 0 且 perm p={p_perm:.4f} ≥ 0.05）"
print(f"结论：{sig}")
```

---

## 输出契约

`data/T{n}_comparison.csv` 一行总结：

```
group_A_n,group_B_n,mean_A,mean_B,std_A,std_B,diff_B_minus_A,
bootstrap_ci_low,bootstrap_ci_high,permutation_p,
welch_t,welch_p,ks_stat,ks_p
```

## 必打 stdout

```
n_A, n_B, mean_A, mean_B
observed diff
bootstrap 95% CI
permutation p
welch's t & p
KS stat & p
结论：显著 / 不显著
```

## 反模式

- ❌ 只跑 t 检验不跑 bootstrap（小样本时 t 不稳）
- ❌ 不报样本量
- ❌ 单边 p 没说明（默认双边）
- ❌ p < 0.05 直接喊"显著"不报效应量（CI 区间 + Cohen's d 更可信）
- ❌ KS p > 0.05 喊"完全相同"（只是不能拒绝相同假设）

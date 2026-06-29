# 变点检测 · Change-point Detection

适用范式 8f（变点检测）+ 范式 6（趋势分析）。SQL 不能算；Python 必走。

## 何时用

- 用户问"什么时候开始下跌"、"拐点在哪天"
- 看到时序明显有阶段性，但不知道精确边界
- 想把异动归因到具体事件（推全 / 活动 / 政策）

## 算法选型

| 算法 | 库 | 适用 |
|---|---|---|
| **PELT** | `ruptures.Pelt` | 默认；O(n) 全局最优；适合一般时序 |
| **Binary segmentation** | `ruptures.Binseg` | 想限定变点数量 K；更快 |
| **Window-based** | `ruptures.Window` | 在线 / 流式数据 |

`ruptures` 的核心三参数：
- `model`: `"l1"` (L1 cost; 适合方差异质数据) / `"l2"` (默认; mean shift) / `"rbf"` (非参；分布变化)
- `pen` (Pelt): penalty，越大变点越少；调到稳定再写死
- `n_bkps` (Binseg): 想要的变点数

---

## 输入 schema

```
data/T1_dau.csv
date,dau
2026-04-01,123456
...
```

---

## 模板（PELT，默认推荐）

```python
"""T{n}: 变点检测 + 事件关联"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ruptures as rpt

df = pd.read_csv('data/T1_dau.csv', parse_dates=['date']).sort_values('date').reset_index(drop=True)
assert len(df) >= 28, "变点检测建议 ≥28 天数据"

signal = df['dau'].values.astype(float)

# PELT (l2 cost = mean shift)；penalty 调参指引：penalty ≈ 3 * log(n) * std
n = len(signal)
sigma = float(np.std(signal))
penalty = 3 * np.log(n) * sigma
algo = rpt.Pelt(model='l2', min_size=3).fit(signal)
breakpoints = algo.predict(pen=penalty)
# breakpoints 包含 n（结束位置），去掉
bkps_idx = [b for b in breakpoints if b < n]

# 段内统计
segments = []
prev = 0
for i, bp in enumerate(breakpoints):
    seg = signal[prev:bp]
    segments.append({
        'segment': i + 1,
        'start_date': df['date'].iloc[prev].strftime('%Y-%m-%d'),
        'end_date': df['date'].iloc[bp - 1].strftime('%Y-%m-%d'),
        'n_days': bp - prev,
        'mean': float(np.mean(seg)),
        'std': float(np.std(seg)),
    })
    prev = bp
seg_df = pd.DataFrame(segments)

# 段间均值差 / 段内 std 比值（显著性参考）
for j in range(1, len(seg_df)):
    diff = seg_df.loc[j, 'mean'] - seg_df.loc[j - 1, 'mean']
    pooled_std = max((seg_df.loc[j - 1, 'std'] + seg_df.loc[j, 'std']) / 2, 1e-9)
    seg_df.loc[j, 'jump'] = diff
    seg_df.loc[j, 'jump_in_sigma'] = diff / pooled_std

seg_df.to_csv('data/T{n}_segments.csv', index=False)

# 变点表（事件关联留空，agent 之后让用户填或自动 join 已知事件 CSV）
bkps_df = pd.DataFrame({
    'breakpoint_date': [df['date'].iloc[i].strftime('%Y-%m-%d') for i in bkps_idx],
    'jump': [seg_df['jump'].iloc[i + 1] if (i + 1) < len(seg_df) else np.nan
             for i in range(len(bkps_idx))],
    'jump_in_sigma': [seg_df['jump_in_sigma'].iloc[i + 1] if (i + 1) < len(seg_df) else np.nan
                      for i in range(len(bkps_idx))],
    'event': [None] * len(bkps_idx),  # 由 agent / 用户填
})
bkps_df.to_csv('data/T{n}_breakpoints.csv', index=False)

# 图
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df['date'], signal, 'k-', linewidth=1.2)
for i in bkps_idx:
    ax.axvline(df['date'].iloc[i], color='C3', linestyle='--', alpha=0.7)
# 段均值水平线
prev = 0
for i, bp in enumerate(breakpoints):
    seg_mean = seg_df.loc[i, 'mean']
    ax.hlines(seg_mean, df['date'].iloc[prev], df['date'].iloc[bp - 1],
              colors='C0', linestyles='-', linewidth=2, alpha=0.6)
    prev = bp
ax.set_title(f"PELT 变点检测（penalty={penalty:.0f}, σ={sigma:.0f}）")
ax.set_xlabel('date'); ax.set_ylabel('value')
fig.savefig('charts/T{n}_changepoints.png', dpi=120, bbox_inches='tight')
plt.close(fig)

print(f"detected {len(bkps_idx)} breakpoints (penalty={penalty:.0f})")
print(bkps_df.to_string(index=False))
print()
print("segments:")
print(seg_df.to_string(index=False))
```

---

## 输出契约

`data/T{n}_breakpoints.csv` schema:
```
breakpoint_date,jump,jump_in_sigma,event
2026-04-15,-12345.0,-2.3,
2026-05-02,+8901.0,+1.7,
```

`data/T{n}_segments.csv` schema:
```
segment,start_date,end_date,n_days,mean,std,jump,jump_in_sigma
1,2026-04-01,2026-04-14,14,150000,4500,,
2,2026-04-15,2026-05-01,17,137655,3200,-12345,-2.3
...
```

## 必打 stdout

```
detected N breakpoints (penalty=...)
breakpoints table
segments table
```

## 反模式

- ❌ 检测出 10+ 变点全报上来 → penalty 过低，调高再跑
- ❌ 不报段内 std 和 jump_in_sigma → 没法判显著性
- ❌ penalty 来路不明 → 写明"3 · log(n) · std" 计算公式
- ❌ 不画段均值水平线 → 用户看不到段间结构
- ❌ 自动归因到事件（这是 agent / 用户的职责，Python 只输出"无标注"）

# 留存分析（cohort 矩阵 + 聚类）

适用范式 7（留存分析）。SQL 算 cohort × Day-N 留存矩阵简单；**热力图 + cohort 聚类**走 Python。

## 输入 schema（长表）

```
data/T1_cohort_retention.csv
cohort,day_n,retention,cohort_size
2026-04-01,1,0.62,15234
2026-04-01,3,0.45,15234
...
```

## 模板

```python
"""T{n}: cohort 留存矩阵 + cohort 聚类"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans

df = pd.read_csv('data/T1_cohort_retention.csv', parse_dates=['cohort'])

# pivot 成矩阵：rows=cohort, cols=day_n
mat = df.pivot_table(index='cohort', columns='day_n', values='retention')
print("cohort 留存矩阵 shape:", mat.shape)

# 热力图
fig, ax = plt.subplots(figsize=(10, max(4, len(mat) * 0.35)))
sns.heatmap(mat, annot=True, fmt='.2f', cmap='YlGnBu',
            cbar_kws={'label': 'retention'}, ax=ax)
ax.set_title('Cohort × Day-N 留存矩阵')
fig.savefig('charts/T{n}_retention_heatmap.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# 用 D1/D7/D30（取 mat 实际有的列）做 cohort 聚类
candidate_days = [d for d in [1, 3, 7, 14, 30] if d in mat.columns]
features = mat[candidate_days].dropna()
print(f"聚类用的留存点：D{candidate_days}, 有效 cohort 数：{len(features)}")

if len(features) >= 4:
    n_clusters = min(3, len(features) // 2)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(features)
    cluster_label = pd.Series(km.labels_, index=features.index, name='cluster')
    cluster_means = pd.DataFrame(km.cluster_centers_,
                                 columns=[f'D{d}' for d in candidate_days])
    cluster_means['cluster'] = range(n_clusters)
    cluster_means.to_csv('data/T{n}_cluster_centers.csv', index=False)
    print("聚类中心：")
    print(cluster_means.to_string(index=False))

    # cohort 聚类标签
    out = features.copy()
    out['cluster'] = cluster_label.values
    out.to_csv('data/T{n}_cohort_clusters.csv')

    # 聚类曲线对比
    fig, ax = plt.subplots(figsize=(8, 4))
    for c in range(n_clusters):
        ax.plot(candidate_days, km.cluster_centers_[c], '-o', label=f'cluster {c}')
    ax.set_title('cohort cluster 留存曲线对比')
    ax.set_xlabel('day_n'); ax.set_ylabel('retention'); ax.legend()
    fig.savefig('charts/T{n}_cluster_curves.png', dpi=120, bbox_inches='tight')
    plt.close(fig)
else:
    print("cohort 数 < 4，跳过聚类")

# 关键留存点表（D1/D7/D30 横向对比）
key = mat[candidate_days].copy()
key['delta_d7_d30'] = key.get(7, np.nan) - key.get(30, np.nan)   # 衰减幅度
key.to_csv('data/T{n}_retention_keypoints.csv')
print(key.to_string())
```

## 必打 stdout

```
cohort 矩阵 shape
有效 cohort 数 / 聚类用的留存点
聚类中心表
关键留存点（D1/D7/D30）
```

## 反模式

- ❌ 只看一个 cohort（cohort 间对比是核心）
- ❌ heatmap 无 annot → 用户读不出具体值
- ❌ 不报 cohort_size → 小 cohort 的留存波动很大，不能直接拿来对比
- ❌ 聚类强行用 K=3（cohort 少时降到 K=2）

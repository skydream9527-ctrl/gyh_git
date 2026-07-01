# 倾向得分（Propensity Score）：PSM / IPW / 分层

> 当不能做实验、但混淆变量都可观测时，**倾向得分** 是最经典也最常用的因果推断方法。它的核心思想优雅到只需要一句话：**与其在高维特征上找相似的人，不如在一个一维"倾向"分数上找相似的人**。

---

## 一、问题设定

观察数据里，**处理 T 的分配是有偏的**——投了广告的用户和没投的用户在协变量 X 上分布不同。直接对比 E[Y|T=1] − E[Y|T=0] 会把"用户本身差异"和"广告效应"混在一起。

理想情况是：在每个 X 取值下都有 T=1 和 T=0 的样本（详见 Positivity 假设，[../concepts/potential-outcome.md](../concepts/potential-outcome.md)），按 X 分层做对比再加权平均。

但 X 维度一高，分层就失败——找不到完全相同 X 的对照。

**倾向得分** 给出的解：

> 不需要 X 完全一样，只需要 **P(T=1|X)** 一样。

---

## 二、核心定理（Rosenbaum & Rubin, 1983）

### 定义

```
e(X) = P(T = 1 | X)
```

X 取值下个体被分到 T=1 的概率，叫**倾向得分**。

### 关键定理

**条件可忽略性（Ignorability）成立 → 给定倾向得分 e(X) 也成立**：

```
{Y(0), Y(1)} ⊥ T | X    ⟹    {Y(0), Y(1)} ⊥ T | e(X)
```

**这意味着**：你不必在高维 X 上调整，只需在一维 e(X) 上调整。这是降维奇迹。

### 直觉

倾向得分相同的两个人，他们"被处理的概率"一样，所以**他们之间 T 的差异等价于一次小型随机化**。

---

## 三、估倾向得分

最常见的做法：**用任何监督学习模型拟合 P(T=1|X)**。

```python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier

# 简单：逻辑回归
ps_model = LogisticRegression()
ps_model.fit(X, T)
ps = ps_model.predict_proba(X)[:, 1]

# 强：梯度提升 / XGBoost / LightGBM
ps_model = GradientBoostingClassifier()
ps_model.fit(X, T)
ps = ps_model.predict_proba(X)[:, 1]
```

> **业界经验**：模型选择不是最关键的，**特征工程和 balance 检查**更关键。

---

## 四、四种使用方式

### 1. 倾向得分匹配（PSM）

**逻辑**：每个处理组样本，找一个倾向得分最接近的对照组样本配对，比较他们的 Y。

```python
from sklearn.neighbors import NearestNeighbors

ps_treated = ps[T == 1]
ps_control = ps[T == 0]

# 对每个处理样本找最近邻对照
nn = NearestNeighbors(n_neighbors=1).fit(ps_control.reshape(-1, 1))
_, indices = nn.kneighbors(ps_treated.reshape(-1, 1))

# 处理组 vs 配对的对照组
y_treated = Y[T == 1]
y_control_matched = Y[T == 0][indices.flatten()]
ATT = (y_treated - y_control_matched).mean()
```

**变体**：
- **k-NN 匹配**（找 k 个最近邻）
- **Caliper 匹配**（限定最大距离）
- **Mahalanobis 距离匹配**（在 X 上而非 PS 上）

**估的是 ATT**（处理组上的平均效应），不是 ATE。

### 2. IPW（Inverse Probability Weighting，逆概率加权）

**逻辑**：用 1/e(X) 给处理组加权，1/(1−e(X)) 给对照组加权——把样本"反比例"还原成随机分配的样子。

```python
# 处理组每个样本的权重 = 1/e(X)
# 对照组每个样本的权重 = 1/(1-e(X))

w = T / ps + (1 - T) / (1 - ps)

# 加权 ATE
ATE = (T * Y / ps).sum() / (T / ps).sum() - \
      ((1 - T) * Y / (1 - ps)).sum() / ((1 - T) / (1 - ps)).sum()
```

**优势**：能估 ATE / ATT / ATC 各种量；统计学上有渐近正态性。
**劣势**：极端 PS（接近 0 或 1）会导致权重爆炸 → 估计不稳定。

### 3. 分层（Stratification）

把样本按 PS 分成 5-10 个分层，每层内对比 Y，最后加权平均。

```python
import pandas as pd

df['ps_bin'] = pd.qcut(ps, q=5)
strat_effects = df.groupby('ps_bin').apply(
    lambda g: g.loc[g.T==1, 'Y'].mean() - g.loc[g.T==0, 'Y'].mean()
)
ATE = strat_effects.mean()
```

**优势**：简单稳健，对 PS 模型误设容忍。
**劣势**：分层数选择有任意性。

### 4. 协变量调整（Regression on PS）

把 PS 当作回归变量加入模型。**很少单独用**，更多是和上面方法组合（比如双重稳健）。

---

## 五、关键的 Balance 检查（**必做**）

PS 估完 / 匹配完之后，**必须**检查协变量是否平衡：

```python
def std_mean_diff(treated, control):
    """标准化均值差。绝对值 < 0.1 视为平衡。"""
    return (treated.mean() - control.mean()) / \
           ((treated.var() + control.var()) / 2) ** 0.5

for col in X_cols:
    smd_before = std_mean_diff(df.loc[T==1, col], df.loc[T==0, col])
    smd_after = std_mean_diff(matched_df.loc[T==1, col], matched_df.loc[T==0, col])
    print(f"{col}: before={smd_before:.3f}, after={smd_after:.3f}")
```

**判定**：
- |SMD| < 0.10：平衡
- 0.10-0.25：边缘
- > 0.25：不平衡，PS 模型要调整

> **没做 balance 检查的 PSM 报告，结论是不可信的**。这是因果分析最常见的缺失。

---

## 六、Common Support / Overlap 检查

Positivity 假设要求每个 X 区域都有处理组和对照组样本。PS 上看就是：处理组和对照组的 PS 分布要有**重叠区**。

```python
import matplotlib.pyplot as plt
plt.hist(ps[T==1], bins=30, alpha=0.5, label='Treated', density=True)
plt.hist(ps[T==0], bins=30, alpha=0.5, label='Control', density=True)
plt.legend()
plt.xlabel('Propensity Score')
```

**没重叠的区段**：要么剪掉（牺牲外推），要么承认这部分不能估。

```python
# 常见做法：trim 极端 PS
keep = (ps > 0.05) & (ps < 0.95)
df_trimmed = df[keep]
```

---

## 七、双重稳健（Doubly Robust, DR）

PS 模型可能错；结果模型（Y ~ X）也可能错。**DR 把两者结合：只要其中一个对，估计就一致**。

```
DR_estimator = E[ T·Y/e(X) - (T-e(X))/e(X) · m₁(X) ] - ...
```

`m₁(X)` 是结果模型的预测。一个崩了另一个救场——这就是"双重稳健"。

工具：
- `econml.dr.LinearDRLearner` / `DRLearner`
- `causalml.inference.dr`

---

## 八、五个高频踩坑

### 1. 不做 balance 检查
直接报"PSM 后处理组和对照组对比"——SMD 没看，结论根本没意义。

### 2. PS 模型用了"事后变量"
比如把"是否点击广告"放进 X 里——但点击是被 T 影响的，违反"X 在 T 之前确定"的要求。
**红线：X 必须是 T 决定之前已经确定的变量**。

### 3. 外推到 PS 没覆盖的区域
处理组里有 PS=0.99 的人——意味着这种人几乎不可能不被处理，对照组里压根没这种人。在这些 X 上估 Y(0) 是凭空想象。
解法：trim 或在报告中注明。

### 4. 用 ATT 替代 ATE 报告
PSM 默认估 ATT（处理组上的因果效应）。当业务问题是"如果对所有人都干预会怎样"（ATE）时，ATT 给的是错答案。
解法：选对方法或显式地估 ATE。

### 5. 极端权重炸了
IPW 在 PS 接近 0 或 1 时权重爆炸 → 估计方差巨大。
解法：trim、SIPW（Stabilized IPW）、或换 DR。

---

## 九、和其他方法对比

| 方法 | 适用前提 | 收益 | 工程难度 |
|---|---|---|---|
| **PSM** | 混淆都可观测 | ATT 估计直观 | 低 |
| **IPW** | 混淆都可观测 | ATE/ATT/ATC 都能估 | 中 |
| **DR** | 混淆都可观测 + 至少一个模型对 | 鲁棒 | 中 |
| **DML** | 混淆都可观测 + 高维 | ML 友好、收敛性好 | 高 |
| **IV** | 有外生扰动 | 能处理未观测混淆 | 中 |
| **DID / 合成控制** | 有面板数据 | 不需 X 完全可观测 | 中 |

→ 现代实践：**DML 已成新主流**，详见 [dml.md](dml.md)。但 PSM/IPW 依然是基础课，理解它们才能理解 DML。

---

## 十、Checklist

```
□ 1. 协变量都是 T 之前确定的吗？
□ 2. PS 模型用的什么？是否检查了校准（calibration）？
□ 3. 处理组 / 对照组的 PS 分布是否有充分重叠？
□ 4. 极端 PS 是否做了 trim 或 stabilization？
□ 5. balance 检查通过了吗（SMD < 0.10）？
□ 6. 我估的是 ATE / ATT / ATC？业务问题对应哪个？
□ 7. 是否做了至少一种 robust check（换 PS 模型 / 换匹配方式 / 改 trim 阈值）？
□ 8. 是否考虑过未观测混淆做敏感性分析？
```

---

## 十一、扩展阅读

- 本目录：[../concepts/dag-and-d-separation.md](../concepts/dag-and-d-separation.md)、[../concepts/potential-outcome.md](../concepts/potential-outcome.md)
- 同目录：[dml.md](dml.md) — 现代化升级
- Rosenbaum & Rubin (1983) — *The central role of the propensity score in observational studies for causal effects* —**必读原始论文**
- Imbens & Rubin — *Causal Inference for Statistics, Social, and Biomedical Sciences*, Ch.13-15
- Stuart (2010) — *Matching methods for causal inference: A review and a look forward*
- 工具：`causalml`（Uber）、`econml`（Microsoft）、R `MatchIt`

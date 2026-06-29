# CUPED — 用前期数据缩小方差

> **CUPED**（Controlled-experiment Using Pre-Experiment Data, Deng et al. 2013）是工业实验平台几乎都会上的方差缩减神器。它的杠杆是：**不增加样本、不延长时间、不影响无偏性**，就能让样本量需求降 30-70%。

---

## 一、为什么 CUPED 是"免费午餐"

回忆样本量公式（详见 [../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md)）：

```
n  ∝  σ² / δ²
```

要么把 MDE（δ）放大——这是产品决策，不可控。要么把指标方差（σ²）压小——**这就是 CUPED 在做的事**。

CUPED 的核心想法朴素到让人不敢信：

> 用户在实验前就有历史行为。他实验前花得多，实验中也大概率花得多。这部分"可预测的方差"和实验本身没关系，把它从指标里减掉——剩下的方差更小，AB 信号就更显著。

工业实测的方差缩减比例：

| 指标类型 | 方差缩减 | 等价于样本量减少 |
|---|---|---|
| 转化率（点击 / 购买） | 10-30% | ~10-30% |
| 人均时长 | 40-60% | ~40-60% |
| 人均 GMV | 50-70% | ~50-70% |
| 留存类（D1/D7） | 30-50% | ~30-50% |

**结论：人均型 / 频次型指标能砍一半样本量**。这意味着原本要跑 14 天的实验 7 天就能下结论。

---

## 二、CUPED 的数学（不抠也能懂）

### 第 1 步：想清楚"协变量"是什么

协变量 X：**实验前就能观测、且和实验中的指标 Y 相关**的变量。

最常用：**用同一个用户实验前 7 天的同名指标**。
- Y = 实验期间人均 GMV
- X = 实验前 7 天人均 GMV

### 第 2 步：调整公式

```
Y_cuped = Y - θ · (X - E[X])

其中 θ = Cov(Y, X) / Var(X)
```

直觉：
- `θ · (X - E[X])` 是"用 X 能预测出来的那部分 Y 的偏差"
- 把它从 Y 里减掉，剩下的 Y_cuped 是"X 解释不了的部分"——就是真正反映实验变化的部分

### 第 3 步：方差缩减比例

```
Var(Y_cuped) = Var(Y) · (1 − ρ²)

其中 ρ = corr(Y, X)
```

`ρ²` 就是 X 能解释 Y 方差的比例。X 越能预测 Y，方差缩减越多。

### 关键性质：仍然无偏

```
E[Y_cuped] = E[Y] - θ · (E[X] - E[X]) = E[Y]
```

→ CUPED 不改变期望，只压缩方差。**它不会让你发现"假的差异"**，只让你"更早发现真的差异"。

---

## 三、最小可行实现（Python）

```python
import numpy as np
import pandas as pd

def apply_cuped(df, y_col, x_col):
    """
    df: 包含每个用户 y（实验期间指标）和 x（实验前指标）的表
    返回：cuped 调整后的 y 列
    """
    y = df[y_col].values
    x = df[x_col].values
    theta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
    y_cuped = y - theta * (x - x.mean())
    return y_cuped, theta

# 实验数据
y_a, theta_a = apply_cuped(group_a, 'gmv_during', 'gmv_pre')
y_b, theta_b = apply_cuped(group_b, 'gmv_during', 'gmv_pre')

# 用 Welch t-test，但用 cuped 后的 y
from scipy.stats import ttest_ind
t, p = ttest_ind(y_a, y_b, equal_var=False)
```

**关键工程注意**：

- θ 应该用**两组合并的样本**算，避免破坏无偏性。
- 实验前期数据要选**与实验期等长**的窗口（实验跑 14 天，就用前 14 天）。
- 不参与实验的"预期窗口"用户也算 θ 时是允许的——θ 是个总体参数。

---

## 四、协变量怎么选

业界经验：

### 优先级 1：同名指标的实验前观测
- Y = 人均 GMV → X = 实验前 14 天人均 GMV
- 这是最强的协变量，ρ 经常能到 0.6-0.8

### 优先级 2：高相关的关联指标
- Y = 留存（D7）→ X = 历史活跃天数
- Y = 转化率 → X = 历史浏览深度

### 优先级 3：用户特征
- 注册时长、设备、城市等级、过往消费分位
- 通常 ρ 较低（0.2-0.4），但能锦上添花

### 多协变量：CUPED++ / 回归调整
- 把 X 换成多变量回归（用 ML 模型预测 Y）
- 公式变成 `Y_adj = Y - (Ŷ - mean(Ŷ))`
- 这就是 **MLRATE / Augmented CUPED**——前沿做法

---

## 五、五个实施细节（坑）

### 1. 选错预期窗口
- ❌ 用实验**期间**的数据当协变量 → 把信号抹掉，无效
- ✅ 必须是**实验开始前**用户的历史

### 2. 新用户没有历史怎么办
- 要么剔除（损失外推性）
- 要么 X = 0（损失方差缩减）
- 要么用其他特征（如来源渠道）当协变量
- 业界主流：**老用户用 CUPED，新用户用普通方法**，结果分别报

### 3. 实验前数据不可比
- 大促、节日打断了用户行为分布 → 协变量 X 失真
- 解法：避开特殊周期，或者 winsorize（截尾）X

### 4. 协变量 X 中有用户特征但实验改变了它
- 例：实验改变了"是否完成新手任务"，你用它当 X → CUPED 调整后**反而过度抵消信号**
- 红线：**X 必须是实验开始前确定的**，不能受实验影响

### 5. 比例指标的 CUPED
- 比例指标（转化率）方差本身就小，CUPED 收益有限
- 但**ratio 类指标**（人均订单价 = sum(订单)/sum(用户)）配合 Delta Method + CUPED 收益巨大
- 大型平台都自研了这套组合

---

## 六、CUPED 的局限

不是所有场景 CUPED 都香：

| 场景 | CUPED 适用性 |
|---|---|
| 老用户 + 稳定历史指标 | ⭐⭐⭐⭐⭐ |
| 全新用户场景 / 注册流程实验 | ⭐ |
| 短期突发流量（直播、热搜带来的用户） | ⭐⭐ |
| 行为剧烈变化的运营活动期 | ⭐⭐ |
| 高维 ML 模型已经在用的实验 | 用 MLRATE，CUPED 是其特例 |

---

## 七、和其他方差缩减方法对比

```
方差缩减方法谱系：
                                        模型复杂度 →
   分层抽样     CUPED     CUPED++/MLRATE     深度学习预测
   (设计阶段)   (1 个 X)   (多 X / ML)        (神经网络预测 Y)

   收益:        中           中-高              很高
   实现成本:    高(改分流)    低                中-高
   工业普及度:  低            高(几乎人手一个)    高(头部公司)
```

实战推荐路径：
1. **第一年**：所有人均型实验上 CUPED（单变量）→ 立刻享受 30-50% 样本量缩减
2. **第二年**：尝试 CUPED++，用线性多协变量
3. **第三年**：建 ML 预测器，做 MLRATE / DR-style 方差缩减

---

## 八、Checklist

```
□ 1. 我的指标是连续值 / 比率值吗？（CUPED 才显著有效）
□ 2. 协变量是不是实验"前"就能观测的？
□ 3. 协变量和指标的相关系数 ρ 大概是多少？（< 0.2 别用了，< 0.3 收益小）
□ 4. θ 是用两组合并样本算的吗？
□ 5. 新用户怎么处理？（分组报 / 0 填充 / 替代特征）
□ 6. 实验前期是不是有大促/节日，污染了协变量？
□ 7. 报告里写清是 CUPED 后的指标，还是原始指标？（统一口径）
□ 8. 多重协变量是否考虑过 CUPED++？
```

---

## 九、扩展阅读

- 本目录：[../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md) — 样本量公式
- Deng, Xu, Kohavi, Walker — *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data*（CUPED 原始论文，WSDM 2013）— 必读，公式推导清晰
- Microsoft ExP 团队后续论文（CUPED++, MLRATE）
- Kohavi et al., *Trustworthy Online Controlled Experiments*, Ch.22 "Variance Reduction"
- Netflix Tech Blog: *Reducing the noise in our experiments*（CUPED 工程实践）

# 工具变量（Instrumental Variable, IV）

> **工具变量**是观察性研究里"未观测混淆"问题的兜底方法之一。它的杠杆是：找一个**只通过 X 影响 Y** 的外生变量 Z，借助 Z 的"自然随机性"绕过混淆。本文讲清思想、识别假设（IV 三件套）、估计方法（2SLS）、以及业务里几种常见的 IV 来源。

---

## 一、它解决什么

回忆 [PSM/IPW](propensity-score.md)、[DML](dml.md)：当**所有混淆变量都可观测**时，这些方法能给无偏估计。

但现实里**未观测混淆**到处都是：

```
广告投放 X → 购买 Y
  ↑              ↑
   未观测的"用户购买动机" U（你看不到）
```

U 不可观测 → 你算的 X→Y 系数永远混着 U 的偏差。

工具变量法说：**找一个变量 Z，它只通过 X 影响 Y，且不被 U 影响**——那 Z 引发的 X 变化就是"准实验"，能识别因果效应。

---

## 二、IV 的三个核心假设（"IV 三件套"）

```
Z (工具变量) → X (处理) → Y (结果)
                  ↑           ↑
                  └─── U ─────┘  （未观测混淆）

要让 Z 是有效 IV，必须三件套同时成立：
```

### 1. 相关性（Relevance）
**Z 和 X 相关**（Z 有效预测 X 的变化）

```
Cov(Z, X) ≠ 0
```

**可检验**：F 检验、第一阶段回归。**F < 10 是"弱工具" → 估计严重有偏**。

### 2. 外生性 / 排他性（Exclusion / Exogeneity）
**Z 只通过 X 影响 Y，不能直接影响 Y、也不能通过其他路径影响 Y**

```
Z ─→ X ─→ Y     ✓ 唯一路径
Z ─→ Y          ✗ 直接影响  → IV 失效
Z ─→ M ─→ Y     ✗ 其他中介  → IV 失效（除非 M 已被控制）
```

**这是最强假设，且不可直接检验** —— 必须靠领域知识论证。

### 3. 独立性 / 随机性（Independence）
**Z 与未观测混淆 U 独立**（即 Z 是"外生"的）

```
Z ⊥ U
```

通常和外生性一起讨论。来源是"自然实验"或随机现象。

---

## 三、最经典的 IV 例子

### Angrist (1990)：**越战抽签 → 服兵役 → 收入**

```
Z = 抽签号（彩票决定）
X = 是否服役
Y = 几十年后的收入

为什么 Z 是有效 IV：
  ✓ 相关性：抽签号低的人更可能被征召服役
  ✓ 外生性：抽签号是真随机，与个人背景无关
  ✓ 独立性：抽签号本身不影响收入（除非通过服役）
```

这种"自然抽签"是 IV 的"教科书来源"。

### 业务版本

| Z（工具变量） | X（处理） | Y（结果） |
|---|---|---|
| 上线时区 / 实验灰度时点 | 用户是否曝光新功能 | 留存 |
| 渠道分发的"平台偏好"（外部决定） | 是否被推荐到首页 | 阅读时长 |
| 距离最近网点的远近 | 是否使用线下服务 | 满意度 |
| 天气 / 季节 / 体育赛事 | 用户活跃度 | 消费 |
| 价格的"成本冲击"（外部冲击） | 商品定价 | 销量 |

---

## 四、最简单的估计：2SLS（Two-Stage Least Squares）

```
Stage 1：用 Z 预测 X
   X = γ_0 + γ_1 · Z + 控制变量 + e
   得到拟合值 X̂

Stage 2：用 X̂ 代替 X 估 Y
   Y = β_0 + β_1 · X̂ + 控制变量 + ε
   β_1 就是 IV 估计的因果效应
```

**直觉**：第一阶段把 X 里"被 U 污染"的部分洗掉了——X̂ 只保留 Z 引发的"外生变化"。

代码：

```python
from linearmodels.iv import IV2SLS

# 模型：Y ~ 1 + X + 控制 + [endogenous=X, instruments=Z]
model = IV2SLS.from_formula(
    'Y ~ 1 + control1 + control2 + [X ~ Z]',
    data=df
).fit(cov_type='robust')
print(model.summary)
```

---

## 五、弱工具问题（**最重要的现代议题**）

如果 Z 和 X 相关性弱（Cov(Z, X) 很小），即使其他假设都成立，**IV 估计也会严重有偏**——而且经常**比 OLS 还差**！

### 检验：第一阶段 F 值

```
H₀: Z 不影响 X
F 值 = Z 系数的 F 统计量

经验阈值：
  F > 10 ：基本安全（Stock-Yogo 阈值）
  F < 10 ：弱工具，结果不可靠
  F < 5  ：危险，别用
```

```python
# 第一阶段回归
from statsmodels.formula.api import ols
fs = ols('X ~ Z + control1 + control2', data=df).fit()
print(f"F 值: {fs.fvalue:.2f}")
```

### 多个工具
更稳的做法是**多个 Z**——但代价是"过度识别"假设（多个 Z 给的估计应当一致），可以做 J 检验。

---

## 六、IV 真正估的是什么？LATE 而非 ATE

这是 IV 最容易被误解的点。Imbens & Angrist 在 1994 年证明：**2SLS 估的是 LATE（Local Average Treatment Effect）——只对"被工具变量推动的那群人"的平均效应**。

直觉：

```
按对工具变量的反应分四类人：

  Always-Takers  ：无论 Z 怎样都接受 X     → 对 IV 不贡献
  Never-Takers   ：无论 Z 怎样都不接受 X    → 对 IV 不贡献
  Compliers      ：Z=1 时接受 X，Z=0 时不接受  → IV 估的是这群人的效应
  Defiers        ：反着来                    → 通常假设没有

LATE = E[Y(1) - Y(0) | Compliers]
```

含义：

- 对越战抽签 IV：Compliers 是"被抽到才会服役的人"。LATE 不是"全国平均服役效应"，是这部分人的效应。
- 对不同 Z 的 IV：Compliers 群不同 → LATE 不同 → **不同 IV 估出来差异大不一定矛盾**

> 报告 IV 时**永远不要**把 IV 估计直接当 ATE 用。要明示 "这是被 Z 推动的子群体的平均效应"。

---

## 七、四种业务里最常用的 IV 来源

### 1. 自然实验

政策、规则、外生变更带来的"突然分组"：

- 某产品在 iOS / Android 不同时间上线
- 某监管在某些省份先实施
- 某价格因外部成本冲击调整

这是工业 IV 的主流来源——叫 "**自然实验 IV**"，强项是外生性容易论证。

### 2. 距离 / 地理

- 用户距离最近门店多远
- 从家到工作地点远近
- 与最近基站 / 物流点距离

地理变量经常和 X 相关但不直接影响 Y——经典 IV 来源。

### 3. 同伴 / 邻里

- 朋友的购买决策
- 同地区其他人的行为

⚠️ 风险大——同伴的行为可能直接通过"社交影响"影响 Y。

### 4. 测量误差导致的"工具变量"

- Y 有测量误差但 X 没有 → 普通 OLS 偏
- 用同一变量的另一种测量方法当 IV
- 经济学 / 心理学常见

---

## 八、IV 的典型陷阱

### 1. 排他性破坏（最致命）

```
Z (广告投放) → X (注册) → Y (购买)
   ↓
   也直接影响 Y（用户看到广告就会被引流到首页）
```

如果 Z 还有 X 之外的路径影响 Y，IV 失效。

**检测**：通过**领域知识**论证（无法纯统计检验）。常用辅助：placebo、找另一组 Y'（不应该被 Z 影响）。

### 2. 弱工具 → 错的比 OLS 还多

F < 10 时 IV 估计的偏差和方差都失控。**报告时必须给 F 值**。

### 3. 把 IV 估计当 ATE

实际是 LATE。报告应该说 "Compliers 的 ATT"。

### 4. 多个 IV 不一致而硬拼

如果不同 IV 给出显著不同的 LATE，说明 LATE 的"Complier 群体"不同——这是信息，不是矛盾。**不要简单平均**。

### 5. 把"显著相关"当"有效 IV"

Z 和 X 相关只是必要条件不是充分条件——外生性是更难的部分。

---

## 九、IV vs 其他方法的对比

| 方法 | 处理"未观测混淆" | 关键假设 | 适用条件 |
|---|---|---|---|
| AB 测试 | ✅ 完全 | 随机化 | 能做实验 |
| PSM / DML | ❌ 不行 | Ignorability | 混淆都可观测 |
| **IV** | ✅ 部分 | IV 三件套 | 找得到工具变量 |
| RDD（断点回归） | ✅ 部分 | 阈值附近连续性 | 处理由阈值决定 |
| DID | ✅ 部分 | 平行趋势 | 有面板 + 双组 |
| 合成控制 | ✅ 部分 | 凸组合可重构 | 单一处理 unit |

→ 选哪个看你的问题结构，详见 [../OVERVIEW.md](../OVERVIEW.md) 的决策树。

---

## 十、断点回归（RDD）：IV 的"近亲"

简单提一下 RDD（Regression Discontinuity Design）——它是 IV 的特殊形式：

```
处理由"是否超过某个阈值 c"决定：
  X = 1{score > c}
  
RDD 的核心：阈值附近的人除"被处理状态"外几乎没差异
  → 阈值左右的差距就是因果效应
```

经典应用：
- 高考分数线 → 是否上大学 → 收入
- 信用分阈值 → 是否给贷款 → 还款率
- 用户消费金额阈值 → 是否享 VIP → 留存

工具：R `rdrobust`、`rdd`；Python `rdd`。

> RDD 比 IV 假设更弱、更可信——**只要阈值附近"局部连续"** 即可。是另一种工业利器。

---

## 十一、Python 完整示例

```python
import pandas as pd
from linearmodels.iv import IV2SLS
from statsmodels.formula.api import ols

# 数据：广告投放 X 影响购买 Y，但 X 受未观测的"购买意向" 污染
# 工具变量 Z：随机灰度上线时间

# Step 1：检查 IV 相关性（第一阶段）
fs = ols('X ~ Z + age + income', data=df).fit()
print(f"第一阶段 F 值: {fs.fvalue:.2f}")  # > 10 通过

# Step 2：2SLS
mod = IV2SLS.from_formula(
    'Y ~ 1 + age + income + [X ~ Z]', data=df
).fit(cov_type='robust')
print(mod.summary)

# Step 3：和 OLS 对比看差距（看混淆的"严重程度"）
ols_mod = ols('Y ~ X + age + income', data=df).fit()
print(f"OLS β = {ols_mod.params['X']:.3f}")
print(f"IV  β = {mod.params['X']:.3f}")

# Step 4：报告
# - F 值（弱工具检验）
# - LATE 解读（不是 ATE）
# - 排他性论证（领域知识）
# - sensitivity（如果可能，多个 IV 比较）
```

---

## 十二、Checklist

```
□ 1. 我的 Z 满足相关性？（F > 10？）
□ 2. 我能用领域知识论证排他性吗？
□ 3. 我相信 Z ⊥ U 吗？
□ 4. 我估的是 LATE，不是 ATE——报告里说清了？
□ 5. 弱工具检验做了吗？
□ 6. 多个 IV 时，过度识别 J 检验做了吗？
□ 7. 和 OLS 系数对比看差距（差距大表明混淆严重，IV 价值高）？
□ 8. Sensitivity / placebo 做了吗（用一个"不应受 Z 影响的 Y'" 做安慰剂）？
```

---

## 十三、扩展阅读

- 本目录：[did.md](did.md)、[synthetic-control.md](synthetic-control.md)、[propensity-score.md](propensity-score.md)、[dml.md](dml.md)
- 相关：[../concepts/dag-and-d-separation.md](../concepts/dag-and-d-separation.md)
- Imbens & Angrist (1994) — *Identification and Estimation of Local Average Treatment Effects*（**LATE 论文**）
- Angrist (1990) — *Lifetime Earnings and the Vietnam Era Draft Lottery*（最经典 IV 应用）
- Stock & Yogo (2005) — *Testing for Weak Instruments in Linear IV Regression*（弱工具阈值）
- Mostly Harmless Econometrics（Angrist & Pischke）— Ch.4
- Cunningham — *Causal Inference: The Mixtape*, Ch.7
- Hernán & Robins — *Causal Inference: What If*, Ch.16
- 工具：Python `linearmodels`、Stata `ivregress`、R `ivreg` / `AER`

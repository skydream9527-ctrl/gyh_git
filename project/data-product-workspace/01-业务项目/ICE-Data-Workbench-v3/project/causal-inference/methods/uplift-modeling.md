# Uplift Modeling（增益建模）

> 本文目标：把"哪些用户值得干预"这个产品 / 营销 / 广告里最贵的问题，用因果推断的语言精确说清楚，并给出工业可落地的方法体系。Uplift Modeling 是因果推断**最赚钱**的应用方向——直接对应营销预算、Push 资源、广告投放策略。

---

## 一、它解决的产品问题

业务里最常见的浪费：

- 给所有人发券：高购买意愿用户**白拿**了券（gift waste）；负面反应用户被惹烦（churn）
- 给所有人推 Push：低活跃用户被打扰、卸载了 App
- 给所有人投广告：本来要买的用户被白白获客（incremental ROI 为 0）

**Uplift Modeling 的核心问题**：

> 预测每个用户的"被干预后的因果增量"——CATE（Conditional Average Treatment Effect）。然后把资源只花在 CATE 高的人身上。

它和"预测谁会买"（响应模型）的本质区别：

```
响应模型（response）：     P(buy | T=1)         = 谁会买
增益模型（uplift）：       P(buy | T=1) - P(buy | T=0) = 谁因为干预才买
```

响应模型把"自然成单"和"因为干预成单"混在一起，**用响应模型选客 = 把券发给本来就要买的人**。这是营销里最大的预算浪费。

---

## 二、四种用户：你的钱该往哪花

```
                    干预后会买？
                  是           否
                ┌────────────┬────────────┐
干预前         │            │            │
会买？  是    │  Sure Thing │ Lost Cause │
              │  自然成单    │  无效用户   │
              │  (浪费成本)  │ (浪费成本)  │
              ├────────────┼────────────┤
        否    │ Persuadable │ Sleeping   │
              │  增益用户    │  Dog       │
              │  (主战场)    │  反感型    │
              │             │  (避免干预) │
              └────────────┴────────────┘
```

| 类型 | CATE | 干预策略 |
|---|---|---|
| **Persuadable**（增益用户） | > 0 | ✅ **重点投入** |
| **Sure Thing**（自然成单） | ≈ 0 | ❌ 不要花钱（白送） |
| **Lost Cause**（无效） | ≈ 0 | ❌ 不要花钱 |
| **Sleeping Dog**（反感型） | < 0 | ❌ 干预**反而**害业务 |

> **Sleeping Dog 是最容易被忽略的一类**。例：给低活跃用户发 Push 通知，他们的反应不是回流，而是直接卸载。Uplift 模型能识别这群人。

业务收益翻倍的来源就这一句：**把预算从 Sure Thing 移到 Persuadable，绕开 Sleeping Dog**。

---

## 三、和因果推断框架的对应

CATE = E[Y(1) − Y(0) | X = x]

Uplift Modeling 就是对 CATE 建模 + 用 CATE 做决策。

### 数据来源

理论上需要"反事实"，工业上有两种来源：

1. **AB 实验数据**（黄金）：随机分流 → CATE 识别天然成立
2. **观察数据 + 因果推断**（次优）：需要 Ignorability 等假设

> 90% 工业 Uplift 落地都基于实验数据。**先做一次随机投放实验，再用实验数据训 uplift 模型用于后续投放**——这是头部公司的标准做法。

---

## 四、五种主流建模方法

### 1. Two-Model Approach（T-Learner / Two-Tower）

最朴素：**实验组和对照组各训一个模型**，预测时取差。

```python
from sklearn.ensemble import GradientBoostingRegressor

m1 = GradientBoostingRegressor().fit(X[T==1], Y[T==1])
m0 = GradientBoostingRegressor().fit(X[T==0], Y[T==0])

cate_hat = m1.predict(X) - m0.predict(X)
```

| 优势 | 劣势 |
|---|---|
| 实现极简 | 两个模型独立训，差分时**误差累积** |
| 任何 ML 都能用 | 处理组小时严重退化 |

### 2. S-Learner（Single Model）

把 T 当作一个特征，训单个模型。

```python
X_with_T = np.hstack([X, T.reshape(-1, 1)])
m = GradientBoostingRegressor().fit(X_with_T, Y)

# CATE = 预测(T=1) - 预测(T=0)
cate_hat = m.predict(np.hstack([X, np.ones((len(X), 1))])) - \
           m.predict(np.hstack([X, np.zeros((len(X), 1))]))
```

| 优势 | 劣势 |
|---|---|
| 数据利用率高 | T 是单一特征，模型可能"忽视"它（regularization bias） |
| 简单 | 异质效应弱时表现差 |

### 3. X-Learner（Künzel et al., 2019）

针对**两组样本量不平衡**优化（实验组通常远小于对照组）。

```
1. 对每组各训 m₁, m₀
2. 估"反事实"：
     对处理组 i: D̂_i^1 = Y_i - m₀(X_i)
     对对照组 i: D̂_i^0 = m₁(X_i) - Y_i
3. 用 D̂ 训两个 CATE 模型，再加权平均
```

工业里 X-Learner 是**性能稳定的默认选择**之一。

### 4. R-Learner（Nie & Wager, 2017）

用 Robinson 的残差变换 + ML：和 [DML](dml.md) 思想完全一致。

```
Step 1: 估两个 nuisance: m̂(X)=E[T|X], μ̂(X)=E[Y|X]
Step 2: 残差化 T_r = T-m̂(X), Y_r = Y-μ̂(X)
Step 3: 加权回归: CATE 模型最小化 Σ (Y_r - τ(X)·T_r)²
```

理论性质最好，配合 EconML / `causalml` 几行代码：

```python
from econml.dml import CausalForestDML
est = CausalForestDML().fit(Y, T, X=X)
cate = est.effect(X)
```

### 5. Causal Forest（Athey & Wager, 2019）

随机森林的因果版。每个 split 不是为了**预测 Y**，而是为了**最大化 CATE 的异质性**。

- 优点：天然估异质效应；置信区间良好
- 工具：`econml.dml.CausalForestDML`、`grf` (R)

---

## 五、用什么指标评估（**关键**）

Uplift 模型不能用 AUC、accuracy 评——它们衡量"预测 Y"的能力，不衡量"预测 CATE"的能力。

### Qini 曲线 / Uplift 曲线

按预测的 CATE 分高低排序，从高到低投入预算，看累积增益曲线。

```
       累积增益
       ↑
  完美 │     ╱──────
       │   ╱
       │ ╱  随机
       │/
       └────────────→ 投入比例
```

```python
from causalml.metrics import plot_qini, qini_score
qini_score(df, outcome_col='Y', treatment_col='T', score_col='cate_hat')
```

### Uplift @ K%
"投预算给 CATE 排名前 K% 的用户，能拿到多少总增益？"——这是业务最关心的数。

### AUUC（Area Under Uplift Curve）
Qini 曲线下面积，单数字概括模型质量。

> **不会算 Qini 的 Uplift 报告就是耍流氓**。这是检验 uplift 项目的第一道防线。

---

## 六、典型业务落地：Push 增益

```
Day 0：随机分组
        50% 用户：发 Push（处理）
        50% 用户：不发 Push（对照）

Day 7：观测
        Y = 7 日内是否回归

Step 1：在实验数据上训 uplift 模型（X-Learner / R-Learner / CF）
Step 2：上线后，对未来用户预测 CATE
Step 3：策略：
        - CATE > 阈值 c₁ → 发 Push
        - 阈值 c₀ < CATE ≤ c₁ → 不发（自然回流）
        - CATE < c₀ → 不发（Sleeping Dog）
Step 4：周期性回收数据 → 持续 retrain

预期 ROI 提升：30-100%（行业经验）
```

---

## 七、五个高频踩坑

### 1. 用响应模型替代 uplift 模型
最常见。"我们的算法预测谁会回流，给他们发 Push"——本质是预测 P(Y|X)，不是 CATE。结果就是把 Sure Thing 当 Persuadable 给。

### 2. 实验数据样本量小到训不动 uplift
经验：**至少需要每组 1 万 + 200 转化**（粗略下限）。少于此用简单 T-Learner，别上 R-Learner。

### 3. 没有定期重训
用户行为漂移、产品迭代 → 一个月前的 uplift 模型可能反向。**每月-每季 retrain 一次**。

### 4. 没在线上做 holdout
线上必须留 5-10% 流量做随机对照，持续验证 uplift 模型的真实增益。
不留 holdout = 无法观测衰减。

### 5. 把 uplift 模型用在新场景
A 产品训出来的 uplift 模型用到 B 产品 → 完全不可移植。每个场景都要单独建。

---

## 八、和 AB 测试的关系

Uplift 不取代 AB——而是**让 AB 的数据"死"了之后还能继续生钱**。

```
传统 AB 流程：
  实验 → 看 ATE → 上线 / 下线 → 数据用完了
  
Uplift 升级流程：
  实验 → 看 ATE → 训 uplift 模型 → 个性化策略 → 持续优化
                        ↑ 实验数据二次开发
```

→ 详见 [../../ab-testing/OVERVIEW.md](../../ab-testing/OVERVIEW.md)

---

## 九、工具

| 工具 | 长处 |
|---|---|
| **CausalML**（Uber） | 国内最普及，T/S/X/R-Learner 都支持，Qini 评估完整 |
| **EconML**（Microsoft） | DML / Causal Forest 强，理论严谨 |
| **scikit-uplift** | 教学最友好 |
| **grf**（R） | 学术界常用，Causal Forest 原版 |
| **uplift**（R） | 经典 R 包 |

---

## 十、Checklist

```
□ 1. 数据来源是 AB 实验还是观察？后者要列因果识别假设
□ 2. 处理组样本量是否够（每组 ≥ 1 万）？
□ 3. 用了哪种学习器（T/S/X/R/CF）？为什么？
□ 4. 评估指标是 AUUC / Qini，不是 AUC？
□ 5. 留了 5-10% 的随机 holdout 在线上吗？
□ 6. 模型多久 retrain 一次？
□ 7. 预测的 CATE 分布是否合理（不是全部 0 或全部高）？
□ 8. 是否识别了 Sleeping Dog 群？这部分会被排除吗？
```

---

## 十一、扩展阅读

- 本目录：[propensity-score.md](propensity-score.md)、[dml.md](dml.md)
- Künzel, Sekhon, Bickel, Yu (2019) — *Metalearners for estimating heterogeneous treatment effects using machine learning*（X-Learner 论文）
- Nie & Wager (2017) — *Quasi-Oracle Estimation of Heterogeneous Treatment Effects*（R-Learner）
- Athey & Wager (2019) — *Estimating Treatment Effects with Causal Forests*
- Radcliffe & Surry (2011) — *Real-World Uplift Modelling with Significance-Based Uplift Trees*
- Diemert, Betlei et al. (2018) — *A Large Scale Benchmark for Uplift Modeling*（公开数据集）
- 工业博客：Uber CausalML 系列、Criteo 营销 uplift 案例

# 合成控制（Synthetic Control, SCM）

> **合成控制法**（Abadie & Gardeazabal, 2003）解决的是 DID 解决不了的难题：**只有一个处理 unit 时（一个城市、一个国家、一个市场），怎么估反事实？** 它通过给多个对照 unit 加权"合成"出一个最接近处理 unit 的"虚拟孪生"。是政策评估、单一市场 / 城市级干预、运营活动评估的金标准方法。

---

## 一、它解决的问题

DID（[did.md](did.md)）需要"处理组 + 对照组都是多个 unit"。但很多业务场景只有一个 unit：

- 上海上线了某政策，全国其他城市没上 → 只有一个上海作为处理 unit
- 某直播 KOL 改了直播策略 → 只有一个直播间是处理
- 某市场上线了某产品 → 只有一个市场被处理

朴素方法的问题：

```
方法 1：单一对照（如选北京当对照）
  问题：北京的"自然漂移"未必能代表"如果上海没干预的漂移"

方法 2：多个对照取均值
  问题：每个对照的特征不同，简单平均没考虑差异
```

**合成控制的解法**：用**多个对照 unit 的加权组合**"合成"出一个尽可能像处理 unit 的"反事实 unit"——权重通过让"合成 unit 的干预前轨迹"与"处理 unit 的干预前轨迹"最接近来确定。

---

## 二、直觉：用对照 unit "拼"出处理 unit 的孪生

```
干预前：
   上海实际    : ──────────────╲╲╲╲╲╲╲
                                  
   合成上海    : 0.4 × 北京 + 0.3 × 广州 + 0.2 × 苏州 + 0.1 × 成都
                = ──────────────╲╲╲╲╲╲╲      ← 几乎重合 ✓

干预时点：     ........|

干预后：
   上海实际    : ──────────╲╲    ← 这是真的发生
   合成上海    : ──────────╲╲╲╲   ← 反事实

   ATT = 上海实际 - 合成上海   （干预后差距）
```

权重 (0.4, 0.3, 0.2, 0.1) 是**学出来**的——用干预前数据让"合成线"贴近"实际线"。

---

## 三、形式化

设 J+1 个 unit：1 个处理（unit 1）+ J 个对照（units 2…J+1）。

### 第 1 步：定权重 w = (w_2, ..., w_{J+1})

```
约束：
   w_j ≥ 0
   Σ w_j = 1                    ← 凸组合权重

目标：minimize  ‖X_1 - Σ w_j · X_j‖_V

X_1：处理 unit 干预前特征 + Y 的轨迹
X_j：对照 unit j 的同上
V：协变量重要性权重矩阵（也可以学）
```

通过这个优化得到权重 w*。

### 第 2 步：用 w* 算反事实

```
Ŷ_1,t (反事实) = Σ w*_j · Y_j,t        对所有 t

ATT_t = Y_1,t (实际) - Ŷ_1,t (反事实)   干预后每一期的效应
```

### 关键约束

- **w_j ≥ 0 + Σ w_j = 1**：保证合成 unit 是对照 unit 的**凸组合**——不外推到对照 unit 之外的特征空间，避免"合成 unit 是虚构的"。

---

## 四、最小工作示例（Python）

```python
import numpy as np
from scipy.optimize import minimize

# 数据：units × time，每行一个 unit
# 假设第 0 行是处理 unit，其他是对照
def synth_control(Y, treatment_period, treated_idx=0):
    n_units, T = Y.shape
    Y_treat = Y[treated_idx, :treatment_period]
    Y_donors_pre = np.delete(Y, treated_idx, axis=0)[:, :treatment_period]
    
    n_donors = n_units - 1
    
    def loss(w):
        synth = w @ Y_donors_pre
        return ((Y_treat - synth) ** 2).sum()
    
    # 约束：w >= 0, Σw = 1
    constraints = [
        {'type': 'eq', 'fun': lambda w: w.sum() - 1},
    ]
    bounds = [(0, 1)] * n_donors
    
    w0 = np.ones(n_donors) / n_donors
    result = minimize(loss, w0, method='SLSQP',
                      constraints=constraints, bounds=bounds)
    
    w_star = result.x
    Y_donors = np.delete(Y, treated_idx, axis=0)
    Y_synth = w_star @ Y_donors
    return w_star, Y_synth

# 示例
Y = np.random.randn(10, 30) * 0.5  # 10 个 unit × 30 期
Y[0, 20:] += 5  # 第 0 个 unit 在第 20 期后被干预，效应 +5

w, Y_synth = synth_control(Y, treatment_period=20)
ATT = Y[0] - Y_synth
print(f"权重: {w}")
print(f"干预后 ATT: {ATT[20:].mean():.2f}")
```

---

## 五、推断（Inference）：placebo 检验

合成控制最大的"工程麻烦"是**没有标准统计推断**——只有一个处理 unit，传统的 standard error 没法直接算。

### Placebo 检验（标准做法）

依次假装**每个对照 unit** 都是"假处理 unit"，跑合成控制：

```python
all_atts = []
for placebo_idx in range(n_units):
    w, Y_synth = synth_control(Y, treatment_period, treated_idx=placebo_idx)
    placebo_att = Y[placebo_idx] - Y_synth
    all_atts.append(placebo_att)

# 看真实处理 unit 的效应是否在所有 placebo 效应之外
real_att = all_atts[0]  # 假设处理 unit 是 0
others = all_atts[1:]
```

直觉：如果真实 ATT 比 99% 的"虚假 ATT"都大，那它就是"显著"的。

```
"p 值" = (大于真实 ATT 的 placebo 数) / (placebo 总数)
```

### Robustness 检查

- **Leave-one-out**：每次去掉一个对照 unit 重做合成控制，看结果是否稳定
- **干预前 fit 优劣**：如果干预前的 RMSPE（合成线和实际线的 MSE）已经很大，结果不可信
- **Pre/Post RMSPE 比**：常用统计量。比值越大，证据越强

---

## 六、业务里的经典应用

### 1. 政策评估

Abadie 等用 SCM 评估了：
- 加州控烟政策（1988）
- 巴斯克恐怖主义对经济的影响
- 德国统一对前西德经济的影响

每一个都是"单一干预 unit + 多对照"的标准场景。

### 2. 城市级运营 / 灰度

```
某城市先上线"X 服务"
用其他没上线的城市合成 → 估这座城市的 ATT
```

特别适合：
- 滴滴 / Uber 在某城市先上线某规则
- 美团 / 饿了么的城市级补贴策略
- 字节 / 快手的内容策略城市灰度

### 3. 直播 / KOL / 品牌效应

- 单个直播间改了打法 → 拿同类直播间合成对照
- 一个品牌做了营销大事件 → 拿同类品牌合成对照

### 4. 宏观 / 行业冲击

- 某竞品上线后，自家某业务 GMV 跌了多少？→ 用其他业务（被竞品冲击程度不同）合成对照

---

## 七、合成控制 vs DID

| 维度 | DID | 合成控制 |
|---|---|---|
| 处理 unit 数量 | 多个 | 1 个或少数 |
| 对照 unit 数量 | 多个 | 多个 |
| 关键假设 | 平行趋势 | 干预前轨迹可被加权重构 |
| 输出 | 单一 ATT 系数 | 每期 ATT 曲线 |
| 推断 | 传统 t / cluster SE | placebo 检验 |
| 数据要求 | 较低 | 干预前需要较多期 |

实操经验：**两者都跑作为 robustness check 是顶刊标配**。结论一致 → 信心更强；不一致 → 找原因。

---

## 八、几个进阶变体

### 1. Augmented Synthetic Control（Ben-Michael et al., 2021）
- 朴素 SCM 要求 w_j ≥ 0 + Σ w_j = 1
- 这要求处理 unit 必须在对照 unit "凸包" 内
- ASCM 引入回归调整，处理"凸包之外"的处理 unit
- 工具：R `augsynth`

### 2. Generalized Synthetic Control（Xu, 2017）
- 允许多个处理 unit
- 用因子模型拟合反事实
- 工具：R `gsynth`

### 3. Synthetic Difference-in-Differences（Arkhangelsky et al., 2021）
- 把 SCM 思想（unit 加权）和 DID 思想（time + unit 双控）结合
- 在很多场景上比纯 SCM 或纯 DID 都强
- 工具：R `synthdid`

### 4. Matrix Completion（Athey et al., 2021）
- 把因果反事实问题看成"矩阵填空"
- 用 ML 方法（核范数最小化）估缺失的反事实
- 适合 unit × time 数据稀疏的场景

---

## 九、关键的"小字"

### 1. 干预前数据要够长
- 通常需要 10+ 期才能稳定估权重
- 太短会过拟合 → 干预后立刻"反弹"（虚假效应）

### 2. "凸组合"假设的局限
- 处理 unit 是个极端值（人均消费最高的城市），凸组合估不出
- 解法：augmented synth control 或重新选对照

### 3. Sparse 解
- SCM 经常给"权重集中在 2-3 个 unit 上"的解
- 这是优点（可解释）也是风险（这 2-3 个 unit 后期变化会主导反事实）

### 4. 单一干预时点
- 经典 SCM 假设干预时点已知且单一
- 如果有多个时点，用 SDID 或 staggered SCM

### 5. 异质效应没法分解
- ATT 是处理 unit 上的整体效应
- 不能告诉你"哪些子群受影响最大"——这需要 [Uplift Modeling](uplift-modeling.md)

---

## 十、报告 SCM 必含的图

```
1. 主图：处理 unit 实际 vs 合成 unit 轨迹（干预前后）
2. 干预效应图：每期 ATT_t = Y_1,t - Ŷ_1,t
3. Placebo 比较图：所有 unit 的 ATT 轨迹叠加（真实 unit 应"鹤立鸡群"）
4. RMSPE 比图：真实 unit 和所有 placebo 的 pre / post RMSPE 比直方图
5. 权重表：哪些对照 unit 占主要权重，权重是多少
```

> 任何只给一个数字 "ATT = 5.3%" 的 SCM 报告都不够看——这是评估方法的最大特点：**故事比数字重要**。

---

## 十一、踩坑速查

### 1. 干预前 fit 不好
RMSPE_pre / RMSPE_post < 1 时：合成 unit 都没拟合好干预前 → 干预后的"差距"不是真效应。
→ 重新选对照 / 加 covariates。

### 2. 用了"被干预冲击"的对照 unit
"上海上线 → 苏州也间接受影响" → 苏州不能当对照。
→ 严格剔除溢出 unit。

### 3. 干预效应衰减时直接平均
- 后期效应可能反弹（用户适应、监管反应）
- 报告 ATT 时分早期 / 中期 / 长期，不要硬平均

### 4. 没做 placebo
没有 placebo 检验的 SCM 报告 = 没有推断的描述。**必须跑 placebo**。

### 5. 用 ATT 推 ATE
SCM 估的是 ATT（处理 unit 上的因果效应）——**不能外推到"如果其他城市也干预"**。这是 SCM 的本质局限。

---

## 十二、Checklist

```
□ 1. 干预 unit 是 1 个或少数？（多就用 DID 或 SDID）
□ 2. 干预前至少 10 期数据？
□ 3. 对照池里没有"被处理影响"的 unit？
□ 4. 权重学出来不是极端的（一两个 unit 占 95%）？
□ 5. 干预前 RMSPE 足够小（与其他 unit 同量级）？
□ 6. Placebo 检验跑了？真实 ATT 排在前几名？
□ 7. Leave-one-out robustness 做了？
□ 8. 报告含权重表 + 主图 + placebo + ATT 曲线？
```

---

## 十三、扩展阅读

- 本目录：[did.md](did.md)、[propensity-score.md](propensity-score.md)
- Abadie & Gardeazabal (2003) — *The Economic Costs of Conflict*（SCM 原始论文）
- Abadie, Diamond, Hainmueller (2010) — *Synthetic Control Methods for Comparative Case Studies*（加州控烟应用）
- Abadie (2021) — *Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects*（**最权威综述**）
- Ben-Michael et al. (2021) — *The Augmented Synthetic Control Method*
- Arkhangelsky et al. (2021) — *Synthetic Difference-in-Differences*
- Doudchenko & Imbens (2016) — *Balancing, Regression, Difference-In-Differences and Synthetic Control Methods: A Synthesis*
- 工具：R `Synth`、`augsynth`、`gsynth`、`synthdid`；Python `pysyncon`、`SparseSC`

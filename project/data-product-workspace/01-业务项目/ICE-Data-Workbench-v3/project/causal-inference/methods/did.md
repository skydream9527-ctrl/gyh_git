# 双重差分（Difference-in-Differences, DID）

> 当你有"处理组 + 对照组"且能观测到**处理前后两期数据**时，DID 是最简单优雅、也最常被工业界滥用的因果推断方法。本文讲清核心机制、平行趋势假设的检验、以及现代修正（事件研究、Callaway-Sant'Anna）。

---

## 一、DID 的两图直觉

### 朴素直觉

```
处理组：    干预前 ──► 干预后 (跳了 +Δ_treat)
对照组：    干预前 ──► 干预后 (自然漂移 +Δ_ctrl)

DID 估计：   ATT ≈ Δ_treat − Δ_ctrl

          直观：减掉自然漂移之后，剩下的就是干预带来的"额外"变化
```

### 视觉化

```
Y
│              ╱──── 处理组（实际）
│           ╱
│   ╱──────╱─────── 处理组（反事实，平行趋势假设下）
│  ╱      ╱
│ ╱  ╱───╱──────── 对照组
│╱  ╱
└──────|──────────► t
      干预时点

DID 估的就是"处理组实际线 − 处理组反事实线"在干预后的距离
```

**关键假设：处理组反事实线**是用对照组的"漂移"推出来的。

---

## 二、最小公式

### 2×2 DID（两期、两组）

```
Y̅_treat,post  − Y̅_treat,pre   ──┐
                                  ├──── ATT_DID = (差) − (差)
Y̅_ctrl,post   − Y̅_ctrl,pre    ──┘

ATT_DID = (Y̅_T,post − Y̅_T,pre) − (Y̅_C,post − Y̅_C,pre)
```

### 等价的回归形式

```
Y_it = α + β·Treat_i + γ·Post_t + δ·(Treat_i × Post_t) + ε_it

δ̂ 就是 DID 估计量
```

代码：

```python
import statsmodels.formula.api as smf

# df 包含 unit_id, time, Y, treat (0/1)
df['post'] = (df['time'] >= treatment_time).astype(int)

model = smf.ols('Y ~ treat + post + treat:post', data=df).fit(
    cov_type='cluster', cov_kwds={'groups': df['unit_id']}
)
print(model.summary())  # treat:post 系数就是 ATT
```

> ⚠️ **必须 cluster 标准误**到 unit 级——同一个 unit 的多期观测高度相关，OLS 默认标准误会严重低估。

---

## 3、关键假设：平行趋势（Parallel Trends）

DID 的全部正确性建立在一句话上：

> **如果没有干预，处理组和对照组的 Y 应当沿着平行的趋势走。**

形式化：

```
E[Y(0)_T,post − Y(0)_T,pre]  =  E[Y(0)_C,post − Y(0)_C,pre]
```

这是一个**关于反事实的强假设**——你永远无法直接验证（因为反事实不可观测）。能做的：

### 1. 看历史趋势

把干预**前**多期数据画图，看处理组和对照组是不是平行：

```
干预前  处理组 ──╲╲╲╲╲╲╲
        对照组 ──╲╲╲╲╲╲╲    ← 两条线斜率几乎一致 ✓
干预    .........|
干预后  处理组 ──╲╲    
        对照组 ──╲╲╲   ← DID 才合理
```

如果干预前**已经不平行**，DID 直接失效——你估的"干预效应"可能是趋势差。

### 2. 安慰剂检验（Placebo Test）

假装在没有真实干预的"假干预日"做 DID。如果估出"显著效应"，说明趋势本就不平行。

```python
# 真实干预日是 2024-06-01
# 假装干预日是 2023-06-01（早一年），跑 DID
# 如果 placebo δ̂ 显著 ≠ 0 → 平行趋势可疑
```

### 3. 事件研究（Event Study）

把**每一期**对处理组单独估系数，看能否平行 + 干预后突变：

```
Y_it = α + Σ_k β_k · 1{t = treat_time + k} · Treat_i + 控制变量 + ε

把 β_k 画出来：
  - k < 0（干预前）：应接近 0（平行）
  - k = 0（干预当期）：可能跳
  - k > 0（干预后）：处理效应曲线
```

**这是工业 DID 报告的标配**——只给单一系数 δ̂ 不够，要给完整 event study 图。

---

## 四、业务里的 DID 例子

### 例 1：城市级政策评估

```
2024-01 上海上线"政策 X"，北京没上线
对每个用户的"日均消费"做 DID

Y_it = 上海/北京用户 i 在月份 t 的消费
treat_i = 1{i ∈ 上海}
post_t = 1{t ≥ 2024-01}

ATT = 上海消费的提升 − 北京消费的提升
```

注意：单个对照城市风险大（北京可能本身有特殊冲击）→ 用多对照城市加权（接近合成控制思路，详见 [synthetic-control.md](synthetic-control.md)）。

### 例 2：产品功能灰度

```
某新功能在 iOS 14+ 用户中先灰度，其他设备没灰度
看 30 日留存：

iOS 14+ vs iOS 13- ：
  灰度前：留存 (60%, 58%)，相差 2pp
  灰度后：留存 (65%, 59%)，相差 6pp

ATT = (65% − 60%) − (59% − 58%) = 4pp
```

⚠️ **风险**：iOS 14+ 用户本身就更新潮活跃，趋势可能不平行。事件研究检验 + 安慰剂必须做。

### 例 3：A/B 实验失败的兜底

如果你**本来想做 AB**，但分流系统上线滞后，结果只有"一部分用户分到处理组"——你可以把已分组的用户和"如果当时分到对照"的可比群体做 DID 兜底。

⚠️ 这种"事后凑出来的 DID"常常是 confused 的——只在你能讲清楚 selection 机制时用。

---

## 五、Two-Way Fixed Effects (TWFE)：DID 的"标准做法"

工业回归型 DID 的实战形式：

```
Y_it = α_i + γ_t + δ · (Treat_i × Post_t) + 控制变量 + ε_it

α_i：unit 固定效应（吸收每个 unit 的恒定差异）
γ_t：time 固定效应（吸收每期共同冲击）
δ：DID 系数
```

```python
from linearmodels.panel import PanelOLS

mod = PanelOLS.from_formula(
    'Y ~ TreatPost + EntityEffects + TimeEffects',
    data=df.set_index(['unit_id', 'time'])
)
result = mod.fit(cov_type='clustered', cluster_entity=True)
```

> 这是现代论文里 90% DID 的写法。但接下来会看到——TWFE 在某些情况下会**给出错误的结论**。

---

## 六、TWFE 的"现代危机"（**重要**）

2018-2021 年一系列论文（Goodman-Bacon, Sun-Abraham, Callaway-Sant'Anna, de Chaisemartin-D'Haultfœuille）发现：

> **当不同 unit 在不同时间被处理（"staggered adoption"）时，标准 TWFE 的 δ̂ 是各组效应的"加权平均"——但权重可能为负**！结果是 δ̂ 可能与"任何 unit 的真实因果效应"都没关系。

### 直观：为什么会出问题

TWFE 隐含地把"早被处理的 unit"用作"晚被处理 unit"的对照。但早被处理 unit 在那个时刻**已经在被处理**——它的 Y 含有处理效应！这就污染了对照。

### 解法：现代 DID 估计量

| 方法 | 论文 | 工具 |
|---|---|---|
| **Callaway & Sant'Anna (2021)** | *Difference-in-Differences with Multiple Time Periods* | R `did`、Python `differences` |
| **Sun & Abraham (2021)** | *Estimating Dynamic Treatment Effects in Event Studies* | R `eventstudyinteract` |
| **de Chaisemartin & D'Haultfœuille (2020)** | *Two-Way Fixed Effects Estimators with Heterogeneous Treatment Effects* | R `DIDmultiplegt` |
| **Borusyak, Jaravel, Spiess (2021)** | *Revisiting Event Study Designs* | R `did_imputation` |

**实操**：

- 单一处理时点 + 多 unit：传统 TWFE 没问题
- 不同 unit 不同时点（staggered）：**用 Callaway-Sant'Anna 等现代方法**

---

## 七、做 DID 必查的清单

### 1. 平行趋势检验
- 干预前至少 3-4 期数据
- 事件研究图：β_{-1}, β_{-2}, β_{-3} 应接近 0 且无趋势
- Placebo 测试：假装更早的干预日，DID 应不显著

### 2. 处理时点是否交错
- 单一处理时点 → TWFE OK
- 交错处理（staggered）→ **必须用现代方法**

### 3. 异质效应
- 不同 unit 的处理效应可能不同
- 报告时给出"按子群的效应"而不是单一 δ̂

### 4. SUTVA / 溢出
- 处理组和对照组之间有溢出（信息扩散、市场竞争）→ DID 失效
- 解法：地理隔离、增大缓冲区、Switchback 实验

### 5. 处理强度变化
- "上线了"是 0/1，但很多干预是连续强度（投入金额）
- 要看 ATE 的"剂量响应"，需要扩展（Wooldridge 等）

### 6. 反向因果
- "因为业绩差所以上线政策" → 处理本身受 Y 影响
- 解法：寻找"外生时点"（自然实验）

---

## 八、和其他方法对比

| 方法 | 数据要求 | 关键假设 | 何时优先 |
|---|---|---|---|
| **AB 测试** | 能随机分流 | 随机化 | 永远首选 |
| **PSM / IPW** | 横截面 + 可观测混淆 | Ignorability | 没有面板时 |
| **DID** | 面板（前后多期）+ 处理 / 对照 | 平行趋势 | 政策、灰度、A/B 不可行 |
| **合成控制** | 单一处理 unit + 多对照 | 凸组合可重构 | 城市 / 国家级单一干预 |
| **IV** | 有外生扰动 | 工具变量假设 | 未观测混淆严重 |

→ 详见 [synthetic-control.md](synthetic-control.md)、[instrumental-variable.md](instrumental-variable.md)

---

## 九、五个经典踩坑

### 1. 平行趋势没检查就跑 DID
最常见的错误。报告里只给 δ̂ 不给 event study 图——结论可信度大打折扣。

### 2. 标准误没 cluster
默认 OLS 标准误会让 t 值虚高 → 假阳性满天飞。**必须 cluster 到 unit 级**。

### 3. 在 staggered 设计下用 TWFE
δ̂ 可能与真实 ATT **方向相反**。已经是顶刊的"重审旧论文"主题。

### 4. 用 DID 做"事后归因"
"我们做了 X 之后业绩涨了，找个对照组做 DID"——如果 X 的实施时点不外生（不是随机的），平行趋势几乎一定不成立。

### 5. 单一对照 + 单一处理
n=1 vs n=1 的 DID 没有任何统计推断保证。**至少多 unit、多对照**才有意义。

---

## 十、Python 完整示例（含 event study）

```python
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

# df 列：unit_id, time, Y, treat_unit (0/1)
# 干预时点 = T0
T0 = 12  # 假设

df['rel_time'] = df['time'] - T0
df['leads_lags'] = df.apply(
    lambda r: f"k_{r['rel_time']}" if r['treat_unit'] == 1 else "control",
    axis=1
)

# event study 回归
formula = "Y ~ C(leads_lags, Treatment('control')) + C(unit_id) + C(time)"
result = smf.ols(formula, data=df).fit(
    cov_type='cluster',
    cov_kwds={'groups': df['unit_id']}
)

# 画 event study 图
coefs = result.params.filter(regex=r'leads_lags')
ses = result.bse.filter(regex=r'leads_lags')
plt.errorbar(range(len(coefs)), coefs, yerr=1.96 * ses, fmt='o')
plt.axhline(0, color='gray', linestyle='--')
plt.axvline(T0, color='red', label='干预时点')
plt.xlabel('relative time')
plt.ylabel('treatment effect')
plt.legend()
```

---

## 十一、Checklist

```
□ 1. 我有至少干预前后各 1-2 期、最好 3-4 期数据吗？
□ 2. 平行趋势用 event study 画过图了吗？
□ 3. 标准误 cluster 到 unit 级了吗？
□ 4. 处理时点是单一的还是交错的？后者用了现代方法吗？
□ 5. 做了 placebo 检验吗？
□ 6. 处理组和对照组之间有溢出风险吗？
□ 7. 报告里同时给了 δ̂、CI、event study 图、平行趋势检查？
□ 8. 是否考虑过合成控制 / IV 作为 robustness check？
```

---

## 十二、扩展阅读

- 本目录：[propensity-score.md](propensity-score.md)、[synthetic-control.md](synthetic-control.md)、[instrumental-variable.md](instrumental-variable.md)、[dml.md](dml.md)
- 相关：[../concepts/dag-and-d-separation.md](../concepts/dag-and-d-separation.md)
- Card & Krueger (1994) — *Minimum Wages and Employment*（最经典 DID 应用）
- Goodman-Bacon (2021) — *Difference-in-Differences with Variation in Treatment Timing*（**TWFE 危机的奠基论文**）
- Callaway & Sant'Anna (2021) — *Difference-in-Differences with Multiple Time Periods*
- Sun & Abraham (2021) — *Estimating Dynamic Treatment Effects in Event Studies*
- Roth, Sant'Anna, Bilinski, Poe (2023) — *What's Trending in Difference-in-Differences? A Synthesis*（综述，必读）
- Cunningham — *Causal Inference: The Mixtape*, Ch.9
- 工具：R `did`、`fixest`；Python `differences`、`linearmodels`

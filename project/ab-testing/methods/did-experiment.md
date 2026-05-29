# DID 实验方案 — 不能纯随机化时的 AB 替代

> 当**纯随机分流 AB 不可行**时（双边市场、地域级灰度、网络效应、合规约束），**DID（双重差分）作为实验方案**是工业落地的金标准。本文从 AB 工程视角讲清 DID 实验设计、典型场景（geo-experiment、switchback）、样本量估算、和落地中常见坑。

> 上下文：
> - [../../causal-inference/methods/did.md](../../causal-inference/methods/did.md) — DID 的统计学原理 + TWFE 现代危机
> - [../../causal-inference/methods/synthetic-control.md](../../causal-inference/methods/synthetic-control.md) — 单 unit 时的兜底方案
> - 本文聚焦 **DID 作为 AB 替代实验方案的工程化设计与落地**

---

## 一、什么时候必须用 DID 而不是 AB

朴素 AB 实验有两个铁前提：

1. **能在用户级随机分流**
2. **处理组和对照组之间没有溢出**

破任一条，朴素 AB 就失效。常见场景：

### 1. 双边市场 / 网络效应
```
打车：处理组司机接单更快 → 抢走对照组司机的单
外卖：处理组商家曝光更多 → 抢走对照组商家的流量
社交：处理组用户行为变化 → 通过关注关系影响对照组

→ 用户级 AB 实验组之间有溢出，差值不再代表"如果全员上线 vs 不上线"
```

### 2. 地域级 / 合规约束的灰度
```
监管要求"先在某城市试点再全国推"
工程不支持用户级灰度（如线下网点改造）
某些 SDK / 投放无法做用户级分流

→ 只能按城市 / 区域分配处理 vs 对照
→ 城市数量小（5-20），不能依赖 CLT
```

### 3. 不可逆 / 战略级变更
```
首页大改版、品牌升级、价格调整
→ 不能让一半用户看 A 一半看 B（产品体验混乱）
→ 只能"前后对比"
```

### 4. 内容生态级实验
```
推荐算法切换、内容池调整
→ 用户级分流会让算法在两套数据上学习互相污染
```

DID 实验方案的核心思想：

> **不再要求"用户级随机"，而是用"处理时点 + 对照群体"的双重差分构造可比性**。

---

## 二、DID 实验的三种主流设计

### 2.1 Geo-Experiment（地理双重差分）

**最常见的 DID 实验形式**。

```
设计：
  - 全国 N 个城市
  - 随机把城市分成 处理组（k 个）和 对照组（N-k 个）
  - 处理组城市上线新功能 / 投放 / 政策
  - 对照组城市保持原状
  - 观察 4-8 周

估计：
  Y_{c,t} = α_c + γ_t + δ · Treat_c · Post_t + ε_{c,t}
  
  c：城市
  t：时间
  α_c：城市固定效应（吸收城市恒定差异）
  γ_t：时间固定效应（吸收全国共同趋势）
  δ：处理效应（实验"系数"）
```

适合：

- 营销投放、广告效果
- 城市级运营策略
- 司机 / 骑手补贴
- 新功能区域灰度

业界标杆：**Google Geo-Experiment 框架**、**Uber CausalML**。

### 2.2 Switchback（时间分桶切换）

适合**双边市场**的标准方案：

```
设计：
  把时间切成小段（典型 30min - 2h）
  每段随机决定全平台是处理还是对照
  在同一个市场内"按时间随机化"

例：
  Mon  9-10am   控制
  Mon  10-11am  处理
  Mon  11-12pm  控制
  Mon  12-1pm   处理
  ...

估计：
  按小段聚合指标，做处理 vs 对照的差值
  实质是"时间维度的 DID"
```

适合：

- 滴滴 / Uber 派单算法
- 美团 / 饿了么 配送策略
- 实时广告竞价
- 高频交易策略

业界标杆：**Lyft / Uber / Doordash** 多年实践，**Doordash *Beyond A/B Testing***系列博客。

### 2.3 Difference-in-Differences with Pre-Period

最朴素的 DID 实验：

```
设计：
  Phase 1（pre, 2-4 周）：     全员对照，收集基线
  Phase 2（intervention）：    部分群体（按 unit / region / cohort）切换到处理
  Phase 3（post, 2-4 周）：    继续观察
  
估计：
  ATT = (Y_treat,post - Y_treat,pre) - (Y_ctrl,post - Y_ctrl,pre)
```

适合：

- 老用户群灰度新功能
- B 端客户分批接入
- 产品大改版对老用户的影响

---

## 三、DID 实验的样本量与功效

朴素 AB 的样本量公式（[../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md)）**不适用** DID 实验——因为分流单位从"用户"变成了"unit（城市 / 时段 / 群体）"。

### 3.1 关键差异：unit 层级方差

```
朴素 AB：
   用户级方差 σ²_user，n 大（百万级）
   样本量 ≈ 16 · σ² / δ²，几天就够

DID 实验：
   unit 级方差 σ²_unit（典型大于 σ²_user 一个数量级）
   n 小（geo: 10-50，switchback: 几十到几百段）
   样本量 ≈ 16 · σ²_unit / δ²，所需 unit 数远超你想的
```

### 3.2 经验估算公式

#### Geo-DID

```
所需城市数（每组）≈  16 · CV² · ρ² / MDE²

其中：
  CV  = 城市级指标的变异系数（典型 0.2-0.5）
  ρ   = 城市间残差相关性（CUPED 后）
  MDE = 想检测的最小相对效应
```

经验：

```
小城市数（5-10）  →  仅能检测 MDE ≥ 10%
中城市数（15-30） →  可检测 MDE ≈ 5%
大城市数（50+）   →  可检测 MDE ≈ 2-3%
```

→ 如果你只有 5 个城市能做实验，**不要期待检测 < 10% 的效应**。功效从设计阶段就被锁死。

#### Switchback

```
所需时段数 T 与单段时长 L 的权衡：
  L 长 → 处理效应充分体现，但段数少 → 方差大
  L 短 → 段数多，但 carry-over 严重

典型：
  L = 1-2 小时
  T = 100-500 段（一周到一个月）
  能检测 MDE ≈ 1-3%
```

### 3.3 用 CUPED / 协变量调整压方差

DID 实验里方差缩减的收益**比朴素 AB 更大**——unit 数少，每个 unit 历史数据丰富：

```
对每个 unit 用历史指标做 CUPED-style 调整：
  Y'_unit = Y_unit - θ · (X_unit_history - mean(X_history))

→ unit 间方差通常降 50-80%
→ 等价样本量翻倍-五倍
```

→ 详见 [cuped.md](cuped.md)。**Geo-DID 实验不上 CUPED 几乎是浪费**。

### 3.4 Synthetic Control 兜底

如果只有 1 个处理 unit（如"上海上线"对照"全国其他城市"），DID 不够，需要合成控制：

→ 详见 [../../causal-inference/methods/synthetic-control.md](../../causal-inference/methods/synthetic-control.md)。

---

## 四、Geo-Experiment 的执行流程（**实战 SOP**）

### Step 1：选 unit 池
- 排除"被处理直接影响"的城市（如临近城市可能溢出）
- 排除"特殊城市"（北上广深可能本身规律不同）
- 选规模、生命周期、品类相近的可比城市

### Step 2：算样本量
- 估每个候选 unit 的指标历史均值与方差
- 用经验公式估每组所需城市数 + 实验时长
- 评估能否检测到业务关心的 MDE

### Step 3：分组
- **预先分层**：按城市规模 / 地理 / 业务特征分层后再随机
- 检查处理组 vs 对照组在 pre-period 上的指标分布**是否平衡**
- 不平衡 → 重新随机或加协变量调整

### Step 4：基线期（pre-period）
- 至少 2-4 周，最好 4-8 周
- 收集所有指标的历史轨迹
- 验证平行趋势（**event study 图**）

### Step 5：上线处理
- 严格的"实施时间点"——文档化
- 记录处理强度（如果不是 0/1，记录每个 unit 的具体处理量）

### Step 6：后期观察（post-period）
- 至少 2-4 周
- 实时监控护栏指标，异常立刻暂停

### Step 7：分析
- TWFE 或现代估计量（Callaway-Sant'Anna 等，详见 [../../causal-inference/methods/did.md](../../causal-inference/methods/did.md)）
- 必带：event study 图、平行趋势检验、placebo 检验

### Step 8：报告
- δ̂ + 95% CI（cluster 标准误！）
- Robustness：不同协变量集 / 不同样本子集 / 合成控制对照
- 文档化所有"sensitivity check"

---

## 五、Switchback 的执行流程

### 时段设计
```
单段时长 L：
  L 短 → 段数多 → 统计功效高，但 carry-over 严重
  L 长 → 充分但段数少
  
典型：30 分钟 - 2 小时
```

### Carry-Over 问题
**这是 Switchback 最大的工程痛点**：

```
处理段 A 的影响延伸到对照段 B 的开头
   → 对照段被污染
   → 处理 vs 对照差异被低估

应对：
  1. 段间设"washout 缓冲"（最早 5-15 分钟数据不计）
  2. 用滞后模型显式建模 carry-over
  3. 用 cluster-robust SE
```

### 时序随机化
不要简单"奇数段处理 / 偶数段对照"——容易有周期性混杂（如午餐时段总是处理）。

```
✅ 真正随机化：每段独立 50% 概率分配
✅ 平衡随机化：保证每个小时 / 每天的处理对照比例平衡
```

### 多市场并行
往往一个城市段数不够，多城市并行 Switchback：

```
北京：     A B A B A B A B  ...
上海：     B A B A B A B A  ...
广州：     A A B B A A B B  ...

→ 城市 × 时段的二维设计
→ 用面板 DID 估计
```

---

## 六、与现代 DID 估计量的关系

朴素 TWFE（Two-Way Fixed Effects）在多个时点 staggered 处理时**给出错误结果**——见 [../../causal-inference/methods/did.md](../../causal-inference/methods/did.md) 第 6 节。

### 实验设计影响估计方法

| 实验设计 | 推荐估计量 |
|---|---|
| **单一处理时点** + 多 unit | 标准 TWFE OK |
| **Staggered 处理**（不同 unit 不同时点）| Callaway-Sant'Anna / Sun-Abraham |
| **Switchback** | 段聚合 + cluster SE |
| **单一处理 unit** | 合成控制（详见 [synthetic-control.md](../../causal-inference/methods/synthetic-control.md)） |

### 设计阶段就要决定估计量

**不要"先收数据再决定怎么分析"**——估计量决定了：

- 样本量需求
- 平行趋势如何检验
- 协变量怎么用
- robustness check 流程

**预注册（pre-registration）实验设计 + 估计量**是头部团队的标准做法。

---

## 七、DID 实验 vs 朴素 AB 的取舍

| 维度 | 朴素 AB | DID 实验 |
|---|---|---|
| 分流 | 用户级（百万） | unit 级（10-100） |
| 网络 / 溢出 | 假设无 | 天然处理 |
| 样本量需求 | 几天 | 2-8 周 |
| 检测精度 | MDE 1-2% | MDE 5-10%（典型） |
| 关键假设 | 随机化 | 平行趋势 |
| 实施复杂度 | 低 | 高（多 unit 协调） |
| 检验方法 | t / z 检验 | TWFE / 现代 DID 估计量 |
| 早停 | 难（详见 [peeking.md](../pitfalls/peeking.md)）| 几乎不可能 |

**业界经验**：

- **能 AB 就 AB**——朴素 AB 永远是首选
- 只在"AB 失效"时上 DID
- DID 实验的成本是朴素 AB 的 5-10 倍——必须有清晰的业务必要性

---

## 八、典型踩坑

### 1. 城市数太少导致"统计功效假象"
- 5 个 vs 5 个城市做 DID → 自由度 = 8，t 分布尾部很宽
- 即使 δ̂ 看起来大，CI 通常巨宽
- 解法：扩 unit 池 / 接受高 MDE / 用合成控制

### 2. 平行趋势检验只看"系数"
- 报告只给 δ̂ 不给 event study 图 → 平行趋势是否成立无法验证
- 解法：必给完整 event study + placebo test

### 3. 标准误不 cluster
- 默认 OLS SE 严重低估方差
- 解法：cluster 到 unit 级（geo: 城市；switchback: 时段）

### 4. Carry-over 被忽略
- Switchback 不留缓冲 → 处理对对照污染 → 效应被低估
- 解法：段头 / 段尾 buffer 数据丢弃 + cluster SE

### 5. 把 TWFE 当 staggered DID 用
- 不同时点处理 → TWFE 系数可能与真实效应反号
- 解法：Callaway-Sant'Anna / Sun-Abraham

### 6. 没有预注册（pre-registration）
- 实验中途调整估计量 / 控制变量 / 排除子样本 → "p-hacking 的 DID 版"
- 解法：实验启动前文档化"全部分析方案"

### 7. 把 ATT 当 ATE
- DID 估的是"被处理 unit 的平均效应"
- 业务问"如果对所有城市上会怎样"→ 这是 ATE，DID 给不了
- 解法：透明地标注"ATT"

---

## 九、报告模板

DID 实验报告必须包含：

```
✦ 实验目标 + MDE
✦ 设计：geo / switchback / pre-post
✦ unit 池：城市数 / 时段数 / 用户群数
✦ 处理时点 + 处理强度
✦ 协变量 + CUPED 调整方法
✦ 主估计：δ̂ + 95% CI（cluster SE）
✦ Event study 图（可视化平行趋势 + 处理效应曲线）
✦ Placebo / robustness checks（至少 3 种）
✦ 决策：上线 / 下线 / 扩大实验
✦ 估计的是 ATT，不是 ATE（明示）
```

---

## 十、Checklist

```
□ 1. 我能 AB 但选了 DID 吗？为什么不能 AB 我说清了吗？
□ 2. unit 数足够支持目标 MDE 吗（按经验公式估过）？
□ 3. unit 池排除了"被溢出"的 unit？
□ 4. 处理 / 对照在 pre-period 上的指标分布平衡吗？
□ 5. Pre-period 至少 2 周（最好 4-8 周）？
□ 6. CUPED 或类似方差缩减用了吗？
□ 7. 标准误 cluster 到 unit 级了吗？
□ 8. 处理时点单一还是 staggered？后者用了现代 DID 估计量？
□ 9. Event study 图 + Placebo + 至少 1 个 robustness check 都做了？
□ 10. 报告明示这是 ATT 不是 ATE？
□ 11. 设计 + 估计方法**预注册**了？
```

---

## 十一、扩展阅读

### AB 实验视角
- 本目录：[sequential-testing.md](sequential-testing.md)、[msprt.md](msprt.md)、[cuped.md](cuped.md)、[../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md)、[../pitfalls/peeking.md](../pitfalls/peeking.md)

### 因果推断视角（基础理论）
- [../../causal-inference/methods/did.md](../../causal-inference/methods/did.md) — DID 的统计学原理 + TWFE 现代危机
- [../../causal-inference/methods/synthetic-control.md](../../causal-inference/methods/synthetic-control.md) — 单 unit 时的兜底
- [../../causal-inference/methods/dml.md](../../causal-inference/methods/dml.md) — 高维协变量场景

### 工程实践
- **Doordash Engineering Blog** — *Beyond A/B Testing* 系列（Switchback 最完整工程实践）
- **Uber Engineering Blog** — *Switchback Tests*
- **Lyft Engineering** — *Causal Inference at Lyft*
- **Google** — Geo-Experiment 文档（GeoExperiments R 包）
- **Meta / Airbnb / Netflix** — quasi-experimentation 系列博客

### 学术
- Card & Krueger (1994) — *Minimum Wages and Employment*
- Goodman-Bacon (2021) — TWFE 危机
- Callaway & Sant'Anna (2021) — 现代 DID 估计量
- Glynn (2018) — *Switchback designs in the presence of carry-over effects*

### 工具
- R `did`、`fixest`、`synthdid`
- R `GeoexperimentsResearch`（Google 开源）
- Python `differences`、`linearmodels`
- Python `causalimpact`（Bayesian 合成控制）

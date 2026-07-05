# 因果推断 — 开篇导读

> 这是 [causal-inference/](.) 目录的总入口。读完这一篇，你应该能回答：因果推断到底解决什么问题、为什么"控制变量+回归"远远不够、有哪些主流框架和方法、应该按什么顺序学。

---

## 一、为什么需要因果推断（一段不肤浅的论述）

数据分析里最常听到的两句话：

> "相关不等于因果。"
> "我们要找驱动业务的真正原因。"

听起来谁都懂，但当你做产品决策时，相关性其实**到处冒充因果性**：

| 你看到的"相关性" | 真正发生了什么 |
|---|---|
| "用了我们 App 30 分钟以上的用户留存率高 80%" | 高活用户本来就会留下来，不是 App 用得多导致留存 |
| "签到送积分以后，DAU 涨了 5%" | 同期还赶上了大促和广告投放 |
| "把广告推给搜索过商品的用户，转化率特别高" | 这些用户本来就要买，没广告也会买 |
| "客服满意度高的用户复购率高" | 高复购用户问题少，更容易给好评 |

这些都是**真实存在的相关**，但作为决策依据是**灾难性错误**——你在用"未来不可复现"的相关来支撑"未来的投入决策"。

因果推断要解决的就是：**在不能（或暂时无法）做随机实验的情况下，怎么从观察数据里近似抽出"如果做 X 会怎样"的答案。**

> 当能做实验时，请优先做。详见 [../ab-testing/](../ab-testing/)。因果推断方法是当**实验做不了**的兜底——但兜底兜得好，业务收益和决策质量是数量级的。

---

## 二、因果推断的统一语言：Pearl 的因果阶梯

Judea Pearl 给整个领域提供了一张地图：**因果阶梯（Ladder of Causation）**。三层，越往上能力越强、要求越多。详见 [concepts/causal-ladder.md](concepts/causal-ladder.md)。

```
┌───────────────────────────────────────────────────────────────┐
│  3. 反事实（Counterfactual）  "如果当时没投广告，他会买吗？"   │ ← 个体层级
│  2. 干预（Intervention）      "如果我们给所有人投广告，整体会怎样？" │ ← 群体层级
│  1. 关联（Association）       "投了广告的人和没投的人有什么差异？"  │ ← 观察层级
└───────────────────────────────────────────────────────────────┘
                        能力 ↓                          数据/假设要求 ↑
```

**重点**：

- 第 1 层只需要观察数据，多数 SQL 查询和回归模型只能做这一层。
- 第 2 层是 AB 测试和大多数因果推断方法的目标。
- 第 3 层最难，但最有价值——它能回答"对**这个**用户该不该投广告"，是 Uplift Modeling 的本质。

**记一条铁律**：用 1 层方法（如线性回归）回答 2 层问题（如 ROI），等同于在沙地上盖楼。这是绝大多数业务报告的真实病因。

---

## 三、两大主流框架

历史上发展出两个互补的语言体系。理解都要懂，但用法不一样。

### 1. Rubin 因果模型 / 潜在结果框架（RCM, Potential Outcomes）

- **核心想法**：每个个体都有两个"潜在结果"——做了 X 时的 Y(1)，没做 X 时的 Y(0)。**因果效应 = Y(1) − Y(0)**。
- **致命问题**：你永远只能观测到其中一个。这叫**因果推断的根本问题**（Fundamental Problem）。
- **干啥用**：定义清楚估计目标（ATE / ATT / CATE），然后用各种方法去逼近。
- **代表方法**：倾向得分匹配、IPW、双重稳健、Causal Forest、DML。
- 详见 [concepts/potential-outcome.md](concepts/potential-outcome.md)。

### 2. Pearl 结构因果模型（SCM, DAG）

- **核心想法**：用一张有向无环图（DAG）画出变量之间的因果结构，再用规则推导哪些效应**可识别**。
- **核心工具**：do-calculus、后门准则（Back-door Criterion）、前门准则（Front-door Criterion）。
- **干啥用**：先想清楚因果**结构**，再决定要不要控制哪些变量、用什么方法。
- **代表方法**：基于 DAG 的识别 + 上面任意估计方法。

```
RCM 关心：怎么估
SCM 关心：能不能估、应该控制谁

实践中：先用 SCM 画图判定可识别 → 再用 RCM 方法去估。
```

---

## 四、为什么"全控制"（throw everything in the regression）是错的

这是 PM 和数据分析师最大的认知陷阱：

> "我把所有相关变量都加进回归不就行了？"

**不行**。在 DAG 视角下，控制变量分三类：

| 类型 | 含义 | 控制后的效果 | 例子（X=广告投放, Y=购买） |
|---|---|---|---|
| **混淆变量（Confounder）** | 同时影响 X 和 Y | ✅ 必须控制 | 用户活跃度（活跃用户更可能被投广告，也更可能买） |
| **中介变量（Mediator）** | 在 X→Y 链路中间 | ❌ 控制会"吞掉"效应 | 点击广告（X→点击→购买，控制点击就量不到广告效应） |
| **碰撞变量（Collider）** | 同时被 X 和 Y 影响 | ❌ 控制会**制造假相关** | 是否看了商详（被广告影响，也被购买意向影响） |

**这就是为什么"加更多变量"反而让结论更错**——尤其是 collider，控制它会无中生有制造负相关。

> 任何严肃的因果分析必须**先画 DAG**，再决定控制谁。详见 [concepts/dag-and-d-separation.md](concepts/dag-and-d-separation.md)。

---

## 五、方法决策树：我该用哪个方法

```
                    数据情况？
              ┌──────────┴──────────┐
        能随机分流              不能随机分流
              │                       │
              ▼                       ▼
         AB 测试               混淆变量是否可观测？
        (黄金标准)            ┌──────┴──────┐
                          可观测            不可观测
                            │                  │
                            ▼                  ▼
              倾向得分 / IPW           找"自然实验"
              回归调整 / DR             ┌────┼────┐
              Causal Forest          IV  RDD  DID  SC
              DML
                                       ▼
                  例：政策上线前后 + 对照地区/对照人群
```

### 五大类方法速查

| 方法 | 适用场景 | 核心假设 | 代表工具 |
|---|---|---|---|
| **PSM / IPW** | 混淆变量都能观测 | 强可忽略性 | `causalml`, `MatchIt` |
| **回归调整 / DR** | 同上，加上模型校准 | 模型至少一个对 | `econml.LinearDRLearner` |
| **DML** | 高维混淆 + ML | 部分线性、Neyman 正交 | `econml.DML` |
| **IV（工具变量）** | 有外生扰动可借力 | 相关性 + 排他性 + 单调性 | `linearmodels.IV2SLS` |
| **RDD（断点回归）** | 处理由阈值决定 | 阈值附近连续性 | `rdrobust` |
| **DID（双重差分）** | 有处理组/对照组面板 | 平行趋势 | `linearmodels.PanelOLS` |
| **合成控制（SC）** | 单一 unit 政策评估 | 加权对照可重构反事实 | `pysyncon`, `SparseSC` |
| **Uplift Modeling** | 个体级干预决策 | 同上 + 异质性可识别 | `causalml`, `econml`, `EconML.metalearners` |

---

## 六、机器学习与因果（现代视角）

经典因果方法用线性模型，机器学习给它打了肌肉。两条主线：

### 1. 估更准（Estimation）
- **DML（Double/Debiased ML）**：用 ML 估两个 nuisance（结果模型和倾向得分），再 Neyman 正交一下，效应估计就稳了。
- **Doubly Robust**：两个模型只要一个对，结论就对。

### 2. 估个体（Heterogeneity）
- **Causal Forest**：随机森林的因果版，能输出每个用户的 CATE（条件因果效应）。
- **Meta-Learner（S/T/X/R-Learner）**：用任意基学习器组合估异质效应。
- **Uplift Modeling**：直接把"该不该干预"当分类问题，业界营销/Push/广告的主力。

> 这是过去 10 年因果推断领域最大的红利。详见 [methods/dml.md](methods/dml.md)、[methods/uplift-modeling.md](methods/uplift-modeling.md)。

---

## 七、推荐学习路径

### 入门（2-3 周）
1. 本目录：[concepts/causal-ladder.md](concepts/causal-ladder.md)、[concepts/potential-outcome.md](concepts/potential-outcome.md)
2. Brady Neal 在线课程 *Introduction to Causal Inference* 前 5 章
3. Pearl 科普书 *The Book of Why*（不会公式都能读）

### 进阶（1-2 个月）
4. Hernán & Robins *Causal Inference: What If*（在线免费，PART I-II）
5. 实战：跑一遍 `dowhy` 官方 example、`econml` Quick Start
6. 本目录：[methods/propensity-score.md](methods/propensity-score.md)、[methods/dml.md](methods/dml.md)

### 高阶（按需）
7. Pearl *Causality* 第二版（数学密度大）
8. Imbens & Rubin *Causal Inference for Statistics, Social, and Biomedical Sciences*
9. 工业界论文：Uber CausalML 系列、Netflix Quasi-Experimentation 系列

### 哲学补充
- Pearl *The Book of Why*（科普版）
- Cunningham *Causal Inference: The Mixtape*（开源书，案例丰富）

---

## 八、最容易踩的五个坑

1. **把"显著"当因果**。线性回归的系数显著只代表条件相关，不代表因果。
2. **控制了 collider 而不自知**。最常见在 selection bias 的研究里——只看了 churn 用户、只看了点击用户。
3. **平行趋势没检查就用 DID**。处理前两条线就不平行的话，DID 系数毫无意义。
4. **PSM 配完不看 balance**。匹配后协变量没拉平，结论照样有偏。
5. **报告时把 ATE 当 ATT**。两者经常差一个数量级。详见 [potential-outcome.md](concepts/potential-outcome.md)。

---

## 九、和本工作区其他模块的关联

- **AB 测试**（[../ab-testing/](../ab-testing/)）：实验是因果推断的最强方法。两者读法是"先实验、后观察"。
- **Agent + LLM**（[../agent-llm/](../agent-llm/)）：Agent 决策评估、LLM 推荐的增量价值估计、个性化策略——本质都是因果问题。
- **knowledge-base 数据治理 / 数据埋点**（[../../knowledge-base/feishu-source-links.md](../../knowledge-base/feishu-source-links.md)）：因果分析的数据质量地基。
- **decisions/**：每次因果分析的最终结论（包括"放弃这条因果路径"这种结论）建议沉淀。

---

## 十、心法

如果只能记一句话：

> **先想"如果"，再看数据。**

每次拿到数据想跑一个回归之前，强迫自己写下：

```
我要回答的反事实问题是：____
我假设的因果结构是：__→__→__
有哪些变量是 confounder / mediator / collider？
我的识别策略是：____
我的关键假设是：____
我打算怎么检验这些假设？____
```

写不出来，就先别跑回归。这个习惯一个月就能让你的分析质量翻倍。

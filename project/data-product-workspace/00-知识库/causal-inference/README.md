# 因果推断 — 概念、理论与实践

> 系统梳理因果推断（Causal Inference）的核心概念、理论框架、识别策略、估计方法，以及在产品、运营、风控、推荐场景的工程化实践。

## 目录导航

| 目录 | 内容 |
|------|------|
| [concepts/](./concepts/) | 核心概念：因果阶梯、潜在结果、DAG与d-分离、识别假设 |
| [methods/](./methods/) | 方法论详解：PSM、IV、DID、合成控制、DML、Uplift建模、方法选型指南 |
| [pitfalls/](./pitfalls/) | 常见陷阱：混淆偏误、碰撞变量控制、平行趋势检验、常见误用 |
| [cases/](./cases/) | 实战案例：营销增量、渠道归因、定价弹性、策略评估 |
| [templates/](./templates/) | 分析模板：因果分析Checklist、方法选型决策树、结果报告模板 |
| [tools/](./tools/) | 工具评测与代码模板：DoWhy/EconML/CausalML使用指南、代码片段 |
| [papers/](./papers/) | 关键论文摘要：经典论文、业界前沿论文解读 |
| OVERVIEW.md | 开篇导读，建立因果推断心智模型 |

### 核心文件
| 文件 | 内容 |
|------|------|
| [concepts/causal-ladder.md](./concepts/causal-ladder.md) | Pearl因果阶梯：关联/干预/反事实三层能力边界 |
| [concepts/potential-outcome.md](./concepts/potential-outcome.md) | Rubin潜在结果框架：ATE/ATT/CATE、因果推断根本问题 |
| [concepts/dag-and-d-separation.md](./concepts/dag-and-d-separation.md) | 因果DAG与d-分离：混淆/中介/碰撞变量识别、后门/前门准则 |
| [methods/propensity-score.md](./methods/propensity-score.md) | 倾向得分方法：PSM/IPW/DR双重稳健 |
| [methods/instrumental-variable.md](./methods/instrumental-variable.md) | 工具变量法：核心假设、两阶段最小二乘、弱工具问题 |
| [methods/did.md](./methods/did.md) | 双重差分：平行趋势假设、事件研究法、DID扩展 |
| [methods/synthetic-control.md](./methods/synthetic-control.md) | 合成控制法：单一处理单元政策评估、权重优化 |
| [methods/dml.md](./methods/dml.md) | 双重机器学习：高维混淆变量下的因果效应估计、Neyman正交 |
| [methods/uplift-modeling.md](./methods/uplift-modeling.md) | Uplift增益模型：营销/Push/推荐个性化干预、Meta-Learner |
| [methods/业务场景方法选型指南.md](./methods/业务场景方法选型指南.md) | 业务场景因果方法选型决策树+速查表+常见误区 |

## 研究范围

### 1. 概念定义与哲学基础
- 因果 vs 相关：从 Hume 到 Pearl
- 反事实（Counterfactual）与潜在结果（Potential Outcome）
- 因果图（Causal DAG）与 d-分离
- 三类因果问题：Association / Intervention / Counterfactual（Pearl 的因果阶梯）

### 2. 理论框架
- **Rubin 因果模型（RCM）/ 潜在结果框架**：ATE / ATT / ATC / CATE
- **Pearl 结构因果模型（SCM）**：do-calculus、后门准则、前门准则
- **DAG 与可识别性**：confounding / collider / mediator
- 假设检视：SUTVA、Ignorability、Positivity、Consistency

### 3. 识别策略与估计方法
| 场景 | 方法 |
|------|------|
| 实验 | RCT、AB 测试 |
| 观察数据-混淆变量可观测 | 倾向得分匹配（PSM）、IPW、回归调整、双重稳健（DR） |
| 观察数据-存在未观测混淆 | 工具变量（IV）、断点回归（RDD）、双重差分（DID） |
| 面板数据 | 固定效应、合成控制（Synthetic Control）、SCM-DID |
| 异质效应 | Causal Forest、Meta-Learner（S/T/X/R-Learner）、DML |
| 中介分析 | 中介效应分解、Front-door |

### 4. 现代机器学习与因果
- Double/Debiased Machine Learning（DML）
- Doubly Robust Estimation
- Causal Forest / Generalized Random Forest
- Deep Learning for Causal Inference（Dragonnet、CFR、TARNet）
- Uplift Modeling（增益模型）：营销、Push、推荐场景

### 5. 工程化与产品落地
- 因果发现（Causal Discovery）：从数据反推 DAG
- 长期效应估计（Surrogate Index、CUPED-style 加速）
- 因果归因：渠道归因、广告增量
- 风控反事实分析、定价弹性估计
- 个性化干预与策略优化（policy learning）

### 6. 工具与库
- DoWhy（Microsoft）、EconML、CausalML（Uber）
- causaldata、CausalNex、PyWhy 生态
- R: MatchIt、grf、CausalImpact

## 关键参考
- Pearl, Glymour, Jewell — *Causal Inference in Statistics: A Primer* (2016)
- Pearl — *Causality: Models, Reasoning, and Inference* (2009)
- Hernán & Robins — *Causal Inference: What If* (2020, 在线免费)
- Imbens & Rubin — *Causal Inference for Statistics, Social, and Biomedical Sciences* (2015)
- Brady Neal — *Introduction to Causal Inference*（在线课程）
- Matheus Facure — *Causal Inference for The Brave and True*（开源书）

## 与本工作区的关联
- 与 [AB 测试](../ab-testing/) 是同一硬币的两面：实验 = 黄金标准的因果识别
- 与 [Agent + LLM](../agent-llm/) 关联：LLM 评估、Agent 决策评估均涉及反事实
- 业务分析落地 → [../data-analysis/](../data-analysis/)
- 产品决策 → [../decision-frameworks/](../decision-frameworks/)

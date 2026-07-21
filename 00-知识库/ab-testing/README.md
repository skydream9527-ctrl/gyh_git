# AB 测试 — 方法论与业界前沿实践

> 系统梳理 AB 测试的理论基础、方法体系、工程实现，以及业界（Google / Microsoft / Meta / Netflix / Airbnb / 字节 / 美团）的前沿实践。

## 研究范围

### 1. 基础理论
- 假设检验、I/II 类错误、统计功效、最小可检测效应（MDE）
- 显著性水平、置信区间、p 值的正确解读与常见误用
- 频率派 vs 贝叶斯派 AB 测试对比

### 2. 实验设计
- 样本量计算与实验周期估算
- 分流策略：用户级 / 会话级 / 设备级 / 分层分流
- 多版本实验（A/B/n、Multi-Armed Bandit、Contextual Bandit）
- 互斥分桶、正交分流、流量复用

### 3. 进阶方法
- 方差缩减：CUPED、分层抽样、回归调整
- 序贯检验（Sequential Testing）与早停策略
- 多重检验校正（Bonferroni、BH-FDR）
- 异质处理效应（HTE）与个体化效应估计
- Switchback / Time-split 实验（双边市场）
- Interleaving（搜索、推荐场景）

### 4. 工程化
- 实验平台架构：分流引擎 / 元数据管理 / 指标计算 / 报告
- 指标体系：OEC（Overall Evaluation Criterion）、护栏指标、Driver 指标
- 数据质量：SRM（Sample Ratio Mismatch）检测、A/A 测试
- 实验治理：实验生命周期、实验备案、知识沉淀

### 5. 失败模式与陷阱
- Twyman's Law、Simpson 悖论、辛普森反转
- 新奇效应（Novelty Effect）、初见效应（Primacy Effect）
- 网络效应 / 溢出效应（双边市场、社交网络）
- 季节性、周期性偏差
- 选择偏差、幸存者偏差

### 6. 业界前沿
- Microsoft ExP 平台、Google Overlapping Experiments
- Netflix Quasi-Experimentation、Meta CausalML
- 字节 DataTester、阿里 TDE、美团 Horae
- 长期效应估计、低敏指标加速

## 目录结构（建议）

```
ab-testing/
├── README.md                     ← 本文件
├── concepts/                     ← 核心概念笔记
│   ├── hypothesis-testing.md
│   ├── power-and-sample-size.md
│   └── ...
├── methods/                      ← 方法论深入
│   ├── cuped.md
│   ├── sequential-testing.md
│   ├── msprt.md
│   ├── did-experiment.md
│   ├── AB实验规范文档.md          ← AB实验全流程规范：设计原则/分流/指标/执行/统计/报告模板
│   └── ...
├── pitfalls/                     ← 陷阱案例库
│   ├── peeking.md
│   ├── common-mistakes.md        ← AB测试15个常见错误与避坑指南（设计/执行/分析/决策全流程）
│   └── ...
├── cases/                        ← 实际案例
│   └── AB实验分析AgentSOP设计.md  ← 生产级AB实验分析Agent六阶段SOP完整设计
├── industry/                     ← 业界实践拆解
│   ├── microsoft-exp.md
│   ├── netflix-quasi.md
│   └── ...
├── papers/                       ← 关键论文摘要
└── playbook.md                   ← 实操手册（最终产出）
```

## 关键参考

- Kohavi, Tang, Xu — *Trustworthy Online Controlled Experiments* (2020)
- Microsoft ExperimentationPlatform 论文系列（KDD / WSDM）
- Netflix Tech Blog: Quasi-Experimentation / Interleaving 系列
- Airbnb Engineering: Experimentation Platform 系列

## 与本工作区的关联

- 与 [因果推断](../causal-inference/) 强相关：AB 测试是因果推断的金标准
- 与 [Agent + LLM](../agent-llm/) 关联：LLM 产品的离线评测 + 在线实验设计
- 输出可沉淀到 [knowledge-base/](../../knowledge-base/) 对应分类

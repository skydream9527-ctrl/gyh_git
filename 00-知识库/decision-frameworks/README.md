# 决策框架与工具库 (Decision Frameworks & Tools)

> 现代互联网企业决策思考模型、行业案例与实操工具

## 📁 目录结构

```
decision-frameworks/
├── README.md                          # 本文件
├── my-decisions/                      # 我的专属决策案例库（核心新增）
│   ├── README.md                      # 案例库导航与归档规则
│   ├── 需求决策/                      # 需求接不接、插不插队、排期调整
│   ├── 口径决策/                      # 指标口径选择、新老口径切换
│   ├── 方案决策/                      # 技术/产品/分析路径A/B选择
│   ├── 投入决策/                      # 新Skill/新项目/新想法要不要做
│   └── 资源决策/                      # 时间精力分配、优先级排序
├── frameworks/                        # 决策框架详解
│   ├── ai-decision-making.md          # AI决策框架（核心）
│   ├── ai-context-decision-infrastructure.md  # AI上下文决策基础设施
│   ├── ooda-loop.md                   # OODA循环
│   ├── first-principles.md            # 第一性原理
│   └── antifragile-decisions.md       # 反脆弱决策
├── methods/                           # 决策工作流SOP
│   ├── 龚云荷决策护栏.md              # 我的决策红线（硬约束）
│   ├── 龚云荷决策剧本库.md            # 高频决策场景现成剧本
│   └── 个人决策工作流SOP.md           # 个人日常决策全流程指南（OODA+各类决策Checklist+反模式）
├── tools/                             # 决策工具使用指南
│   ├── rice-scoring.md                # RICE优先级评分
│   ├── decision-matrix.md             # 决策矩阵
│   ├── swot-analysis.md               # SWOT分析
│   ├── porter-five-forces.md          # 波特五力分析
│   ├── pestel-analysis.md             # PESTEL分析
│   ├── blue-ocean-strategy.md         # 蓝海战略
│   ├── ansoff-matrix.md              # 安索夫矩阵
│   ├── premortem-analysis.md          # 预-mortem分析
│   ├── bayesian-updating.md           # 贝叶斯更新
│   ├── systems-thinking.md            # 系统思维工具
│   └── game-theory-basics.md          # 博弈论基础
├── templates/                         # 可复用模板
│   ├── decision-record.md             # 决策记录模板(ADR)
│   ├── trade-off-analysis.md          # 权衡分析模板
│   └── risk-assessment.md             # 风险评估模板
└── cases/                             # 行业决策案例
    ├── ai-llm/                        # AI/LLM应用
    ├── e-commerce/                    # 电商行业
    ├── fintech/                       # 金融科技
    ├── saas/                          # SaaS服务
    ├── gaming/                        # 游戏行业
    ├── social/                        # 社交平台
    └── pm-workspace/                  # PM工作区
```

## 🎯 核心理念

### 决策质量 ≠ 决策结果

好的决策过程可能带来坏结果（运气差），坏的决策过程可能带来好结果（运气好）。

**我们追求的是：持续优化决策过程，长期来看提高好结果的概率。**

### 决策的三个层次

| 层次 | 描述 | 工具 |
|------|------|------|
| **战略决策** | 方向性、长期影响 | 第一性原理、系统思维、AI决策框架 |
| **战术决策** | 执行路径、资源分配 | RICE、决策矩阵、预-mortem |
| **运营决策** | 日常优化、快速迭代 | A/B测试、贝叶斯更新、数据仪表盘 |

### AI决策：新范式

AI 不是决策的替代者，而是决策的增强器。核心问题不是"AI能不能决策"，而是：

1. **何时用AI判断 vs 人类判断** → [AI决策框架](./frameworks/ai-decision-making.md)
2. **如何构建AI决策的上下文** → [AI上下文基础设施](./frameworks/ai-context-decision-infrastructure.md)
3. **如何评估AI决策质量** → [贝叶斯更新](./tools/bayesian-updating.md)
4. **如何设计人机协作决策流程** → [AI决策框架 §协作模式](./frameworks/ai-decision-making.md)

## 🚀 快速开始

1. **明确决策类型**：这是战略/战术/运营决策？
2. **判断AI参与度**：参考 [AI决策框架的自动化光谱](./frameworks/ai-decision-making.md)
3. **选择合适框架**：根据决策类型、时间约束和AI能力选择
4. **收集信息**：数据 + 专家意见 + 反对观点 + AI分析
5. **结构化分析**：使用工具量化或可视化
6. **做出决策**：明确记录依据和假设（ADR模板）
7. **跟踪复盘**：贝叶斯更新 + 建立反馈循环

## 📚 学习路径

### 初级：决策基础
- 理解常见认知偏误
- 掌握RICE和决策矩阵
- 学会写决策记录(ADR)
- 理解AI决策的基本光谱

### 中级：量化决策
- 贝叶斯思维应用
- 预期价值计算
- 风险评估与对冲
- AI辅助决策的上下文构建

### 高级：系统决策
- 系统思维与因果回路
- 博弈论与机制设计
- 反脆弱决策设计
- 人机协作决策流程设计

## 🔗 核心文件导航

| 你想做什么 | 去哪看 |
|-----------|--------|
| **启动一次决策（推荐）** | 填 [决策请求卡](../../TEMPLATES/决策/决策请求卡.md) → AI 走 [决策生产线](../../WORKFLOWS.md)（第 4 节） |
| **查我之前做过的类似决策** | [我的决策案例库](./my-decisions/)（按需求/口径/方案/投入/资源分类） |
| **按我的红线决策** | [龚云荷决策护栏](./methods/龚云荷决策护栏.md) |
| **按决策类型走剧本** | [龚云荷决策剧本库](./methods/龚云荷决策剧本库.md) |
| 理解AI该怎么决策 | [AI决策框架](./frameworks/ai-decision-making.md) |
| 让AI认识你的业务 | [AI上下文基础设施](./frameworks/ai-context-decision-infrastructure.md) |
| 日常决策走什么流程 | [个人决策工作流SOP](./methods/个人决策工作流SOP.md) |
| 快速做优先级排序 | [RICE评分](./tools/rice-scoring.md) |
| 多选项结构化比较 | [决策矩阵](./tools/decision-matrix.md) |
| 做战略环境分析 | [SWOT](./tools/swot-analysis.md) → [波特五力](./tools/porter-five-forces.md) → [PESTEL](./tools/pestel-analysis.md) |
| 找增长方向 | [安索夫矩阵](./tools/ansoff-matrix.md) → [蓝海战略](./tools/blue-ocean-strategy.md) |
| 防止决策翻车 | [预-mortem分析](./tools/premortem-analysis.md) → [风险评估](./templates/risk-assessment.md) |
| 记录决策过程 | [ADR模板](./templates/decision-record.md) |
| 看行业案例（外部行业参考） | [cases/](./cases/) 目录下 7 个行业 |

---

> **`cases/` 与 `my-decisions/` 的区别**：`cases/` 收录外部行业的决策案例，供学习参考（向外看）；`my-decisions/` 是你自己做过的真实决策（决策简报 + 回看结果），供检索相似历史、复用判断（向内看）。

**维护者：** 龚云荷（gongyunhe）  
**最后更新：** 2026-07-04

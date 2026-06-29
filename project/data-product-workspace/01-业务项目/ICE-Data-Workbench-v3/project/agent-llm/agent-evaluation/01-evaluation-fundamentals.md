# 01. Agent 评测基础：评什么、为什么、和 LLM 评测的本质区别

> 本文目标：建立"为什么 Agent 必须有评测体系，以及它和单纯评 LLM 的不同之处"的认知。读完你能解释**评测的四层结构、Agent 评测的特殊难点、五大评测维度**。

---

## 一、为什么必须建评测集

不建评测集时的迭代节奏：

```
改 prompt → 跑 2 个 demo → 看着还行 → 上线 → 用户反馈差 →
改 prompt → 跑 2 个 demo → 看着还行 → 上线 → ...
```

每次改你不知道是真好了，还是这次"运气好"。**这就是玄学**。

建了评测集后：

```
改 prompt → 跑全套 200 题 → 总分 78 → 81 → 看哪些 case 改善/恶化 →
判断是否上线 → 持续跟踪
```

**这才是工程化**。

---

## 二、Agent 评测和 LLM 评测的 5 个本质差别

| 维度 | 单纯 LLM 评测 | Agent 评测 |
|---|---|---|
| **任务类型** | 单轮 QA / 单轮生成 | 多轮、多步、调工具、可能与人交互 |
| **状态空间** | 输入 → 输出，无状态 | 有 memory、tool 调用历史、外部环境状态 |
| **正确性边界** | 答对 vs 答错 | 答对 + 路径合理 + 工具用得对 + 没造成副作用 |
| **失败模式** | 胡说、拒绝、格式错 | 死循环、工具误用、规划错、级联错误、上下文丢失 |
| **可重复性** | 高（temperature=0 几乎确定） | 低（环境变化、工具返回会变） |

**结论**：直接套用 LLM benchmark（MMLU, MT-Bench）来评 Agent，**永远评不出真问题**。

---

## 三、Agent 评测的 5 大维度

仅看"任务成功率"不够。一个完整 Agent 评测应该覆盖：

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Task Success Rate  : 任务最终是否完成（黑盒）            │
│ 2. Trajectory Quality : 中间 step 是否合理（白盒）          │
│ 3. Tool Use Quality   : 工具是否选得对、参数是否合法        │
│ 4. Efficiency         : 步数 / token 消耗 / 延迟 / 成本     │
│ 5. Safety & Side-effect: 没误删文件、没乱发邮件、没泄密     │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Task Success（任务级）
最终交付是否符合规格。例如"订一张周五去北京的票"，是否拿到符合条件的票号。

> 注意：**有些任务的成功不可机器判断**——"写一篇引人入胜的产品发布稿"。这时要走 LLM-as-Judge 或人工评。

### 3.2 Trajectory Quality（路径级）
即使任务完成，过程也可能很差：

```
✓ 任务: 查一下今天上海天气
  Trajectory A: 调 weather_api → 返回 → 总结  ← 3 步
  Trajectory B: 调 search → 调 search → 调 search → 调 weather_api  ← 9 步
                ↑ 这就是糟糕的 trajectory：浪费 token、慢、贵
```

衡量方法：
- **步数对比** vs reference trajectory
- **是否走 dead-end**：调了工具但结果没用上
- **是否绕路**：信息已知却又重复检索

### 3.3 Tool Use Quality
独立于任务成败，单看工具调用合不合规：
- **Tool selection**：选对了工具吗？（FC = function correctness）
- **Argument correctness**：参数填对了吗？（AC）
- **Argument validity**：schema 合法吗？
- **Hallucinated tools**：有没有调一个根本不存在的工具？
- **Order**：依赖关系对不对？

> Berkeley Function Calling Leaderboard（BFCL）就是专门评这些。详见 [03-mainstream-benchmarks.md](03-mainstream-benchmarks.md) §4。

### 3.4 Efficiency
Agent 跑赢了不代表赢得起：

| 指标 | 含义 |
|---|---|
| **avg steps** | 平均完成任务用几步 |
| **token in / out** | 进/出 token 平均量 |
| **avg latency** | p50 / p95 端到端时长 |
| **$ per task** | 单任务平均成本（tool call + LLM 调用） |

### 3.5 Safety / Side-effects
**危险行为黑名单**：
- 删了不该删的文件
- 调了带副作用工具（send_email, payment, exec_sql）但没用户授权
- 泄露 system prompt 或用户数据
- 走入死循环烧钱

**评测方法**：
- 红队（Red-team）：手工构造对抗 prompt
- 自动化对抗：用另一个 LLM 生成攻击性 prompt
- 沙箱回放：所有"危险工具"先在 sandbox 里调，看会不会出事

---

## 四、四层评测结构（贯穿全目录）

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1  端到端评测     业务任务成功率（黑盒）                   │
│            ▲             例：订单完成率、报告完整度               │
│            │                                                     │
│ Layer 2  阶段评测       每个 phase 的产出质量                    │
│            ▲             例：搜索阶段是否找到关键信息             │
│            │                                                     │
│ Layer 3  组件评测       单 prompt / 单工具能力                   │
│            ▲             例：reranker 单独评、planner 单独评     │
│            │                                                     │
│ Layer 4  在线监控       生产流量上的指标                          │
│                          例：用户拒收率、人工接管率               │
└─────────────────────────────────────────────────────────────────┘
```

**每一层都要建**。只评 Layer 1 太粗（看不到为什么失败），只评 Layer 3 太细（看不到整体效果），缺 Layer 4 就脱离真实用户。

---

## 五、评测集要怎么造

### 5.1 数据来源
1. **真实用户日志（最珍贵）**：从 production 流量采样，去敏感化。
2. **专家手写**：领域专家造"难题"、"边界 case"。
3. **LLM 合成 + 人工筛**：用强模型生成候选，人工 review 留下高质量的。
4. **公开 benchmark 改造**：拿 GAIA/AgentBench 子集，按业务场景改写。
5. **失败案例反哺**：线上失败 case 入库，作为 regression 题。

### 5.2 容量级别建议

| 评测目的 | 题量 | 备注 |
|---|---|---|
| 快速冒烟 | 20-50 | 每次 PR 跑 |
| 中等版本对比 | 100-300 | 每周跑、每次大改跑 |
| 严肃发布评估 | 500-1000+ | 月度 / 季度 |
| benchmark 论文级 | 1000-10000 | 学术发布 |

> **质量 > 数量**：100 道精心标注的题比 5000 道含噪声的题有用得多。

### 5.3 标注 schema 推荐

```yaml
- id: e2e_task_001
  category: "research"        # 任务大类
  difficulty: "medium"
  topic: "查 Q1 财报数据并分析趋势"

  # 期望产出
  expected_aspects:
    - "覆盖至少 3 家公司"
    - "包含同比/环比对比"
  must_cite:
    - "公司官方财报"
  forbidden:
    - "未引用来源的具体数字"

  # 期望路径
  reference_trajectory:
    - tool: search
      query_pattern: "Q1 财报"
    - tool: read_pdf
    - tool: summarize

  # 已知正确答案的关键事实（如有）
  ground_truth_facts:
    - fact: "公司 A 营收 X 亿"
      source: "https://..."

  # 红线
  safety_constraints:
    - "不能擅自调 send_email"
```

---

## 六、Agent 评测的 6 个常见陷阱

### 陷阱 1：只评最终输出
忽略路径质量，**让模型学到"反正最后蒙对就行"** 的歪路。

**对策**：trajectory-aware metrics + 步数惩罚。

### 陷阱 2：评测集就是训练数据
模型见过的题再考一遍，分数高得不像话。

**对策**：
- 评测集 hold-out
- 用合成日期 / 反事实数据
- 定期换"未来日期"题

### 陷阱 3：评测环境和生产环境不一致
评测里工具是 mock，生产里工具会超时、返回错误。

**对策**：
- **Stochastic eval**：评测时随机注入工具失败（5%-10% 概率）
- 部分 case 跑真实工具
- 定期"shadow eval"：复制生产请求到 staging 跑评测

### 陷阱 4：LLM-as-Judge 偏见
裁判模型打分有 8 种已知偏见（详见 [02-evaluation-methods.md](02-evaluation-methods.md) §4）。

**对策**：多 judge 投票、随机化位置、限定 rubric。

### 陷阱 5：忽略成本/延迟
分数高 1%，token 翻倍，**业务上是亏的**。

**对策**：评测看板必须包含成本和延迟。

### 陷阱 6：迭代不可重现
每次评测看到不同结果，无法判断是否真有改进。

**对策**：
- 固定 seed
- 固定模型版本（包括 minor）
- 评测题目版本化
- 一切跑分写入运行日志

---

## 七、什么时候不需要建评测集

诚实地说：**有些场景不值得**。

```
✗ 不需要建 :
   - 一次性 demo / hackathon
   - 概念验证 (PoC) 阶段
   - 模型用作"灵感工具"，输出由人最终把关

✓ 必须建 :
   - 任何要上生产的 Agent
   - 要做版本迭代对比
   - 要选型（A 厂 vs B 厂模型）
   - 涉及成本/延迟优化决策
```

---

## 八、给团队的 5 条经验

1. **从 Day-1 就建小评测集（20 题就够）**——比从 0 起步的成本低 10×。
2. **别完美主义**：先有粗糙评测胜过没有。
3. **失败案例必须回流**：线上挂的题，下次评测里必须考。
4. **评测脚本工程化**：版本化、可复跑、可比较。
5. **别让评测分数成为唯一目标**——会出现"为分数优化"的反模式。

---

下一篇：[02-evaluation-methods.md](02-evaluation-methods.md) — 5 种主流评测方法：rule-based / reference-based / LLM-as-judge / human / online。

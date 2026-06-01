# Tree of Thoughts (ToT) 原理与应用策略

> 本文是 [react-and-variants.md](react-and-variants.md) 的纵深篇——把 Tree of Thoughts 的**搜索机制**讲透（节点 / 评估 / 剪枝怎么定义、四种实现策略、采样与评估的成本平衡），再给出**应用策略**（什么场景一定用 ToT、什么场景千万别用、在 [`project/ice-workbench/`](../../ice-workbench/) 里怎么薄薄套一层）。
>
> 阅读路径：先看 [react-and-variants.md §7](react-and-variants.md) 建立直觉，再看本文。

---

## 一、ToT 解决的真问题

LLM 的 CoT / ReAct 都是**单线推理**——一旦走错就再也回不来。这在两类任务上特别致命：

```
任务类型 A：组合优化 / 谜题
  例：24 点（用 4 个数 +-*/ 凑出 24）
  → 第一步选错运算 → 之后再聪明也救不回来

任务类型 B：长程规划
  例：写小说大纲、研究路径规划
  → 第一段定调错 → 后面越走越偏
```

ToT (Yao et al., 2023) 的核心洞察：

> 让 LLM 像人类做难题一样——**不是"想一条思路就执行"，而是"想几条思路、各往前走一步、看哪条像样、剪掉差的、保留好的"**。

把单线推理升维成**树搜索**。这一改动在 24 点任务上把成功率从 4%（CoT）拉到 74%（ToT）。

---

## 二、四要素：把 ToT 拆解到能写代码

ToT 不是一个单独算法，而是 4 个组件的组合：

```
┌─────────────────────────────────────────────────────────────┐
│ ToT 的 4 个核心抽象                                          │
└─────────────────────────────────────────────────────────────┘

①  Thought Decomposition         "一步思考"是什么？
    （问题怎么切片）              （24 点：一次运算；写作：一段大纲）

②  Thought Generation            从一个状态怎么生成多个候选？
    （想出 K 条候选）              （sampling K 次 / 一次生成 K 个）

③  State Evaluation              一个中间状态有多好？
    （打分 / 投票）                （value 模型 / vote 投票）

④  Search Algorithm              用什么搜索策略遍历这棵树？
    （怎么遍历 + 剪枝）            （BFS / DFS / Beam）
```

理解 ToT = 理解这 4 件事**各自都是 LLM call**——而这也是 ToT 贵的根本原因。

### 2.1 Thought Decomposition——切片粒度决定一切

| 粒度 | 例子 | 优劣 |
|---|---|---|
| 单 token | 几乎没人用 | 树太深，搜索不动 |
| 一句话 | 大纲推理、作文 | 平衡型，最常用 |
| 一个动作 | 写一段代码、做一次运算 | 适合可验证场景 |
| 一段段落 | 长文档、章节大纲 | 搜索浅但每步贵 |

**切片粒度 = 树的深度**。粒度太小搜索发散；粒度太大每步评估不准。论文里 24 点选"单步运算"、写作选"一句话"是因为每种任务有天然粒度。

### 2.2 Thought Generation——两种策略

```
策略 A: Sample (温度高，独立采样 K 次)
  for i in range(K):
    thought_i = LLM.generate(state, temperature=0.7)
  → 适合开放式任务（没有"标准答案"），多样性好

策略 B: Propose (一次性生成 K 个有差异的候选)
  thoughts = LLM.generate(
      f"Given {state}, propose {K} different next steps"
  )
  → 适合受限场景，K 个候选互相不重复
```

**经验规则**：约束多用 Propose（避免重复采样），开放任务用 Sample（多样性更好）。

### 2.3 State Evaluation——ToT 真正的难点

这一步决定 ToT 成败：

```
评估 1: Value（独立打分）
  for each state:
    score = LLM.score(state, scale="1-10")
  → 简单，但分数不稳定（同一个状态多次跑分数浮动 ±2）

评估 2: Vote（候选间互投）
  best = LLM.choose("which of these K states is best?")
  → 比 Value 稳，因为对比比绝对评分容易；但每次 K 选 1 都要全量上下文
```

**致命陷阱**：评估自己也是 LLM，有自己的偏好和幻觉。一个不可靠的 evaluator 会把 ToT 搜索引向更差的分支。**没有可验证的 evaluator → 不要用 ToT**。

### 2.4 Search Algorithm——三种主流

```
BFS（广度优先）                  DFS（深度优先 + 回溯）
  每层保留 b 个最优               一直走到底，失败回溯
  → 24 点这种深度浅的任务 ✅      → 长程规划 / 写作 ✅

Beam Search                      Best-First (A*-style)
  每层只保留 top-b（朴素 BFS）    根据 score 选下一个展开
  → 内存可控的折中                → 评估稳时最优，否则不稳
```

实际中 **BFS + beam=5** 是默认选择。

---

## 三、一次 ToT 推理的完整 trace（24 点为例）

把抽象具象化：

```
任务：用 [4, 9, 10, 13] 通过 +-*/ 凑出 24

层 0（根）：[4, 9, 10, 13]
   │
   │ Generate K=4 个 propose
   ▼
层 1：
   ├─ "10 - 4 = 6"  → 剩 [6, 9, 13]
   ├─ "10 + 4 = 14" → 剩 [14, 9, 13]
   ├─ "13 - 9 = 4"  → 剩 [4, 4, 10]
   └─ "13 - 4 = 9"  → 剩 [9, 9, 10]

   评估每个状态: "能凑出 24 吗？"
   ├─ [6, 9, 13]   → likely (有希望)
   ├─ [14, 9, 13]  → likely (有希望)
   ├─ [4, 4, 10]   → unlikely
   └─ [9, 9, 10]   → unlikely

   保留 top-2 (beam=2)
   │
   ▼
层 2 ([6, 9, 13] 展开)：
   ├─ "13 - 9 = 4"  → [6, 4]
   ├─ "13 - 6 = 7"  → [7, 9]
   ├─ "9 - 6 = 3"   → [3, 13]
   └─ ...
   评估，剪枝...

层 3：直到剩 1 个数 = 24

成功路径：(10-4)*(13-9)·... 其中一条
```

注意 trace 里**至少做了**：
- 生成调用：4 次（层 1）+ 4 次×2 节点（层 2）+ 4 次×2（层 3）≈ 20 次
- 评估调用：4 + 8 + 8 ≈ 20 次

**总 LLM 调用 ≈ 40 次**——而 CoT 只需要 1 次。这就是 ToT 贵的根源。

---

## 四、ToT 的成本经济学

ToT 不是"思想可贵就值得用"。每次 ToT 推理的 token 消耗约为：

```
Cost ≈ depth × branching × (gen_cost + eval_cost)

      = depth × (b_gen × prompt_size_gen)        # 生成
      + depth × (b_eval × prompt_size_eval)      # 评估
      + 评估的内存累积（每层都要看历史）
```

**经验数字**（GPT-4 / Claude Opus 级模型）：
- CoT 单次：~$0.01
- ReAct 5 步：~$0.05
- **ToT (depth=4, b=5)**：~$0.30 - $1.00

→ ToT 成本比 ReAct 高 **1-2 个数量级**。

什么时候这笔钱值得？
- 任务**对了就有强经济价值**（重要决策、核心算法、不能错的报告）
- 任务**很贵的人工替代**（人类专家 1 小时 vs ToT 跑 30 秒）
- 任务**有可验证的中间状态**（不是 ToT 又花钱又得到坏答案）

---

## 五、ToT 的 4 种典型配置

### 配置 A — "Game Solver" 型

```
任务：24 点、数独、走迷宫、谜题
切片：每一次合法动作
生成：Propose K=4-8（动作有限）
评估：Value 函数（"距离目标多远"）
搜索：BFS, beam=5, depth ≤ 5
```

### 配置 B — "Planner" 型

```
任务：项目计划、研究路径、写作大纲
切片：一段 / 一句
生成：Sample K=3-5
评估：Vote（K 选 1）
搜索：Best-First, depth ≤ 4
```

### 配置 C — "Code Search" 型

```
任务：找最优实现路径、重构方案选择
切片：一个修改步骤
生成：Propose K=3
评估：跑测试 + LLM 评（混合）
搜索：DFS + 回溯
```

### 配置 D — "Hybrid Decision" 型（最实用）

```
不直接落 ToT 完整循环，而是把 ToT 思想"嵌入"ReAct：
  1. ReAct 主循环正常跑
  2. 在"决策关键点"调一次 ToT-style "K 选 1"：
     "下一步有 3 种思路 [A, B, C]，对比后选最好"
  3. 决策完回到 ReAct

成本远低于完整 ToT，效果显著高于纯 ReAct。
```

→ 配置 D **是生产环境最值得复用的模式**。

---

## 六、应用策略：什么时候必须用 / 千万别用

### ✅ 必须用 ToT 的 3 类场景

1. **任务有可被自动验证的"是否正确"**——24 点、数独、有 unit test 的代码生成、SQL 正确性检查。验证器可靠 = ToT 评估可靠 = 搜索能收敛。
2. **第一步选错代价巨大**——长篇论文大纲、关键架构选型、重要业务决策。先 propose 多条思路评估再展开，比单线一路走到黑值得。
3. **搜索空间结构清晰**——状态、动作、终止条件都能形式化定义。否则 ToT 搜的是"自己定义模糊的树"，越搜越乱。

### ❌ 千万别用 ToT 的 3 类场景

1. **实时对话 / 客服 Agent**——ToT 平均 10-30 秒一次，用户已经走了
2. **没有可靠 evaluator**——评估自己也是 LLM，乱评比单线推理还差
3. **任务步骤本身简单**——本质是 1-2 步的事情，套 ToT 只会变贵不变好

### 中间地带：用配置 D（Hybrid）

绝大多数生产场景**不该用纯 ToT**，但**配置 D 的"决策点 K 选 1"是普适的**。代价小、收益明显。

---

## 七、ToT 的工程坑

### 坑 1 — 评估器漂移（Evaluator drift）

LLM 自评有偏好，比如：
- 偏向"更长"的答案（看起来认真）
- 偏向"措辞流畅"的（不一定正确）

**解法**：
- 评估用**不同 prompt 模板**多次跑，取平均
- 关键场景用**verifier 模型**（专门 fine-tune 过的判别模型）
- 有 ground truth 时用 **rule-based 评估**取代 LLM 评估

### 坑 2 — 状态表示爆炸

每个状态要带完整历史 → 第 4 层 prompt 已经几 KB → 评估慢且贵。

**解法**：
- 状态用**摘要 + diff** 表示（不存历史 trace）
- 评估只看"当前状态 + 目标"，不带完整路径

### 坑 3 — 多样性塌陷

Propose K 个候选，结果模型生成出几乎一样的 3 条 → 浪费搜索预算。

**解法**：
- prompt 里强制"K 个候选必须明显不同"
- 用 **temperature=0.9 + topp=0.95** 增加多样性
- Sample 而非 Propose

### 坑 4 — 终止条件模糊

"何时停下来认为答案已找到"在开放式任务里很难定义。

**解法**：
- **设定 max_depth**（4-6 层基本就该出答案）
- **early stop**：当前层最佳 score > 阈值则停
- 终止判定单独再调一次 LLM

### 坑 5 — 调试困难

40 次 LLM 调用 + 树形 trace + 多层评估 → 出错时定位极难。

**解法**：
- **结构化 trace**：每个节点存 (parent, depth, thought, score, children_ids)
- **可视化树**：开发期画出搜索树，直观看到剪枝是否合理
- **回放 mode**：保存随机种子，能 deterministic 重跑

---

## 八、在 [`project/ice-workbench/`](../../ice-workbench/) 中怎么用

### 8.1 现状：ice-workbench 没有 ToT 内核

ice-workbench 当前是 **ReAct + Compaction** 架构（详见 [react-mechanism-and-strategy.md §7](react-mechanism-and-strategy.md)）：
- 主循环：[`backend/app/services/llm_gateway.py`](../../ice-workbench/backend/app/services/llm_gateway.py)，`MAX_TOOL_ROUNDS=50`
- 不存在"多分支推理 + 评估 + 剪枝"的搜索抽象

直接挂"完整 ToT 内核"代价太大（且违反 ice-workbench "5 轮 tool-call 上限"哲学）。**推荐挂"配置 D Hybrid"**。

### 8.2 接入路径：把 ToT 当成"建议工具"

#### Step 1 — 注册一个 builtin tool 或 skill

在 [`backend/app/services/tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py) 加一个 `propose_and_choose` 工具：

```python
{
  "name": "propose_and_choose",
  "description": "在做关键决策前，并行生成 K 条候选思路，然后对比选最优。"
                 "适用于：选 SQL 表达式、选指标定义、选回归口径等关键决策点。"
                 "不适用于：常规问答、信息查询。",
  "parameters": {
    "decision_context": "string",   # 当前面对的决策
    "k": {"type": "integer", "default": 4},
  }
}
```

实现：
```python
def propose_and_choose(decision_context, k=4):
    # 1. 让 LLM propose K 条候选
    candidates = llm.generate(f"propose {k} alternatives for: {decision_context}")
    # 2. 评估
    chosen = llm.generate(
        f"Which of these is best for {decision_context}? Vote. {candidates}"
    )
    return {"candidates": candidates, "chosen": chosen, "rationale": ...}
```

→ Agent 可以**自主**判断"现在是不是关键决策点"，需要才调。**保持 ReAct 主循环不变**，避免架构地震。

#### Step 2 — 适用场景：data-analysis Agent

ice-workbench 的 [`agents/data-analysis/`](../../ice-workbench/agents/data-analysis/) 是最适合 ToT 思想的 Agent，关键决策点很多：

| 决策点 | 单线 ReAct | propose_and_choose |
|---|---|---|
| 选维度组合 | 选第一想到的 | 列 4 种维度 + 评估业务相关性 |
| 选回归方法 | 默认 OLS | 列 [OLS / Logistic / Tree / DiD] + 选 |
| 选样本筛选 | 简单过滤 | 列多种筛选 + 评估代表性 |
| SQL 写法 | 一稿 | 列 3 种 + 评估性能 / 可读性 |

→ 这些场景下成本是 1.5-3 倍 ReAct，但**结果质量显著提升**。

#### Step 3 — 重要：评估器需要事实根据

如果纯 LLM 自评，会陷入"评估漂移"坑。建议：
- SQL 写法的"性能评估" → 让评估调用 `kyuubi_query` 看 EXPLAIN（[`tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py)）
- 回归方法选择 → 评估问"这个方法对当前数据合不合适"+具体诊断指标（不是单纯打分）

→ ToT 的评估器**绑定一个真实数据源**比纯 LLM 评估稳得多。

#### Step 4 — 成本守门

`propose_and_choose` 一次调用 ≈ K+1 次 LLM call ≈ 5 次 → 成本不容忽视。建议：
- 每个 conversation 限制最多 3 次（防止滥用）
- 在审计日志（[CLAUDE.md](../../ice-workbench/CLAUDE.md) Audit Logging Rules）里专门记录
- 用低价模型做 propose，用强模型做评估（异质）

### 8.3 完整 ToT 也不是不能做——bg_task 是合适的载体

ice-workbench 的 [`backend/app/services/bg_task_svc.py`](../../ice-workbench/backend/app/services/bg_task_svc.py) 处理"用户提交后台任务"的场景。这类任务**不要求实时**，可以承受 30 秒-数分钟搜索。

适合在 bg_task 里跑完整 ToT 的任务：
- 长报告大纲生成（"为这个数据分析任务列 5 种汇报结构 → 评估 → 选最优"）
- 实验设计推荐（"AB 测试这个指标有 3 种切分方式，逐一评估"）
- 复杂 SQL 优化（"重写成 4 种 SQL，比对 EXPLAIN，选最优"）

实现思路：在 bg_task 里写一个独立的 `tot_runner.py`，**不污染主 ReAct 循环**。

### 8.4 在 ice-workbench 接 ToT 的 checklist

```
□ 1. 决定挂"完整 ToT" 还是"配置 D Hybrid"——绝大多数选 Hybrid
□ 2. 接入点：tool_runner（Hybrid）或 bg_task_svc（完整 ToT）
□ 3. 评估器尽量绑定真实数据源（kyuubi EXPLAIN / 测试 / 运行结果）
□ 4. 单次调用成本预算（每 propose_and_choose 限 K≤4）
□ 5. 单 conversation 调用次数上限（≤ 3）
□ 6. 审计日志记录 (decision_context, candidates, chosen, rationale)
□ 7. 结构化 trace：propose 候选和评估结果都存 task workspace
□ 8. UI 提示用户"此处使用了多路径推理"（让用户感知 vs ReAct 差异）
□ 9. 评估漂移监控：人工审 50 条 propose_and_choose trace，判断评估是否合理
□ 10. 失败降级：propose_and_choose 失败时退回单线推理（不要让搜索失败拖垮主流程）
```

---

## 九、ToT 与其他范式的关系

```
CoT          单线推理
   ↓
ReAct        单线推理 + 工具 + 反馈
   ↓
ToT          多路径推理 + 评估 + 剪枝   ← 升维到搜索
   ↓
LATS         ToT + RL（Monte Carlo Tree Search 风格的奖励学习）
   ↓
o1 / r1      把 search 内化进模型本体（RL 训出来的 reasoning）
```

**ToT 是从"语言模型推理"到"搜索推理"的关键桥梁**。理解 ToT 也就懂了 OpenAI o1 系列、DeepSeek-R1 这些 reasoning 模型的核心思想——它们在做的事和 ToT 一样，只是搜索过程被压进了模型权重，对外表现成"一次推理"而已。

---

## 十、扩展阅读

- 同目录：[react-and-variants.md](react-and-variants.md)、[react-mechanism-and-strategy.md](react-mechanism-and-strategy.md)
- 长期记忆配套：[memory-systems.md](memory-systems.md)、[openviking-vs-hindsight.md](openviking-vs-hindsight.md)
- 论文：
  - Yao et al. (2023) — *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*
  - Hao et al. (2023) — *Reasoning with Language Model is Planning with World Model* (RAP)
  - Zhou et al. (2024) — *Language Agent Tree Search* (LATS, 把 ToT + RL 结合)
- 相关博客：
  - Lilian Weng — *LLM Powered Autonomous Agents*（树搜索章节）
  - Princeton NLP — *Tree of Thoughts* 官方仓库（含 24 点 / 创意写作 / mini crossword 三个 demo）
- ice-workbench 实战参考：[`tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py)、[`bg_task_svc.py`](../../ice-workbench/backend/app/services/bg_task_svc.py)

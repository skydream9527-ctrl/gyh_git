# ReAct 机制原理与应用策略

> 本文是 [react-and-variants.md](react-and-variants.md) 的纵深篇——把 ReAct 的**机制底层**讲透（为什么它有效、prompt 怎么编排、token 流如何被解析、控制变量怎么调），再给出**生产级应用策略**（包括在 [`project/ice-workbench/`](../../ice-workbench/) 的具体接法）。
>
> 阅读路径建议：先看 [react-and-variants.md](react-and-variants.md) 第 1-4 节建立直觉，再看本文。

---

## 一、ReAct 的本质：把"语言模型"当成"程序计数器"

通常理解 ReAct 是"思考 + 行动循环"，但它**真正的工程价值**在另一件事上：

> ReAct 把 **"下一步做什么"** 这个决策从代码里 hard-code 出来，**外包给了 LLM 的上下文窗口本身**——上下文里出现什么，下一步就做什么。

换句话说，ReAct 不是"框架"，是一种**用 prompt 当 program counter** 的设计模式。LLM 在每一轮看到的是：

```
[历史 Thought / Action / Observation]
[当前最新 Observation]
"现在写下一个 Thought 和 Action："
```

→ 模型生成的 token 流就是下一条指令。**整个执行序列就是一段被 LLM 续写的文本**。

理解这一点，才能解释下面一连串"为什么"：

- 为什么 prompt 模板对 ReAct 至关重要 → 因为模板就是它的"指令格式"
- 为什么 max_steps 要硬编码 → 因为 LLM 不会自己 break
- 为什么 schema 校验比 prompt 重要 → 因为续写出来的"参数"经常长得像样但是错的
- 为什么 Anthropic 后来推 **structured tool_use** → 把"格式正确"从 prompt 工程降级成 API 保证

---

## 二、ReAct 循环的 7 个微观步骤

把一轮 ReAct 拆到 token 级别，发生的事情远比"想 → 做 → 看"复杂：

```
┌─────────────────────────────────────────────────────────────┐
│ 第 N 轮 ReAct 内部                                           │
└─────────────────────────────────────────────────────────────┘

① 上下文组装
   system_prompt + 工具 schema + 历史 (thought/action/obs)*N + cue
                                                               ↓
② LLM 推理（流式 token）
   "Thought: ... Action: tool_x Action Input: {...}"
                                                               ↓
③ Stop sequence 截断
   遇到 "Observation:" 就停（防止模型自己幻觉出工具结果）
                                                               ↓
④ 解析 Action（这一步是工程坑最密集的地方）
   - 旧式：正则切 "Action: ... Action Input: {...}"
   - 新式：API 直接返回 tool_use block（结构化）
                                                               ↓
⑤ Schema 校验
   参数类型 / required / enum 三件套，错就反馈给模型重试
                                                               ↓
⑥ 工具执行（带超时 + 沙箱）
   timeout / OOM / 网络错误统一包成 error envelope
                                                               ↓
⑦ Observation 拼回上下文
   工具返回值 → "Observation: ..." → 加到历史
                                                               ↓
   回到 ①（直到模型输出 "Final Answer:" 或 max_steps）
```

每一步都有可能出错，**生产级 ReAct 实现的 80% 代码都在处理 ②-⑦ 的失败模式**。

---

## 三、为什么 ReAct 真的有效：3 个机制叠加

### 机制 1 — 显式中间步骤减少错误率

CoT（Chain-of-Thought）已经证明：让模型**写出**推理过程，比直接答比更准。原因不是"模型在思考"——它没有思考——而是：

```
P(answer | question) ≪ P(answer | question, thought_1, thought_2, ...)
```

每一段 thought 都是后续 token 的**上下文锚点**。写出来的中间步骤让最终答案的条件概率更尖锐。

### 机制 2 — Observation 把分布拉回真实世界

LLM 单跑 CoT 时，**所有"事实"都来自模型权重**——遇到知识盲区就开始编。ReAct 把工具返回拼进上下文：

```
Thought: 我需要知道 2024 年小米 SU7 销量
Action: web_search("2024 SU7 sales")
Observation: ... 13.5 万辆 ...   ← 这是真实事实，不是模型权重里的
Thought: 已知销量 13.5 万...
```

这一行 Observation **强制模型在真实数据基础上继续推理**，把"幻觉的概率分布"压缩到"真实分布"附近。

### 机制 3 — 失败可被观察和反馈

工具失败 → Observation 是错误信息 → 模型下一轮 Thought 通常会调整：

```
Action: get_user(id="U123")
Observation: ERROR USER_NOT_FOUND
Thought: 用户 ID 错了。换个查法。
Action: search_user(name="李四")
```

这是**反馈环**——和强化学习的"reward signal"是同构的，只不过是用语言来传递。

> **三句话总结**：CoT 让推理更准，工具让事实可信，反馈让错误能纠。

---

## 四、Prompt 模板的微观工程

ReAct 的 prompt 看起来就一段，实际上每一行都有讲究：

```
You have access to the following tools:
{tools}                              ← 工具描述质量决定选择正确率

Use the following format:
Question: ...
Thought: 你应该想想要做什么
Action: 工具名称，必须是 {tool_names} 之一
Action Input: 工具的 JSON 输入
Observation: 工具结果
... (Thought/Action/Observation 可以重复 N 次)
Thought: 我现在知道答案了
Final Answer: ...

Begin!

Question: {input}
{agent_scratchpad}                   ← 历史 thought/action/obs 拼接处
```

### 4.1 工具描述（`{tools}`）的写法决定 70% 的选择正确率

**坏例子**：
```
search: 搜索工具
```
→ 模型经常用错（"搜索"是搜什么？数据库？网页？知识库？）

**好例子**：
```
search_papers(author: str, year: int, venues: list):
  在论文库中按作者+年份+会议筛选论文。
  仅当用户明确询问"某人的论文"且能给出年份和会议时使用。
  不能用来搜博客 / 新闻 / 通用网页。
```
→ 边界、参数、反例都在描述里。模型选错率显著下降。

### 4.2 Stop sequence 是 ReAct 的"括号匹配"

如果不设 stop=`["Observation:"]`，模型会自己续写：
```
Action: search_papers(...)
Observation: 假装找到了 5 篇... (← 模型瞎编！)
```
→ 必须用 API 的 `stop` 参数在 `Observation:` 处打断。新式 tool_use API 不存在这个问题（API 直接返回 tool_use 就停止），但走 OpenAI/Anthropic legacy completion 接口时这一刀至关重要。

### 4.3 `{agent_scratchpad}` 增长策略

每一轮把上一轮的 `Thought/Action/Observation` 拼进去，**不剪枝则上下文爆炸**：

```
Round 1: 1 KB
Round 5: 10 KB
Round 10: 50 KB（很可能开始 lost-in-the-middle）
```

生产做法：
- 保留**最近 K 步原文** + **早期步骤的摘要**
- Observation **截断长度**（数据库返回 10MB 别原样塞）
- 失败的 Action 可以缩成"step 3 失败：USER_NOT_FOUND"

---

## 五、ReAct 的 5 个失败模式与对应策略

### 失败模式 1：循环——一直调同一个工具

**症状**：第 8 步还在调 `search_papers(author="张教授")`，参数只换了字母大小写。

**根因**：模型卡在某个错误观点上，每次"反思"都得到同样结论。

**解法**：
- **重复检测**：把 (action_name, json.dumps(args, sort_keys=True)) 哈希，连续 ≥3 次相同 → 强制注入 system 提示"你在重复，换思路或调用 give_up"
- **参数抖动**（数据查询场景）：自动微调超时/limit 让响应不同

### 失败模式 2：参数错——格式对但语义错

**症状**：`get_user(id="李四")`——把名字塞进了 ID 字段。

**根因**：JSON schema 没有 enum/format 约束，模型按"看起来对"填。

**解法**：
- **Pydantic / Zod 校验**+ 错误反馈给模型重生（不是直接抛）
- **示例驱动**：工具描述里写 1-2 个正反例
- **类型严格化**：`id: str` 改成 `id: str = Field(pattern=r"^U\d+$")`

### 失败模式 3：早收敛——还没查完就 Final Answer

**症状**：模型查了 1 篇论文就说"答案是 X"，明明任务说"两篇"。

**根因**：CoT 一旦"觉得答出来了"，停止信号会跳过未完成步骤。

**解法**：
- **任务分解前置**：先让模型生成 plan（变成 Plan-and-Execute 混合）
- **后置 verifier**：另一个 LLM 调用，问"任务要求是 N 项，这里只覆盖了 M 项，对吗？"

### 失败模式 4：上下文爆炸——第 6 步开始变慢且变蠢

**症状**：前 5 步效果不错，6-8 步开始模型答非所问。

**根因**：`agent_scratchpad` 变长 → lost-in-the-middle + 每次推理 token 数翻倍。

**解法**：
- **历史压缩**：第 K 步之前的 (T/A/O) 三元组用更小的模型摘要成一句
- **滑窗 + 关键节点保留**：保留 system + 最近 N 步 + 起始任务定义
- **换范式**：改用 Plan-and-Execute（步骤明确就不需要长链路推理）

### 失败模式 5：工具选错——给了 30 个工具，模型挑错那个

**症状**：明明是查 SQL 的需求，模型用了 web_search。

**根因**：工具描述被淹没在长 prompt 里。

**解法**：
- **动态工具检索**：embedding 召回 top-K 相关工具，每轮只塞 5-10 个进 prompt
- **分组**：高度相关的工具放一起，无关的拆 sub-agent（不同 agent 不同工具集）
- **去重 / 合并**：3 个相似工具合成 1 个带枚举参数

---

## 六、应用策略速查表

不同任务对应不同 ReAct 配置。下表来自实操经验：

| 场景 | 推荐配置 |
|---|---|
| 简单数据查询（"查某指标"） | max_steps=3, 单工具，无反思层 |
| 多源信息聚合（"对比 X 和 Y"） | max_steps=8, 工具 5-10 个，加 verifier |
| 代码 / 数据分析 Agent | max_steps=15, 加 reflexion 层（失败重试） |
| 长文档 / 研究型任务 | 改用 Plan-and-Execute，ReAct 只做 sub-step |
| 实时对话客服 | max_steps=5, 严格超时（90s 内必须回答） |
| Coding Agent (Cursor 类) | ReAct 内核 + Reflexion 外层 + 工具检索 |

### 6.1 max_steps 的取值哲学

- 太小（≤3）：处理不了多步骤任务
- 太大（≥30）：失败成本高，单次任务可能花 $1+
- **看任务真实步数 × 1.5**：典型任务平均 5 步 → max_steps=8

### 6.2 工具数量的取值哲学

- ≤5：选错率很低，但能力有限
- 5-15：甜区
- 15-30：开始要做动态检索
- ≥30：必须分 sub-agent，不能塞同一个 prompt

### 6.3 温度 (temperature) 的取值

- ReAct 推荐 **0-0.3**：稳定优先于创意
- 不要 0：浮点累加会有非确定性，反而难调试
- 多次跑同任务对比：温度 0 也会出现细微差异（API 服务端 batching）

---

## 七、在 [`project/ice-workbench/`](../../ice-workbench/) 中的实战接入

ice-workbench 已经实现了一套**生产级 ReAct 内核**，是研究 ReAct 工程化的好范本。

### 7.1 现有实现的要点

| 元素 | 在哪 | 备注 |
|---|---|---|
| 主循环 | [`backend/app/services/llm_gateway.py`](../../ice-workbench/backend/app/services/llm_gateway.py) | `MAX_TOOL_ROUNDS = 50`、`TOOL_TIMEOUT_SEC = 30` |
| Sub-agent / bg-task ReAct | [`backend/app/services/agent_runtime.py`](../../ice-workbench/backend/app/services/agent_runtime.py) | 非流式版本 |
| 工具注册 / 调度 | [`backend/app/services/tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py) | builtin + user-defined skills |
| Schema 校验 | 各 builtin 工具内 + skill JSON schema | 失败返回 `error_code` |
| 上下文压缩 | [`backend/app/services/compaction_svc.py`](../../ice-workbench/backend/app/services/compaction_svc.py) | 默认 on |
| Stream 协议 | [`backend/app/api/v1/ws.py`](../../ice-workbench/backend/app/api/v1/ws.py) | text / tool_use_delta / message_done |

### 7.2 ice-workbench 是怎么解决前述 5 个失败模式的

| 失败模式 | ice-workbench 的解法 |
|---|---|
| 1. 循环 | `MAX_TOOL_ROUNDS=50` 硬上限 + 用户可 abort |
| 2. 参数错 | builtin 工具里 raise 标准 error_code（如 `KYUUBI_INVALID_QUERY`），下一轮模型自然反应 |
| 3. 早收敛 | 暂未做 verifier 层 → **可以扩展**（见 7.3） |
| 4. 上下文爆炸 | `compaction_svc` 自动摘要长会话 |
| 5. 工具选错 | builtin 工具数量被刻意控制（now/echo/kyuubi/feishu_*/write_file/execute_python）+ skill 动态加载 |

### 7.3 4 个**没现成实现、值得加**的策略

#### 策略 A — 工具调用重复检测

`agent_runtime.py` 的循环里加一个最近 3 次 (tool_name, args_hash) 的滑窗，命中重复就插一条 system message："你刚刚连续调用了 X 三次，结果相同，请换思路或终止。"

#### 策略 B — 后置 verifier

针对**多项任务**（任务文案明确说"对比 N 项"或"列出 K 个"），在最终答前调一次小模型："任务要求 N 项，输出实际覆盖了 M 项吗？" 不一致就退回多一轮 ReAct。

#### 策略 C — 工具描述强化

[`backend/app/services/tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py) 中，`kyuubi_query` / `feishu_publish` 这类外部 CLI 工具的描述加：
- 两个反例（"不要用来 INSERT" / "不要用来跨工作空间查询"）
- 失败 error_code 列表（让模型预判）

实测可降低 20-40% 的错调率。

#### 策略 D — Streaming-aware tool 取消

ice-workbench 的 inflight guard 已经处理"用户 abort"，但**模型自己产生的 tool_use_delta 在中途也可能想撤回**——目前架构是不可撤的。如果要做更高级 ReAct（推理时改主意），可以考虑在 tool_use_delta 完成前给一个"撤回 token"。

### 7.4 集成到具体 Agent 时的 checklist

```
□ 1. 工具描述写到"反例 + error_code 列表"级别
□ 2. max_steps 按任务复杂度配（不要全局一个值）
□ 3. compaction 阈值贴合该 Agent 的对话特征
□ 4. 多项任务加后置 verifier
□ 5. 重复检测（连续 3 次同工具同参数 → 强制提示）
□ 6. 工具失败统一 error envelope（参考 ice-workbench `*_NOT_CONFIGURED`）
□ 7. 流式输出时 stop sequence 设置正确
□ 8. 历史窗口策略：保留最近 K + 早期摘要
```

---

## 八、ReAct vs 其他范式：什么时候不该用 ReAct

| 任务特征 | 用 ReAct | 不用 ReAct |
|---|---|---|
| 步骤未知，要边走边定 | ✅ | — |
| 步骤数 ≤ 3 且确定 | — | 用 Workflow |
| 步骤多但前后无依赖 | — | 用 Plan-and-Execute |
| 中间状态可评估 | — | 用 [Tree of Thoughts](tree-of-thoughts.md) |
| 多角色协作 | — | 用 Multi-Agent |
| 失败可重试 + 反思 | — | 用 Reflexion 包 ReAct |

**ReAct 的核心价值**是"步骤不确定"——一旦能确定步骤，更省钱的范式都比 ReAct 好。

---

## 九、检查表（应用 ReAct 时反复 ask）

```
□ 我真的需要"动态决策"吗？还是 Workflow 就行？
□ 工具描述写到了"反例 + error_code"级别吗？
□ 有 max_steps 兜底吗？
□ 工具参数有 schema 校验 + 失败反馈给模型吗？
□ 长链路有上下文压缩 / 历史摘要吗？
□ 有重复检测 / give_up 工具吗？
□ 工具数量 > 15 时有动态检索吗？
□ 工具调用结果是真实可信的（带超时 + 错误）吗？
□ 有失败案例的离线评测集吗？
□ 上线后能采样观察 ReAct trace 吗？
```

---

## 十、扩展阅读

- 同目录：[react-and-variants.md](react-and-variants.md)（决策树 + 与 Reflexion / P&E / Multi-Agent 的对比）
- 进阶范式：[tree-of-thoughts.md](tree-of-thoughts.md)
- 工具协议：[../tools-protocols/function-calling.md](../tools-protocols/function-calling.md)、[../tools-protocols/mcp.md](../tools-protocols/mcp.md)
- 长期记忆配套：[memory-systems.md](memory-systems.md)、[openviking-vs-hindsight.md](openviking-vs-hindsight.md)
- 论文：Yao et al. (2022) — *ReAct: Synergizing Reasoning and Acting in Language Models*
- 相关博客：Lilian Weng — *LLM Powered Autonomous Agents*；Anthropic — *Building Effective Agents*
- ice-workbench 的 ReAct 内核：[`backend/app/services/llm_gateway.py`](../../ice-workbench/backend/app/services/llm_gateway.py)、[`agent_runtime.py`](../../ice-workbench/backend/app/services/agent_runtime.py)

# 02. 5 种主流评测方法对比

> 本文系统讲清楚 Agent 评测里 5 种主流方法的**原理、适用场景、优缺点、典型坑**。读完你能根据具体评测维度选对方法。
>
> 5 种方法：**Rule-based / Reference-based / LLM-as-Judge / Human / Online metrics**。

---

## 一、方法选型快速决策表

| 评什么 | 首选方法 | 备选 |
|---|---|---|
| 任务结果是否符合 schema | Rule-based | LLM-as-Judge |
| 输出是否包含关键事实 | Rule-based（关键词/正则）| LLM-as-Judge |
| 答案语义是否正确 | Reference-based（exact / fuzzy / semantic）| LLM-as-Judge |
| 答案是否引用对来源 | Rule-based + Reference-based | - |
| 输出风格 / 流畅度 / 同理心 | LLM-as-Judge → Human spot-check | Human |
| 多个候选答案的相对好坏 | LLM-as-Judge（pairwise）| Human pairwise |
| Trajectory 是否合理 | LLM-as-Judge + 步数对比 | Rule-based |
| Tool 是否选对、参数对不对 | Rule-based（schema 校验） | - |
| 主观满意度 | Online（CSAT / 拒收率 / 接管率） | Human |
| 长上下文检索精度 | Reference-based（needle 对比） | - |
| 边界 / 安全 | Rule-based（红线词表）+ Human red-team | - |

---

## 二、方法 1：Rule-based 评测

### 2.1 适用场景
- 输出有**确定结构**：JSON、SQL、API 调用
- 必须包含/禁止某些**关键内容**
- 工具调用的 schema / argument 校验
- 红线 / 合规检测

### 2.2 典型规则集

```python
def eval_search_agent(output: dict) -> dict:
    score = {}
    # 结构正确
    score["schema_valid"] = validate_schema(output, SCHEMA)
    # 关键字段存在
    score["has_citations"] = len(output.get("citations", [])) >= 3
    # 不能含禁忌词
    score["no_forbidden"] = not any(w in output["text"] for w in FORBIDDEN)
    # 引用 URL 真实存在
    score["citation_alive"] = all(check_url(c) for c in output["citations"])
    return score
```

### 2.3 常用规则类型
- **正则匹配**：必须包含 / 不能包含
- **JSON Schema 校验**：jsonschema 库
- **函数签名校验**：tool name / arg names / arg types 是否匹配
- **数值范围**：例如温度回答必须 -50~50
- **引用真实性**：URL 可达 / 出现在 ground-truth 来源里

### 2.4 优点
- ✅ **极快、零成本、确定性**
- ✅ 易解释，易调试
- ✅ 法规/安全相关必须用

### 2.5 缺点和坑
- ❌ 无法评语义、风格
- ❌ 维护成本高（每条规则都得写测试）
- ⚠️ 容易"捕鼠器化"——为绕规则而生成奇怪答案

### 2.6 实战建议
- **第一道防线**：所有 Agent 评测都先过 rule-based 卡掉明显错误
- 红线词表用业务侧维护（合规 + PM 共同维护）

---

## 三、方法 2：Reference-based 评测

### 3.1 适用场景
有**已知正确答案**或参考输出。

### 3.2 三种比较方式

#### (a) Exact / Fuzzy Match
```
预期: "ID-12345"
输出: "id-12345"
→ exact: ✗   case-insensitive: ✓
```
适合：ID、数字、枚举答案。

#### (b) BLEU / ROUGE / F1（n-gram 重叠）
机器翻译、摘要常用。LLM 时代用得越来越少，因为：

> "The cat sat on mat" vs "On the mat sat a cat" — 语义相同，BLEU 极低。

#### (c) Embedding Similarity（语义相似度）
```python
from sentence_transformers import SentenceTransformer, util
model = SentenceTransformer("BAAI/bge-large-zh")
sim = util.cos_sim(model.encode(output), model.encode(reference))
```
- 阈值通常 0.85+ 算"语义匹配"
- 适合开放回答的"接近度"评估
- 注意 embedding 模型选型对结果影响大

### 3.3 用于 RAG 的常见指标

| 指标 | 含义 |
|---|---|
| **Recall@K** | top-K 检索结果中包含 ground-truth 的比例 |
| **MRR** | 第一个相关结果的排名倒数均值 |
| **nDCG** | 排序质量综合分（高度相关排前面更好） |
| **Faithfulness**（RAGAS） | 回答中的 claim 能在引用 context 里找到 |
| **Answer Relevance** | 回答是否切题 |

### 3.4 优点
- ✅ 客观、可重复
- ✅ 适合**有标准答案**的任务

### 3.5 缺点和坑
- ❌ 没有 reference 就用不了
- ❌ Reference 也可能有错
- ⚠️ 多种正确答案时，过严的 reference 让正确答案被判错

---

## 四、方法 3：LLM-as-Judge

### 4.1 为什么火
- 无 reference 也能评
- 可评开放性回答的**语义和风格**
- 比人工便宜 100×、快 1000×

### 4.2 三种范式

#### (a) Single Scoring（单点评分）
```
Prompt: "请按以下 5 条 rubric 对答案打分（1-5）：
   1. 准确性
   2. 完整性
   3. 引用质量
   4. 表达清晰度
   5. 不含幻觉
   答案：<output>
   参考资料：<retrieved_context>"
```

#### (b) Pairwise Comparison（两两对比）
```
"哪个答案更好？A、B、平局。
 A: <output_v1>
 B: <output_v2>"
```
**比单点打分更稳定**——人脑擅长"选哪个更好"，绝对打分容易飘。

#### (c) Reference-Anchored（参考答案对齐）
```
"参考答案：<gold>
 模型答案：<output>
 模型答案在多大程度上覆盖了参考答案的关键点？给 0-100 分。"
```

### 4.3 LLM Judge 的 8 种已知偏见

| 偏见 | 表现 | 防御 |
|---|---|---|
| **Position bias** | A、B 顺序影响判断（裁判偏向第一个或第二个） | 随机化 / 双向跑取均值 |
| **Length bias** | 偏向更长的答案 | rubric 写明长度无关 / 控制 max_tokens |
| **Verbosity bias** | 偏向 markdown / bullet 多的答案 | 同上 |
| **Self-enhancement** | 同模型评同模型偏高 | 用不同 family 模型当 judge |
| **Authority bias** | "GPT-4 写的"被打高分（如果泄露） | 不告诉 judge 模型来源 |
| **Sycophancy** | 用户说"这个好对吧?" judge 顺着说 | rubric 写中立指令 |
| **Anchor bias** | rubric 里的例子分数被照抄 | rubric 例子不要打具体分 |
| **CoT bias** | 让 judge 写 reasoning 反而打分更乐观 | 结构化 rubric + 强制每条独立打分 |

### 4.4 实战 prompt 模板

```
你是一个严格的评审。给定问题、模型答案、参考答案：

【打分维度】
- accuracy (1-5): 与参考答案在事实上的一致性
- completeness (1-5): 是否覆盖了参考答案的所有要点
- citation (1-5): 引用是否真实、对应、相关
- safety (binary): 是否含有红线内容（人身攻击/虚假/越权操作）

【评分规则】
- 每个维度独立打分，不要被其他维度影响
- 答案长度不应影响打分
- 如果不确定，倾向更低分
- 必须按 JSON 输出

【任务】
问题：{question}
参考答案：{reference}
模型答案：{output}

输出 JSON：{"accuracy": ..., "completeness": ..., "citation": ..., "safety": ..., "reasons": [...]}
```

### 4.5 怎么验证 Judge 自己靠谱？

**Judge 也要被评测**。常用做法：

```
Step 1: 准备 100 道有人工标注分的题
Step 2: Judge 跑这 100 题
Step 3: 算 Judge 与人工标注的一致性（Cohen Kappa / 皮尔逊相关）
Step 4: 如果一致性 < 0.7，judge 不能用于生产
```

> 详见 [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)。

### 4.6 优点
- ✅ 可扩展、可重复
- ✅ 能评开放性

### 4.7 缺点和坑
- ❌ 偏见多，需校准
- ❌ 强 judge（GPT-4o / Claude Opus）成本依然不低
- ⚠️ Judge 同 model 时严重 bias

---

## 五、方法 4：Human Evaluation

### 5.1 适用场景
- 终极裁判（其他方法的 ground-truth 来源）
- 需要专业判断的领域：医疗、法律、金融
- 评测体验类指标：流畅度、自然度、同理心
- 红队测试

### 5.2 常见做法

| 形式 | 适用 | 注意 |
|---|---|---|
| **Likert 打分** (1-5) | 单点评估 | 多人标注 + 平均 |
| **Pairwise A/B** | 两版本对比 | 顺序随机化 |
| **Best-of-N** | 多候选选最佳 | 候选数 ≤ 5 |
| **Error annotation** | 标错点类型 | 给标注 schema |
| **Open-ended feedback** | 收集挂哪了 | 适合早期 |

### 5.3 标注质量保证

```
1. 标注 guideline 写清楚（举例 + 边界 case）
2. 多人交叉标 → 算 Inter-rater agreement (Kappa, ICC)
   - Kappa > 0.6 才算可用
3. 黄金题混入抽查（标注员不知道）
4. 异常标注者下线
```

### 5.4 成本与速度
- 每条 ~1-5 分钟，专业领域 ~10-30 分钟
- 100 题 × 3 人 = 300-1500 人时——所以高价值题才走人工

---

## 六、方法 5：Online Metrics（生产监控）

### 6.1 为什么离线评测不够
离线评测**永远比线上偏乐观**——
- 评测题分布 ≠ 真实流量分布
- 评测里工具是 mock，线上工具会失败
- 用户行为（编辑、撤回、追问）是真实信号

### 6.2 关键在线指标

```
任务级:
   - 任务完成率（self-report 或 后置事件）
   - 平均完成步数
   - 平均时长
   - 单任务成本

用户行为级:
   - 拒收率（用户编辑/撤回 LLM 输出的比例）
   - 重试率（"重新生成"按钮点击率）
   - 接管率（人工介入率，客服 agent 重要指标）
   - CSAT（满意度调查）
   - 留存（次日/7 日活跃）

系统级:
   - p50 / p95 latency
   - 错误率
   - 工具调用失败率
   - 上下文超长截断率
```

### 6.3 与 A/B 实验衔接

```
新模型 v2 离线评测 +3% → 不能直接全量
                       ↓
           5% 流量 A/B → 看在线指标
                       ↓
       拒收率/CSAT/成本 没掉 → 全量
```

> A/B 设计与显著性、辛普森悖论、长期效应等：[../../ab-testing/](../../ab-testing/)。

---

## 七、组合策略：实战中怎么搭配

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Layer 1 (快速门禁)                                          │
│      Rule-based (几十毫秒) → Reference-based (秒级)          │
│      → 卡掉格式错、明显错、红线                                │
│                                                             │
│   Layer 2 (语义评测)                                          │
│      LLM-as-Judge (秒级到分钟级)                             │
│      → 用 GPT-4o / Claude Opus 当 judge，多 prompt 投票       │
│                                                             │
│   Layer 3 (人工校准)                                          │
│      Human eval (随机抽 5-10%)                                │
│      → 校准 LLM judge 一致性、捕捉新失败模式                   │
│                                                             │
│   Layer 4 (生产监控)                                          │
│      Online metrics + A/B                                   │
│      → 长期追踪、回归检测                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**缺一不可**。每天只跑 Layer 1，每周补 Layer 2，每月做一次 Layer 3 抽样校准，Layer 4 一直在跑。

---

## 八、评测工程化常见落点

| 工具 | 用途 |
|---|---|
| **OpenAI Evals** | 通用评测框架，模板丰富 |
| **PromptFoo** | YAML 驱动的 prompt 评测 + CI |
| **DeepEval** | Python 评测框架，含 RAGAS / G-Eval 模板 |
| **LangSmith** | LangChain 配套，含 trace + eval |
| **Langfuse** | 开源 trace + eval 平台 |
| **Helicone / Phoenix** | LLM 监控 + 评测 |
| **Inspect AI** | UK AISI 的 Agent 评测框架 |
| **MLflow + 自建** | 大企业自建评测看板 |

---

## 九、5 个原则

1. **先 rule，再 reference，最后 LLM-judge**——便宜的先跑，挡掉明显错。
2. **任何 LLM judge 用前先验证**——和人工标的 Kappa < 0.6 别上。
3. **多 judge 投票 + 位置随机化**降低偏见。
4. **离线评测必须配在线监控**，否则隔天就漂。
5. **失败案例自动回流评测集**，让 regression 有据可循。

---

下一篇：[03-mainstream-benchmarks.md](03-mainstream-benchmarks.md) — 主流公开 benchmark 全景图。

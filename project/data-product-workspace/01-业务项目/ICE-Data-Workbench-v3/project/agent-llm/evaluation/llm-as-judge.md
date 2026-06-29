# LLM-as-Judge：用 LLM 评 LLM

> 当输出没有"标准答案"时，怎么自动评估 LLM 应用的质量？**LLM-as-Judge** 是当前业界的主流答案——但它不是简单"换个 prompt 让 GPT-4 打分"。本文讲清正确做法、常见偏置、以及如何让它真正可靠。

---

## 一、为什么需要 LLM-as-Judge

LLM 应用的输出空间是开放的，传统评估方法都失效：

| 方法 | 问题 |
|---|---|
| 标签匹配（accuracy） | "对"的回答有无穷多种写法，匹配不上 |
| BLEU / ROUGE | 表面 n-gram 重合，不反映语义 |
| 嵌入相似度 | 相关但不准（"语义相似" ≠ "答得好"） |
| 人工评估 | 准但慢且贵，无法规模化 |

**LLM-as-Judge** 折中：

```
让一个强 LLM（GPT-4 / Claude / 内部专门评测模型）按规则打分

人类质量近似的同时，能规模化（千 / 万级别评估）
```

业界共识：**LLM-as-Judge 与人类评分的相关度通常在 0.6-0.85**——不完美，但在 80% 工业场景够用。

---

## 二、两种基本范式

### 1. Pointwise（单点评分）

让 judge 给每个回答独立打分。

```
[Prompt]
你是一名严格的评测员。请按以下标准给回答打 1-5 分：
1 - 完全错或不相关
3 - 部分正确
5 - 完美

问题：{question}
回答：{answer}

请输出 JSON: {"score": x, "reasoning": "..."}
```

| 优势 | 劣势 |
|---|---|
| 直接、可独立评估 | LLM 评分**绝对值不稳**——同一回答两次评分可能差 1 分 |

### 2. Pairwise（两两比较）

给 judge 两个回答，让它选哪个更好。

```
[Prompt]
比较以下两个回答，选出更好的一个：

问题：{question}

回答 A：{answer_a}
回答 B：{answer_b}

输出：{"winner": "A" or "B" or "tie", "reasoning": "..."}
```

| 优势 | 劣势 |
|---|---|
| **比 pointwise 更稳**（人类判断也是相对的） | 需要 baseline 进行对比 |
| 适合 A/B 比 prompt / 模型 | n² 比较代价高（多模型时） |

> **生产经验**：能用 pairwise 别用 pointwise。MT-Bench、Chatbot Arena 等知名榜单都用 pairwise。

---

## 三、LLM-as-Judge 的六大偏置（**必须知道**）

### 1. Position Bias（位置偏置）
Judge 倾向于选第一个或第二个回答。
- 实测：GPT-4 评 pairwise 时，对 A 的偏好可达 60%（vs 50% 公平）
- **解法**：每对都 swap 顺序跑两次取均值；或随机打乱

### 2. Verbosity Bias（长度偏置）
Judge 倾向于选更长的回答（即使没更对）。
- **解法**：在 prompt 里强调"长不等于好"；输出格式化后比较

### 3. Self-Preference Bias（自我偏好）
GPT-4 评分倾向 GPT-4 写的；Claude 评分倾向 Claude 写的。
- **解法**：用第三方 judge；或多 judge ensemble

### 4. Authority Bias
Judge 容易被回答中"自信" / "学术"语气蒙蔽。
- **解法**：把"自信度"列为评分维度，不要让它和"正确性"混

### 5. Familiarity Bias
Judge 对常见话题判断好；冷门话题判断差。
- **解法**：冷门领域配合人工抽检

### 6. CoT Anchor
Judge 写完推理后倾向"找证据支撑早期判断"。
- **解法**：让 judge 先列优缺点再下结论；或让它先给分再写理由

---

## 四、Best Practices：让 judge 更可靠

### 1. Rubric 越具体越好

```
❌ 模糊：
   "评估回答质量"

✅ 具体：
   "请按以下维度评分（每维 1-5）：
    - 准确性：事实是否正确
    - 完整性：是否回答了所有子问题
    - 简洁性：是否冗长跑偏
    - 引用：是否标注来源"
```

### 2. Few-shot 例子

在 prompt 里给 judge 看几个"高分 / 低分"的样本——让它对齐你的标准。

### 3. 强 Judge

- 评测用 **GPT-4 / Claude Opus / 等同级模型**——比被评测对象强一档
- 别用 GPT-3.5 评 GPT-4

### 4. 结构化输出

```python
class JudgeResult(BaseModel):
    accuracy: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    final_score: int = Field(ge=1, le=5)
    reasoning: str
```

强制 JSON 输出 → 可批量处理、可追踪每维。

### 5. Multi-Judge Ensemble

3-5 个不同 judge 投票 → 收益相对明显但成本上升。
- 适合：高价值评测（模型选型、上线决策）
- 不适合：日常 dev evaluation

### 6. 校准（Calibration）

定期取 50-100 条 judge 评过的样本让人评，比较：
- 一致性（agreement rate）
- 偏置（是否系统性高 / 低）
- 不一致样本分析（看 judge 错在哪里）

> **没校准过的 LLM-Judge 不能信**。这是最常被跳过的步骤。

---

## 五、典型工作流

### 阶段 1：建立黄金集

```
50-200 个 query + 期望特征（不是期望答案，而是评分维度）
```

### 阶段 2：设计 judge prompt

参考前面的 best practices。结构化 + few-shot + 强 rubric。

### 阶段 3：人工 vs LLM 对齐

```
对同一批样本人工评分 + LLM judge 评分 → 算相关度（Spearman ρ / Cohen κ）
ρ > 0.7：可信
ρ 0.5-0.7：需要改 prompt
ρ < 0.5：换 judge 或加更多 example
```

### 阶段 4：自动化评测流水线

```
新版本 prompt / 模型 → 跑黄金集 → LLM judge 评分 → 出报告
↓
和 baseline 对比（pairwise）→ 统计显著性检验
↓
通过 → 上线候选；不通过 → 继续迭代
```

### 阶段 5：在线监控

每天抽 1% 流量做 LLM-judge 评分，监控质量漂移。
→ 详见 [../production/observability.md](../production/observability.md)

---

## 六、典型评分维度

按场景选维度：

### 一般问答
- 准确性 / 完整性 / 相关性 / 简洁性

### RAG 应用
- **Faithfulness**（回答是否忠于检索片段）
- **Answer Relevance**（回答是否切题）
- **Context Precision**（检索片段是否相关）

### 客服 Agent
- 解决问题率 / 礼貌度 / 政策合规 / 升级判断

### 代码生成
- 编译通过 / 测试通过 / 代码风格 / 可读性

### 创意写作
- 创意度 / 连贯性 / 风格匹配 / 语法

> 设计维度时**让每维独立**——避免"准确"和"完整"含义重叠。

---

## 七、评测工具

| 工具 | 长处 |
|---|---|
| **RAGAS** | RAG 专用、内置 faithfulness / context precision 等 |
| **TruLens** | 可观测 + eval 一体 |
| **DeepEval** | pytest 风格、CI 集成友好 |
| **promptfoo** | YAML 配置 + CLI 友好 |
| **Phoenix（Arize）** | 在线监控 + 离线 eval |
| **MT-Bench** | 业界标准 multi-turn 对话基准 |
| **lm-evaluation-harness** | 学术基准全集 |

代码示例（DeepEval）：

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval

g_eval = GEval(
    name="Correctness",
    criteria="判断 actual_output 是否正确回答了 input",
    evaluation_params=["input", "actual_output"],
    threshold=0.7
)

test_case = LLMTestCase(
    input="法国首都是？",
    actual_output="巴黎",
)

assert_test(test_case, [g_eval])
```

---

## 八、几个反直觉的发现

### 1. "更贵的 judge 不一定更好"
- GPT-4 在某些任务上不如专门微调的小模型
- 经验：**领域适配 > 通用强大**

### 2. "判断比生成更难"
- 让 LLM 评估"哪个推理更好"经常错；让它"自己重做一次"反而更稳
- 含义：高难度判断不要单押 LLM-Judge

### 3. "Pairwise 比 pointwise 准很多"
- 但 pairwise 没法跨独立批次比较
- 解法：固定 baseline 做 pairwise

### 4. "LLM judge 的'置信度'不可靠"
- judge 说"我 95% 确定"≠ 真的 95%
- 不要依赖 judge 自报置信度

### 5. "评测会主导优化方向"
- LLM 应用 = 你优化什么就得到什么
- **评测维度设计 = 产品方向选择**

---

## 九、Checklist

```
□ 1. 我的 judge prompt 有清晰的 rubric 吗？
□ 2. 用了 pairwise 还是 pointwise？为什么？
□ 3. judge 模型比被评模型强一档吗？
□ 4. position bias 做了 swap 控制吗？
□ 5. judge 评分和人工评分做过相关度校准吗？
□ 6. 黄金集多大？多久 refresh 一次？
□ 7. 在线监控有 LLM-judge 抽样吗？
□ 8. 多 judge ensemble 在关键决策上用了吗？
□ 9. 评测维度设计是否真正反映"产品好不好"，不是"prompt 好看不好看"？
```

---

## 十、扩展阅读

- 相关：[../production/observability.md](../production/observability.md)、[../rag/retrieval-basics.md](../rag/retrieval-basics.md)
- Zheng et al. (2023) — *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*（**必读基础论文**）
- Wang et al. (2023) — *Large Language Models are not Fair Evaluators*（位置偏置研究）
- Liu et al. (2023) — *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment*
- Zheng et al. — *Chatbot Arena*（pairwise 大规模实战）
- RAGAS 论文（Es et al., 2023）
- Anthropic / OpenAI 关于评测的官方博客

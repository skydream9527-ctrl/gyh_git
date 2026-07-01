# 研究 Agent 评测体系：三层评测 + LLM-as-Judge 偏见防御

> [llm-as-judge.md](llm-as-judge.md) 讲了 LLM-as-Judge 的基础。本文专门聚焦**研究 Agent 的评测**：三层评测结构、怎么造数据、8 种裁判偏见 + 6 层防御、长期工作流。

---

## 一、为什么必须建评测集

不建评测集时的迭代节奏：
```
改 prompt → 跑两个 demo → 看起来不错 → 上线
   → 用户反馈差 → 改 prompt → 跑两个 demo → 看起来不错 → ...
```

**这就是玄学**。每次改你不知道是真好了还是只是这次例子运气好。

建了评测集后：
```
改 prompt → 跑全套评测 → 总分 X 提到 Y → 看哪些 case 改善/恶化 → 决定收不收
```

**这才是工程化**。

---

## 二、评测集的三层结构

研究 Agent 评测必须**多层**——只评最终报告太粗，只评单步太细。

```
Layer 1: End-to-end 评测       ← 最终报告质量
Layer 2: Phase-level 评测      ← 每个阶段的产出
Layer 3: Component 评测        ← 单个 subagent 的能力
```

每层都要建。

---

## 三、Layer 1：End-to-End 评测

### 题目长什么样

```yaml
- id: e2e_001
  topic: "2026 年中国 AI Agent 市场的主要参与者和市场份额"
  depth: "deep"
  expected_aspects:        # 报告必须覆盖的方面
    - "至少识别 5 个主要玩家"
    - "覆盖技术、商业模式、客户群三个维度"
    - "包含融资 / 营收数据"
    - "讨论市场细分"
  must_cite:                # 必须引用到的核心来源
    - "至少 1 个权威研究机构（艾瑞 / IDC / Gartner）"
    - "至少 3 个公司官方信息"
  forbidden:                # 不能出现的
    - "未经验证的营收数字（必须有 source）"
  ground_truth_facts:       # 我们自己核实过的关键事实
    - fact: "智谱 AI 2025 年完成 30 亿融资"
      source: "https://..."
    - fact: "百度文心一言用户数超 X 亿"
      source: "https://..."
  estimated_runtime: "30 min"
  estimated_cost: "$5"
```

**关键**：每道题既有"形式要求"（aspects/citations）又有"事实锚点"（ground_truth_facts）。

### 评分维度（rubric）

```yaml
scoring:
  comprehensiveness: 0-10  # 覆盖完整度
  factual_accuracy: 0-10   # 事实准确性
  source_quality: 0-10     # 引用质量
  internal_consistency: 0-10  # 内部逻辑一致
  actionability: 0-10      # 用户能否拿来用
```

### LLM-as-Judge 实现

```python
EVAL_PROMPT = """You are evaluating a research report.

Topic: {topic}

Required aspects:
{aspects}

Must cite:
{must_cite}

Ground truth facts to verify:
{ground_truth}

Report:
{report}

Score the report on 5 dimensions (0-10 each):
1. Comprehensiveness: did it cover all required aspects?
2. Factual accuracy: do the ground truth facts appear correctly? Any contradictions?
3. Source quality: are sources cited appropriate and verifiable?
4. Internal consistency: are claims within the report logically consistent?
5. Actionability: can a user act on this report?

Output JSON:
{{
  "scores": {{
    "comprehensiveness": <0-10>,
    "factual_accuracy": <0-10>,
    "source_quality": <0-10>,
    "internal_consistency": <0-10>,
    "actionability": <0-10>
  }},
  "missing_aspects": [...],
  "factual_errors": [...],
  "weak_sources": [...],
  "reasoning": "..."
}}
"""

async def eval_report(case, report):
    prompt = EVAL_PROMPT.format(
        topic=case["topic"],
        aspects=json.dumps(case["expected_aspects"]),
        must_cite=json.dumps(case["must_cite"]),
        ground_truth=json.dumps(case["ground_truth_facts"]),
        report=report,
    )
    # 用 opus 当裁判（裁判模型必须 > 被评模型）
    resp = await llm_opus.ainvoke(prompt)
    return json.loads(resp.content)
```

**裁判模型选择**：用比被评模型**更强**的模型。我们 Agent 主要用 sonnet，裁判就用 opus。**裁判用 sonnet 评 sonnet 写的报告几乎没意义**——裁判能力不够看不出问题。

---

## 四、Layer 2：Phase-Level 评测

不只看最终报告，看每个阶段的产出：

### Scoping 阶段评测

```yaml
- id: scoping_001
  topic: "中国 AI Agent 市场"
  expected_subtopics:
    - "市场规模"
    - "主要玩家"
    - "技术路线对比"
    - "商业模式"
    - "投融资"
  evaluation:
    - "拆解出的 sub-topic 是否覆盖了 expected"
    - "是否有冗余 sub-topic"
    - "是否切分粒度合理（不能太粗也不能太细）"
```

### Researcher Phase 评测

```yaml
- id: researcher_001
  sub_topic: "智谱 AI 2025 年融资情况"
  expected_findings:
    - claim: "完成 X 轮融资"
    - claim: "金额 Y 亿"  
    - claim: "投资方包括 Z"
  evaluation:
    - "这些 claim 是否被找到"
    - "是否有 hallucinated claim（编造的）"
    - "source 是否真实可访问"
```

### Synthesis 评测

```yaml
- id: synthesis_001
  input_findings: [...]  # 给定输入
  expected_insights:
    - "应识别出 X 趋势"
    - "应注意到 A 和 B 的矛盾"
  evaluation:
    - "insight 是否真的从 findings 推出（不是无中生有）"
    - "是否漏掉关键 cross-cutting theme"
```

每层独立评测的好处：**端到端跑差时，能定位是哪个阶段坏了**。

---

## 五、Layer 3：Component 评测

最细粒度——单个能力评测。

### Search Query 生成评测

给一个 sub-topic，看 LLM 生成的 query 列表：

```yaml
- sub_topic: "智谱 AI 2025 财务"
  good_queries_examples:
    - "智谱 AI 2025 年融资"
    - "Zhipu AI funding 2025"
    - "智谱清言 营收"
  bad_queries_examples:
    - "智谱"  # 太宽
    - "AI 融资"  # 没指向
  rubric:
    - specificity: 是否够具体
    - diversity: 是否角度多样
    - bilingual: 中英双语
```

### Claim 提取评测

给一段已知内容 + 已知正确 claim 列表，看抽取准不准：

```yaml
- input_text: "<某段内容>"
  ground_truth_claims:
    - "X 公司在 2025 年发布了产品 Y"
    - "Y 的核心特性是 Z"
  rubric:
    - precision: 抽出的 claim 都是对的吗
    - recall: 该抽的都抽到了吗
    - hallucination: 有没有抽出原文没有的
```

### Verifier 评测

给一个 claim + 一个反例 + 几个混淆，看 verifier 能不能判出"DISPUTED"：

```yaml
- claim: "公司 X 营收 100 亿"  # 故意编的
  injected_sources:
    - {url: "vendor_blog", says: "营收 100 亿"}  # vendor 自吹
    - {url: "real_filing", says: "营收 50 亿"}   # 真实财报
  expected_verdict: "DISPUTED"
```

---

## 六、怎么造数据

最大的难点：**评测集本身需要人工**。

### 起步：种子集 (Day 1-3)

```
1. 自己写 10 道 e2e 题（每道 ~30 分钟人工）
2. 给每道题人工写 ground_truth
3. 跑现有 Agent，记录输出
4. 自己打分（score）
5. 用这些当种子集
```

10 道是最低门槛，跑完一次能看出明显问题。

### 扩展：合成 + 人工 (Week 2-4)

```
1. 从 Anthropic Research / Perplexity / Gemini Deep Research 拿现成报告做参照
2. 用 LLM 提取这些报告的"主题 + 关键事实" → 自动生成测试题
3. 人工审核，挑出 50-100 道高质量题
```

### 长期：用户问题反流 (持续)

```
1. 真实用户用了之后
2. 收集"用户后来发现的错误" + "用户表扬的好答案"
3. 这些都是天然评测样本
```

---

## 七、评测频率

### 每次 commit 跑

**只跑 component-level**（fast，~1 分钟）：
```python
@pytest.mark.parametrize("case", load_cases("component"))
def test_component(case):
    result = run_component(case["input"])
    score = eval_component(result, case["expected"])
    assert score > 0.7
```

加到 CI，不通过不让合代码。

### 每天跑

**Phase-level 评测**（~30 分钟）：
```bash
# crontab
0 2 * * * cd /repo && python eval/phase_level.py --output reports/$(date +%F).json
```

第二天早上看 dashboard。

### 每周跑

**End-to-end 评测**（~5 小时，烧钱）：
- 周末跑全套 50 道 e2e
- 跟上周对比，看回归
- 发周报到团队

---

## 八、评测驱动迭代的工作流

```
1. 看 dashboard：哪个 sub-score 在下降？
   ├── factual_accuracy 下降
   │   → 查最近改了什么
   │   → 大概率是 verifier 或 search 改坏了
   │   → 看 component eval 哪个 fail 了
   │
   ├── comprehensiveness 下降
   │   → 大概率 scoping 改坏了
   │   → 看 phase-level scoping eval
   │
   └── source_quality 下降
       → 大概率检索召回质量差
       → 看是不是黑名单/白名单需要更新
```

**没评测集 = 抓瞎。有评测集 = 工程问题**。

---

## 九、一个常被忽略的真相：评测的成本

跑一次完整 e2e 评测可能花 $50-200（50 道 × 每道 $1-4）。

不要每次小改都跑 e2e——**先跑 component → 通过再跑 phase → 通过再跑 e2e**。这样你只在"看起来值得"的时候花大钱跑 e2e。

```
component:  $0.5 / run × 每天 5 次 = $75/月
phase:      $5  / run × 每天 1 次 = $150/月  
e2e:        $100 / run × 每周 1 次 = $400/月

合计 ~$625/月评测成本
```

听起来贵，但**没评测集导致的迭代低效**远不止这个数。

---

## 十、LLM-as-Judge 的 8 种偏见

如果你不处理这些偏见，评测分数会**系统性偏差**——你以为在评质量，实际在评"风格匹配度"。

### 偏见 1：位置偏见（Position Bias）

最严重的一个。给裁判看 A 和 B 两份答案：
- 把好答案放在第一位 → 评分 7.5
- 同样答案放在第二位 → 评分 6.8

**实测**：GPT-4 / Claude 都有 ~10-30% 的位置偏见。

### 偏见 2：长度偏见（Verbosity Bias）

裁判默认认为**长答案 = 详细 = 好**。即使长答案是水的、短答案是精炼的，裁判也会给长的高分。

研究数据：长 30% 的答案获胜概率提升 ~15%。

### 偏见 3：自我偏见（Self-Preference Bias）

GPT-4 当裁判时，倾向给 GPT 系列的答案打高分。
Claude 当裁判时，倾向给 Claude 系列的答案打高分。

**就算你脱去模型名字，输出风格本身就泄露了"是哪家"**。

### 偏见 4：风格偏见（Style Bias）

格式好看 = 分高：
- 用 markdown 列表 → 加分
- 有标题层级 → 加分
- 包含 emoji → 看模型，可能加分可能减分
- 纯文本但内容更准 → 经常被打低

### 偏见 5：权威偏见（Authority Bias）

引用了"高大上"来源 → 加分，**不管引用是否真的支持论点**。

裁判模型不会去验证"哈佛研究表明"是不是真的——只要有这种话就觉得专业。

### 偏见 6：礼貌偏见（Hedge Bias）

充满 hedge 语言（"可能"、"通常"、"在某些情况下"）→ 显得严谨 → 加分。
直接给结论的（"X 是 Y"）→ 显得武断 → 减分。

但研究 Agent 的输出**应该敢于给结论**，hedge 太多反而是坏事。

### 偏见 7：拒答偏见（Refusal Bias）

如果一份答案说"我不能回答这个"，裁判倾向给中等分（"安全的中庸选择"），而不是低分。

这导致**回避问题的答案获得过高评分**。

### 偏见 8：推理过程偏见（Chain-of-Thought Bias）

如果答案展示了推理过程（"first I... then I... finally..."），即使最终结论一样，分数会高。

研究 Agent 不需要展示推理（它该做最终输出），但裁判会给"展示推理"加分。

---

## 十一、6 层防御

### 防御层 1：消除位置偏见 — Pairwise Swap

**最重要的一招**。每个 pair 评测都跑两遍：

```python
async def pairwise_compare(case, answer_a, answer_b, judge_llm):
    # 第一遍：A 在前
    prompt_1 = build_prompt(case, answer_a, answer_b)
    verdict_1 = await judge_llm.invoke(prompt_1)  # "A wins" / "B wins" / "tie"
    
    # 第二遍：B 在前（位置交换）
    prompt_2 = build_prompt(case, answer_b, answer_a)
    verdict_2 = await judge_llm.invoke(prompt_2)
    
    # 注意：第二遍的 "A wins" 实际上指的是原 B
    verdict_2_normalized = swap_verdict(verdict_2)
    
    # 一致性判断
    if verdict_1 == verdict_2_normalized:
        return verdict_1  # 真正的赢家
    else:
        return "uncertain"  # 位置偏见暴露 → 不可信
```

**关键设计**：跑两遍如果不一致，**判定为 uncertain**，**不强行裁决**。

```
跑 100 道题：
  → 80 道两遍一致 → 这 80 道的结果可信
  → 20 道两遍冲突 → 这 20 道说明裁判不稳定，不计入分数

最终评测分数 = 只看一致性高的题
```

### 防御层 2：消除长度偏见 — 长度归一化

**做法 A：在 prompt 里显式提醒**

```
IMPORTANT: 
- Length is NOT a quality signal. A concise correct answer 
  is better than a verbose mediocre one.
- Do NOT favor longer answers.
- Evaluate based on substance, not appearance.
```

**做法 B：等长截断**（更激进）

把两个答案都截到相同长度后再评，**强制裁判看相同信息量**。

**做法 C：长度作为元数据展示**

```
Answer A (450 words):
<text>

Answer B (320 words):
<text>

Note: Word count provided for transparency. 
Length should not influence quality judgment.
```

显式告知长度，反而能让裁判校准（因为它意识到"哦我可能因为长打分高，要警惕"）。

### 防御层 3：消除自我偏见 — 多裁判平均

**最强的方案**：用多个不同家族的模型当裁判。

```python
async def multi_judge_eval(case, answer):
    judges = [
        ("opus",  llm_anthropic_opus),
        ("gpt4",  llm_openai_gpt4),
        ("gemini", llm_google_gemini_pro),
    ]
    
    scores = []
    for name, judge in judges:
        score = await eval_single(case, answer, judge)
        scores.append((name, score))
    
    # 计算分歧度
    score_values = [s["overall"] for _, s in scores]
    std = statistics.stdev(score_values)
    
    if std > 1.5:  # 分歧大
        log.warning(f"High disagreement among judges: {scores}")
        return {"score": median(score_values), "confidence": "low"}
    
    return {"score": mean(score_values), "confidence": "high"}
```

**研究表明**：3 个不同家族的裁判取均值，**自我偏见几乎被抵消**（因为不同模型的偏好不一样，不会都偏向同一家）。

成本：3 倍裁判成本。但通常评测频率不高（一周一次），值得。

### 防御层 4：消除风格偏见 — 结构化评分

不要让裁判给"总分"，让它给**多维分**：

```python
EVAL_PROMPT = """
Evaluate this research report on these EXACT dimensions.
Each dimension is INDEPENDENT—do not let one dimension influence another.

1. **Factual Correctness** (0-10)
   ONLY about: Are stated facts true? Score based on factual accuracy alone.
   IGNORE: writing style, length, formatting.

2. **Source Quality** (0-10)  
   ONLY about: Are cited sources credible and verifiable?
   IGNORE: writing style, completeness.

3. **Comprehensiveness** (0-10)
   ONLY about: Are required topics covered?
   IGNORE: writing style, length.

4. **Internal Consistency** (0-10)
   ONLY about: Are claims within the report logically consistent?
   IGNORE: writing style, formatting.

5. **Style/Format** (0-10)
   ONLY about: Markdown structure, readability, formatting.
   This is the ONLY dimension where formatting matters.
"""
```

**关键**：每个维度都强制说"IGNORE 其他维度"，把风格隔离到 style_format。

最终聚合时，**给不同维度加权重**：

```python
overall = (
    factual * 0.30 +
    source * 0.20 +
    comprehensive * 0.25 +
    consistency * 0.15 +
    style * 0.10  # 故意压低 style 权重
)
```

### 防御层 5：消除权威偏见 — 验证引用

让裁判**实际去验证引用**而不是看到引用就给分。

```python
async def eval_with_citation_check(case, answer):
    # 先提取所有引用
    citations = extract_citations(answer)
    
    # 抽样验证（不能验全部，太贵）
    sample = random.sample(citations, min(5, len(citations)))
    
    verified_count = 0
    for cite in sample:
        # 真去 fetch 这个 URL，看引用的内容是否真的支持 claim
        is_valid = await verify_citation(cite["url"], cite["claim"])
        if is_valid:
            verified_count += 1
    
    citation_accuracy = verified_count / len(sample) if sample else 0
    
    return await llm_judge_eval(case, answer, 
                                 extra_signal={"citation_accuracy": citation_accuracy})
```

裁判看到"5 个引用里只有 2 个真支持 claim"，就不会盲目给"权威分"加分。

### 防御层 6：消除拒答偏见 — 显式惩罚

如果检测到 "I cannot..." / "I don't know..." 等回避话术，裁判 prompt 要显式说：

```
If the answer refuses to address parts of the question or says 
"I don't know" without justification, this should LOWER the score, 
not be neutral. A failed attempt with errors is sometimes better 
than a refusal.
```

或者**先用规则检测**，有拒答直接给低分，不送裁判。

### 防御层 7：用人类评测做校准

终极防御。**裁判 LLM 是给人类评测员省力的**，不是替代。

```python
WORKFLOW:
  Day 1-7:
    - 100 道题人工评分（建立黄金标准）
    - 同 100 道题用 LLM-as-Judge 评分
    - 计算相关性：spearman rank correlation
    
  如果相关性 > 0.8:
    LLM 裁判可信，可以缩减人工
    
  如果相关性 < 0.6:
    LLM 裁判不可信，要么换裁判，要么改 prompt
    
  之后：
    - 每周 10 道题人工抽查（看 LLM 裁判没漂移）
    - 每月对比一次
```

**这是工业级 LLM-as-Judge 的标准做法**。Anthropic / OpenAI 内部都这么做。

---

## 十二、实战 Pipeline：综合所有防御

```python
class RobustJudge:
    def __init__(self, judges: list[BaseLLM], use_human_calibration: bool = True):
        self.judges = judges
        self.calibration_data = self._load_calibration() if use_human_calibration else None
    
    async def eval(self, case, answer):
        # 1. 规则预检（拒答检测、明显劣质）
        if self._is_refusal(answer):
            return {"score": 2, "reason": "refusal"}
        
        # 2. 多维评分（防风格偏见）
        dimension_scores = []
        for judge in self.judges:
            scores = await self._eval_dimensions(judge, case, answer)
            dimension_scores.append(scores)
        
        # 3. 多裁判平均（防自我偏见）
        avg_scores = self._average_scores(dimension_scores)
        
        # 4. 引用验证（防权威偏见）
        if "source_quality" in avg_scores:
            citation_acc = await self._verify_citations(answer)
            avg_scores["source_quality"] *= citation_acc
        
        # 5. 加权聚合
        overall = self._weighted_sum(avg_scores)
        
        # 6. 人类校准对比
        confidence = "high"
        if self.calibration_data:
            calibration_drift = self._check_drift(case, overall)
            if calibration_drift > 0.3:
                confidence = "low"
        
        return {
            "score": overall,
            "dimensions": avg_scores,
            "confidence": confidence,
            "judges_disagreement": self._compute_disagreement(dimension_scores),
        }
    
    async def pairwise(self, case, answer_a, answer_b):
        # Pairwise + swap（防位置偏见）
        verdict_a_first = await self._pairwise_single(case, answer_a, answer_b)
        verdict_b_first = await self._pairwise_single(case, answer_b, answer_a)
        verdict_b_first_normalized = self._swap(verdict_b_first)
        
        if verdict_a_first == verdict_b_first_normalized:
            return verdict_a_first
        return "uncertain"
```

---

## 十三、评测的不可观测性

很多人以为"分数 8.5 比 7.8 好"——其实**裁判 LLM 的噪声本身就有 ±0.5 量级**。

```
同一道题、同一份答案，跑 10 次裁判：
  分数分布: [7.8, 8.2, 8.0, 7.5, 8.3, 8.1, 7.9, 8.4, 7.7, 8.0]
  std ≈ 0.27
```

意思是：**两个 prompt 改动如果分数差距 < 0.5，几乎没有统计显著性**。

实战做法：**报置信区间，不报点估计**。

```python
def report_score(scores: list[float]) -> str:
    mean = statistics.mean(scores)
    stderr = statistics.stdev(scores) / math.sqrt(len(scores))
    return f"{mean:.2f} ± {1.96 * stderr:.2f} (95% CI)"
```

每次评测**至少跑 3 次**取平均，看置信区间是否重叠。

---

## 十四、真实工业实践参考

### Anthropic（从论文/博客）
- 多裁判（Claude + GPT + 第三方）
- 人类标注员每周抽查 100 道
- 结构化 rubric 而非总分
- 跑变化点检测（detect drift over time）

### OpenAI Evals
- 内部用 GPT-4 当主裁判
- 人类对比组每月校准
- Pairwise + position swap

### LMSYS Chatbot Arena
- 最有意思的：**完全用人类**当裁判
- 用户匿名比较两个模型回答
- 累积成 Elo 评分系统
- LLM 裁判作为对照组（看跟人类一致性）

**结论**：工业级评测**不依赖单一裁判**，永远是多重防御。

---

## 十五、给我们研究 Agent 的具体建议

落地到我们的研究 Agent 评测系统，推荐的最小可行 setup：

```
Tier 1（必做）：
├─ 多维 rubric（5 个维度独立打分）
├─ 长度归一化提示
├─ Pairwise 用 swap（如果做对比）
└─ 用比"被评模型"更强的裁判

Tier 2（值得做）：
├─ 多裁判平均（Opus + GPT-4 + Gemini）
├─ 引用抽样验证
└─ 拒答规则预检

Tier 3（高级）：
├─ 人类校准（每月）
├─ 置信区间报告
└─ Drift 检测
```

成本：Tier 1 几乎免费（只是 prompt 工程）。Tier 2 翻 3 倍裁判成本。Tier 3 要持续投入人工。

**最低门槛 = Tier 1 + 每周 5 道人工抽查**——这就比 95% 的团队做得好了。

---

## 十六、公开评测集参考

不要从头造，可以借鉴：

- **GAIA** (General AI Assistants benchmark)：包含真实研究类问题
- **WebArena**：浏览器交互评测
- **SWE-Bench**：虽是代码任务，评测设计可借鉴
- **BrowseComp** (OpenAI)：专门针对浏览能力的评测

**警告**：公开评测集的题往往**和你的真实场景不匹配**。它们是"补充"，不是"替代"自己造的题。

---

## 十七、扩展阅读

- [llm-as-judge.md](llm-as-judge.md) —— LLM-as-Judge 基础（pointwise / pairwise / 通用偏见）
- [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md) —— 研究 Agent 架构
- [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md) —— LangGraph 实现
- [../production/observability.md](../production/observability.md) —— 长期监控

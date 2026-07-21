# 04. 业务侧 Agent 评测落地：从黄金集到在线 A/B

> 公开 benchmark 用来摸"行业脉搏"，但**真正决定上线的永远是业务侧评测体系**。本文给一套可直接抄的落地流水线：黄金集、CI 集成、在线监控、A/B 设计、异常回流。
>
> 阅读完应该能回答："给我 1 周时间，怎么从 0 起步建一套可用的 Agent 评测体系？"

---

## 一、最小可用版（1 周冷启动）

```
Day 1-2  ┌────────────────────────────────────────────────┐
         │ 业务收集 30 道真实场景题（PM + 业务 + 工程一起出）│
         │ → 每题写：input / 期望产出 / 红线 / 关键事实     │
         └────────────────────────────────────────────────┘
Day 3    ┌────────────────────────────────────────────────┐
         │ 写第一版 rule-based eval（5-10 条规则）          │
         │ + LLM-as-Judge prompt（accuracy / completeness）│
         └────────────────────────────────────────────────┘
Day 4    ┌────────────────────────────────────────────────┐
         │ 接入 CI: 每次合 PR 跑一次，结果落库               │
         └────────────────────────────────────────────────┘
Day 5-7  ┌────────────────────────────────────────────────┐
         │ 上线 staging: 5% 流量做 shadow                  │
         │ 监控: 拒收率 / latency / 成本                    │
         │ 失败 case 自动回流到评测集                       │
         └────────────────────────────────────────────────┘
```

> 1 周后你已经有：30 题黄金集 + CI 集成 + 在线监控 + 失败回流。**这比 80% 的团队都好**。

---

## 二、黄金集（Golden Set）的工程化建设

### 2.1 题目分层

```
Tier 1 (Smoke, ~30 题)       每次 PR 必跑，<3 分钟
Tier 2 (Regression, ~200 题) 每周/大改跑，<30 分钟
Tier 3 (Release, ~1000 题)   月度跑，能跑数小时
Tier 4 (Adversarial, 50 题)  红线/边界，每次发布前必过
```

**避免 1 个集合通吃**——开发反馈循环要快，发布前要全。

### 2.2 题目构造的 4 个来源

| 来源 | 占比 | 备注 |
|---|---|---|
| **生产日志采样**（去敏） | 40-50% | 最贴近真实分布 |
| **PM/业务专家造**（含 corner case） | 20-30% | 关键边界 |
| **失败案例反哺** | 20-30% | 不让同一个坑踩两次 |
| **LLM 合成 + 人工审核** | 10% | 补充长尾 |

### 2.3 标注 schema（直接抄）

```yaml
# tests/golden/customer_support/T-CS-001.yaml
id: T-CS-001
category: customer_support
subtype: refund_request
difficulty: medium
source: prod_log_2026_05  # 来源可追溯

# 输入
input:
  user_message: |
    我上周在你们这买的 X 还没发货，订单号 12345，能取消并退款吗？
  context:
    user_tier: vip
    order_id: "12345"

# 期望
expected:
  must_call_tools:
    - name: get_order
      args: { order_id: "12345" }
    - name: refund_order
  must_not_call_tools:
    - name: contact_legal   # 不该升级到这里
  expected_aspects:
    - "确认订单状态"
    - "明确退款流程和时间"
    - "告知 VIP 享受免运费补偿"
  forbidden:
    - "无来源声称'已退款'但未真调 refund"
  max_steps: 6
  max_cost_usd: 0.05

# 红线
safety:
  - "不能透露其他用户订单信息"
  - "不能擅自承诺超过政策的优惠"

# 期望最终回复（可选 reference）
reference_response: |
  好的，我已经为您操作退款，订单 #12345...

# 评分权重
scoring_weights:
  task_success: 0.4
  tool_correctness: 0.3
  efficiency: 0.1
  safety: 0.2
```

### 2.4 维护机制

```
每周 :
   - 失败案例自动入库（人工 review 后）
   - 已修复的 bug 转为 regression case

每月 :
   - 抽样人工 review（避免黄金集本身有错）
   - 看分布是否还代表生产流量（漂移检查）

每季 :
   - 全量 review，淘汰过期题（产品功能改了）
   - 引入新场景题
```

---

## 三、评分管线设计

### 3.1 多层评分组合

```python
def evaluate_one_case(case, agent_output):
    score = {}

    # Layer 1: Rule-based (cheap)
    score["schema_valid"]    = check_schema(agent_output)
    score["tools_correct"]   = check_tools(case.expected, agent_output.trajectory)
    score["no_red_flags"]    = not violates_red_lines(agent_output, case.safety)
    score["step_count"]      = len(agent_output.trajectory)
    score["cost_usd"]        = compute_cost(agent_output)

    # 早期短路: 安全红线挂 → 直接判 0
    if not score["no_red_flags"]:
        return {**score, "final": 0, "reason": "safety_violation"}

    # Layer 2: LLM-as-Judge (expensive)
    judge_score = llm_judge(
        question=case.input,
        reference=case.reference_response,
        output=agent_output.final_response,
        rubric=case.expected.expected_aspects,
    )
    score.update(judge_score)

    # 加权汇总
    score["final"] = weighted_sum(score, case.scoring_weights)
    return score
```

### 3.2 LLM Judge 实战配置

```python
JUDGE_PROMPT = """
你是评审。请给以下答案在 4 个维度独立打分（1-5）：

【答案】
{output}

【参考要点（必须覆盖）】
{aspects}

【参考答案（仅供参考，不必完全一致）】
{reference}

【打分维度】
- accuracy: 关键事实是否准确
- coverage: 是否覆盖参考要点
- citation: 引用是否真实、对应
- clarity: 表达是否清晰

【约束】
- 每个维度独立打分
- 长度不影响打分
- 必须输出 JSON

输出: {"accuracy":int, "coverage":int, "citation":int, "clarity":int, "reasons":[...]}
"""

# 用 2 个不同 family 的 judge 投票
judges = ["claude-4-sonnet", "gpt-4o"]
scores = [llm_call(j, JUDGE_PROMPT.format(...)) for j in judges]
final = average(scores)
```

### 3.3 输出报告

```
┌────────────────────────────────────────────────────────────┐
│ Eval Run #2026-06-04T10:23  PR #1234  branch: feat/xxx     │
│ Model: claude-4-sonnet      Agent: support-agent v0.7      │
│ Set: golden_v3 (200 cases)                                 │
├────────────────────────────────────────────────────────────┤
│ Overall:                                                   │
│   task_success      87.5%   (+2.5% vs main)                │
│   tool_correctness  92.0%   (-0.5%)                        │
│   safety_violation  0       (0)                            │
│   avg_steps         4.2     (+0.3)                         │
│   avg_cost          $0.041  (+$0.003)                      │
│                                                            │
│ By Category:                                               │
│   refund        90% ↑    cancel       85% ↓                │
│   tracking      88% ↑    return       80% =                │
│                                                            │
│ Regressions (failed but passed on main):                   │
│   T-CS-042  分类错误: 应该调 cancel_order 但调了 refund      │
│   T-CS-091  超出 max_steps                                 │
│                                                            │
│ Wins (failed on main, passing now):                        │
│   T-CS-018, T-CS-073, T-CS-104                             │
└────────────────────────────────────────────────────────────┘
```

---

## 四、CI / CD 集成

### 4.1 流水线策略

```
PR 提交        ┌────────────┐
   ─────────→ │ Smoke (30) │ <3 min  → 必须 pass 才能合入
              └────────────┘
                   │
夜间 main      ┌────────────┐
   ─────────→ │ Regression │ ~30 min  → 失败发飞书/Slack
              │  (200)     │
              └────────────┘
                   │
发布前         ┌────────────┐
   ─────────→ │ Release    │ ~3 hr    → 配合 Adversarial 必须过
              │  (1000)    │
              └────────────┘
                   │
模型版本       ┌────────────┐
   ─────────→ │ 全量 Bench │ 半天    → 选型决策
              └────────────┘
```

### 4.2 Gate 设置（直接抄）

```yaml
# .github/workflows/eval.yml 片段
gates:
  must_pass:
    - safety_violation == 0          # 任何红线挂全失败
    - schema_valid_rate >= 0.99
  warn_only:
    - task_success_drop >= 3%        # 比 main 跌 3% 触发 review
    - cost_increase >= 20%
    - latency_p95_increase >= 30%
```

### 4.3 实操工具栈

| 工具 | 角色 |
|---|---|
| **PromptFoo / DeepEval** | 评测脚本核心 |
| **GitHub Actions / GitLab CI** | 触发器 |
| **MLflow / Wandb** | 跑分历史看板 |
| **Langfuse / LangSmith** | trace 抓取（可视化失败 case） |
| **自建 Postgres + Grafana** | 长期趋势 + 告警 |

---

## 五、在线监控（Layer 4）

### 5.1 关键指标分级

```
红色（必报警）:
   - 安全/合规 violation > 0
   - p95 latency > SLA
   - 错误率 > 1%
   - 单任务成本超预算

黄色（每天看）:
   - 拒收率（用户重试/编辑率）
   - 接管率（人工介入比）
   - CSAT 跌
   - 工具调用失败率

绿色（每周看）:
   - 任务平均步数趋势
   - 长尾用户分布
   - 不同模型版本占比
```

### 5.2 失败回流自动化

```
生产 trace                       ┌──────────────────┐
   ─────────→  trace store ────→ │ 自动分类失败原因  │
                                  │                  │
                                  │ - 工具调用错      │
                                  │ - 输出格式错      │
                                  │ - 用户拒收        │
                                  │ - 主动接管        │
                                  └──────────────────┘
                                          │
                                          ▼
                                  ┌──────────────────┐
                                  │ 周会 review 池    │
                                  │ 人工标→入黄金集    │
                                  └──────────────────┘
                                          │
                                          ▼
                                    下次评测必跑
```

### 5.3 Trace 抓取的 5 个必备字段

```json
{
  "trace_id": "...",
  "user_id_hash": "...",
  "input": "用户原文（去敏）",
  "model_version": "claude-4-sonnet@2026-05-12",
  "agent_version": "v0.7.3",
  "trajectory": [
    {"step": 1, "type": "thinking", "content": "..."},
    {"step": 2, "type": "tool_call", "name": "get_order", "args": {...}, "result": {...}},
    ...
  ],
  "final_response": "...",
  "metrics": {
    "latency_ms": 3210,
    "tokens_in": 1800,
    "tokens_out": 420,
    "cost_usd": 0.042,
    "steps": 4
  },
  "feedback": {
    "user_rating": 4,    # 可选
    "user_edited": false,
    "user_retried": false
  }
}
```

---

## 六、A/B 实验设计

### 6.1 离线 → 在线衔接

```
新版本 v2 离线评测
         │
         ▼
   ┌──────────────────┐
   │ 离线评测 +X% ?   │
   └────────┬─────────┘
            │
   X 显著负? → 不上 A/B（先回炉）
   X = 0   ?  → 不一定上（除非省成本）
   X 显著正? → 进入 A/B
            │
            ▼
   ┌──────────────────┐
   │ Canary 1-5% 流量 │ 24-72h
   └────────┬─────────┘
            │
   红色指标 OK?
            │
   ┌─────── 否 ───────┐
   │ 立刻回滚 + 复盘   │
   └──────────────────┘
            │ 是
            ▼
   ┌──────────────────┐
   │ A/B 50/50         │ 1-2 周
   └────────┬─────────┘
            │
   关键业务指标显著 + 无副作用?
            │
            ▼
        全量上线
```

### 6.2 A/B 设计要点
- **指标分级**：主指标（任务成功率）+ 护栏指标（成本、延迟、拒收率、安全）
- **样本量**：用 power calculation，常见 1-2 周流量
- **分流维度**：按 user_id 哈希，确保同用户始终看同一版本
- **回滚预案**：触发条件、操作手册、回滚 SLA

> 详细：[../../ab-testing/](../../ab-testing/)。

---

## 七、Agent 评测特有的 5 个工程坑

### 坑 1：Trace 不全
评测只看 final answer，但答错了不知道是哪一步坏。

**对策**：每个 step 都落 trace + step-level eval。

### 坑 2：环境不一致
Eval 时 mock 工具，生产真工具。

**对策**：
- 至少跑一份"真实工具"评测（成本高但必要）
- Mock 工具加入故意失败 5%-10%

### 坑 3：评测 Agent 自身在迭代
Agent 框架变了，老 case 跑不了。

**对策**：
- Agent 版本和评测集版本绑定记录
- 每次大改前先把当前评测结果 snapshot

### 坑 4：LLM judge 跨版本漂移
GPT-4o 小版本一更新，judge 分数集体偏移。

**对策**：
- judge 模型 pin 死（甚至自部署）
- 每月跑一次"校准题"，发现漂移就告警

### 坑 5：用户行为指标的归因
拒收率上升，是新版本变差了，还是题目分布变了？

**对策**：
- 流量分组保留稳定的"对照组"
- 长期 baseline 持续监控

---

## 八、模板文件清单（建议放仓库的位置）

```
your-agent-repo/
├── tests/
│   ├── golden/
│   │   ├── smoke/         # 30 题
│   │   ├── regression/    # 200 题
│   │   ├── release/       # 1000 题
│   │   └── adversarial/   # 50 题
│   └── eval/
│       ├── runners/       # 各类 evaluator
│       ├── judges/        # LLM judge prompts
│       └── reports/       # 报告模板
├── eval_pipeline.py        # 主入口
└── .github/workflows/
    ├── eval-smoke.yml
    ├── eval-nightly.yml
    └── eval-release.yml
```

---

## 九、给 Tech Lead 的 7 条经验

1. **评测投入是迭代速度的乘数** —— 这事不做，所有"模型升级"都没法量化。
2. **从小开始**：30 题黄金集 + 5 条规则 + 1 个 LLM judge prompt → 1 周可用。
3. **失败回流自动化** —— 这是评测集长大的核心机制。
4. **Trace 是评测的一等公民** —— 没有 trace 等于盲调。
5. **LLM judge 必须先校准**（与人工标注 Kappa > 0.6）。
6. **永远配在线监控**：离线 ≈ 60% 信心，离线 + 在线 ≈ 95%。
7. **保留可解释报告**：评测看板要能"点进 case 看 trace"，黑盒分数没人信。

---

## 十、一句话总结

> 评测不是"评测团队"的事——是 **PM、业务、工程、Agent owner、QA 一起的工程纪律**。
>
> 哪怕只投 1 周建最简版本，半年后回看，团队的 Agent 迭代速度会被这一周的投资 10 倍化。

---

至此，agent-evaluation/ 目录全部完成。返回 [README.md](README.md) 总览。

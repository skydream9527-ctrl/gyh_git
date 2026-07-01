# LLM/Agent 可观测性

> 没有 observability 的 LLM 应用 = 在黑屋子里调一台盲盒机器。本文讲清 LLM 应用区别于传统系统的观测维度、主流工具、最小落地路径。

---

## 一、为什么 LLM 应用的可观测性"不一样"

传统软件可观测三件套：metrics（指标）、logs（日志）、traces（追踪）。LLM 应用全部继承，**额外**增加：

| LLM 应用特有维度 | 为什么重要 |
|---|---|
| **每次 LLM 调用的 prompt + response** | 这是行为来源，不能只看输入输出 |
| **Token 用量 + 成本** | 直接对应账单，不是事后体检项 |
| **多步 Agent 的完整 trace** | 一个 Agent 跑 10 步要能看到每步的 thought / action / observation |
| **质量评分** | LLM 输出"对错"通常没有客观判定，需要主观或半自动评估 |
| **用户反馈** | 👍 / 👎 反馈是质量信号 |
| **检索召回内容**（RAG） | 召回不对，回答必错 |

**LLM 工程的特殊困境**：
- 同一个 prompt 调一万次 → 一万种结果
- 没有传统的"测试金字塔"
- 上线后才发现 prompt 漂移、模型升级、工具失败 → 一切都要在生产观测

---

## 二、最小可观测三件套（必须有）

### 1. Trace（每次调用的完整记录）

记录字段：

```json
{
  "trace_id": "...",
  "parent_id": "...",
  "timestamp": "...",
  "model": "claude-opus-4-7",
  "messages": [...],         // 完整 prompt
  "response": "...",         // 完整输出
  "tool_calls": [...],
  "tokens": {"input": 1234, "output": 567, "cached": 1000},
  "cost_usd": 0.045,
  "latency_ms": 2340,
  "user_id": "...",
  "session_id": "...",
  "feature": "search_agent",  // 业务标签
  "metadata": {...}
}
```

**关键**：
- 完整 prompt + response（不只是 hash）→ 才能复现
- 用 `feature` 标签区分不同业务流量
- 用 `session_id` 串起多步 Agent

### 2. Metrics（聚合指标）

按时间窗口（5min / 1h / 1d）聚合：

```
延迟：    p50 / p95 / p99 of TTFT、total_latency
成本：    每天 token 用量 + USD 总额、按 feature 分布
质量：    错误率（API 4xx/5xx）、超时率、重试率
用量：    QPS、每用户调用次数
工具：    每个工具的成功率、平均参数错误率
RAG：     召回为空率、召回 top-K 平均相关度
```

### 3. Alerts（告警）

至少要监控的告警：

```
□ p99 延迟 > 阈值
□ 错误率 > 1%
□ 单日成本 > 预算 × 1.5
□ 模型 API quota / rate limit 接近
□ Tool failure rate > 5%
□ 用户点踩率突增
```

---

## 三、主流工具

### 商用 / SaaS

| 工具 | 主擅长 | 成本 |
|---|---|---|
| **LangSmith**（LangChain Inc.） | 与 LangChain/LangGraph 深度集成、tracing 最完整 | 免费档 + 付费 |
| **Langfuse**（开源 + SaaS） | 开源版可自托管、UI 友好 | 免费档 + 付费 |
| **Helicone** | 透明代理（一行配置） | 有免费额度 |
| **Phoenix（Arize）** | 评测 + 监控、开源 | 免费 |
| **Datadog LLM Observability** | 企业级、和现有 APM 集成 | 高 |
| **Weights & Biases (W&B)** | 训练 + 实验管理 | 中 |

### 开源 / 自建

```
最小路径：
  把 trace 写进 Postgres / ClickHouse + Grafana 看板

中等路径：
  Langfuse 自托管（Docker compose 一键起）

完整路径：
  Phoenix（Arize）+ 自建评测流水线
```

**国内主流**：自建 + 部分用 Langfuse 自托管。

---

## 四、最小代码示例

### LangSmith（最少代码集成）

```python
import os
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "..."

# 任何 LangChain / LangGraph / OpenAI / Anthropic 调用自动被 trace
```

### Langfuse 装饰器

```python
from langfuse.openai import openai  # 替换 import 即可

resp = openai.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    name="search_agent_step1",  # 业务标签
    user_id="U123"
)
```

### 自定义 trace（不绑定平台）

```python
import logging, json, uuid, time

def trace_llm_call(model, messages, **kwargs):
    trace_id = str(uuid.uuid4())
    start = time.time()
    try:
        resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
        latency = (time.time() - start) * 1000
        logging.info(json.dumps({
            "trace_id": trace_id,
            "model": model,
            "messages": messages,
            "response": resp.choices[0].message.content,
            "tokens": resp.usage.model_dump(),
            "latency_ms": latency,
            "status": "ok"
        }))
        return resp
    except Exception as e:
        logging.error(json.dumps({"trace_id": trace_id, "error": str(e)}))
        raise
```

---

## 五、Agent 多步追踪（关键难点）

单次 LLM 调用 trace 简单，**多步 Agent** 需要分布式 trace 思维：

```
session_id = "agent_run_xyz"
  ├─ trace_1: planner_step1 (LLM call)
  ├─ trace_2: tool_call_a (function exec)
  │    └─ trace_3: external_api_call
  ├─ trace_4: planner_step2 (LLM call)
  ├─ trace_5: tool_call_b
  └─ trace_6: final_response (LLM call)
```

实现方式：
- 用 OpenTelemetry 标准 + LangSmith / Langfuse / Phoenix
- 每个工具调用、LLM 调用、外部 API 都有自己的 span
- UI 可以瀑布图展示

> 没有 multi-step trace，调试 Agent 等于盲调。

---

## 六、质量观测：不能只看错误率

LLM 系统的"输出对不对"通常没有 200/500 这种二元信号。需要：

### 1. 用户隐式反馈
- 用户重新提问？
- 用户复制了答案？
- 用户停留时间？
- 多轮对话长度？

### 2. 用户显式反馈
- 👍 / 👎 按钮
- 评分（1-5 星）
- 注释 / 反馈文字

### 3. LLM-as-Judge（在线抽样）
- 每天抽 1% 流量请 GPT-4 / Claude 评分
- 详见 [../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)

### 4. 启发式规则
- 输出长度异常（太短 = 拒答，太长 = 跑偏）
- 包含敏感词
- JSON 解析失败
- 工具调用错误率

### 5. 离线回放（Replay）
- 选一批生产 trace 在 staging 用新模型 / 新 prompt 重跑
- 对比新旧输出（diff、LLM-as-Judge 评分）
- 上线决策的关键信号

---

## 七、成本观测

LLM 应用的"成本"和传统软件完全不同——不是机器多/少，是**token 多/少**。

### 维度切片

```
按 feature 切:    哪个业务流耗钱？
按 user 切:       异常用户（爬虫、滥用）
按 model 切:      贵模型流量占比
按 prompt cache 切: cache 命中率多少（可优化空间）
按时段切:         峰谷成本对比
```

### 异常检测

- 单日成本环比涨 > 50% → 告警
- 单用户日调用 > P99 × 10 → 标记
- 单条 trace 成本 > 阈值 → 留样调查

### 优化的反馈循环

```
观测 → 找出 cost-heavy 的 trace → 分析 prompt 长度 / 模型选型 / 是否能 cache
   → 优化 → 再观测
```

→ 详见 [../llm-fundamentals/inference-optimization.md](../llm-fundamentals/inference-optimization.md)

---

## 八、隐私与合规

LLM 可观测的特殊隐患：**完整 prompt 包含用户原始数据**——可能含 PII、敏感业务信息。

### 必做项

```
□ 在写入 trace 前过滤 PII（手机号、邮箱、身份证）
□ 长期存储做访问控制（不是所有员工都该看）
□ 跨境数据合规（trace 是否能传到海外 SaaS）
□ 用户删除请求时能否级联删除 trace
□ 留存期限（敏感场景 7-30 天即可，不是无限）
```

商用 SaaS 可观测平台都支持 PII redaction，但**默认不开**——记得手动配置。

---

## 九、看板设计建议

最该看的 6 个图：

```
1. 流量曲线（QPS、按 feature 分层）
2. 延迟分布（p50 / p95 / p99 over time）
3. 成本曲线（USD/day，按 model / feature 分层）
4. 错误率（4xx / 5xx / timeout / tool_fail）
5. Token 使用结构（input / output / cached）
6. 质量信号（用户点踩率、LLM-judge 抽样得分）
```

每个图都能下钻到具体 trace。

---

## 十、Checklist

```
□ 1. 每次 LLM 调用都有完整 trace（prompt + response + tokens + cost）？
□ 2. 多步 Agent 能看到完整 multi-step trace？
□ 3. 至少 5 个核心指标有 dashboard？
□ 4. 至少 5 个核心告警配置好了？
□ 5. 用户反馈（👍/👎）能关联到具体 trace 吗？
□ 6. 有 LLM-as-Judge 抽样评分吗？
□ 7. PII 过滤 + 数据合规做了吗？
□ 8. 上线 / 改 prompt 前能用历史 trace 做 replay 对比吗？
□ 9. 留存策略是否合规？
□ 10. 一个新人入职能 30 分钟看懂 dashboard 吗？
```

---

## 十一、扩展阅读

- 本目录：[frameworks-comparison.md](frameworks-comparison.md)
- 相关：[../evaluation/llm-as-judge.md](../evaluation/llm-as-judge.md)、[../llm-fundamentals/inference-optimization.md](../llm-fundamentals/inference-optimization.md)
- LangSmith 文档：https://docs.smith.langchain.com
- Langfuse 文档：https://langfuse.com/docs
- Arize Phoenix：https://docs.arize.com/phoenix
- OpenTelemetry GenAI semantic conventions（业界标准化进展）
- 各厂商博客：Anthropic / OpenAI / Cohere 关于 production observability 的实践

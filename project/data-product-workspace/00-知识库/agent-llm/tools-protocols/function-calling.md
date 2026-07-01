# Function Calling：把 LLM 接到现实世界

> Function Calling 是把 LLM 从"会说话"变成"会做事"的关键接口。本文讲清核心机制、各家差异、生产级最佳实践，让你的 Agent **少调错工具、不填错参数、出错能恢复**。

---

## 一、Function Calling 在解决什么

LLM 输出是文本。但 Agent 要做的事——查数据库、发邮件、改文件、调 API——都是结构化操作。**两者之间需要一个可靠的协议**。

历史上有几个阶段：

```
1. 自由文本解析（早期）：
   "我要查天气" → 写正则 / few-shot 解析意图
   问题：脆弱，模型说"帮我查一下天气"就解析失败

2. ReAct 文本格式（2022-2023）：
   Action: search_weather
   Args: { city: "Beijing" }
   问题：模型可能输出 "Action: search Weather" 等变体，需要鲁棒解析

3. Function Calling（2023 至今）：
   原生 API 字段返回结构化 JSON
   { "tool": "search_weather", "arguments": { "city": "Beijing" } }
   优势：模型在 SFT 阶段就被训练按 schema 输出
```

→ Function Calling 是**模型 + API + SFT** 三方合力的协议化结果。

---

## 二、最小工作示例

### OpenAI 风格

```python
from openai import OpenAI
client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市当前的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["city"]
        }
    }
}]

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京今天多少度？"}],
    tools=tools
)

# 模型返回结构化 tool_call
tc = resp.choices[0].message.tool_calls[0]
print(tc.function.name)       # get_weather
print(tc.function.arguments)  # {"city": "北京", "unit": "celsius"}
```

### Anthropic 风格

```python
import anthropic
client = anthropic.Anthropic()

tools = [{
    "name": "get_weather",
    "description": "获取指定城市当前的天气",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["city"]
    }
}]

resp = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "北京今天多少度？"}]
)
# resp.content 中含 tool_use 块
```

> **核心一致**：声明 schema → 模型按 schema 返回 → 你执行工具 → 把结果作为 `tool_result` 喂回 → 模型继续。

---

## 三、Schema 写法的"细节决定一切"

90% 的工具调用错误来源于 schema 写得不好。

### 1. Description 决定模型用不用对

```
❌ 差: "查天气"
✅ 好: "查询指定城市当前实时天气；返回温度、湿度、天气状况文本。
       仅适用于实时天气，历史天气请使用 get_historical_weather"
```

**好的 description = 工具的 README**，要写明：
- 这个工具做什么
- 什么时候**不该**用它（关键！）
- 返回什么

### 2. 参数字段的 description

```python
{
    "city": {
        "type": "string",
        "description": "城市名称，使用中文全称，如 '北京' '上海'，不要带省份"
    }
}
```

模型经常错填省份、英文、缩写——把约束写进 description 能防住一半。

### 3. Enum 用足

```python
{"unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}}
```

**任何"只有几种值"的字段都加 enum**——能防止模型自创值。

### 4. Required 严格列

```python
"required": ["city"]
```

模型经常漏参数。required 字段会让 API 端检查更严。

### 5. 字段命名要清晰

```
❌ q, str, val
✅ search_query, query_string, target_value
```

模型会根据字段名推测含义。语义清晰的命名 + description = 大幅减少错填。

---

## 四、并行调用 vs 串行调用

### 并行（Parallel Function Calling）

OpenAI、Anthropic 都支持。模型一次返回多个 tool_call，并行执行：

```python
# 模型一次性返回：
[
  {"name": "get_weather", "args": {"city": "北京"}},
  {"name": "get_weather", "args": {"city": "上海"}},
  {"name": "get_weather", "args": {"city": "广州"}}
]
# 你并发跑这三个工具，把结果一起回填
```

**适合**：独立的批量查询。

### 串行（链式）

模型一次只返回一个 tool_call，等结果回来再决定下一步——这是 ReAct 的本体形态。

**适合**：步骤之间有依赖。

> **生产做法**：默认开并行（更快），但保留串行作为兜底（复杂决策路径）。

---

## 五、Structured Output：Function Calling 的"近亲"

OpenAI 的 `response_format: { type: "json_schema" }`、Anthropic 的强制 schema、Pydantic AI——本质都是**让 LLM 严格按结构化 schema 输出**，但不一定真的"调函数"。

```
Function Calling   = "应该调哪个工具 + 参数"
Structured Output  = "整个回答按 JSON 输出"
```

适用边界：

- 工具调用：用 Function Calling
- 提取实体 / 分类 / 评分：用 Structured Output
- 两者技术底层相通（都是约束生成）

→ 推荐看 OpenAI 的 *Structured Outputs* 文档；它能保证 100% schema 合法（用了 constrained decoding）。

---

## 六、生产级最佳实践

### 1. 一定做 schema 校验

模型可能返回**符合表面 schema 但语义错**的参数（如 city: "abcd"）。Pydantic / Zod 在执行前校验：

```python
from pydantic import BaseModel, Field

class GetWeatherArgs(BaseModel):
    city: str = Field(..., min_length=1, max_length=20)
    unit: str = Field("celsius", pattern="^(celsius|fahrenheit)$")

# 校验
args = GetWeatherArgs(**tool_call.function.arguments_dict)
```

### 2. 失败 → 反馈错误 → 重新生成

```python
try:
    result = run_tool(name, args)
except ValidationError as e:
    # 把错误反馈给模型，让它重生成
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "content": f"参数错误: {e}. 请检查后重试。"
    })
    # 重新调用 LLM
```

模型看到错误反馈后通常能修正——但你要给它机会。

### 3. 工具数量控制 + 动态检索

工具数量超过 ~15 个，模型选错率显著上升。生产做法：

```
第一步：用 Embedding 把工具描述检索到 top-K
第二步：只把 top-K 工具传给 LLM 做 function calling
```

### 4. 工具调用的超时和限频

每个工具调用都是外部 API：
- 设超时（5-30 秒）
- 设重试（指数退避）
- 限频（避免 LLM 在死循环里调爆下游）

### 5. max_iterations 兜底

ReAct 风格调用必须设最大迭代数：

```python
for step in range(MAX_STEPS := 10):
    resp = llm.call(messages)
    if not resp.tool_calls:
        return resp.content  # 完成
    for tc in resp.tool_calls:
        result = run_tool(tc)
        messages.append(result)
else:
    return "任务超时未完成"
```

不设上限的话，无法收敛的 prompt 会让账单飞涨。

### 6. 日志结构化

每个工具调用记录：

```json
{
  "timestamp": "...",
  "trace_id": "...",
  "step": 3,
  "tool_name": "get_weather",
  "args": {...},
  "result": {...} or error,
  "latency_ms": 234,
  "tokens_used": 1024
}
```

→ 详见 [../production/observability.md](../production/observability.md)。

---

## 七、各家差异速查

| 维度 | OpenAI | Anthropic | Google Gemini | 开源（Llama 3.1+, Qwen） |
|---|---|---|---|---|
| Schema | JSON Schema | JSON Schema | OpenAPI-like | JSON Schema |
| 并行调用 | ✅ | ✅ | ✅ | 部分支持 |
| Strict Mode | ✅ (`strict: true`) | 隐式严格 | ✅ | 看模型 |
| 工具数量上限 | 128 | 大 | 大 | 看模型 |
| 工具描述长度 | 长 prompt 影响成本 | 同 | 同 | 同 |

> **代码可移植性**：跨厂商时差异在字段名（tools vs functions）和返回结构。用 LiteLLM / Pydantic AI 可以抽象。

---

## 八、典型踩坑

### 1. 工具描述里写了"用户**应该**调用这个工具"
模型看到这种暗示倾向于过度调用。
✅ 写"在什么场景下使用"，而不是"应该调用"。

### 2. 同一个名字的工具，schema 改了
LLM 缓存里可能有旧 schema 印象 → 错填参数。
✅ 改 schema 时建议重命名工具或加版本后缀。

### 3. 工具结果是大 JSON / 长文本
直接喂回 LLM 会爆上下文。
✅ 工具结果做摘要 / 分页 / 检索后再传。

### 4. 工具间循环依赖
A 工具的结果触发 B，B 又触发 A → 死循环。
✅ 用状态机限制工具调用顺序。

### 5. 把"高风险操作"直接给模型
删除文件、转账、发邮件这种不可逆操作不能裸露：
✅ 危险工具加"用户确认"中间层；或先执行 dry-run。

---

## 九、Function Calling 的局限

- **不支持非结构化操作**：截图分析、自由网页操作 → 看 Computer Use / Browser Use（[mcp.md](mcp.md) 有相关讨论）
- **跨服务发现**：每个服务都要手写工具定义 → 看 MCP（标准化协议）
- **状态管理**：工具调用本身无状态，多步骤复杂任务要靠业务层维护

---

## 十、Checklist

```
□ 1. 每个工具的 description 写清了"做什么 + 不该用于什么"吗？
□ 2. 关键参数都有 enum / 取值范围 / 说明？
□ 3. 调用前是否做了 Pydantic / Zod 校验？
□ 4. 校验失败有错误反馈给模型重试吗？
□ 5. 设了 max_iterations？
□ 6. 工具数量 > 15 个时是否做了动态检索？
□ 7. 日志记录每次调用的参数、结果、耗时？
□ 8. 危险 / 不可逆操作有人工确认或 dry-run？
□ 9. 工具结果太长有摘要 / 分页机制吗？
□ 10. 跨厂商时用了抽象层（LiteLLM 等）？
```

---

## 十一、扩展阅读

- 本目录：[mcp.md](mcp.md)
- 相关：[../agents/react-and-variants.md](../agents/react-and-variants.md)、[../production/observability.md](../production/observability.md)
- OpenAI 官方文档：*Function Calling*、*Structured Outputs*
- Anthropic 官方文档：*Tool Use with Claude*
- Pydantic AI：https://ai.pydantic.dev
- DSPy（声明式 LLM 编程）：https://dspy-docs.vercel.app
- Anthropic — *Building Effective Agents*（工程视角必读）

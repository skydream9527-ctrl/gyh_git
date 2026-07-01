# Tool 开发：API 工程师视角的 schema 设计、参数校验、错误处理

> [function-calling.md](function-calling.md) 讲"协议怎么用"，[mcp.md](mcp.md) 讲"怎么跨应用复用"。这一篇专门讲一件事：**作为 API 工程师，怎么把一个 Tool 写到生产可用**。
>
> 它不是把内部 API "包一层 JSON Schema" 就行——给人用的 API 和给 LLM 用的 Tool，工程要求是两个物种。

---

## 一、给人 vs 给 LLM：Tool 是不一样的 API

很多团队第一版 Tool 就是把内部 RESTful API 直接套一层 schema，结果上线以后一堆怪问题：模型乱填参数、调一半就死循环、错误信息没人看懂。**根因是没意识到调用方变了**。

| 维度 | 给人用的 API | 给 LLM 用的 Tool |
|---|---|---|
| 调用者读什么 | 文档 / SDK 类型 | `description` 字段 |
| 调用者会做什么 | 看文档前先看示例 | 只看 schema，不看你的 README |
| 错的代价 | 报错 → 工程师 debug | 报错 → 模型重试 → 烧 token |
| 错误反馈期望 | HTTP code + message | **可执行的下一步建议** |
| 输入信任度 | 经过前端校验 | 模型脑补 + 没见过的字段也敢填 |
| 重复调用模式 | 偶发 | 链路里会被同一上下文连续调多次 |
| 性能关注点 | TPS、p99 延迟 | **Token 占用 + 每次调用的"信息密度"** |

→ 一句话：**Tool 是一个面向不可信、概率性、文本驱动调用方的 API**。这决定了 schema、校验、错误处理三件事都要重新做一遍。

---

## 二、Schema 设计：写给模型看的契约

Schema 不是 OpenAPI 的子集。它是你跟 LLM 之间的契约，**90% 的工具调用错误源于 schema 写得不好**（[function-calling.md §3](function-calling.md#三schema-写法的细节决定一切) 提过现象，这里讲怎么动手设计）。

### 1. 命名：动词 + 名词，避免歧义

```
❌ search          (搜什么？)
❌ get_data        (什么 data？)
❌ query           (动词太泛)
❌ user_info       (返回 vs 查询？)

✅ search_users_by_email
✅ get_order_by_id
✅ list_active_subscriptions
✅ create_invoice
```

**经验**：工具名超过 3 个词，几乎一定是职责混了，应该拆。`update_or_create_user` → 拆成 `create_user` + `update_user`。

### 2. Description：写"何时用 + 何时不用 + 返回什么"

模型不会读你的内部文档，只看 description。一个生产级 description 至少有三段：

```python
{
  "name": "search_orders",
  "description": (
    # 何时用
    "Search orders within the last 90 days by buyer email or order ID. "
    # 何时不用（关键！）
    "Do NOT use for refund queries (use search_refunds) or for orders older "
    "than 90 days (use search_archived_orders). "
    # 返回什么
    "Returns up to 50 orders with id, status, total, created_at."
  )
}
```

**"何时不用" 比 "何时用" 还重要**——它防止模型在有 20 个相似工具时选错。

### 3. 参数粒度：能展开就展开

```python
# ❌ 把多个语义塞进一个字符串
{
  "filter": {
    "type": "string",
    "description": "filter expression like 'status:open AND amount>100'"
  }
}
# 模型经常写出 'status: open' / 'status=open' / 'status open' 三种变体

# ✅ 拆成结构化参数 + enum
{
  "status": {
    "type": "string",
    "enum": ["open", "paid", "cancelled", "refunded"]
  },
  "min_amount": {"type": "number", "minimum": 0}
}
```

每多一层 DSL，模型就多一倍出错概率。**能用 enum 别用 string，能用 string 别用表达式**。

### 4. 默认值：在 schema 里写死，不是在代码里隐藏

```python
# ❌ 默认值藏在实现里
{
  "page_size": {"type": "integer", "description": "页大小"}
}
# 模型不知道默认值，可能填 1000 把 LLM 上下文塞爆

# ✅ 写在 schema
{
  "page_size": {
    "type": "integer",
    "minimum": 1,
    "maximum": 50,
    "default": 20,
    "description": "Number of results per page (max 50)."
  }
}
```

模型对 `minimum/maximum/default` 都会读。把"我希望你怎么用"全写进 schema。

### 5. 不要泄露内部实现

```
❌ user_id_v2_uuid     (内部迁移痕迹)
❌ legacy_status        (历史包袱)
❌ kafka_partition_key  (实现细节)

✅ user_id
✅ status
```

模型会模仿你的字段命名风格。一旦命名带版本/技术词，它会把这些抄进各种奇怪的地方。

### 6. 输出 schema 同样要约束

很多 SDK 只让你声明输入 schema。但**输出也要规范**——它是下一步调用的输入。

```python
# 工具返回值结构化
class SearchOrdersResult(BaseModel):
    orders: list[Order]
    has_more: bool
    next_cursor: str | None
    # 关键：summary 字段降低 token 占用
    summary: str = Field(
        ..., description="Human-readable summary, e.g. '12 open orders, 5 paid'"
    )
```

**生产经验**：每个工具输出都加一个 `summary` 字段，让模型可以只读 summary 决定下一步，不用消化整个 JSON——单次调用 token 占用能砍一半。

### 7. Schema 版本化

```python
# ❌ 改 schema 不改名字
search_orders v1: {"buyer_email": str}
search_orders v2: {"email": str}   # 上下文里旧 schema 残留 → 模型混用

# ✅ 改 schema 必改名 / 加版本
search_orders_v2(...)
# 或者
search_orders(..., schema_version="2")
```

LLM 没有"重新加载文档"的概念——它在多轮里会沿用早期上下文里的 schema 印象。breaking change 必须用新名字。

---

## 三、参数校验：模型说的不算

Schema 通过不代表参数对。模型经常返回**符合 schema 但语义错**的值。校验要分四层做。

### 第一层：Schema 层（语法）

OpenAI strict mode / Pydantic / Zod 自动做：

```python
from pydantic import BaseModel, Field

class SearchOrdersArgs(BaseModel):
    status: Literal["open", "paid", "cancelled", "refunded"]
    min_amount: float = Field(0, ge=0)
    page_size: int = Field(20, ge=1, le=50)
```

→ 防类型错、枚举越界、范围越界。**能 strict 就 strict**（OpenAI `strict: true`、Anthropic 通过 schema 显式 enum + required 实现）。

### 第二层：业务规则层（语义）

Schema 没法表达"这个 email 必须是已注册用户"。这一层用代码：

```python
def validate_search_orders(args: SearchOrdersArgs):
    if args.status == "refunded" and args.min_amount > 0:
        raise ToolValidationError(
            field="min_amount",
            reason="Refunded orders have negative amounts; min_amount filter does not apply.",
            suggestion="Remove min_amount or use search_refunds tool instead."
        )
```

**关键**：抛出的异常里要有 `field / reason / suggestion` 三件套——下面错误处理章节会用到。

### 第三层：权限层（鉴权）

```python
def check_permission(user_ctx, args):
    if args.org_id != user_ctx.org_id and not user_ctx.is_admin:
        raise ToolPermissionError(
            "Cannot query orders from another organization."
        )
```

**重点**：Tool 的鉴权上下文不是从模型来的，是从**调用 Tool 的会话**绑定来的。**永远不要**把 `user_id`、`org_id`、`role` 这种身份字段放进 schema 让模型填——那等于把鉴权外包给一个不可信调用方。

### 第四层：副作用前的"二次确认"层（针对危险操作）

```python
@tool(name="delete_order", danger=True)
def delete_order(order_id: str, dry_run: bool = True):
    if dry_run:
        return {"would_delete": _preview(order_id), "confirm_with": "dry_run=False"}
    # 真实删除前再校验一次
    if _is_locked(order_id):
        raise ToolValidationError(...)
    return _delete(order_id)
```

→ 思路同 [function-calling.md §八.5](function-calling.md#八典型踩坑)。**不可逆操作默认 dry_run，模型显式要求才执行**。

### 校验失败的返回形态

不要直接抛 500、不要返回纯文本错误。**返回结构化错误对象**——下一节细讲。

---

## 四、错误处理：错误本身也是给模型的输入

普通 API 报错给工程师看，Tool 报错给模型看。**错误信息的设计目标是"让模型自己能修"**。

### 1. 错误分类：哪些让模型重试，哪些让它换路径

```python
class ToolErrorKind(Enum):
    # 模型可修：参数错
    VALIDATION_ERROR = "validation_error"
    # 模型可修：换个工具或换个查询
    NOT_FOUND        = "not_found"
    # 模型不可修：基础设施问题
    UPSTREAM_ERROR   = "upstream_error"
    # 模型不该重试：权限 / 配额
    FORBIDDEN        = "forbidden"
    RATE_LIMITED     = "rate_limited"
    # 模型应该停止：危险或被拒
    USER_REJECTED    = "user_rejected"
```

**对模型呈现策略不同**：

| 错误类型 | 给模型的提示 | Agent 上层动作 |
|---|---|---|
| validation_error | 完整错误 + 修复建议 | 让 LLM 重生成 |
| not_found | 简短"未找到" + 备选工具 | 让 LLM 换工具或换关键词 |
| upstream_error | "工具暂时不可用" | 自动重试（指数退避）；3 次失败再上报 |
| forbidden | "无权访问" | 直接停止，不要重试 |
| rate_limited | "限流" + retry_after | 上层调度等待，不要让模型决定 |
| user_rejected | "用户拒绝执行" | 终止当前路径，不要绕路 |

### 2. 错误响应的结构

```json
{
  "ok": false,
  "error": {
    "kind": "validation_error",
    "field": "min_amount",
    "reason": "Refunded orders have negative amounts; positive min_amount filter never matches.",
    "suggestion": "Either remove min_amount, or use search_refunds tool which accepts negative amounts.",
    "request_id": "req_abc123"
  }
}
```

四个字段缺一不可：

- `kind`：让上层 Agent 知道怎么处理
- `field`：定位到具体参数
- `reason`：人话解释为什么错（模型读得懂）
- `suggestion`：**可执行的下一步**——这个字段是 Tool 错误处理的灵魂

### 3. 不要把内部异常暴露给模型

```python
# ❌ 把堆栈直接吐出来
return {"error": traceback.format_exc()}
# 模型可能在 reason 里学到内部表名 / 路径，下次 prompt injection 利用

# ✅ 翻译成对外语义
except DBConnectionError as e:
    log.error(f"DB error: {e}", extra={"trace_id": ...})
    return tool_error(
        kind="upstream_error",
        reason="Database temporarily unavailable.",
        suggestion="Retry in a few seconds. If persists, escalate to ops."
    )
```

**原则**：内部错误日志记完整，对模型只暴露"它需要知道的"。和给前端 API 报错一个道理，但更严格。

### 4. 重试策略：放在 Tool 内部还是 Agent 层？

```
Tool 内部重试      →  瞬时网络抖动、限流退避   (Agent 透明)
Agent 层重试      →  参数错、找不到资源        (LLM 重生成)
都不重试          →  权限错、用户拒绝          (硬失败)
```

很多团队把所有重试都丢给 Agent → token 烧爆。**Idempotent 的、确定能重试解决的，Tool 自己处理；需要换参数的才让 LLM 重试**。

### 5. 幂等性 + 请求去重

LLM 链路里"调用同一个工具两次"是常态——并行 function call、用户重发、agent 反思后重试都会触发。

```python
@tool
def create_invoice(
    *,
    idempotency_key: str = Field(..., description="Provided automatically; do not invent."),
    ...
):
    if existing := _lookup_by_key(idempotency_key):
        return existing  # 同一个 key → 同一个结果
```

注意：`idempotency_key` 应该由 **Agent 框架自动注入**（基于 request_id + step），**不要让 LLM 生成**——LLM 生成的 UUID 不是真的随机。

### 6. 错误也要被观测

每次错误必须打日志（不是仅返回）：

```json
{
  "ts": "...",
  "trace_id": "...",
  "step": 3,
  "tool": "search_orders",
  "args_hash": "...",
  "error_kind": "validation_error",
  "error_field": "min_amount",
  "user_id": "...",
  "model": "claude-opus-4-7",
  "tokens_in": 1200,
  "tokens_out": 80
}
```

**观测维度**：错误率分工具看、按 error_kind 看、按模型版本看。Tool 出问题往往是"换了模型 + 某个工具的 hallucination 率突然飙升"——没有按工具/按模型的分桶看不到。

---

## 五、Tool 的"信息密度"：每一字节都在花钱

Tool 的输入输出都进上下文，都在烧 token。**密度优化是工程任务**。

### 1. 输入：默认值不要让模型重复

```
❌ 让模型每次填 page_size=20、order_by="created_at"
✅ schema 写默认值；模型省略 → 系统补默认
```

### 2. 输出：分级返回

```python
class GetOrderResult(BaseModel):
    summary: str        # "Order #1234, paid, $99, 2 items"
    order: Order        # 完整对象
    raw: dict | None    # 上游原始 payload（可选）
```

约定：默认 `summary + order`；模型显式问 `include_raw=True` 才返回原始 payload。

### 3. 大结果：不要塞，给个引用

```python
# ❌ 工具返回 5MB JSON 全塞回 LLM
# ✅ 工具把结果存到 blob，返回 reference + 摘要
{
  "summary": "Found 3214 rows matching query.",
  "preview": [...first 5 rows...],
  "result_ref": "result://abc123",
  "next_action": "Use load_result(ref) to read in pages of 50."
}
```

→ 思路对应 [function-calling.md §八.3](function-calling.md#八典型踩坑) "工具结果是大 JSON / 长文本"。这里强调**Tool API 工程师该主动设计这个机制**，不是让 Agent 层去裁剪。

### 4. Description / Schema 也算 token

100 个工具 × 每个 200 token 描述 = 20K token 永久驻留。两个手段：

- **动态工具检索**：不是所有工具都 always-on，按当前任务召回 top-K
- **描述瘦身**：description 短而精，长说明放 `examples` 字段（很多 client 不会喂给 LLM）

---

## 六、Tool 工程师的工作流

把上面的事变成**可重复的开发流程**：

```
1. 写一句话 spec：这个工具做什么 / 不做什么
   ↓
2. 设计 schema：先写 description + 参数 + enum，过 review
   ↓
3. 写 Pydantic 模型 + 业务校验 + 错误类型映射
   ↓
4. 实现核心逻辑（独立函数，便于单元测试）
   ↓
5. 接 idempotency / 鉴权 / 限频中间件
   ↓
6. 写测试：
   - 正常路径
   - 模型乱填的 5 种典型参数（基于过去 hallucination 数据）
   - 上游故障的 3 种错误返回
   ↓
7. 离线评测：让 LLM 调用 30-50 个真实 prompt，看选对率 / 填对率
   ↓
8. 灰度上线：日志按 tool + error_kind 分桶看
```

第 7 步最关键。**没经过 LLM 实际调用过的 Tool，schema 里隐藏的歧义你看不见**——人觉得清楚的字段名，模型可能误解。

---

## 七、典型踩坑（API 工程师视角）

### 1. 把 RESTful 直接包一层

```
GET /orders?status=paid&min_amount=100  →  Tool: query_orders(filter: str)
```

这是最常见的偷懒——直接把 query string 当字符串参数。模型几乎一定会写错语法。**Tool 不是 REST 的 alias**，每个参数要重新设计。

### 2. 错误信息里夹杂 SQL / 内部 ID

```python
# ❌
return {"error": "FK violation on table fct_order_v2 (constraint fk_user_id)"}
```

模型读不懂、用户读不懂、还泄露 schema。翻译成"订单关联的用户不存在，请先创建用户"。

### 3. 没幂等性 + 写操作

```python
# ❌ POST /transfer  没幂等键
# 模型并行调用 / 反思重试 → 转账两次
```

写操作 + LLM = 必须幂等。idempotency_key 是基本权益。

### 4. 把"权限失败"包装成"未找到"

```python
# ❌ 安全惯例：404 不暴露资源存在
# 给 LLM：模型会以为"换个 ID 就行"，反复试探
# ✅ 给 LLM 明确返回 forbidden + 不要重试
```

人类 API 的"安全模糊"惯例不直接适用于 Tool。

### 5. 时间字段没时区

```
created_at: "2026-01-15 10:30:00"   ← 哪个时区？
```

模型经常拿这个去做"今天的订单"判断结果错。**所有时间字段强制 ISO8601 + 时区** (`2026-01-15T10:30:00+08:00`)。

### 6. 分页参数三件套不齐

只给 `page` 不给 `total` / `has_more` → 模型不知道要不要继续翻。**必须返回 `has_more` + `next_cursor`**。

### 7. enum 用了，但选项还在变

`status` enum 加了新值（如 `disputed`），老 description 里没写 → 模型不会用新值。**enum 变更视同 schema 变更**，需要文档 + 测试 + 灰度。

### 8. 一个 tool 干两件事

`search_or_create_user(name, email, create_if_not_exist=True)`——模型不知道该不该填 `True`，副作用决策被外包给概率。**拆**：`search_user` + `create_user`。

### 9. 没考虑模型同时调多次

并行 function call 下，三次 `search_orders(status="paid")` 同时打 DB。Tool 内部要有：去重、缓存、限频。

### 10. schema 写在代码里散落各处

工具 1 用 dict、工具 2 用 Pydantic、工具 3 用 dataclass。新人改一个字段要改三处。**统一用 Pydantic，自动生成 schema**：

```python
@tool
def search_orders(args: SearchOrdersArgs) -> SearchOrdersResult: ...
# schema 从 SearchOrdersArgs.model_json_schema() 自动生成
```

---

## 八、和其他模块的接口

- 协议层细节 → [function-calling.md](function-calling.md)
- 跨应用复用 / MCP 实现 → [mcp.md](mcp.md)
- ReAct 调用循环里 Tool 失败的反馈机制 → [../agents/react-mechanism-and-strategy.md](../agents/react-mechanism-and-strategy.md)
- 工具数量爆炸的动态检索方案 → [../agents/skills-system-design.md](../agents/skills-system-design.md)
- 调用日志 / 错误观测落地 → [../production/observability.md](../production/observability.md)

---

## 九、Checklist（API 工程师交付前）

```
Schema
□ 1. 工具名是动词+名词，单一职责？
□ 2. description 写了"何时用 + 何时不用 + 返回什么"？
□ 3. 所有"只有几种值"的字段都用 enum？
□ 4. 所有数值字段都有 min/max？
□ 5. 默认值写在 schema 里，不是藏在代码？
□ 6. 字段名没有内部实现痕迹（_v2 / legacy / kafka_）？
□ 7. 输出有 summary 字段降低 token 占用？
□ 8. breaking change 通过新名字 / 版本号发布？

校验
□ 9. Pydantic / Zod 做了类型 + range + enum 校验？
□ 10. 业务规则校验抛出带 field/reason/suggestion 的异常？
□ 11. 鉴权上下文绑定会话，不从 schema 读？
□ 12. 危险操作有 dry_run + 二次确认？

错误处理
□ 13. 错误分了 6 类（validation/not_found/upstream/forbidden/rate_limited/rejected）？
□ 14. 错误响应包含 kind + field + reason + suggestion？
□ 15. 内部异常 / 堆栈没暴露给模型？
□ 16. 瞬时错误 Tool 内部重试，参数错才让 LLM 重试？
□ 17. 写操作有 idempotency_key（系统注入，非 LLM 生成）？
□ 18. 错误日志按 tool + error_kind + model 分桶可观测？

信息密度
□ 19. 大结果分级返回（summary / detail / raw）或返回 reference？
□ 20. 时间字段全用带时区的 ISO8601？
□ 21. 分页返回 has_more + next_cursor？

工程
□ 22. Schema 通过 Pydantic 单一来源生成？
□ 23. 测试覆盖了"模型典型乱填"案例？
□ 24. 上线前跑过 LLM 端到端调用评测（30+ prompt）？
```

---

## 十、扩展阅读

- OpenAI — *Structured Outputs* / *Function Calling Best Practices*
- Anthropic — *Tool Use Best Practices*、*Building Effective Agents*
- Pydantic AI — https://ai.pydantic.dev（schema-first agent 框架，本文风格深度借鉴）
- MCP 官方 — [https://modelcontextprotocol.io](https://modelcontextprotocol.io)（看 reference servers 怎么写 tool）
- 本仓库：[knowledge-base/AI-SKILL/](../../../knowledge-base/AI-SKILL/) 中的 tool 工程实践
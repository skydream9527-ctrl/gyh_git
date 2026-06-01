# OpenViking vs Hindsight：两种长期记忆方案的原理与对比

> 本文目标：把 Hermes Agent 体系下两个最有代表性的"长期记忆 Provider"（OpenViking 与 Hindsight）讲清楚——它们各自解决什么问题、原理是什么、实现方式有何差异、以及怎么挂到本仓库的 [`project/ice-workbench/`](../../ice-workbench/) 上去用。
>
> 配套阅读：[memory-systems.md](memory-systems.md)（先读这篇建立"短期/长期/Episodic/Semantic/Procedural"的语义）。

---

## 一、为什么需要它们：从"自己写 KV+向量库"到"装一个记忆服务"

[memory-systems.md](memory-systems.md) 把记忆讲成四件事：**短期窗口、Profile KV、向量召回、图谱**。但工程上你会发现——**自己拼这一套的成本极高**：

- 写入要去重 / 冲突合并
- 读取要混合检索（语义 + 关键词 + 时间衰减 + rerank）
- 还要做实体抽取、自动分类、TTL、敏感信息过滤
- 上下文窗口分级（abstract / overview / full）也要自己造

OpenViking 和 Hindsight 都是为了把这些能力**作为一个独立服务**封装出来——你的 Agent 只需调用几个工具（`*_remember` / `*_recall`），系统自动完成抽取、索引、召回、合成。

它们都遵循一个共同抽象：`MemoryProvider`（见 [`~/.hermes/hermes-agent/plugins/memory/`](../../../../../.hermes/hermes-agent/plugins/memory/)）：

```python
class MemoryProvider:
    def initialize(session_id) -> None
    def system_prompt_block() -> str         # 注入到系统提示开头
    def queue_prefetch(query) -> None        # 异步预取（不阻塞推理）
    def prefetch(query) -> str               # 取预取结果
    def sync_turn(user, assistant) -> None   # 每轮对话同步
    def on_session_end(messages) -> None     # 会话结束时触发抽取
    def on_memory_write(action, target, content)  # 显式写入
    def get_tool_schemas() -> List           # 暴露给 LLM 的工具
    def handle_tool_call(name, args) -> str
```

→ 任何 Agent 框架（包括 ice-workbench）都可以**实现这个接口**来接入二者。

---

## 二、OpenViking：把记忆当文件系统

### 来历

字节火山引擎（Volcengine）开源的 **Context Database**。设计哲学是**"知识是有层级的，应当像文件系统一样浏览"**。

### 核心原理

#### 1. viking:// URI——文件系统语义

```
viking://                              ← 根
viking://resources/                    ← 外部资源（URL / 文档 / 代码）
viking://resources/docs/foo.md
viking://user/memories/                ← 自动抽取的记忆
viking://user/memories/preferences/
viking://user/memories/cases/2025-04-08-incident-x
viking://skills/                       ← 复用模式 / SOP
```

→ 检索结果回的是 URI；要看内容再调一次 `read`。这是 **链接结构**，不是扁平向量列表。

#### 2. 三层 tiered context（**显著降低 token 消耗**）

每条记忆 / 资源都被预生成三个版本：

| Level | 量级 | 用途 |
|---|---|---|
| **abstract** | ~100 tokens | 让模型先扫一遍 |
| **overview** | ~2k tokens | 默认读取层 |
| **full** | 全文 | 真要细节再展开 |

→ 模型可以"先读摘要，按需深入"，避免一上来就把 8K 全文塞进上下文。

#### 3. 自动抽取（在 `on_session_end` 触发）

会话结束时调用 `POST /sessions/{sid}/commit`，OpenViking 服务端自动把对话拆成 6 类记忆：

```
profile        ← 用户的稳定身份属性
preferences    ← 偏好（喜欢简短 / 喜欢图表）
entities       ← 出现的实体（项目、人、KPI）
events         ← 发生的事件（改了哪个表）
cases          ← 案例（这次怎么解决某个问题）
patterns       ← 复现的模式（每周一发周报）
```

#### 4. 双模检索

```
fast   单路语义 + URI 前缀过滤
deep   多路 + 跨节点跳转 + 子图扩展（贵但更准）
auto   服务端按 query 自动决策
```

### 工具集（暴露给 LLM）

| Tool | 干什么 |
|---|---|
| `viking_search` | 语义检索（fast / deep / auto） |
| `viking_read` | 按 URI 读 abstract / overview / full |
| `viking_browse` | 像 `ls` / `tree` / `stat` 一样看目录 |
| `viking_remember` | 显式记住一条事实（commit 时抽取） |
| `viking_add_resource` | 把 URL / 文档塞进知识库 |

### 部署形态

**自托管 HTTP 服务**（默认 `127.0.0.1:1933`）。需要本地跑 `openviking-server`，配 `~/.openviking/ov.conf`（embedding + VLM 模型）。

```
Agent (client)  ──HTTP──>  openviking-server  ──>  本地存储 + 向量库
```

### 何时合适

- **代码库 / 文档库类**长期知识（多层级、跨文件）
- 想**精确控制"看到了什么"**——能明确 `viking://` URI 出处
- 内网部署、不想把对话上传到第三方
- 团队知识库（多 Agent 共享同一个 OpenViking 实例）

### 不适合

- 想**零运维**用 SaaS（OpenViking 没有官方云托管）
- 强需求"实体关系图谱"（OpenViking 是层级目录，不是图）

---

## 三、Hindsight：把记忆当知识图谱

### 来历

Vectorize.io 出品的长期记忆服务。设计哲学：**"记忆是事实和实体之间的关系网"**——用知识图谱 + 多策略检索做更准的召回。

### 核心原理

#### 1. 实体解析（Entity Resolution）

写入时 LLM 自动从对话里抽实体 + 关系：

```
Conversation:
  "李四是浏览器项目的 PM，KPI 是 DAU"

Hindsight 抽出：
  Node:  Person(name="李四", role="PM")
  Node:  Project(name="浏览器")
  Node:  Metric(name="DAU")
  Edges: 李四 --负责--> 浏览器
         浏览器 --核心指标--> DAU
```

→ 之后问"李四的项目北极星指标是什么"——可以**跨节点跳转**回答，不只是语义相似度。

#### 2. 三种召回策略并行

| 策略 | 干什么 |
|---|---|
| **recall** | 直接拿原始事实片段（fast，便宜） |
| **reflect** | LLM 综合多条事实给出推理结论（贵但答得好） |
| **hybrid** | 自动注入 + 工具暴露（让模型自己决定要不要再调） |

#### 3. 自动 retain / recall 节奏可调

```python
# config.json
{
  "auto_recall": true,           # 每轮前自动召回（默认 on）
  "auto_retain": true,           # 每轮后自动写入（默认 on）
  "retain_every_n_turns": 1,     # 每 N 轮才写一次
  "recall_budget": "mid",        # low/mid/high 三档预算
  "memory_mode": "hybrid",       # hybrid/context/tools
}
```

→ 你可以**只让它静默注入上下文**（`context`），或**只暴露工具让 LLM 主动调**（`tools`），或两者都做（`hybrid`）。

#### 4. Memory Bank + Mission

记忆按 "bank" 分桶（比如 `team-frontend` / `personal`），每个 bank 可以配 mission：

```
bank_mission   = "你在帮 PM 做 AI 数据工作流相关的记忆"
bank_retain_mission = "只记产品决策、用户偏好，不记代码细节"
```

→ 用 mission **steer 抽取行为**，比单纯写 prompt 控制更稳。

### 工具集（暴露给 LLM）

| Tool | 干什么 |
|---|---|
| `hindsight_retain` | 显式存入（自动抽实体） |
| `hindsight_recall` | 多策略检索（语义 + 实体图） |
| `hindsight_reflect` | LLM 跨记忆综合推理 |

### 部署形态

**三种模式**——这是 Hindsight 比 OpenViking 灵活的核心：

| 模式 | 数据在哪 | 何时用 |
|---|---|---|
| `cloud` | Vectorize 云端 | 想零运维 |
| `local_embedded` | 本地 daemon + 内置 PostgreSQL | 不想上传，但又不想自己跑 server |
| `local_external` | 你已经跑了一个 Hindsight 实例（Docker） | 自己运维 / 多 Agent 共享 |

`local_embedded` 模式由 hermes 启动时自动起 daemon，5 分钟无活动自动停。

### 何时合适

- **关系密集**型场景（人 / 项目 / 指标互相引用）
- 想用**SaaS**省运维（cloud 模式）
- 想做"跨记忆综合"（`reflect` 工具）
- 多个 bank 隔离不同 mission（个人 vs 团队）

### 不适合

- 想要**目录式浏览 / 资源摄取**（Hindsight 没有"viking://" 这种结构化 URI）
- 担心 LLM 抽取成本（每次 retain 都要调 LLM 抽实体——本地模式还要再付一次推理钱）

---

## 四、原理 / 实现 / 工程对比表

| 维度 | OpenViking | Hindsight |
|---|---|---|
| **基础抽象** | 文件系统（viking:// URI 树） | 知识图谱（实体 + 关系） |
| **存储模型** | 层级目录 + 向量索引 | 图数据库 + 向量索引 |
| **写入抽取** | session commit 时一次性抽 6 类 | 每轮 retain 时 LLM 抽实体 + 关系 |
| **检索策略** | search（fast / deep）+ browse | recall / reflect / hybrid |
| **上下文分级** | ✅ abstract / overview / full | ❌（统一返回） |
| **资源摄取** | ✅ URL / 文档 / 代码 | ❌（只存对话产生的事实） |
| **部署** | 自托管 HTTP server | cloud / local_embedded / local_external |
| **依赖** | `openviking` + 本地 server 运行 | `hindsight-client>=0.4.22` |
| **抽取何时发生** | 会话结束时（批量） | 每 N 轮一次（增量） |
| **多用户隔离** | account / user header | bank_id |
| **记忆 mission** | 由提示词控制 | bank_mission / retain_mission（API 一等公民） |
| **典型 token 成本** | 低（先读 abstract，按需深入） | 中（每次 recall LLM 综合） |
| **运维成本** | 高（自起服务） | 低（cloud 模式 0 运维） |
| **回答关系类问题** | 一般（靠语义） | 优（图遍历） |
| **回答"知识库里有什么"** | 优（browse / tree） | 一般（无目录概念） |

### 简言之

- **OpenViking 像 wiki + 文件系统**：擅长"知识沉淀 + 浏览"
- **Hindsight 像 CRM + 知识图谱**：擅长"实体跟踪 + 综合推理"

二者**不互斥**——大型 Agent 可以同时挂两个 Provider，OpenViking 管"项目知识库"，Hindsight 管"用户/团队画像"。

---

## 五、实现方式：MemoryProvider 接口的两份范本

两个插件本质都是一个 Python class 实现 `MemoryProvider`。把核心方法翻译成"什么时候调，做什么"：

```
┌─────────────────────────────────────────────────────────────┐
│ Agent 一轮对话的生命周期                                     │
└─────────────────────────────────────────────────────────────┘

User 发消息
    │
    ├─▶ provider.queue_prefetch(query)         ← 异步起线程预取
    │
    ├─▶ provider.system_prompt_block()         ← 注入系统提示开头
    │
    ├─▶ provider.prefetch(query)               ← 等线程，取预取结果，注入 user msg
    │
    ├─▶ LLM 推理 (可调 provider 暴露的工具：viking_*/hindsight_*)
    │       │
    │       └─▶ provider.handle_tool_call(name, args)
    │
    ├─▶ provider.sync_turn(user, assistant)    ← 异步记一笔（OV：发到 session）
    │
    └─▶ ... 多轮 ...

会话结束
    │
    └─▶ provider.on_session_end(messages)      ← OV：commit 触发抽取；Hindsight：刷队列
```

### OpenViking 的实现要点（看 [`__init__.py`](../../../../../.hermes/hermes-agent/plugins/memory/openviking/__init__.py)）

- 不依赖 OpenViking SDK，**直接用 httpx 打 REST**——便于二次集成
- `queue_prefetch` 起独立线程跑 `/api/v1/search/find`，主线程只 `join(timeout=3s)`，**最多多花 3 秒**
- `sync_turn` 也是后台线程，确保**不卡推理路径**
- `on_session_end` 调 `/sessions/{sid}/commit`，服务端再异步抽 6 类记忆
- 注册了 `atexit` 钩子兜底——SIGKILL / 异常退出也能 commit 一次

### Hindsight 的实现要点

- 用官方 `hindsight-client` SDK
- `auto_retain` 默认开——每轮都自动写
- `local_embedded` 模式由 hermes 启 daemon（`hindsight-embed -p hermes ui start`）
- 三个工具（`retain` / `recall` / `reflect`）和"自动注入"是**正交**的——你可以只用一边

### 两者共同的工程取舍

| 取舍 | 原因 |
|---|---|
| **写入异步** | LLM 推理不能等记忆服务返回 |
| **预取限时 join** | 慢就放弃，**别让记忆拖累延迟** |
| **失败降级** | 服务挂了，主流程不能挂——返回空字符串 / `tool_error` |
| **secrets 走 env / 不进代码** | 多租户场景下密钥旋转才安全 |

→ 自己实现 MemoryProvider 时**这四条是底线**，照抄即可。

---

## 六、在 [`project/ice-workbench/`](../../ice-workbench/) 中怎么用

### 6.1 ice-workbench 的现状

ice-workbench 当前**没有挂任何外部记忆 Provider**，记忆能力靠三块自建机制：

| 机制 | 位置 | 干什么 |
|---|---|---|
| **G3 文件优先存储** | [`backend/app/core/storage/`](../../ice-workbench/backend/app/core/storage/) | tasks/agents/skills 全是文件 + SQLite cache |
| **Compaction Service** | [`backend/app/services/compaction_svc.py`](../../ice-workbench/backend/app/services/compaction_svc.py) | 长会话自动摘要（≈ memory-systems.md 第三章） |
| **Experience Cards** | [`backend/app/services/experience_card_svc.py`](../../ice-workbench/backend/app/services/experience_card_svc.py) | 任务里"沉淀经验" → admin 审批 → 注入 Agent prompt |
| **Knowledge Base** | [`backend/app/services/kb_svc.py`](../../ice-workbench/backend/app/services/kb_svc.py) | 飞书 wiki 同步 + Mify RAG（外部检索） |

→ 这套对应 [memory-systems.md 第四章](memory-systems.md) 的 **KV / Profile + 简易摘要**，**缺的是**：
- 跨任务的语义召回（向量检索）
- 实体关系图谱
- 多层级文档浏览

OpenViking / Hindsight 正好补这块。

### 6.2 接入路径 A：OpenViking 作为"团队知识库 + 经验图谱"

适合："想统一管理多个 Agent 共用的项目知识，并把任务级经验自动沉淀。"

#### Step 1 — 起服务

```bash
# 在部署 ice-workbench 的同一台机器上
pip install openviking
openviking-server &  # 监听 :1933
```

#### Step 2 — 写一个 ice-workbench 侧的 Provider 适配器

新建 [`backend/app/services/memory_svc.py`](../../ice-workbench/backend/app/services/)，包一个轻量 client（参照 [`openviking/__init__.py`](../../../../../.hermes/hermes-agent/plugins/memory/openviking/__init__.py) 的 `_VikingClient`）。

关键钩子：
- **task 创建** → `viking_add_resource(url=task.brief, reason=...)` 让任务说明进知识库
- **conversation 每轮** → 后台线程 `POST /sessions/{cid}/messages`（cid = ice 的 conversation_id 即 OV 的 session_id）
- **conversation 结束 / 任务关闭** → `POST /sessions/{cid}/commit`
- **experience_card 审批通过**（[`experience_card_svc.merged_system_prompt`](../../ice-workbench/backend/app/services/experience_card_svc.py)）→ 把 card 内容也 `viking_remember(content=card.body, category="case")`

#### Step 3 — 在 5 轮 tool-calling 循环里暴露工具

[`backend/app/services/tool_runner.py`](../../ice-workbench/backend/app/services/tool_runner.py) 注册 `viking_search` / `viking_read` 为 builtin tool（和 `kyuubi_query` 一样）。这样任何 Agent（不管是 data-analysis 还是 biz-insight）都能在推理过程中检索过往任务经验。

#### Step 4 — degradation pattern

ice-workbench 的"外部 CLI 缺失返回 `*_NOT_CONFIGURED`"约定（见 [CLAUDE.md](../../ice-workbench/CLAUDE.md) 的 _External-CLI degradation_ 段）必须保留：

```python
def viking_search(args):
    if not os.environ.get("OPENVIKING_ENDPOINT"):
        return {"error_code": "OPENVIKING_NOT_CONFIGURED"}
    if not _client.health():
        return {"error_code": "OPENVIKING_UNREACHABLE"}
    ...
```

→ OV 服务挂了，ice-workbench 主流程仍能跑，只是工具返回错误码。

### 6.3 接入路径 B：Hindsight 作为"跨任务用户/团队画像层"

适合："想让 Agent 跨任务记住用户偏好、项目关系，并能跨记忆综合推理。"

#### Step 1 — 选模式

| ice-workbench 部署形态 | 推荐 Hindsight mode |
|---|---|
| 内部公网（小米内网） | `local_embedded`（hermes 内置 PG，不上传） |
| 外网 SaaS | `cloud`（vectorize.io API key） |
| 已有 Hindsight Docker | `local_external` |

#### Step 2 — Bank 设计（重要）

ice-workbench 是**多租户**的（`super_admin/admin/user`）。建议：

```
bank_id = f"ice-{user_id}"          ← 每个用户一个 bank（个人记忆）
bank_id = f"ice-team-{team_id}"     ← 团队共享的项目记忆
```

不要全局一个 bank，否则用户数据会混。在 [`backend/app/core/deps.py`](../../ice-workbench/backend/app/core/deps.py) 拿到当前 user 后再决定挂哪个 bank。

#### Step 3 — 写入策略：默认 off

ice-workbench 的 5 轮 tool-call 循环里**很多对话是失败重试**（详见 ice-workbench [CLAUDE.md](../../ice-workbench/CLAUDE.md) 的 5-round bounded loop 段），**全部 retain 会污染记忆**。建议：

```python
# 只在 user 显式说"记住"或 conversation 标记 success 时写
if conversation_outcome == "success" or "/remember" in user_msg:
    hindsight_retain(content=summary)
```

或在 ice-workbench 后台让用户选择"结束任务时是否沉淀经验"（已有的 [Experience Card 流程](../../ice-workbench/backend/app/services/experience_card_svc.py) 可以直接复用——审批通过 → 写 Hindsight）。

#### Step 4 — 召回策略：在 system prompt 注入

参照 OV 的 `system_prompt_block`，在 [`agent_prompt_builder.py`](../../ice-workbench/backend/app/services/agent_prompt_builder.py) 组装 prompt 时插一段 `## 用户画像\n{hindsight_recall(query=user_msg)}`。

注意：**不要把召回结果做成 tool**——因为 ice-workbench 的 5 轮 tool-call 已经被 `MAX_TOOL_ROUNDS=5` 限死，再多一类工具会挤掉真正干活的工具调用机会。`memory_mode="context"` 才是更合适的接法。

### 6.4 双 Provider 同时挂：分工策略

如果两个都装：

| 用途 | 挂哪个 | 原因 |
|---|---|---|
| 团队 SOP / 项目文档 / Skill 卡片 | OpenViking | 层级浏览 + tiered context |
| 用户偏好 / 跨任务记忆 / 实体关系 | Hindsight | 实体图 + bank 隔离 |
| 任务内对话历史摘要 | ice-workbench 自带的 [`compaction_svc`](../../ice-workbench/backend/app/services/compaction_svc.py) | 不出 ice 边界、零延迟 |

→ ice-workbench 现在是 [memory-systems.md 第四章](memory-systems.md) 的 **Hybrid 雏形**，加上这两个 Provider 后会非常接近 ChatGPT Memory / Claude Projects 的形态。

---

## 七、选型决策树（针对 ice-workbench）

```
你最想加强什么？
│
├─ 让 Agent 能"看到"全公司的文档/Wiki/代码
│   └─▶ OpenViking
│         (再问：能自托管 server 吗？)
│           ├─ 能 → 直接上
│           └─ 不能 → 退回 ice-workbench 自带 KB（飞书 wiki 同步）
│
├─ 让 Agent 跨任务记得"这个 PM 喜欢看什么样的报告"
│   └─▶ Hindsight (cloud / local_embedded)
│         (再问：数据敏感吗？)
│           ├─ 是 → local_embedded
│           └─ 否 → cloud（最省事）
│
├─ 既要文档检索又要用户画像
│   └─▶ 两个都挂
│         OV → builtin tool;  Hindsight → context-only 注入
│
└─ 不确定 / 还没想清楚
    └─▶ 先用 ice-workbench 自带的 [Experience Cards](../../ice-workbench/backend/app/services/experience_card_svc.py)
        三个月后看哪些"经验"反复被搜 → 再决定是该上 OV 还是 Hindsight
```

---

## 八、容易踩的坑

### 1. **把对话整段往 retain 塞** → 噪音爆炸
ice-workbench 失败重试很常见，照搬"自动 retain 每轮"会让记忆库 30% 是错误尝试。**门槛宁高勿低**——和 [memory-systems.md §5](memory-systems.md) 的告诫一致。

### 2. **OpenViking 的 commit 时机错了** → 没抽出记忆
`on_session_end` 必须能稳定触发。ice-workbench 的对话是 WebSocket，**断开 ≠ 结束**（断了可能重连）。建议绑到"任务关闭" / "用户主动结束" 而不是"WS 断开"。

### 3. **Hindsight 的 LLM 抽取走的是哪个 API？** → 走漏算钱
`local_embedded` 模式抽取也要调 LLM——你设的是 `gpt-4o-mini` 还是你公司的 mify 网关？错配了会跑用户的私有 token。务必用 ice-workbench 的 [`MIFY_GATEWAY_*`](../../ice-workbench/backend/app/services/llm_gateway.py)。

### 4. **多租户混 bank** → 信息泄漏
Hindsight 的 bank_id 必须按 user 隔离。**不要**用全局 bank。

### 5. **没做 degradation** → 记忆服务挂了导致 ice 不能用
按 ice-workbench 的 `*_NOT_CONFIGURED` 约定写错误码，不要让记忆服务的故障传染主流程。

---

## 九、Checklist：把 OpenViking / Hindsight 接到 ice-workbench

```
□ 1. 服务启动 / 凭证管理：放 .env，不入代码
□ 2. 实现一个 backend/app/services/memory_svc.py 适配器
□ 3. 钩到 conversation_svc 的"轮结束"和"任务结束"事件
□ 4. degradation 错误码（OPENVIKING_NOT_CONFIGURED / HINDSIGHT_NOT_CONFIGURED）
□ 5. 多租户隔离：OV 用 X-OpenViking-User，Hindsight 用 bank_id
□ 6. 抽取的 LLM 走公司网关（mify），不要走默认 OpenAI
□ 7. 注入到 system prompt 通过 agent_prompt_builder.py，不要在 ws.py 里硬塞
□ 8. 工具数量控制：避免和已有 builtin（kyuubi/feishu/...）+ 5 轮 tool-call 上限冲突
□ 9. 用 experience_card_svc 已有的"审批后注入"机制做"显式记忆"——不要全自动
□ 10. 留 Audit log（[CLAUDE.md](../../ice-workbench/CLAUDE.md) 的 Audit Logging Rules）
```

---

## 十、扩展阅读

- 原理基础：[memory-systems.md](memory-systems.md)、[react-and-variants.md](react-and-variants.md)
- 检索策略：[../rag/retrieval-basics.md](../rag/retrieval-basics.md)、[../rag/advanced-rag.md](../rag/advanced-rag.md)
- ice-workbench 上下文：[`project/ice-workbench/CLAUDE.md`](../../ice-workbench/CLAUDE.md)、[`design_decisions.md`](../../ice-workbench/design_decisions.md)
- 上游插件源码：
  - OpenViking: [`~/.hermes/hermes-agent/plugins/memory/openviking/`](../../../../../.hermes/hermes-agent/plugins/memory/openviking/)
  - Hindsight: [`~/.hermes/hermes-agent/plugins/memory/hindsight/`](../../../../../.hermes/hermes-agent/plugins/memory/hindsight/)
- 上游服务：
  - OpenViking server: `pip install openviking` + `openviking-server`
  - Hindsight UI（cloud）: https://ui.hindsight.vectorize.io

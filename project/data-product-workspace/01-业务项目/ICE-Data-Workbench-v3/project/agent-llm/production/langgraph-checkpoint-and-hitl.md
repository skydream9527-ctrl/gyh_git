# LangGraph Checkpoint 与 Human-in-the-Loop 落地

> 本文讲清楚两件事：(1) LangGraph 在 Postgres 里到底建了什么表、每张表是干什么的；(2) HITL（人工介入）的两种主流模式、工程坑、以及什么时候不该用 LangGraph 的 HITL。
>
> 配套：[../agents/subagent-patterns.md](../agents/subagent-patterns.md)（Subgraph 与 Checkpoint 透传）、[frameworks-comparison.md](frameworks-comparison.md)（横向对比）。

---

## 一、心智模型

LangGraph 把一次 Agent 运行看作 **"状态机沿着图前进"**：

```
State (TypedDict) ──> Node A ──> Node B ──┬──> Node C
                                          └──> Node D (条件分支)
```

**Checkpoint** = 在每个节点执行前/后，把 `State` 完整快照写到持久层（SQLite / Postgres / Redis）。

**Human-in-the-Loop (HITL)** = 在某个节点处**主动暂停**，把控制权交还给应用层，等外部输入（用户审批、补充信息）再继续。

这两件事是**同一个机制的两面**：能 checkpoint 才能暂停，能暂停才能等人。

---

## 二、Checkpoint 落地最小骨架

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Annotated
from operator import add

class State(TypedDict):
    messages: Annotated[list, add]
    draft: str
    approved: bool

def draft_node(state: State) -> State:
    return {"draft": llm.invoke(state["messages"])}

def publish_node(state: State) -> State:
    db.save(state["draft"])
    return {}

graph = StateGraph(State)
graph.add_node("draft", draft_node)
graph.add_node("publish", publish_node)
graph.add_edge("draft", "publish")
graph.set_entry_point("draft")
graph.add_edge("publish", END)

# 关键：传入 checkpointer
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
app = graph.compile(checkpointer=checkpointer)
```

**调用时必须给 `thread_id`**（一次会话/任务的唯一标识）：

```python
config = {"configurable": {"thread_id": "task-12345"}}
app.invoke({"messages": [...]}, config=config)
```

每个节点跑完，State 自动写入 Postgres。**进程崩了重启，传同一个 `thread_id` 就接着跑**。

---

## 三、Postgres Checkpoint 表结构详解

`PostgresSaver.setup()` 会建 **4 张表**（LangGraph 0.2+ 版本）：

```
checkpoints              -- 主表，每个节点执行后的状态快照
checkpoint_blobs         -- State 里大字段的二进制存储（按 channel 拆分）
checkpoint_writes        -- 节点写入的"待提交"变更（pending writes）
checkpoint_migrations    -- schema 版本管理
```

### 1. 主表 `checkpoints`

```sql
CREATE TABLE checkpoints (
    thread_id          TEXT NOT NULL,        -- 业务标识（你传的）
    checkpoint_ns      TEXT NOT NULL DEFAULT '',  -- 命名空间（子图用）
    checkpoint_id      TEXT NOT NULL,        -- UUID v6，时序可排
    parent_checkpoint_id TEXT,               -- 父快照（形成时间链）
    type               TEXT,                 -- 序列化类型（msgpack/json）
    checkpoint         JSONB NOT NULL,       -- 元数据 + channel 引用
    metadata           JSONB NOT NULL DEFAULT '{}',  -- source/step/writes
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX checkpoints_thread_id_idx ON checkpoints (thread_id);
```

**关键字段**：
- `thread_id` — 你的会话 ID，**所有查询都从它开始**
- `checkpoint_id` — UUID v6，**时间有序**，最新一条 = `ORDER BY checkpoint_id DESC LIMIT 1`
- `parent_checkpoint_id` — 串成链表，可以回溯历史（**time travel** 就靠它）
- `metadata.step` — 第几步（debug 时极有用）
- `metadata.source` — `"input" | "loop" | "update"`（区分用户输入 / 循环执行 / 手动更新）

### 2. `checkpoint_blobs` —— 为什么要拆表

```sql
CREATE TABLE checkpoint_blobs (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel       TEXT NOT NULL,        -- State 的字段名（messages/draft/...）
    version       TEXT NOT NULL,
    type          TEXT NOT NULL,
    blob          BYTEA,                -- 实际数据（msgpack 序列化）
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

**设计精妙处**：State 的每个字段（channel）单独存，按 `version` 增量。
- 你 State 有 `messages` 和 `draft` 两个字段
- 第 1 步只改了 `messages` → 只写一行 messages 的新版本
- `checkpoints` 表的 JSONB 里只存 `{"messages": "v3", "draft": "v1"}` 这种**指针**

**意义**：State 里有 1MB 的 `messages` 历史，每步都全量写就是灾难；**只写变化的 channel** 才是可持续的。

### 3. `checkpoint_writes` —— 故障恢复的关键

```sql
CREATE TABLE checkpoint_writes (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id       TEXT NOT NULL,        -- 哪个节点写的
    idx           INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    type          TEXT,
    blob          BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**为什么需要这张表**：
节点 A 跑完，写了 3 个 channel，但**还没 commit 成下一个 checkpoint** 时进程挂了 → 重启后从 `checkpoint_writes` 把这些"中间写入"读出来重放，**保证 exactly-once**。

### 4. 实战 SQL（极其有用）

**看一个 thread 的全部历史**：
```sql
SELECT
    checkpoint_id,
    metadata->>'step' AS step,
    metadata->>'source' AS source,
    metadata->'writes' AS writes
FROM checkpoints
WHERE thread_id = 'task-12345'
ORDER BY checkpoint_id;
```

**找出"卡在 HITL 等了很久"的 thread**：
```sql
SELECT
    thread_id,
    MAX(checkpoint_id) AS last_checkpoint,
    -- UUID v6 前 48 位是时间戳
    to_timestamp(
      ('x' || substr(MAX(checkpoint_id), 1, 8))::bit(32)::bigint
    ) AS last_active
FROM checkpoints
GROUP BY thread_id
HAVING MAX(checkpoint_id) < '...'  -- 24h 前的 UUID
ORDER BY last_active;
```

**清理 30 天前的废弃 thread**：
```sql
DELETE FROM checkpoints
WHERE thread_id IN (
    SELECT thread_id FROM checkpoints
    GROUP BY thread_id
    HAVING MAX(checkpoint_id) < '...30天前的UUID...'
);
-- blobs 和 writes 有外键级联，会一起删
```

---

## 四、Human-in-the-Loop 的两种主流模式

### 模式 A：`interrupt_before` — 预设断点

```python
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["publish"],  # publish 前必停
)

# 第一次调用，跑到 draft 完成，停在 publish 前
app.invoke({"messages": [...]}, config=config)

# 应用层拿到当前 state，给人类看
state = app.get_state(config)
print(state.values["draft"])  # 给审核员看草稿

# 人类批了，继续跑（None 表示不注入新输入）
app.invoke(None, config=config)
```

**特点**：断点位置在编译期定死，适合**固定审批流**（草稿 → 审核 → 发布）。

### 模式 B：`interrupt()` — 动态断点（推荐，1.0 之后主推）

```python
from langgraph.types import interrupt, Command

def review_node(state: State):
    # 跑到这里，把 draft 抛出去等人
    decision = interrupt({
        "draft": state["draft"],
        "question": "Approve or request changes?",
    })
    # decision 是人类回填的内容，恢复时才会拿到
    if decision["action"] == "approve":
        return {"approved": True}
    else:
        return {"messages": [{"role": "user", "content": decision["feedback"]}]}
```

恢复时用 `Command(resume=...)` 注入人类决策：

```python
# 第一次调用，跑到 interrupt 抛出
result = app.invoke({"messages": [...]}, config=config)
# result 里包含 __interrupt__ 字段，应用层渲染给用户

# 人类点了"批准"
app.invoke(
    Command(resume={"action": "approve"}),
    config=config,
)
```

**特点**：断点是**运行时决定的**（比如只有"金额 > 1 万"才需要审批），灵活度高得多。

---

## 五、工程落地要注意的 4 个坑

### 坑 1：State 里不要塞大对象

Checkpoint 是**全量序列化**写库的，State 里塞了 10MB 的文档原文，每个节点写一次 = 性能灾难。

**做法**：大对象写对象存储/Redis，State 只存 ID 或 URL。

### 坑 2：`thread_id` 是契约，必须严肃设计

- 一个用户的一次任务 = 一个 thread_id
- 不要用 user_id 当 thread_id（会串流）
- 建议格式：`{user_id}:{task_type}:{uuid}`

### 坑 3：HITL 的"等待"是异步的

中断后**进程不会傻等**，是直接返回。应用层要：
- 把 `thread_id` 存到自己的业务表里（关联工单/审批单）
- 通过 webhook / 轮询 / WebSocket 通知人类
- 人类回填后，**另起一次请求**调 `app.invoke(Command(resume=...), ...)`

### 坑 4：Checkpoint 表会爆

默认每个节点都写。一个长 Agent 跑 50 步 = 50 条 checkpoint。

**做法**：
- 生产环境用 Postgres，加 TTL 清理脚本（按 thread_id 最后更新时间）
- 或自定义 `Checkpointer`，只在关键节点写

---

## 六、生产环境必做的 4 件事

1. **加分区**：`checkpoints` 按 `thread_id` hash 分区，否则单表过亿后查询变慢。
2. **加 TTL job**：上面那个 DELETE 脚本每天跑一次，别让表无限膨胀。
3. **监控 blob 大小**：`SELECT pg_column_size(blob) FROM checkpoint_blobs ORDER BY 1 DESC LIMIT 10;` —— 找出谁在塞大对象。
4. **不要用同一个库**：checkpoint 库的写入 QPS 高且模式特殊，**别和业务库混**，单独一个 Postgres 实例（或至少独立 schema + 连接池）。

---

## 七、什么时候不要用 LangGraph 的 HITL

- 流程很短（1-2 步）：直接在应用层做暂停状态机更简单
- 不需要恢复历史：没必要引入 Postgres 依赖
- 团队不熟 LangChain 生态：心智成本可能 > 收益

---

## 八、其他 Checkpointer 选择

如果数据量大 / Postgres 不合适：

- **Redis Checkpointer**（社区版）：低延迟，但持久化弱，适合短任务
- **自定义 Checkpointer**：实现 `BaseCheckpointSaver` 4 个方法（`get_tuple` / `list` / `put` / `put_writes`），可以接 DynamoDB / MongoDB / 自家存储
- **关键点**：`put_writes` 必须是幂等的（idx + task_id 做唯一键）

---

## 九、Checkpoint + Subgraph：组合用法

子图的 checkpoint 落在 `checkpoint_ns = "subgraph_name:task_id"` 下。父图 checkpoint 透传到子图，**子图中断也能从中断点恢复**。详见 [../agents/subagent-patterns.md](../agents/subagent-patterns.md) 里的 Subgraph 一节。

```
checkpoint 表里：
  thread_id     | checkpoint_ns       | step
  task-001      | ""                  | parent step 3
  task-001      | "subgraph:abc"      | subgraph step 5  ← 子图状态
```

**注意**：子图里抛 `interrupt()`，父图状态是"半挂"——只有跑完的节点才更新父 state。详见 subagent-patterns 文档的"陷阱 5"。

---

## 十、扩展阅读

- [frameworks-comparison.md](frameworks-comparison.md) —— LangGraph 与其他框架横向对比
- [../agents/subagent-patterns.md](../agents/subagent-patterns.md) —— Subgraph 的 7 大设计陷阱
- [../rag/agentic-rag-implementation.md](../rag/agentic-rag-implementation.md) —— LangGraph 实现 CRAG / Self-RAG
- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/

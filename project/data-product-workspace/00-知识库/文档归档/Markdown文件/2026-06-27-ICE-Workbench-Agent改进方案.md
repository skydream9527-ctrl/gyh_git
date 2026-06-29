# ICE Workbench Agent 改进方案

> 📝 围绕 general / data-analysis 两个 agent,梳理了 skill 元数据、并行执行、子 agent 失败应对、工具失败处理、memory 机制、NL→SQL 职责耦合、模型改进评价七个方向。本文汇总**需要讨论的开放问题**。

---

# 一、skill 的 metadata 是否够用

## 现状

- skill metadata 载体是 SKILL.md 的 YAML frontmatter,由 `skill_svc.py:112-157` 解析
- 实际可用字段只有 `name` + `description`(description 里塞 Triggers 关键词列表)
- 辅助有 `INTRO.zh.md`(中文展示文案,给前端 picker 用)
- 发现机制两条路:`agent.json` 的 skills 字段(推荐 hint)+ `skills/INDEX.md`(全局索引,纯文本表格)

## 核心问题

1. **数量压力**:已 17 个 skill,领域跨度大(数据分析 / 文档处理 / 新闻收集),LLM 在 17 行里选,准确率下降
2. **重叠无优先级**:`feishu` / `feishu-pyramid-writer` / `data.an` 都能"写飞书报告",无互斥规则
3. **依赖不透明**:kyuubi 依赖 kyuubi-cli、feishu 依赖 feishu CLI、daily-news-collector 依赖 Tavily key——这些只在 SKILL.md 正文里,metadata 层不暴露,LLM 选了才发现不能用,浪费一轮工具调用
4. **关键词匹配脆弱**:Triggers 是关键词列表,用户说"跑个数看看"不命中任何 Triggers

## 改进方向

| 阶段 | 内容 |
|-|-|
| **短期(低成本)** | frontmatter 加 `dependencies` 字段(数组),runtime 渲染时标注"依赖未装",降低选中概率 |
| **中期(中成本)** | 加 `category` / `priority` / `mutually_exclusive_with`,解决重叠选择 |

---

# 二、同时处理两个问题如何执行

## 现状

- 完全串行,无并行能力
- `spawn_subagent` 是 `await asyncio.wait_for(...)` 同步阻塞,120s 超时
- 子 agent 内部工具也串行(`agent_runtime.py:172` 注释明确为审计确定性牺牲并行)
- 长任务用 `run_background`(异步),但**不回灌结果给父 agent**,只发通知

## 以"同时分析 BM 和 BF 的 DAU"为例

当前执行路径:串行处理 → 耗时翻倍(最坏 240s)、上下文不共享导致 BF 可能重复查 BM 已查数据、超时风险叠加

## 三种改进模式对比

| 模式 | 耗时 | 上下文共享 | 改动量 |
|-|-|-|-|
| 当前串行 spawn | 2×T | ❌ | 无 |
| 并行 spawn(`spawn_subagent_batch` + `asyncio.gather`) | max(T1,T2) | ❌(独立反而好) | 中 |
| 单 agent 多任务(改 SOP) | T | ✅ | 高 |

## 技术可行性确认

- `inflight_svc` 按 `(task_id, conv_id)` 加锁,子 agent 的 `conv_id = {parent_conv}::{run_id}`,**锁不冲突**,并行 spawn 技术可行
- 短期零代码方案:prompt 鼓励 general"能合并的合并",派一个子 agent 处理多命题

---

# 三、父 agent 如何应对子 agent 失败

## 现状

- 三层防线:错误码 + runtime 异常捕获 + prompt 约束
- **最弱环节**:父 agent 收到错误码后怎么做,完全靠 LLM 判断,无代码保障
- `spawn_routing.md` 只约束了"不要无脑透传",对失败场景无明确指引

## 三个风险场景

| 风险场景 | 说明 |
|-|-|
| **1. 无声失败** | 父 agent 可能把 "sub-agent exceeded 120s" 透传给用户,或假装成功编结论 |
| **2. 部分产物丢失** | 子 agent 超时可能已写 CSV/图表,但返回值只有 `{"error_code": "SUBAGENT_TIMEOUT"}`,**无 files_written 字段**,父 agent 不知道写了什么 |
| **3. 派单循环** | data-analysis 失败 → 换 zijian-data-analysis → 也失败(根因是 kyuubi 挂了),浪费 2×120s |

## 前置条件

需先量化失败频率(查 event_log / transcript):

- 失败率 < 5%:当前靠 LLM 自决可能够用
- 失败率 > 15%:失败恢复是高优先级

## 低成本改进(不依赖频率数据)

- `spawn_subagent` 失败返回值加 `files_written` 字段
- prompt 加失败应对决策树(重试 / 换 agent / 自己干 / 报告用户)

---

# 四、工具调用失败后的处理逻辑(重点)

## 完整的部分(基础链路 OK)

| 层 | 机制 | 位置 |
|-|-|-|
| 工具自身 | 返回 `{"error_code": "...", "message": "..."}` 不抛异常 | `tool_runner.py` 各工具 |
| 超时捕获 | `run_tool_with_timeout` + 工具级 floor | `llm_gateway.py:667-683` |
| 异常兜底 | `except Exception` 返回 `TOOL_ERROR` | 同上 |
| 归一化 | `normalize_tool_outcome` 把业务失败识别为 `success=False` | `llm_gateway.py:685-703` |
| 回灌 LLM | tool_result + `is_error: True` | `ws.py:1118-1126` |
| 审计 | event_log(WARN)+ tool_calls.jsonl | `ws.py:1064-1086` |

错误码分类清晰,四类:

- `*_NOT_CONFIGURED` / `*_NOT_INSTALLED` — 配置缺失(永久)
- `*_TIMEOUT` — 超时(可能临时)
- `*_FAILED` / `*_ERROR` / `*_CLI_ERROR` — 业务失败
- `VALIDATION_ERROR` — 输入错误

## 重点缺口一:不同错误码应给出不同"建议动作"

**现状**:错误码回灌给 LLM 时是原始的 `{"error_code": "KYUUBI_CLI_ERROR", "message": "kyuubi-cli not on PATH"}`。LLM 要自己从 message 文本推断该怎么做,而 message 是给开发者看的,不是给 LLM 看的。

**问题**:同一类错误,不同错误码应该有完全不同的应对,但现在没有结构化字段告诉 LLM:

| 错误码 | 正确应对 | 当前 LLM 可能的错误应对 |
|-|-|-|
| `KYUUBI_NOT_CONFIGURED` | 直接报告用户"CLI 未安装",不重试 | 反复重试(配置不会自己变好) |
| `SQL_BLOCKED` | 改 SQL(被安全规则拦截) | 重试同一个 SQL |
| `KYUUBI_TIMEOUT` | 可重试 1 次(可能网络抖动) | 直接放弃,或无脑重试 N 次 |
| `VALIDATION_ERROR` | 改参数 | 重试同参数 |
| `FEISHU_CLI_NOT_INSTALLED` | 报告用户 | 换工具(但没有等价替代) |

**根因**:错误码虽然分类了,但**缺一个"建议动作"字段**。现在靠 `tool_contract.md` 的 prompt 约束("看错误码决定下一步"),但 prompt 约束不如结构化字段可靠——LLM 可能不遵守,或遵守了但判断错。

**改进方向**:给错误返回值加 `recoverable` + `suggested_action` 字段:

```json
{
  "error_code": "KYUUBI_TIMEOUT",
  "recoverable": true,
  "suggested_action": "retry_once",
  "message": "..."
}
```

runtime 层或 prompt 层据此引导 LLM。这同时解决问题三(父 agent 应对子 agent 失败)——两者本质都是"LLM 收到错误后该怎么做,缺结构化指引"。

## 重点缺口二:失败后的上下文污染(副作用不清理)

**现状**:工具失败后,系统**不处理已产生的副作用**。对幂等工具(read/query)无所谓,对有副作用的工具是隐患。

**典型场景**:`write_file` 第一次写 report.md 成功,第二次因参数错失败 → report.md 只剩"后半段",第一次写的内容丢了。LLM 可能不知道第二次 write_file 是覆盖而非追加。

**更深的问题**:

- 无回滚机制——`write_file` / `feishu_publish` 等有副作用工具失败后,已产生的文件/已发布的文档不会被清理
- 无"已副作用清单"——LLM 不知道前序工具已经改了哪些状态,可能基于错误假设继续
- 跨工具状态一致性无保障——query 失败了,但前面 write 的中间文件还在,LLM 可能误用

**影响范围**:

- `write_file`:覆盖风险(中频)
- `feishu_publish`:重复发布风险(低频但后果严重,可能发两篇文档)
- `execute_python`:副作用相对小(沙箱内),但可能写了半截文件

**改进方向(分难度)**:

| 难度 | 方案 |
|-|-|
| **低成本** | `write_file` 加 `mode: "overwrite" | "append"` 参数(现在默认覆盖),LLM 显式选择,减少误覆盖 |
| **中成本** | 有副作用工具失败时,返回值带 `side_effects` 字段(如 `{"files_written": ["report.md"]}`),让 LLM 知道已经改了什么 |
| **高成本(暂不做)** | 事务性工具调用,失败自动回滚——对 LLM agent 场景过重 |

---

# 五、memory 写入有没有 policy

## 现状

- policy 存在,但全是 prompt 级软约束,代码层零校验
- `context-protocol.md` 明确了四类该写(user/feedback/project/reference)和五类不该写(SOP/可查事实/对话细节/过期规则/敏感数据)
- `_tool_memory_save` 和 `MemoryWriter.save_memory` 代码层只校验两件事:`type_` 是四类之一、`body` 非空

## 核心问题

代码完全不校验:敏感数据、与 system.md 重复、过期、body 长度、与已有 memory 冲突。

## 风险场景

| 风险 | 说明 |
|-|-|
| 1. **敏感数据泄露** | LLM 可能把用户随口说的 token 写进 memory,明文落盘 |
| 2. **memory 膨胀** | LLM 热情过高每轮都写,索引突破 200 行上限(policy 说控制,代码不强制) |
| 3. **冲突条目堆积** | 用户偏好变了,新旧 memory 共存,读取时都可能命中 |
| 4. **SOP 抄袭** | LLM 把 system.md 规则抄进 memory,重复注入浪费上下文 |

## 改进方向

- **低成本**:memory_save 加敏感词扫描(正则匹配 key/token/密码),命中拒绝写入
- **中成本**:写入前语义去重(新 memory 与同 scope 已有 memory 的 hook 做 token 重叠检测,重叠高则提示更新而非新增)
- **中成本**:加 `expires_at` / `last_verified_at` 字段,读取时标注"可能过期"

---

# 六、memory 有没有结构化字段

## 现状

结构化字段很薄:

| 字段 | 位置 | 代码是否使用 |
|-|-|-|
| name | frontmatter | ❌ 代码用文件名 |
| description | frontmatter | ❌ 代码不读 |
| metadata.type | frontmatter | ✅ 唯一被校验 |
| title | MEMORY.md 索引行 | ✅ 索引用 |
| hook | MEMORY.md 索引行 | ✅ 检索用 |

## 核心问题:三个关键字段缺失

1. **无时间字段**:没有 `created_at` / `updated_at` / `last_verified_at`,代码无法判断哪条过期,用户偏好变了无法按时间取最新
2. **无业务线/领域标签**:`metadata.type` 粒度太粗(只有四类),无法按业务线过滤
3. **description 字段未被利用**:frontmatter 里有但 `_rank_entries` 检索时不读,只看 slug + title + hook

## 判断:当前够用,但加两个字段性价比高

| 判断 | 说明 |
|-|-|
| **现在够用** | memory 数量少(单用户单 agent 通常 < 20 条),关键词匹配够准 |
| **建议加** | - `created_at` + `updated_at`:写入自动填,读取标注"X 天未验证",成本极低<br>- `domain`(可选):业务线标签,看 memory 增长情况再定 |

> 🔴 **不建议加**:`priority` / `confidence`(让 LLM 写入时纠结)、embedding 向量(20 条用 embedding 是杀鸡用牛刀)

---

# 七、memory 读取是全量还是检索

## 现状:检索式读取,算法朴素

读取流程(`ContextLoader._load_memory_dir`):

1. 读 MEMORY.md 索引(全量,但只是标题+hook,很小)
2. `_rank_entries` 按 query 关键词打分排序,取 top-5
3. 逐个读 top-5 的 .md 全文,拼进 context
4. 累计字节 > `_MAX_CONTEXT_BYTES`(500KB)则截断

检索算法特点:

- 纯关键词重叠(token 交集计数),无 TF-IDF,无语义
- 只看 slug + title + hook,**不看正文,不看 description**
- 无 query 时取前 N 条(文件系统顺序)
- 无命中时兜底取前 3 条

读取量控制:

| 机制 | 值 |
|-|-|
| memory_limit | 默认 5(每层) |
| _MAX_CONTEXT_BYTES | 500KB(三层总和) |
| _MAX_MEMORY_FILE_BYTES | 100KB(单文件) |

Task State 是**全量读取**,不走检索(单文件,policy 说控制 100 行)。

## 核心问题:检索算法三个弱点

1. **关键词匹配脆弱**:用户问"最近留存怎么样",memory hook 是"Q2 主攻视频体裁" → 零命中,走兜底取前 3 条
2. **无语义理解**:memory hook 是"报告风格偏好",query 是"怎么写汇报" → 零命中,但语义相关
3. **正文不参与检索**:关键信息在正文(如 Why 里的业务背景)检索不到

## 读取量大时的处理:字节截断,会丢信息

超 500KB 直接截断,后面的 memory 不读,只留"已截断"提示。LLM 不知道被截断了什么,可能基于不完整信息决策。

## 工业界常用压缩方式 + 适用性

| 方式 | 本项目现状 | 对 memory 适用性 |
|-|-|-|
| 摘要压缩(Summarization) | ✅ 已用于对话历史(`compaction_svc.py`) | 不适用(memory 已是精华,再压缩丢信息);可借鉴:长期未访问 memory 摘要成 hook |
| 检索增强(RAG/embedding) | ❌ 未用 | 中期可行,但当前 memory<20 条投入产出比低,>50 条时再上 |
| 分层加载(Lazy Loading) | ❌ 未用 | 短期高性价比:只加载索引,LLM 主动 read_memory 拉全文,省 90% token |
| 重要性衰减(Recency Decay) | ❌ 未用 | 低成本建议立即做:前提是先加时间戳,读取时按 `score = keyword_overlap × time_decay` |
| 上下文窗口分区 | 部分采用(500KB 是 memory 区预算) | 可改进:全局 token budget manager 动态分配各区 |
| 工具结果摘要 | ❌ 未用 | 间接相关,当前 memory 都是短文本暂不需要 |

## 推荐方案(按优先级)

| 优先级 | 方案 | 解决问题 | 成本 |
|-|-|-|-|
| P0 | memory 加 `created_at` / `updated_at` + 读取时间衰减 | 过期检测 + 偏好变更 | 低 |
| P1 | 检索时纳入 description 字段 | 提升检索召回 | 极低(改一行) |
| P2 | 分层加载(索引 + read_memory 工具) | 上下文膨胀 | 中 |
| P3 | embedding 语义检索 | 关键词匹配脆弱 | 中高(memory>50 条时) |
| P4 | 长期未访问 memory 自动摘要 | 索引膨胀 | 中 |

---

# 八、retry 在哪一层统一管理

## 性质:项目真实存在的缺口

这是一个**项目确实存在的不足**。现状:

- 三层(tool/agent/executor)都无自动 retry
- 唯一重试是用户手动点按钮(`ws.py:1330-1392`),且只在主循环有,子 agent 循环没有
- 对临时性错误(网络抖动导致的 `*_TIMEOUT`)直接失败,本应自动重试 1 次

## 项目是否存在相关问题:是

具体表现:

- kyuubi 查询偶发超时,LLM 收到 `KYUUBI_TIMEOUT` 后要么放弃要么瞎试,没有 executor 层兜底重试
- 主循环有手动重试,子 agent 循环连手动重试都没有——子 agent 工具失败只能靠 LLM 自决

## 是否值得向 mentor 提出:值得,但优先级中

理由:

- 这是影响用户体验的真实缺口(临时错误直接失败)
- 但严重程度取决于临时错误的发生频率——如果 kyuubi/feishu CLI 稳定,频率低,优先级可降
- 提出时建议带上"需先量化超时频率"的前提,避免盲目投入

> 💡 **提出方式**:不要单独提"加 retry",而是和问题九(error_type 分类)绑定——因为条件重试的前提是能区分临时/永久错误。

---

# 九、tool 失败是否返回结构化 error_type(根因)

## 性质:项目真实存在的缺口,且是问题八、十一的根因

这是四个问题里**最值得提出的**。现状:

- 返回扁平的 error_code 字符串,无 `error_type` / `recoverable` / `suggested_action` 字段
- error_code 命名隐含分类(如 `*_TIMEOUT` / `*_NOT_CONFIGURED`),但需 LLM 自己推断
- `*_CLI_ERROR` / `*_FAILED` 是大杂烩,临时错误和永久错误混在一起

## 项目是否存在相关问题:是,且是核心缺口

具体表现:

- LLM 收到 `KYUUBI_CLI_ERROR` 后,无法快速判断是 SQL 语法错(改 SQL)、连接错(可重试)还是权限错(报告用户)
- executor 层无法做条件重试(因为不知道错误是否可恢复)
- 父 agent 无法结构化应对子 agent 失败(之前 spawn 问题三的根因)

## 是否值得向 mentor 提出:值得,优先级高

理由:

- 这是问题八(条件重试)和问题十一(SQL 错误细分)的共同前提
- 改动可控:给错误返回值加 `error_type` + `recoverable` + `suggested_action` 三个字段,不破坏现有 error_code
- 收益面广:同时改善 LLM 恢复策略、executor 重试逻辑、子 agent 失败应对
- 与之前讨论的 spawn 问题三(父 agent 应对子 agent 失败)是同一个根因,可以合并提出

> 🔥 **提出方式**:作为"失败处理体系"的基础设施改进,而非孤立问题。

---

# 十、对 timeout、参数错误、SQL 错误是否有不同处理策略

## 需要拆开看

### 10a. Timeout 处理 —— 项目已做得较好,非缺口

- 双层超时(executor 30s + 工具内部 300s/320s)
- 工具级 floor 避免数据工具被误杀
- 超时后杀进程清理

> ✅ 这部分不值得提,项目设计合理

### 10b. 参数错误(VALIDATION_ERROR)—— 项目已做得好,非缺口

- 所有工具统一用 `VALIDATION_ERROR` + 明确 message
- 同步返回不抛异常

> ✅ 这部分不值得提

### 10c. SQL 错误细分 —— 项目真实缺口

- `SQL_BLOCKED`(被拦截)处理好,有独立错误码
- 但 `KYUUBI_CLI_ERROR` 是大杂烩:SQL 语法错、连接错、权限错、服务端 500 全混在一起
- LLM 只能从 stderr 原文推断错误性质
- kyuubi 无 `KYUUBI_EMPTY` 等价码(空结果直接返回 `rows: []`)

## 是否值得向 mentor 提出:值得,但依赖问题九

理由:

- SQL 错误细分是 data-analysis / ab-experiment 等数据 agent 的高频场景
- 但细分 SQL 错误的前提是先有 error_type 框架(问题九)
- 单独提"细分 SQL 错误"显得碎,应作为问题九的具体应用场景提出

> 💡 **提出方式**:作为问题九的落地案例——"有了 error_type 后,优先把 `KYUUBI_CLI_ERROR` 拆成 syntax/connection/permission 三类"。

---

# 十一、四个 tool 问题的重新分类

| 问题 | 性质 | 项目是否有缺口 | 是否值得提出 | 优先级 |
|-|-|-|-|-|
| 一、"不要重试自己"含义 | 概念澄清 | 否 | 不值得 | — |
| 二、retry 层级管理 | 真实缺口 | 是 | 值得(绑定问题九) | 中 |
| 三、结构化 error_type | 真实缺口(根因) | 是 | 值得 | 高 |
| 四、timeout/参数/SQL 策略 | 部分缺口 | 仅 SQL 细分 | 值得(作为问题九案例) | 中(依赖九) |

## 值得向 mentor 提出的核心议题

合并后其实只有**一个核心议题**:

> 工具失败处理缺少结构化 error_type 分类,导致 LLM 难判断恢复策略、executor 层无法做条件重试、SQL 执行错误混在大杂烩里。

这个议题下包含三个递进的改进点:

1. **(根因)** 加 `error_type` / `recoverable` / `suggested_action` 字段 —— 问题九
2. **(应用 1)** executor 层基于 error_type 做条件重试 —— 问题八
3. **(应用 2)** 把 `KYUUBI_CLI_ERROR` 细分为 syntax/connection/permission —— 问题十c

> 📝 而问题一(概念澄清)和问题十的 4a/4b(timeout、参数错误处理)是项目已做好的部分,提出时可作为"现状 baseline"说明,体现对现有设计的理解,而非作为改进点。

---

# 十二、data-analysis agent 如何把用户指令转化为 SQL

## 现状:data-analysis 的 NL→SQL 完整链路

data-analysis agent 把 NL→SQL 拆成了**五阶段 SOP**(`sop.md`),但**核心的 NL→SQL 翻译仍然由 LLM 在一个黑盒里完成**,没有真正的语义层。

### 关键发现:Phase 4 的 SQL 生成有两条路径

| 路径 | 说明 |
|-|-|
| **路径 A:LLM 直接写 SQL(主路径)** | - data-analysis 的 identity.md 和 sop.md 没有强制要求走 skill<br>- LLM 基于自己的知识 + 对话上下文直接生成 SQL<br>- 这正是文章里说的"**让理解自然语言和生成正确 SQL 耦合在一个黑盒里**" |
| **路径 B:走 nl-mapping-table-sql skill(映射表场景)** | - 只在用户明确提到"映射表/dim表/dm表/ads表/维度枚举"时触发<br>- 这个 skill **已经有了语义层的雏形**(见下文分析)<br>- 但只覆盖"映射表查询"这一窄场景,不覆盖 data-analysis 的主流程 |

## 是否出现了"职责耦合"问题

**答案:主路径(路径 A)出现了,且正是文章批评的问题;路径 B(nl-mapping-table-sql)已经部分解决了,但覆盖面太窄。**

### 路径 A 的问题(与文章完全吻合)

data-analysis 主流程让 LLM 同时做三件事:

1. **理解自然语言**:用户说"CC 消费 UV 近 14 天环比下跌" → 理解时间窗、指标、对比方式
2. **知道表结构**:CC 消费 UV 在哪张表?哪个字段?怎么 JOIN?
3. **生成正确 SQL**:写出语法正确、口径正确的 SQL

这三件事耦合在 LLM 的一个推理过程里。文章说的"一个出错,全盘皆输"在这里完全适用:

- LLM 记错表名 → SQL 报错或查错表
- LLM 记错指标口径(如把"消费 UV"当成"曝光 UV")→ SQL 跑通但结论错
- LLM 忘加分区过滤 → 全表扫描,超时

data-analysis 的 identity.md 用 **prompt 约束**缓解(如"数据唯一来源:结论必须基于当次 kyuubi 查询结果,不凭印象"),但这只是约束 LLM 行为,没有从架构上分离职责。

### 路径 B 的进步(nl-mapping-table-sql 已有语义层雏形)

nl-mapping-table-sql 这个 skill **已经实现了文章说的"语义层"理念**,虽然不完整:

**已有的语义层要素**

| 文章概念 | nl-mapping-table-sql 的实现 | 位置 |
|-|-|-|
| Class(业务实体) | 表名映射(用户说"多维指标表" → `dm_browser_multi_dimension_indicators_di`) | table-schema.md |
| Property(属性/维度) | 维度索引(用户说"启动方式" → `app_launch_way`) | dimension-index.md |
| Measure(度量/指标) | 指标定义(指标名 → 计算公式) | core-metrics-reference.md |
| 确定性引擎 | SQL 模板(参数替换,非 LLM 生成) | sql-templates.md |

**具体例子(对照文章)**

文章举的例子:"上个季度 VIP 客户的平均客单价"。

nl-mapping-table-sql 的处理方式:

1. LLM 只做**意图解析**:识别业务线(浏览器)、查询类型(维度枚举)、目标表(多维指标表)、维度字段(启动方式)
2. **查表结构文件**确认表/字段存在(强制校验,不存在则终止)
3. **查 SQL 模板**,参数替换生成 SQL(确定性,非 LLM 生成)

这正是文章说的"**让 LLM 只做 NL → 结构化语义表达的翻译,让确定性引擎做语义表达 → SQL 的编译**"。

**但路径 B 的局限**

1. **覆盖面窄**:只覆盖"映射表查询"(dim/dm/ads 表的维度枚举、指标聚合、多表关联),不覆盖 data-analysis 主流程的"自由分析"(如异动归因、趋势预测)
2. **模板是硬编码的**:SQL 模板是预先写死的 markdown,不是真正的"语义模型"——加新表/新指标要手动写模板,无法动态组合
3. **LLM 仍参与 SQL 生成**:Step 3A-6 说"基于 SQL 模板,替换参数,生成最终 SQL",这个"替换参数"还是 LLM 做的,不是确定性引擎做的
4. **data-analysis 主流程不强制走 skill**:identity.md 只说"SQL 走 kyuubi_query",没说"必须先走 nl-mapping-table-sql"

## 是否应用了"语义层"方案

**答案:部分应用,但停留在"文档型语义层",未达到"模型型语义层"。**

### 现状:文档型语义层

nl-mapping-table-sql 的语义层是**一堆 markdown 文档**:

- table-schema.md(表结构)
- dimension-index.md(维度索引)
- core-metrics-reference.md(指标定义)
- sql-templates.md(SQL 模板)

LLM 通过 `read_skill` 读这些文档,然后**自己理解 + 自己生成 SQL**。这比"纯靠 LLM 脑补"好(有事实依据),但仍然是:

- LLM 读文档 → LLM 理解 → LLM 生成 SQL
- 文档是"参考",不是"约束"
- 没有确定性引擎消费结构化语义表达

### 文章说的模型型语义层

文章说的是:

```
LLM 输出结构化意图 → 确定性引擎消费 → 生成 SQL
{class, filters, measures} → 语义模型 → SQL
```

这需要:

1. **结构化的语义模型**(不是 markdown,是 JSON/YAML + 代码逻辑)
2. **确定性编译器**(把结构化意图翻译成 SQL,非 LLM)
3. **LLM 只输出意图**(不输出 SQL)

项目目前**只有第 1 点的雏形(markdown 文档),缺第 2 点和第 3 点**。

## 改进方向(对照文章)

| 文章建议 | 项目现状 | 差距 | 可行性 |
|-|-|-|-|
| 职责分离(LLM 翻译 + 引擎编译) | 主路径未分离,skill 路径部分分离 | 主路径需改造 | 中(需建编译器) |
| 语义层(Class/Property/Measure) | 有 markdown 文档雏形 | 需升级为结构化模型 | 中(已有素材) |
| 确定性引擎 | 无,LLM 生成 SQL | 需新建 | 中高(模板引擎可起步) |
| LLM 只输出结构化意图 | LLM 直接输出 SQL | 需改 prompt + 加意图解析工具 | 中 |

### 务实建议

完全照搬文章的"语义层 + 编译器"架构成本高,但可以**渐进式**:

1. **短期**:把 nl-mapping-table-sql 的 SQL 模板从"LLM 参考读"升级为"LLM 填参数 + 代码渲染"——LLM 只输出 `{template_id, params}`,代码做模板替换。这实现了"确定性引擎"的雏形。
2. **中期**:把 table-schema.md / dimension-index.md 升级为结构化 YAML(已有 search/data_tables.yaml 雏形),代码可解析校验,而非 LLM 读 markdown。
3. **长期**:建完整的语义模型(Class/Property/Measure)+ 编译器,覆盖 data-analysis 主流程。

---

# 十三、项目是不是只有自己运行测试的数据(重点)

## 答案:是的

项目没有 NL→SQL 的 benchmark,只有单元测试和少量 skill 级 evals,且都不覆盖 data-analysis 的 NL→SQL 准确率评测。

## 现状:三类测试,都不含 NL→SQL benchmark

### 1. 后端单元测试(backend/tests/)

- 约 45 个测试文件,覆盖:auth、conversation、tool_runner、agent_runtime、compaction、storage 等
- **都是机制测试**(如"plan_mode 是否过滤了 write 工具""compaction 是否保持 tool_use/tool_result 配对")
- **没有 NL→SQL 准确率测试**:搜 `kyuubi` / `nl_mapping` / `sql` / `nl2sql`,命中的测试都是机制相关(如 skill 是否 task-scoped),不测 SQL 生成质量

### 2. Skill 级 evals(仅 2 个 skill 有)

- `skills/text2html2png/evals/evals.json`
- `skills/mify-model-gateway/evals/evals.json`
- 格式:`{prompt, expected_output, assertions}`(断言式,人工评判)
- **nl-mapping-table-sql 没有 evals**(这是最需要 benchmark 的 skill)
- **data-analysis agent 没有 evals**

### 3. 无标准 benchmark 数据集

- 没有 Spider / Bird / WikiSQL 等公开 NL→SQL benchmark 的适配
- 没有自建的"问题 → 正确 SQL" golden set
- 没有线上 case 回归集

## 问题分析

### 问题 1:NL→SQL 准确率无法度量

- data-analysis 主路径(路径 A)的 SQL 生成质量**完全无法量化**
- 不知道准确率是多少,不知道改了 prompt 是变好还是变坏
- 这和文章说的"一个出错全盘皆输"呼应——连"出错了"都难以系统发现

### 问题 2:nl-mapping-table-sql 有语义层雏形却无 evals

- 这个 skill 是最接近"可度量"的(有表结构、有模板、有标准答案)
- 却没有 evals,无法验证"LLM 意图解析 + 模板匹配"的准确率
- 如果要做问题十二说的"语义层升级",没有 benchmark 无法验证改进效果

### 问题 3:evals 体系存在但不普及

- mify-model-gateway 的 evals 格式是好的(`prompt + expected_output + assertions`)
- 但只有 2 个 skill 用了,且是人工断言,非自动评分
- 没有 eval runner(自动跑 evals + 打分的脚本)

## 工业界常见做法 + 适用性

| 做法 | 说明 | 项目适用性 |
|-|-|-|
| 公开 benchmark(Spider/Bird) | 学术 NL→SQL 数据集,有标准答案 | ❌ 不适用:项目是内网业务表,schema 和公开 benchmark 完全不同 |
| 自建 golden set | 从线上 case 提取"问题→正确SQL",人工标注 | ✅ 高适用:但需人工投入,可从 nl-mapping-table-sql 的模板场景起步 |
| LLM-as-judge | 用另一个 LLM 评判生成 SQL 的正确性 | ✅ 中适用:可作为 golden set 的补充,降低人工标注成本 |
| 执行正确性 | 跑 SQL,对比结果行数/数值 | ⚠️ 部分适用:需测试库,且"结果对"不等于"口径对" |
| 断言式 evals | 人工写 assertions(项目现有格式) | ✅ 已有,但需推广到 nl-mapping-table-sql 和 data-analysis |

## 改进方向

| 阶段 | 内容 |
|-|-|
| **短期(低成本,高价值)** | - 给 nl-mapping-table-sql 补 evals:从现有 SQL 模板反推"问题→模板ID→参数→正确SQL"的 golden set。这个 skill 有结构化模板,最容易建 benchmark<br>- 复用 mify-model-gateway 的 evals 格式,加一个 eval runner 脚本自动跑 |
| **中期(中成本)** | - 给 data-analysis agent 建 golden set:从历史成功任务里提取"用户命题→最终SQL",人工标注正确性<br>- 用 LLM-as-judge 做初步评分,人工复核边界 case |
| **长期(高成本)** | - 建回归测试 CI:每次改 prompt / 改 skill,自动跑 evals,对比准确率变化<br>- 这也是问题十二(语义层升级)的前提——没有 benchmark,语义层改了也不知道好不好 |

---

# 议题关联性

> 📝 **两组强耦合**:
> 1. 工具失败处理(议题三/八/九/十)本质是一个核心议题——缺结构化 error_type,是 LLM 恢复策略、executor 重试、子 agent 失败应对、SQL 错误细分的共同根因
> 2. 语义层与评价(议题十二/十三)强耦合:要做语义层升级,必须先有评价方法;反之 benchmark 应优先建在 nl-mapping-table-sql 上
> **建议讨论顺序**:先定评价方法 → 再推语义层改造;先加 error_type → 再做条件重试和 SQL 细分

---

*本文档由飞书文档导出，原链接: https://mi.feishu.cn/wiki/QmBwwFLwZiaPXwk0Vzlc23Ognxf*
*导出时间: 2026-06-27*

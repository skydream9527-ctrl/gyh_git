# nl-sql 取数 Agent 效果评测方案

> **定位**:本篇是 [04-business-eval-pipeline.md](04-business-eval-pipeline.md) 通用方法论在**取数 / SQL 生成**场景的落地。黄金集分层、CI 集成、A/B、在线监控这些**通用机制直接复用 04**;本篇只写**取数 Agent 特有**的部分——尤其"SQL 正确性到底怎么判"。
>
> 对应目标:Q3「nl-sql 覆盖 80% 日常取数、准确率 90%+」——本方案给出这两个数字**可度量的定义**。
>
> 被评对象:上游检索层 [sql-kb](../../../sql-kb/)(历史需求→相似 SQL)+ 下游生成层(LLM 写 SQL 草稿)。

标注:文中 text-to-SQL 评测指标(Execution Accuracy 等)为业界公开方法归纳,已按理解重述。

---

## 一、取数 Agent 为什么不能照搬通用评测

通用 agent 评测默认"有一个标准答案,比一比就行"。取数场景**这个前提基本不成立**,五个特有难点:

| 难点 | 说明 | 对评测的影响 |
|------|------|------|
| **同需求多种正确 SQL** | `count(distinct uid)` vs 子查询去重,写法不同结果一样 | 不能比字符串,要比**执行结果** |
| **结果随数据变** | 同一 SQL 今天跑和明天跑结果不同 | 要固定**数据快照 / 分区** |
| **不能在生产库乱跑** | 评测批量执行 SQL 有成本和风险 | 要**样本库 / LIMIT / dry-run** |
| **口径"看着对其实错"** | 能跑出数,但用错了表、指标定义错 | 必须对**指标口径字典**校验,不能只看"能跑" |
| **探索型 vs 官方口径型** | 探索取数没有唯一答案;官方口径取数有权威定义 | 两类**验收标准不同**(你在 [Agent 取数复盘](../../data-analysis/methods/) 里已有这个区分) |

> 结论:取数 Agent 评测的核心不是"字符串对不对",而是**"结果对不对 + 口径对不对 + 安全不安全"**。

---

## 二、分层评测框架(映射到取数链路)

沿用 [agent-evaluation 的 4 层框架](README.md),具体到 nl-sql:

```
需求描述
   │
   ▼  ┌─────────────────────────────────────────────┐
   │  │ Layer 1  检索层评测（sql-kb）                │
   │  │   给需求 → 召回的历史相似 SQL / 表 命中吗？   │
   │  │   指标：Recall@K、命中表覆盖率                │
   │  └─────────────────────────────────────────────┘
   ▼  ┌─────────────────────────────────────────────┐
   │  │ Layer 2  生成层评测（LLM 写 SQL）            │
   │  │   生成的 SQL 正确吗？（见第三节五层判定）     │
   │  │   指标：Execution Accuracy、口径正确率        │
   │  └─────────────────────────────────────────────┘
   ▼  ┌─────────────────────────────────────────────┐
   │  │ Layer 3  端到端评测                          │
   │  │   需求 → 最终 SQL → 结果，能直接用吗？        │
   │  │   指标：一次采纳率、返工率                     │
   │  └─────────────────────────────────────────────┘
   ▼  ┌─────────────────────────────────────────────┐
      │ Layer 4  在线监控                            │
      │   真实使用中的采纳率/返工率/慢查询/口径事故   │
      └─────────────────────────────────────────────┘
```

**为什么要分检索层和生成层单独评**:如果端到端错了,得知道是"没检索到对的参考"(Layer 1 问题)还是"参考对但 SQL 写错"(Layer 2 问题)。分层才能定位,否则只能盲调。检索层直接影响下游——检索层 Recall 上不去,生成层再强也没用。

---

## 三、核心:SQL 正确性怎么判(五层判定)

这是取数评测最难、也最该讲清楚的一环。从易到难五层,**逐层加严**:

```
① 能执行吗          语法对、表/字段存在        → 静态检查 + dry-run
② 结果对吗          结果集与参考 SQL 一致       → Execution Accuracy（核心）
③ 口径对吗          用对表、指标定义符合字典     → 口径校验（规则 + 人工/LLM）
④ 安全高效吗        无全表扫描、分区裁剪、不碰敏感表 → 静态规则
⑤ 满足需求吗        回答了用户真正想问的         → LLM-as-Judge / 人工
```

### 3.1 核心指标:Execution Accuracy(EX)

业界 text-to-SQL 主流用两类指标:

| 指标 | 怎么算 | 适不适合取数 |
|------|--------|------|
| **Execution Accuracy(EX)** | 把生成 SQL 和参考 SQL 都在库上执行,**比结果集是否一致** | ✅ 首选。对"多种写法同结果"鲁棒 |
| Exact / Component Match | 比 SQL 结构(字符串/语法树) | ❌ 不用。同结果不同写法会误判为错 |

**取数场景优先 EX**:我们不关心 SQL 长什么样,只关心跑出来的数对不对。

结果集比对要**规范化**后再比(否则列顺序、浮点精度、排序会误判):

```python
def result_match(df_pred, df_gold) -> bool:
    def norm(df):
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]      # 列名归一
        df = df.round(6)                                   # 浮点精度对齐
        df = df.sort_index(axis=1)                         # 列顺序无关
        df = df.sort_values(list(df.columns)).reset_index(drop=True)  # 行顺序无关
        return df
    return norm(df_pred).equals(norm(df_gold))
```

> 除非需求明确要求排序(`ORDER BY`),否则行序不该影响判定。

### 3.2 口径校验(取数特有,最容易漏)

"能跑出数"不等于"口径对"。比如统计 DAU 用错了活跃标记字段,SQL 完美执行、结果是错的。所以要对 [指标口径字典](../../数据资产/指标口径字典/) 做校验:

- **表级**:用的表是不是该口径的权威表?(如"有效 DAU"必须来自指定聚合表)
- **字段级**:是否用了口径字典规定的过滤条件(如 `is_app_dau_2024=1`)?
- **落地**:把口径字典变成可执行的检查规则,或作为 LLM-judge 的 rubric。

这是取数 Agent 和普通 agent 评测最不一样的地方——**正确性必须锚定到组织的口径定义,不能只看技术执行**。

### 3.3 安全 / 效率静态检查(红线,直接短路)

生成的 SQL 上生产前,静态扫一遍:

```python
def static_check(sql: str) -> list[str]:
    issues = []
    low = sql.lower()
    if "limit" not in low and is_探索型(sql):
        issues.append("探索查询无 LIMIT，可能全表扫描")
    if not has_partition_filter(sql):        # 检查是否带 dt/date 分区过滤
        issues.append("缺分区过滤，可能全分区扫描")
    for t in SENSITIVE_TABLES:               # 敏感表白名单
        if t in low:
            issues.append(f"命中敏感表 {t}，需权限确认")
    return issues
```

安全红线(碰敏感表、无分区裁剪的大表全扫)应像 04 说的那样**直接判 0、短路**,不再往下评。

---

## 四、黄金集建设(SQL 版)

分层沿用 [04 的 Tier 1-4](04-business-eval-pipeline.md);取数特有的是**标准答案怎么来**和**两类需求分开**。

### 4.1 标准答案的来源(你已经有资产)

| 来源 | 说明 |
|------|------|
| **已验证的交付 SQL** | 历史真实取数中"跑对过、业务认过"的 SQL,就是权威参考 |
| **[SQL 模板库](../../数据资产/SQL模板库/)** | 参数化模板 = 高频需求的标准答案 |
| **[指标口径字典](../../数据资产/指标口径字典/)** | 口径校验的判定依据 |
| **失败回流** | 线上答错/被返工的需求,人工修正后入集 |

### 4.2 关键:探索型 vs 官方口径型分开

```
官方口径型（如"有效 DAU""财收流水"）
  → 有唯一权威答案 → 用 Execution Accuracy 严格判（结果必须一致）

探索型（如"看看哪类内容涨得快"）
  → 没有唯一答案 → 用 LLM-as-Judge + 人工判（需求满足度 / 口径合理性）
```

黄金集每条都标 `type: 官方口径型 | 探索型`,评分管线据此走不同判定路径。

### 4.3 标注 schema(直接抄)

```yaml
# tests/golden/取数/T-SQL-001.yaml
id: T-SQL-001
category: 取数
type: 官方口径型          # 官方口径型 | 探索型
difficulty: medium
source: 交付_2026_06     # 可追溯

input:
  requirement: "统计双端信息流最近 30 天有效 DAU 分天趋势"
  biz_line: 内容

expected:
  # 官方口径型：给权威 SQL + 结果特征
  reference_sql_file: gold_sql/T-SQL-001.sql
  must_use_tables:
    - iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
  must_have_filters:
    - "is_dau_feed_dapan_2024 = 1"     # 口径字典规定
  result_shape:
    columns: [dt, feed_dau]
    row_count_range: [28, 31]           # 30 天左右
    sanity: "feed_dau 在 2000万~3000万量级"

safety:
  - "必须带 date 分区过滤"
  - "不得查询用户明细表"

scoring_weights:
  execution_accuracy: 0.5   # 结果对不对（官方口径型权重最高）
  caliber_correct: 0.3      # 口径对不对
  safety: 0.2
```

---

## 五、评分管线(模板 / 伪代码,非直接可运行)

> ⚠️ 本文的 Python 代码是**结构模板**,用于讲清评分的编排逻辑;其中 `run_on_snapshot` / `check_caliber` / `is_探索型` / `has_partition_filter` / `weighted_sum` / `llm_judge_sql` / `dry_run` 等均为**未实现的占位函数**,需按你的环境补齐后才能运行。(第三节的 `result_match` 是完整实现,可直接用。)

短路逻辑:先跑便宜的静态检查,红线挂直接 0;再执行比对;探索型才走 LLM-judge。

```python
def evaluate_sql_case(case, gen_sql):
    score = {}

    # ① 静态检查（最便宜）——安全红线短路
    issues = static_check(gen_sql)
    score["static_issues"] = issues
    if any(is_red_line(i) for i in issues):
        return {**score, "final": 0, "reason": "safety_violation"}

    # ② 能否执行（沙箱 / 样本库 / LIMIT）
    ok, err = dry_run(gen_sql)
    score["executable"] = ok
    if not ok:
        return {**score, "final": 0, "reason": f"exec_error: {err}"}

    if case.type == "官方口径型":
        # ③ Execution Accuracy：结果集比对
        df_pred = run_on_snapshot(gen_sql)
        df_gold = run_on_snapshot(load_sql(case.expected.reference_sql_file))
        score["execution_accuracy"] = result_match(df_pred, df_gold)
        # ④ 口径校验：对照口径字典
        score["caliber_correct"] = check_caliber(gen_sql, case.expected)
    else:
        # 探索型：无唯一答案 → LLM-as-Judge（见 02 章）
        score.update(llm_judge_sql(case.input, gen_sql, rubric=case.expected))

    score["final"] = weighted_sum(score, case.scoring_weights)
    return score
```

> LLM-as-Judge 的正确用法、偏见与校准见 [02-evaluation-methods.md](02-evaluation-methods.md) / [llm-as-judge.md](llm-as-judge.md)。

---

## 六、指标体系与 Q3 目标的可度量定义

把"准确率 90%""覆盖 80%"翻译成能算的指标:

| Q3 目标 | 可度量定义 | 怎么算 |
|---------|-----------|--------|
| **准确率 90%+** | 官方口径型需求的 **端到端 Execution Accuracy ≥ 90%** | 黄金集里官方口径型题,结果集一致的占比 |
| **覆盖 80% 取数** | 需求类型覆盖率 | 把日常取数归类,统计 Agent 能正确处理的类型占比 |

分层指标总表(建议监控的):

| 层 | 指标 | 目标参考 |
|----|------|---------|
| 检索层 | Recall@5(期望参考 SQL 在 top-5) | ≥ 85% |
| 生成层 | Execution Accuracy(官方口径型) | ≥ 90% |
| 生成层 | 口径正确率 | ≥ 95%(口径错是事故) |
| 生成层 | 安全红线违规数 | = 0 |
| 端到端 | 一次采纳率(直接可用不改) | 逐步提升 |
| 端到端 | 返工率(需大改/重写) | 逐步下降 |

> **口径正确率的目标比准确率还高**——因为口径错是"看着对的错",最危险,一次都不能容忍进生产。

---

## 七、在线监控(取数特有指标)

除了 04 讲的通用监控,取数 Agent 要额外盯:

```
红色（必报警）:
   - 口径错误事故 > 0（用错口径出数并被采用）
   - 敏感表越权访问
   - 生成 SQL 导致慢查询/全表扫描拖垮集群

黄色（每天看）:
   - SQL 采纳率（直接用 / 小改 / 重写 三档占比）
   - 返工率
   - 执行失败率

绿色（每周看）:
   - 各需求类型的准确率趋势
   - 检索层 Recall 趋势
```

**"采纳率"是取数 Agent 最真实的效果信号**:用户是直接拿去跑,还是改几笔,还是推翻重写。它比任何离线分数都贴近"真用起来了没"。这类反馈应自动回流成黄金集(见 04 的失败回流机制)。

---

## 八、1 周冷启动(取数版)

对齐 04 的最小可用版,取数化:

```
Day 1-2  从历史交付里挑 30 个真实取数需求，配上"已验证过的权威 SQL"
         标注 type（官方口径型/探索型）+ 涉及表 + 口径 + 红线
Day 3    写静态检查（分区/LIMIT/敏感表）+ 结果集比对函数 result_match()
Day 4    接 CI：每次改 nl-sql skill / prompt 跑一次官方口径型 30 题
Day 5-7  接一个样本库/快照做 dry-run + 执行比对；采纳率埋点上线
```

一周后你有:30 题黄金集(区分两类)+ 执行比对 + 口径校验 + 采纳率埋点。**准确率 90% 从此有客观数字,不再靠感觉。**

---

## 九、取数 Agent 评测特有的坑

1. **只比字符串** → 同结果不同写法误判。**必须用 Execution Accuracy。**
2. **在生产库跑评测** → 成本/风险失控。**用样本库或固定分区快照。**
3. **只看"能跑"不看口径** → 放过"看着对的错"。**必须对口径字典校验。**
4. **结果随日期漂移** → 今天过明天挂。**固定数据快照 + 固定日期参数。**
5. **探索型硬套标准答案** → 误杀合理的探索。**分型评,探索型走 LLM-judge/人工。**
6. **只评生成、不评检索** → 端到端错了定位不到。**检索层 Recall 单独监控。**

---

## 十、落地清单

```
□ 1. 从历史交付挑 30 题，标 type / 权威SQL / 涉及表 / 口径 / 红线
□ 2. result_match() 结果集规范化比对写好
□ 3. 静态检查（分区裁剪 / LIMIT / 敏感表白名单）
□ 4. 口径校验对接指标口径字典
□ 5. 官方口径型 → EX 判；探索型 → LLM-judge
□ 6. 样本库 / 分区快照，dry-run 环境
□ 7. 采纳率 / 返工率埋点，失败回流入黄金集
□ 8. 检索层 Recall@5 单独监控（sql-kb）
□ 9. 准确率/口径正确率纳入 CI，跌破阈值告警
```

---

## 延伸阅读

- 通用评测落地(黄金集/CI/A/B/在线监控) → [04-business-eval-pipeline.md](04-business-eval-pipeline.md)
- 评测方法(LLM-as-Judge 等) → [02-evaluation-methods.md](02-evaluation-methods.md)、[llm-as-judge.md](llm-as-judge.md)
- 评测分层框架 → [README.md](README.md)
- 在线 A/B → [../../ab-testing/](../../ab-testing/)
- 被评检索层 → [sql-kb 项目](../../../sql-kb/)、[sql-kb 的 RAG 原理](../rag/RAG原理与实现-以SQL需求库为例.md)
- 标准答案来源 → [数据资产/SQL模板库](../../数据资产/SQL模板库/)、[数据资产/指标口径字典](../../数据资产/指标口径字典/)
- Agent 取数复盘经验 → [../../data-analysis/methods/](../../data-analysis/methods/)

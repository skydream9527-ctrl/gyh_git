# 自建数据分析 Agent

都江堰（djy）自建信息流业务的数据分析 Agent。专注「自建组」与「火山组」对比、消费下钻、内容/作者/版本归因等场景。

> 知识来源：cortex-addon `projects/data_analysis_agent/{data-analysis-report,djy-data-query}` 两个 skill。

## 特点

- **统一取数模式**：所有 SQL 都把 `model.sql`（约 220 行字段定义）作为 CTE 子查询，外层只做维度分组 + 指标聚合 — 一次写对，跨任务口径自动一致
- **维度 / 指标字典**：60 个维度 + 100+ 指标的权威清单（含派生指标公式），由 [metrics/dimensions.csv](knowledge/metrics/dimensions.csv) / [metrics/indexes.csv](knowledge/metrics/indexes.csv) 提供
- **7 大分析框架**：P0 下钻 / P1 转化 / P1 对比 / P2 异动 / P2 筛选 / P3 假设 / P3 链路，每个 Phase 1 子任务必须命中且仅命中一个

## 工作流（5 阶段，每阶段需用户确认）

| Phase | 主要动作 | 工具 |
|---|---|---|
| 0 · 需求澄清 | 1~3 个澄清问题 → 输出分析框架 | 纯对话；含飞书链接走 `feishu fetch` |
| 1 · 取数 | CTE 拼 SQL → kyuubi 跑 → 落 CSV → 异常门 | `read_agent_knowledge` + `kyuubi_query` + `write_file` |
| 2 · 可视化 | 趋势 / 分布 / 对比 / 热力 | `execute_python` 沙箱 |
| 3 · 飞书报告 | 5 项自检 → 创建 docx → 嵌图 | `feishu_publish` + `feishu_upload_image` |

详见 [`prompt/identity.md`](prompt/identity.md)、[`prompt/sop.md`](prompt/sop.md) 与 [`prompt/analysis-frameworks.md`](prompt/analysis-frameworks.md)。

## 目录

```
zijian-data-analysis/
├── agent.json
├── README.md
├── prompt/
│   ├── identity.md              # v3 身份与关键承诺
│   ├── sop.md                   # 主 SOP（5 阶段流程）
│   ├── analysis-frameworks.md   # 7 大分析框架
│   └── cards.md                 # 经验卡（自动累积）
└── knowledge/                   # 通过 read_agent_knowledge 工具读取
    ├── index.yaml
    ├── sql/
    │   ├── model.sql            # 都江堰 DAU 用户消费明细底表 SELECT 模板
    │   ├── cte_template.md      # CTE 拼接模式 + 5 项硬约束
    │   └── examples.md          # 4 条示例 SQL（实验组 / 体裁 / DAU / 实验×体裁交叉）
    ├── metrics/
    │   ├── dimensions.csv
    │   └── indexes.csv
    └── tables/
        └── djy_dau_user_consum_index_di.md
```

## 关键约束（5 条）

1. **所有 SQL 必须以 model.sql 为 CTE**，外层不重写业务逻辑
2. **时间分区显式**（`WHERE date BETWEEN ... AND ...`，YYYYMMDD 整数）
3. **fieldType=5 维度做过滤时还原完整 CASE WHEN**，禁止凭印象只取部分值
4. **fieldType=4 派生指标外层运算**（如 `SUM(all_consum_pv)/NULLIF(SUM(consum_pv),0)`）
5. **节假日 / AB 实验 / 数据延迟**写进报告免责，不放进结论

## 与现有 Agent 的关系

| Agent | 覆盖范围 | 用什么取数 |
|---|---|---|
| **zijian-data-analysis**（本 Agent） | 仅都江堰自建信息流 | model.sql CTE 模式 |
| `data-analysis` | BM/BF/CC 三业务线（NL→SQL） | `nl-mapping-table-sql` skill |
| `volcano-abtest` | 火山引擎 ABtest 实验 | `datum` CLI |
| `ab-experiment` | AB 显著性下钻 | knowledge/sql_templates |

如果用户提到自建/火山实验组对比、都江堰、djy_rec_expid → 走本 Agent；
如果是 NH / MCC / newhome 内容中心或浏览器其他业务线 → 走 `data-analysis` 或 `volcano-abtest`。

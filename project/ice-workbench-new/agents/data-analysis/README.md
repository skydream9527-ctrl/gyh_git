# data-analysis Agent

互联网内容分发与浏览器工具赛道的数据分析师，覆盖 **BM/BF/CC** 业务线（SR/NV 因 SQL 索引未配齐暂不支持）。

## 能力栈

| 层 | 能力 | 实现 |
|---|---|---|
| 取数 | NL → SQL → kyuubi 执行 | `nl-mapping-table-sql` skill + `kyuubi_query` 工具 |
| 落地 | CSV / Excel / SQL 留档 | `write_file` 工具 |
| 统计 / 预测 / 可视化 | NL → Python → 沙箱执行 | `nl-python` skill + `execute_python` 工具 |
| 报告 | 飞书 docx + 嵌图 | `feishu_publish` + `feishu_upload_image` |

## 8 分析范式

每个 Phase 2 子任务必带 1 个范式 tag。详见 [`prompt/analysis-paradigms.md`](prompt/analysis-paradigms.md) 与 [`prompt/paradigms/*.md`](prompt/paradigms/)。

| # | Paradigm | SQL | Python? | 详见 |
|---|---|---|---|---|
| 1 | 对比分析 | ✅ | 可（bootstrap CI / KS test） | [01-comparative.md](prompt/paradigms/01-comparative.md) |
| 2 | 拆解归因 | ✅ | 可（非线性 / SHAP） | [02-decomposition.md](prompt/paradigms/02-decomposition.md) |
| 3 | 波动分析 | ✅ | 必（STL 周期剥离） | [03-fluctuation.md](prompt/paradigms/03-fluctuation.md) |
| 4 | 漏斗分析 | ✅ | 可（Sankey / 存活分析） | [04-funnel.md](prompt/paradigms/04-funnel.md) |
| 5 | 分布分析 | ✅ | 必（gini / 双峰检测） | [05-distribution.md](prompt/paradigms/05-distribution.md) |
| 6 | 趋势分析 | ✅ | 必（变点 / STL） | [06-trend.md](prompt/paradigms/06-trend.md) |
| 7 | 留存分析 | ✅ | 可（cohort 聚类） | [07-retention.md](prompt/paradigms/07-retention.md) |
| 8 | 预测分析 | 8a-c | 必 8d/8e/8f | [08-predictive.md](prompt/paradigms/08-predictive.md) |

## SOP（5 阶段，每阶段必须用户确认）

1. **命题澄清** — 多轮对话问「观察 + 问题 + 决策目的」
2. **任务拆解** — 按"业务命题 → 范式组合"表起草，每 T 必带 paradigm tag
3. **单任务 checklist** — 业务线 / 指标 / 时间 / 维度 / 对标 / 读者
4. **SQL → Python → 校对**（每个子任务循环）
   - 4a 生成 SQL → 4b 执行 kyuubi → 4c 落 CSV → 4d 异常门
   - 4e 生成 Python（按范式 tag）→ 4f 沙箱执行 → 4g 用户校对关键数字
5. **综合报告** — 7 项自检 → `feishu_publish` → `feishu_upload_image` 嵌图

详见 [`prompt/system.md`](prompt/system.md)。

## 沙箱（execute_python）

- venv：`backend/.venv-sandbox/`，bootstrap 一次：`make install-sandbox`
- 运行时：每次调用一个新进程，无状态
- 限制：CPU 60s / 内存 1GB / 文件 50MB / 网络断开
- 工作目录：`<task_workspace>/files/output/`（相对路径写在这里）
- 产物：`data/T{n}_*.csv` / `charts/T{n}_*.png` / `models/T{n}_*.pkl`

详见 [`/skills/nl-python/SKILL.md`](../../skills/nl-python/SKILL.md)。

## 关键约束

- Python 永远是 SQL 的下游，**不直连数据源**
- 预测必带置信区间 + 显式假设 + 失效条件 + 置信度
- SR/NV 业务线 SQL 索引未配齐 → 终止并提示 gongyunhe
- 结论必须基于本次 kyuubi + Python 沙箱结果，不凭印象
- 写飞书前读 `feishu/reference/extended-markdown.md`，避免 `overwrite`

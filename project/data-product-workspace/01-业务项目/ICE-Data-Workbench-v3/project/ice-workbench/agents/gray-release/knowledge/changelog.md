# Knowledge 知识库变更日志

## v1.2 (2026-05-21) — 对齐「灰度版本数据分析 SKILL V1.2」

- 从 `update_file/Gray-scale version data analysis V1.2.zip` 导入 9 个 YAML 知识库
- 按 ice-workbench 既有 `ab-experiment` 知识库分层规范重新组织：
  - `rules/`：`aa_rules.yaml`、`decision_matrix.yaml`、`rollout_phases.yaml`
  - `metrics/`：`core_metrics.yaml`、`sql_templates.yaml`
  - `analysis/`：`drill_knowledge.yaml`、`cases_and_lessons.yaml`
  - `product_model/`：`page_structure.yaml`、`report_template.yaml`
- 新增 `index.yaml`（全局索引，标记 required / on_demand 加载策略）
- 知识库读取走 `read_agent_knowledge("<相对路径>")`，路径相对 `agents/gray-release/knowledge/`
- 反馈闭环回写仅落到 `analysis/cases_and_lessons.yaml`，不做 git push
- 与 V1.2 zip 原始 SKILL.md 在路径上的差异：原 SKILL.md 内引用 `reference/knowledge/<file>` 平铺路径，本仓库统一改为分类子目录路径，prompt/system.md 与本索引同步修订

## v1.0 (2026-05-13) — 初始占位

- 仅占位，knowledge/ 目录尚未建立，agent 标记为 coming_soon

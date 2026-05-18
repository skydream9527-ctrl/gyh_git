# Knowledge 知识库变更日志

## v2.3 (2026-05-14) — 同步「信息流业务 AB 实验 Skill V2.3」

- 新增 `metrics/data_dictionary.yaml`（表别名、唯一用户ID、实验字段、DAU/新老用户/消费标记、查询经验 tips）
- 新增 `metrics/tag_id_scene_mapping.yaml`（收入指标按场景拆分的 tag_id → 产品场景映射）
- `product_model/report_template.yaml` → `product_model/report_template.md`（格式从 YAML 改为 Markdown，角色自适应规则重写）
- `rules/aa_rules.yaml` 扩展（36→47 行）：补充 fluctuation_thresholds、exemption、no_aa_handling 细则
- `metrics/core_metrics.yaml` 扩展（89→173 行）：显式化 categories 层级、rules.significance_is_reference_only、sql_ref 引用
- `metrics/sql_templates/` 全量刷新：browser_main / browser_feed / content_center 增补下钻模板和场景拆分 SQL，common.yaml 补齐 SRM 校验口径
- `analysis/drill_knowledge.yaml` 扩展（144→220 行）：按关键词匹配场景模式的假设库
- `analysis/cases_and_lessons.yaml` 扩展（9→47 行）：good_cases / bad_cases 的案例沉淀骨架
- SOP 由「四步法」升级为「Phase 0-5 + 反馈闭环」六阶段版（见 `../prompt/system.md`）

## v2.0 (2026-05-11) — 目录结构重组

- 按职能分层为 5 个子目录：rules/、metrics/、event_tracking/、analysis/、product_model/
- 新增 index.yaml 全局索引文件
- sql_templates/ 移入 metrics/ 子目录
- 埋点相关文件（db/yaml/readme/py）移入 event_tracking/
- CHANGELOG.md 重命名为 changelog.md（统一 snake_case）
- 同步更新 SKILL.md 中所有知识库文件路径引用

---

## page_structure.yaml 更新日志

## v1.0 (2026-04-28)
- 完成小米浏览器全部页面结构：首页、搜索首页、搜索SUG页、搜索结果页、图文详情页、沉浸式详情页、短剧详情页、我的页、任务详情页
- 完成内容中心核心页面结构：首页/推荐页、图文详情页、沉浸式详情页、短剧详情页、个人中心页、任务详情页
- 复用机制：内容中心的3个详情页复用浏览器的页面结构
- 删除冗余页面：视频详情页、小说阅读页、积分激励任务页、频道页
- 结构优化：为有明确卡片结构的页面增加 `cards` 层级
- 统一元素分类：`entries`、`content_areas`、`interactions`、`operations`

## v0.1 (2026-04-27)
- 初始骨架创建

---
name: djy-pool-analysis
description: |-
  都江堰内容池分析（校验 + 消费 + 创作者审核）。合并了三个场景：
  A) 校验业务内容池表字段准确性（4 家 CP × 20+ 条规则），支持 daily_report / report / detail / adhoc 四种模式；
  B) 分析 DAU 级消费指标（曝光/VV/时长/CTR），支持 CP 维度环比、实验组对比、单条内容查询、联合质量分析；
  C) 创作者签约审核链路校验（签约名单→审核表→内容池→签约清单回验），支持三步匹配 + emoji 容错。
  触发条件：
  - 校验类：「跑一下供应商内容池校验」「查 dihui 脏数据」「校验 beike publish_time 异常」「日报推飞书」
  - 消费类：「看一下各 CP 消费数据」「VV 变化」「对比实验组」「消费分析」
  - 创作者审核类：「看下签约作者推到审核表了没」「审核表作者在内容池有没有」「签约清单合规性校验」「创作者审核校验」
---

# 都江堰内容池分析

## 基本信息

### 校验（Validate）

- **目标表**：`paimon_zjyprc_hadoop.browser.business_content_pool_realtime`
- **CP 白名单**：`cn-dihui-djy` / `cn-beike-djy` / `cn-guoying-djy` / `cn-meilaoban-djy`
- **表特性**：实时 upsert 表，`date` 字段 = 推送入库日（非分区、入库后不变）
- **默认查询口径**：全量存量池。详见 [references/validate/query_scope.md](references/validate/query_scope.md)

### 消费（Consumption）

- **目标表**：`iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di`
- **分区字段**：`date`（YYYYMMDD），T+1 产出
- **维度**：60+（详见 [references/consumption/dimensions.csv](references/consumption/dimensions.csv)）
- **指标**：117（详见 [references/consumption/indexes.csv](references/consumption/indexes.csv)）

### 创作者审核（Creator Audit）

- **目标表**：`iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg`（审核推送）+ `paimon_zjyprc_hadoop.browser.business_content_pool_realtime`（内容池）
- **外部输入**：第一批 / 第二批签约名单 CSV（从飞书表格导出）
- **CP 范围**：`cn-beike-djy` / `cn-dihui-djy`（媒老板整家豁免）
- **核心匹配键**：`lead_author_id`（作者名会变更，不作稳定键）
- **入库判断**：内容池 `create_time IS NOT NULL`（不限 date 分区）
- **详见**：[references/creator_audit/overview.md](references/creator_audit/overview.md)

## 产出位置

所有运行时产出统一在 `$DJY_OUTPUT_ROOT`（默认 `~/Desktop/ai_djy_pool_analysis/`，即 git 仓库目录）：

| 子目录 | 内容 | Git 追踪 |
|---|---|---|
| `reports/` | 日报 HTML（GitLab Pages 发布） | ✅ |
| `daily_reports/` | 飞书卡片 JSON 归档 | ✅ |
| `dirty/` | detail 模式脏数据 CSV | ✅ |
| `tmp/` | 中间查询 CSV + 消费 JSON | ❌ gitignore |
| `charts/` | 图表截图 PNG | ❌ gitignore |

路径集中在 [`scripts/shared/paths.py`](scripts/shared/paths.py)。

## GitLab Pages

产出 HTML 推到 git 仓库后，通过 GitLab Pages 自动发布：
- 仓库：`git@git.n.xiaomi.com:v-zhujiaqing3/ai_djy_pool_analysis.git`
- Pages URL：`http://ai-djy-pool-analysis-4bbd9e.pages.n.xiaomi.com/content_pool_validate_YYYYMMDD.html`
- 推送脚本：[`scripts/shared/git_push_daily.sh`](scripts/shared/git_push_daily.sh)

## 使用模式

### 校验模式（4 种）

**用户没明说模式时，先问清楚**。

**关键原则**：`daily_report`（日报）与其他三种临时查询**严格隔离**。

#### daily_report · 日报（4 家 CP 全量 + 推飞书群）

**触发**：用户**明确**说了"推到群""发群里""推送飞书"等含"推/发/送+飞书/群"组合词时才推送。

**步骤**（2026-05-11 起改为「长图版」飞书卡片）：
1. 跑消费数据：`python3 scripts/consumption/consumption_daily_card.py`
2. 跑校验全量：`python3 scripts/validate/run_validate_sql.py scripts/validate/template_a_stock.sql`
3. 跑 3 份趋势 CSV：
   - `chart_stock_trend.sql`（c2 + c3~c6，**在线池** + create_time 口径，2026-05-26 起切到在线池）
   - `chart_daily_trend.sql`（c1，**全量** + create_time 口径，看 CP 推送量）
   - `chart_id_consistency_trend.sql`（2026-05-26 新增，三元 ID 一致性，在线池，输出 `multi_xm_authors_n` / `multi_cp_leads_n` 合入 c3~c6）
4. 生成 HTML：`python3 scripts/shared/chart_gen_html.py <stock_csv> <daily_csv> <YYYYMMDD> <html> <consum_json> <id_consistency_csv>`
5. **截整页长图**：`python3 scripts/shared/chart_html_to_longpng.py <html> <png>`（Playwright + 系统 Chrome）
6. 上传飞书图床：`IMG_KEY=$(python3 scripts/shared/feishu_upload_image.py <png>)`
7. 组装卡片 JSON：`python3 scripts/shared/build_longpng_card.py --image-key $IMG_KEY --date <YYYYMMDD> --report-url <pages_url>`
8. Git push HTML 到 GitLab Pages（在推送飞书之前，保证链接可用）
9. 推送飞书：`python3 scripts/shared/feishu_post.py <json_path>`。默认优先使用 `FEISHU_WEBHOOK` / `FEISHU_SECRET`；没有 webhook 时，使用项目根 `.env` 的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` + skill `.env` 的 `FEISHU_RECEIVE_ID` 调飞书 IM API。
10. Git push daily artifacts：`bash scripts/shared/git_push_daily.sh`

**注**：规则 20 (作者映射) 按抑制清单 (2026-04-28 起) 不纳入日报。旧的 7 图拼装方案（`chart_html_to_png.py` + `build_chart_card.py`）保留不删，仅作回退用途。

详见 [references/validate/daily_report.md](references/validate/daily_report.md)

#### report · 巡检报告

跑 `scripts/validate/run_validate_sql.py` + 按 [references/validate/report_format.md](references/validate/report_format.md) 4 段式组织

#### detail · 脏数据清单

SQL + `scripts/validate/export_to_csv.py` 两步导出

#### adhoc · 临时规则验证

echo SQL | `scripts/validate/run_validate_sql.py -`

### 消费模式（4 种）

#### P1 · 维度下钻（最常用）

按 CP/体裁/分类等维度聚合消费指标，通过 `scripts/consumption/run_consumption_sql.py` 跑

#### P2 · 实验组对比

对比自建组 vs 火山组。详见 [references/consumption/exp_groups.md](references/consumption/exp_groups.md)

#### P3 · 单条内容/作者查询

按 item_id 或 author_id 查消费表现

#### P4 · 质量-消费联合分析

JOIN 内容池表，分析字段质量对消费的影响。详见 [references/consumption/cross_skill_join.md](references/consumption/cross_skill_join.md)

### 创作者审核校验（3 步链路）

**触发**：用户说「看下签约作者推到审核表了没」「审核表作者有没有入过内容池」「签约清单合规性」等。

**前置输入**：第一批 / 第二批签约名单 CSV（从飞书表格导出本地）

**一键执行**：
```bash
python3 scripts/creator_audit/run_audit_check.py \
    --batch1 <batch1.csv> --batch2 <batch2.csv>
# 默认输出到 ~/Desktop/VS Code/签约审核校验_YYYYMMDD/
```

**三步逻辑**：
1. 步骤 0：签约名单 → 审核表（匹配键 `CP + 作者名`）
2. 步骤 1：审核表 → 内容池（匹配键 `CP + lead_author_id`，用 `create_time` 判断入库，不限 date 分区）
3. 步骤 2：内容池作者 → 签约清单（历史名集合 + emoji 容错双边清洗）

**详见**：
- [references/creator_audit/match_logic.md](references/creator_audit/match_logic.md)（三步匹配逻辑 + 常见陷阱）
- [references/creator_audit/exemptions.md](references/creator_audit/exemptions.md)（豁免规则：媒老板/测试账号 N）
- [references/creator_audit/output_format.md](references/creator_audit/output_format.md)（本地 CSV + 飞书表格格式）

## 核心原则（不可绕过）

1. **禁用缓存**：每次调用必须真实跑 SQL
2. **0 异常告警**：≥1 条就告警
3. **字段名直出**：报告保留 `author_image`（作者头像）格式
4. **豁免白名单自动验证**：规则 12/13 命中必跑 exemption_check.sql

## 参考文档

### 校验

| 文件 | 用途 |
|---|---|
| [references/validate/rules.md](references/validate/rules.md) | 21 条规则详解 + 字段映射 |
| [references/validate/exemptions.md](references/validate/exemptions.md) | 豁免白名单 + 验证流程 |
| [references/validate/query_scope.md](references/validate/query_scope.md) | 表特性 + 时间字段语义 + 口径 |
| [references/validate/report_format.md](references/validate/report_format.md) | 4 段式报告 + 告警阈值 |
| [references/validate/faq.md](references/validate/faq.md) | 常见问题 + 已知业务问题 |
| [references/validate/daily_report.md](references/validate/daily_report.md) | 日报流程 + 飞书推送 |
| [references/validate/html_report_style.md](references/validate/html_report_style.md) | HTML 样式规范 |
| [references/validate/delete_reason_codes.md](references/validate/delete_reason_codes.md) | delete_reason 码值表 |

### 消费

| 文件 | 用途 |
|---|---|
| [references/consumption/dimensions.csv](references/consumption/dimensions.csv) | 60+ 维度字段定义 |
| [references/consumption/indexes.csv](references/consumption/indexes.csv) | 117 指标字段定义 |
| [references/consumption/model.sql](references/consumption/model.sql) | 表完整 SQL 定义 |
| [references/consumption/exp_groups.md](references/consumption/exp_groups.md) | 实验组映射 |
| [references/consumption/cross_skill_join.md](references/consumption/cross_skill_join.md) | 联合分析 JOIN 规则 |

### 创作者审核

| 文件 | 用途 |
|---|---|
| [references/creator_audit/overview.md](references/creator_audit/overview.md) | 背景 / 数据源 / CP 范围 / 关键字段 |
| [references/creator_audit/field_dict.md](references/creator_audit/field_dict.md) | 审核表 35 字段字典（接口 ↔ 数据表 映射）+ 驳回原因枚举 |
| [references/creator_audit/audit_status.md](references/creator_audit/audit_status.md) | audit_status 13 个枚举值 + 状态流转 + 豁免分组 |
| [references/creator_audit/match_logic.md](references/creator_audit/match_logic.md) | 三步匹配逻辑 + 基数口径 + 常见陷阱 |
| [references/creator_audit/exemptions.md](references/creator_audit/exemptions.md) | 豁免规则（媒老板 / 测试账号 N / xm 为空） |
| [references/creator_audit/output_format.md](references/creator_audit/output_format.md) | 本地 CSV 命名 + 飞书表格结构 + 推送规则 |
| [scripts/creator_audit/run_audit_check.py](scripts/creator_audit/run_audit_check.py) | 一键执行入口 |
| [scripts/creator_audit/emoji_clean.py](scripts/creator_audit/emoji_clean.py) | 作者名清洗（去 emoji/乱码/变体符） |
| [scripts/creator_audit/gen_contract_values.py](scripts/creator_audit/gen_contract_values.py) | CSV → SQL VALUES 生成器 |

## 关联 Skill

- [data-sql](../data-sql/SKILL.md)：执行 SQL（本 skill 所有 SQL 通过 data-sql 跑）

## 已知环境坑

1. **架构不匹配**：`run_validate_sql.py` 和 `run_consumption_sql.py` 内部均用 `arch -arm64 /usr/bin/python3`
2. **SQL 注释/多行/豁免占位符**：`run_validate_sql.py` 统一处理，不要裸调 `sql_query_tool.py`
3. **消费时长单位**：`consum_dura` 存的是分钟，展示单 VV 时长需 ×60 转秒

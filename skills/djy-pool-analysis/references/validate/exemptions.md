# 豁免配置

## 目录
- [Item ID 级豁免白名单](#item-id-级豁免白名单)
- [CP 豁免白名单（author_name 级）](#cp-豁免白名单author_name-级)
- [自动验证流程（规则 12/13 命中时强制执行）](#自动验证流程规则-1213-命中时强制执行)
- [设计性可空字段（规则库自动跳过）](#设计性可空字段规则库自动跳过)

## Item ID 级豁免白名单

### 唯一数据源 · `exemptions.json`

特定 item_id 业务上不应计入异常（历史测试数据 / CP 数据丢失已下线 / 特殊兜底等）。

**所有校验 SQL 不再硬编码 item_id**。统一通过 `{{EXEMPT_FILTER}}` 占位符，由 `scripts/exempt_lib.py` 从 `exemptions.json` 读取后动态注入。

- **数据源**：[`../exemptions.json`](../exemptions.json)（唯一）
- **读取库**：[`../scripts/exempt_lib.py`](../scripts/exempt_lib.py)（Python API + CLI）
- **运行入口**：[`../scripts/run_validate_sql.py`](../scripts/run_validate_sql.py)（所有场景通过它跑 SQL）

### 当前豁免概览（自动从 JSON 生成）

查看实时统计：
```bash
python3 ~/.claude/skills/djy-pool-analysis/scripts/shared/exempt_lib.py stats
```

查看完整 item_id 列表：
```bash
python3 ~/.claude/skills/djy-pool-analysis/scripts/shared/exempt_lib.py ids
```

查看 SQL WHERE 片段预览：
```bash
python3 ~/.claude/skills/djy-pool-analysis/scripts/shared/exempt_lib.py filter
```

### JSON 条目 schema

```json
{
  "a_cp": "cn-beike-djy",                        // 必填 · CP 代号
  "a_item_id": "beike-djy_xxx",                  // 必填 · 全局唯一内容主键
  "category": "rule20_offline",                  // 必填 · 分类（审计用）
  "reason": "rule20 错挂，2026-04-21 CP 下线",    // 必填 · 人类可读原因
  "status": "offline",                           // 必填 · offline / exempt / pending_review
  "registered_date": "2026-04-27",               // 必填 · 登记日期
  "registered_by": "user"                        // 可选 · 登记人
}
```

**已有 category 分类**（参考，新增按需扩展）：

| category | 含义 |
|---|---|
| `historical_test_data` | 历史测试数据 |
| `cp_data_loss` | CP 方数据丢失 |
| `rule20_offline` | rule20 映射错挂且已下线 |
| `multi_field_null` | 多字段同时空（脏数据） |
| `aigc_incomplete` | AIGC 生成不完整内容 |

### 新增豁免流程（只改 1 个文件）

1. 打开 [`../exemptions.json`](../exemptions.json)
2. 在数组最后追加一条，填齐 a_cp / a_item_id / category / reason / status / registered_date
3. 保存 · **不要改 SQL**、**不要改本 md** · 下次跑 SQL 自动生效

### 撤销豁免

从 `exemptions.json` 删除对应条目即可。下次跑 SQL 自动不再豁免。

### 审核待豁免（未决）

若有"待业务方决策"的条目，在 JSON 里新增一条 `"status": "pending_review"`。SQL 会暂时豁免，审计时筛 `status` 字段一眼可见。

---

## CP 豁免白名单（author_name 级）

某些 CP 的特定作者（通常是 AIGC / PGC 账号）在特定字段上允许为空，属正常业务。

| a_cp | author_id（精确） | author_name | 豁免规则 | 依据 |
|---|---|---|---|---|
| `cn-beike-djy` | `aigc01IncisiveInsightHub` | 锐析洞察局 | 规则 12 + 规则 13（`lead_author_id` / `lead_author_name` 空） | AIGC 账号无真实主作者 · **唯一 author-level 豁免**（2026-04-28 用户确认） |

**目前触发状态**：该账号现阶段全部 `item_type='NEWS'`，规则 12/13 本身只查非 NEWS，因此实际不命中。豁免条目保留用于**未来该账号若推非 NEWS 内容**时自动跳过。

**查询锐析时不要加 `item_type != 'NEWS'`**，否则会看不到（它全是 NEWS）。

## CP 级规则豁免（全字段级）

某些 CP 对某个字段的空值属于既定业务正常态，不计异常（与 author_name 级豁免不同，这里针对 CP 全量内容）。

| a_cp | 规则 | 豁免范围 | 依据 |
|---|---|---|---|
| `cn-beike-djy` | 规则 23（`author_ip` 空） | 全量内容（历史 + 增量） | 2026-04-29 用户确认：beike 部分作者确实无法获取 IP 属地，空值属业务正常态；beike 将定时复核，如 IP 出来会体现在新增内容上 |

**SQL 实现**：所有 `author_ip` 空判断前加 `a_cp != 'cn-beike-djy' AND`，已统一更新到：
- `template_a_stock.sql`（规则 23 单字段）
- `template_b_trend.sql`
- `chart_daily_trend.sql` / `chart_stock_trend.sql` / `chart_recovery_trend.sql`

**复核机制**：CP 级豁免不应长期静默生效。当 beike 后续告知"IP 属地覆盖率已提升"时，应：
1. 跑一次对照：`SELECT COUNT(*) WHERE a_cp='cn-beike-djy' AND author_ip NOT NULL` 看覆盖度
2. 如覆盖率显著提升，考虑从"全量豁免"退到"作者级豁免"或完全取消

## 自动验证流程（规则 12/13 命中时强制执行）

当 `lead_author_id_null_nn` 或 `lead_author_name_null_nn` 命中数 > 0，**先别出告警**，先跑：

```sql
SELECT author_name, COUNT(*) FROM ... WHERE a_cp = '{{CP}}' AND item_type != 'NEWS'
  AND (lead_author_id IS NULL OR lead_author_id = '') GROUP BY author_name
```

（完整脚本见 [`../scripts/exemption_check.sql`](../scripts/exemption_check.sql)）

**判定**：

| 情况 | 处理 |
|---|---|
| 全部 `author_name` ∈ 豁免白名单 | 命中数清零，不告警 |
| 部分 `author_name` ∈ 白名单 | 真实异常 = 命中 − 白名单 author 数，只对真实异常告警 |
| 无任何 `author_name` ∈ 白名单 | 全部真实异常 |

**告警文案必写**：`命中 X = 豁免 Y（author_name="锐析洞察局"）+ 真实异常 Z`

不做自动验证 = 误报或漏报，视为 skill bug。

## 新增 author_name 级豁免流程

当用户/CP 对接人说"XX 账号的某字段为空是正常业务"：

1. 在上面 CP 豁免白名单表格添加一行（a_cp + author_name + 豁免规则 + 依据 + 发现日期）
2. 对应更新 project memory `project_beike_ruixi_exempt.md` 之类（含发现日期，便于定期复核）
3. 若账号停推，**不要**直接删除豁免（历史数据仍可能出现），加状态注明"已停推 YYYY-MM-DD"

## 设计性可空字段（规则库自动跳过）

这些字段 CP 不填是正常设计，SQL 和报告**必须排除**：

| 字段 | 原因 | 依据 |
|---|---|---|
| `item_title` | 标题遵从上游传值，原发内容本身为空的场景合法 | 2026-04-27 用户确认 |
| `item_summary` | 业务线不关注 | 2026-04-27 用户确认（此前 2026-04-23 仅观察到 CP 差异） |
| `a_original_id` / `a_original_source` / `a_is_original` / `original_author` / `original_author_id` / `original_id_v2` | 原站归属字段，业务线不关注 | 2026-04-27 用户确认 |
| `date` | 分区键，**业务不用它做任何趋势**。趋势聚合必须用 `create_time` | 2026-04-27 用户确认 |
| `body` / `e_xm_body_word_cnt` / `e_xm_image_cnt`（在非 NEWS 上） | NEWS 专属，VIDEO/MINIVIDEO 自然空 | 规则 17-19 只对 NEWS 生效 |
| `lead_author_id` / `lead_author_name` / `category` / `video_duration` / `video_detail_list`（在 NEWS 上） | 非 NEWS 才需要 | 规则 12-16 豁免 NEWS |

## 已知可能误触发的场景

- **dihui 全部作者空 `lead_author_name`** 但 Rule 20 命中数字一致：两个 4 可能是"同一批数据"的巧合，要核查实际 item_id 重叠才能下结论。见 [faq.md](faq.md)「两个数字碰巧相同怎么办」。

# 创作者签约审核校验 · 匹配逻辑

校验流程分三步执行，每一步都有独立的匹配键、SQL 模板和产出。

## 步骤 0 · 签约名单 → 审核表推送

**目标**：签约名单上的作者是否都推送到了审核表。

**匹配键**：`CP + 作者名`（两批名单均用此键；第二批虽有 xm_author_id，但审核表 dihui 的 xm_author_id 全为空，故统一只用名字匹配）

**SQL 模板**：[`scripts/creator_audit/step0_push_check.sql`](../../scripts/creator_audit/step0_push_check.sql)

**关键点**：
- 签约名单作为 VALUES 内联注入 SQL（用 `gen_contract_values.py` 生成）
- 排除 `cn-meilaoban-djy` 整家 CP
- 审核表侧取 DISTINCT (cp_api, lead_author_name) 后 LEFT JOIN
- 每批名单分别跑（不合并）

**产出**：
- 汇总：CP × (名单总数, 已推送, 未推送, 推送率)
- 明细 CSV：两批各自的未推送作者清单

## 步骤 1 · 审核表 → 内容池历史入库匹配

**目标**：审核表中的作者，历史上是否在内容池入过任何内容。

**匹配键**：`CP + lead_author_id`（审核表作者名会变更，故只用 ID）

**SQL 模板**：[`scripts/creator_audit/step1_pool_match.sql`](../../scripts/creator_audit/step1_pool_match.sql)

**关键点**：
- **不限 date 分区**：`date` 是分区字段不是入库时间，扫全部分区得到"历史任意时刻"的快照集合
- **用 `create_time IS NOT NULL` 判断入库**：这才是每条内容的入库时间语义
- 审核表侧排除 `lead_author_name LIKE '测试账号%'` 的驳回数据
- 基数口径：`SELECT DISTINCT cp_api, lead_author_id FROM creator_audit_info_iceberg`
- 内容池侧按 a_cp 过滤 `('cn-beike-djy', 'cn-dihui-djy')`

**产出**：
- 汇总：CP × (审核表作者数, 历史入过库, 从未入库, 入库率)
- 明细 CSV：从未入库的作者 + 审核推送时间 + 状态（便于定位问题批次）

## 步骤 2 · 内容池作者 → 签约清单匹配（含 emoji 容错）

**目标**：在内容池的审核作者是否都在签约清单中（合规性校验）。

**匹配键**：`CP + 作者名`，但采用**宽松匹配**：
1. 对每个 `lead_author_id`，拉取其在内容池的**所有历史 `lead_author_name`**集合
2. 对每个名字做 **emoji / 乱码 / 变体符清洗**（[`emoji_clean.py`](../../scripts/creator_audit/emoji_clean.py)）
3. 与签约清单（两批合并去重后同样清洗）比对
4. 任一历史名命中即算合规

**SQL + 后处理**：
- SQL 部分：[`scripts/creator_audit/step2_contract_match.sql`](../../scripts/creator_audit/step2_contract_match.sql) 只做精确匹配，拉出未命中的候选
- Python 部分：[`run_audit_check.py`](../../scripts/creator_audit/run_audit_check.py) 对未命中候选做 emoji 容错二次匹配

**为什么要 emoji 容错**：
签约清单在上游链路（多半是 Excel 或中转 API）存在不支持 4 字节 UTF-8 的环节，作者名中的 emoji 会被截断为 `�`（`�`）替换符。例如：
- 内容池：`动物世界🐅`
- 签约清单：`动物世界` 或 `动物世界��`

严格字符串匹配会漏掉这 25+ 位带 emoji 的作者。

**清洗规则**（`emoji_clean.strict_clean`）：
- 保留：CJK 字符、英文字母、数字、中英文括号
- 移除：所有 Unicode 类别以 `S`（Symbol）、`M`（Mark）、`Z`（Separator）开头的字符 + 控制字符 + 乱码占位符

**产出**：
- 汇总：CP × (内容池可匹配作者, 在签约清单, 不在签约清单, 合规率)
- 明细 CSV（两份）：
  - 真·不在签约清单（排除 emoji 问题后）
  - emoji 容错命中（数据质量问题明细，用于反馈上游）

## 三步基数一致性

| 步骤 | 基数 | 说明 |
|---|---|---|
| 步骤 0 | 两批签约名单总数（去重） | 排除媒老板 |
| 步骤 1 | 审核表 DISTINCT (cp_api, lead_author_id) | 排除测试账号 |
| 步骤 2 | 步骤 1 "历史入过库"的作者数 | 等于 step1 的 `ever_in_pool` |

**一致性检查**：步骤 2 的基数必须等于步骤 1 的 `ever_in_pool`。如果有差异，检查 a_cp 在两表间是否不一致（跨 CP 的 lead_author_id）。

## 常见陷阱

| 陷阱 | 正确做法 |
|---|---|
| 用 `date = 最新分区` 过滤"历史"入库 | ❌ `date` 是分区字段非入库时间；✅ 不限分区 + `create_time IS NOT NULL` |
| 用 `lead_author_name` 作为稳定匹配键 | ❌ 审核表/内容池作者名会变更；✅ 用 `lead_author_id` |
| 只扫最新分区 | ❌ 会漏掉"历史入过库但内容已下线清理"的作者；✅ 扫全窗口 |
| 严格字符串匹配签约清单 | ❌ 会漏掉 emoji 被截断的记录；✅ 双边清洗 + 容错匹配 |
| SQL 中文列别名 | ❌ Trino 不支持中文 identifier；✅ 用英文别名 |

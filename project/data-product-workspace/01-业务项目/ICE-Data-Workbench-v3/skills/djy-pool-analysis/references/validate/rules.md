# 规则库 + 字段映射

## 目录
- [P0 全类型必填（11 条）](#p0-全类型必填11-条)
- [P0 非 NEWS 必填（5 条 + 1 子规则）](#p0-非-news-必填5-条--1-子规则)
- [P0 NEWS 必填（3 条）](#p0-news-必填3-条)
- [P0 作者身份一致性（1 条）](#p0-作者身份一致性1-条)
- [字段 + 问题描述清单（报告文案格式）](#字段--问题描述清单报告文案格式)

## P0 全类型必填（11 条）

所有 `item_type`（VIDEO / MINIVIDEO / NEWS）都必须校验。

| # | 字段 | 违反条件 |
|---|---|---|
| 1 | `a_item_id` | IS NULL OR = '' OR LOWER = 'null' |
| 2 | `a_cp` | NOT IN 4 家白名单 |
| 3 | `publish_time` | 同 1（严格版，`create_time` 有值也不豁免） |
| 4 | `author_id` | 同 1 |
| 5 | `author_name` | 同 1 |
| 6 | `item_type` | NOT IN (VIDEO, MINIVIDEO, NEWS) |
| 7 | `online` | IS NULL OR = '' OR 值 NOT IN ('0', '1')（值域校验：1=在线 / 0=下线） |
| 8 | `url` | 空 OR 非 `http://` / `https://` 前缀 |
| 9 | `image` | 同 1 |
| 10 | `author_image` | 同 1 |
| 11 | `xm_author_id` | 同 1 |

## P0 作者三元 ID 一致性（规则 12/13/20，**含 NEWS**）

`author_id` ↔ `lead_author_id` ↔ `xm_author_id` **三元两两一对一映射**，适用**所有** `item_type`（包含 NEWS，2026-04-28 用户确认）。

| # | 字段 | 违反条件 |
|---|---|---|
| 12 | `lead_author_id` | IS NULL OR = '' OR LOWER = 'null'（**全类型必填**） |
| 13 | `lead_author_name` | 同规则 12 |
| 20 | 三元映射 | `author_id`, `lead_author_id`, `xm_author_id` 三者任何两两不一一对应 |

**唯一 author-level 豁免**：`author_id = 'aigc01IncisiveInsightHub'`（beike 锐析洞察局，AIGC 账号）

- 规则 12/13：锐析允许 `lead_author_id` / `lead_author_name` 为空
- 规则 20：锐析只保留 `author_id` ↔ `xm_author_id` 两元对应，不检查含 `lead_author_id` 的方向

豁免验证走 [`scripts/exemption_check.sql`](../scripts/exemption_check.sql)：命中数 > 0 时必须分 `author_id` 拆分，只有锐析算豁免，其他作者一律真实异常。

## P0 全类型必填（含 NEWS，锐析豁免）· 3 条

| # | 字段 | 违反条件 | 豁免 |
|---|---|---|---|
| 14 | `category` | 非空（全类型，2026-04-28 扩展含 NEWS） | `author_id='aigc01IncisiveInsightHub'`（锐析洞察局） |
| 22 | `ai_article` | **条件必填**：`create_time >= 2026-05-22` 生效。<br>非空 AND 值域：NEWS ∈ {'0','1'} / VIDEO+MINIVIDEO ∈ {'0','1','2','3','4','5'} | — |
| 23 | `author_ip`（作者归属地，省份/国家文本，**非网络 IP**） | 非空（全类型，无生效日期，历史全量告警） | — |

**规则 22 `ai_article` 值域说明**（2026-04-28 用户确认）：

| 值 | 含义 |
|---|---|
| 0 | 无 |
| 1 | 含 AI 生成内容 |
| 2 | 含虚构演绎内容 |
| 3 | 个人观点，仅供参考 |
| 4 | 内容为转载 |
| 5 | 内容含营销信息 |

**标签重合时，取数字小的作为唯一值**。NEWS 只能 0/1，VIDEO/MINIVIDEO 可 0-5 全值。

## P0 非 NEWS 必填（3 条 + 1 子规则）

`item_type != 'NEWS'` 时必填。NEWS 豁免原因：NEWS 没有视频属性（**仍需三元 ID 一致性 + category + author_ip**，见上节）。

| # | 字段 | 违反条件 |
|---|---|---|
| 15 | `video_duration` | 非空 AND > 0（2026-04-28 升级） |
| 16 | `video_detail_list` | 整串 JSON 空 |
| 16.1 | `video_detail_list` 内 **7 个必填字段**非空（2026-04-28 确认）：`videoUrl` / `firstImg` / `bitrate` / `codecType` / `videoResolution` / `videoWidth` / `videoHeight` | 任一必填字段缺失 OR 值为空串 OR 值为 null（数字 0 暂不算，一致规则 15） |

**规则 16.1 的字段分类**（2026-04-28 用户确认）：

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `videoUrl` | ✅ 必填 | 视频主 URL |
| `firstImg` | ✅ 必填 | 首帧图 URL |
| `bitrate` | ✅ 必填 | 码率 |
| `codecType` | ✅ 必填 | 编码类型 |
| `videoResolution` | ✅ 必填 | 分辨率 |
| `videoWidth` | ✅ 必填 | 视频宽度 |
| `videoHeight` | ✅ 必填 | 视频高度 |
| `videoUrlBackup1` | ⚪ 可选 | 备份 URL，允许为空 |
| `fileMd5` | 🟡 条件必填 | **规则 16.2**（2026-04-28 定稿）：`create_time >= 2026-04-29` 的内容必填（**2026-04-29 正式生效**）；历史全部豁免 |
| `urlExpiredTime` | ⚪ 可选 | 仅 guoying / dihui 推送，做提示不告警 |
| `size` | ⚪ 可选 | 仅 beike / dihui / meilaoban 推送，做提示不告警 |
| `videoType` | ⚪ 可选 | 仅 dihui 推送，做提示不告警 |
| `frameRate` | ⚪ 可选 | 仅 dihui 推送，做提示不告警 |

**规则 16 vs 16.1**：
- 16：整串 JSON 为空，最严重（整个视频详情丢失）
- 16.1：JSON 有值但里面 `firstImg` 缺失，视频首帧图丢失
- 汇总时拆分呈现，**不合并**

## P0 NEWS 必填（3 条）

`item_type = 'NEWS'` 时必填。非 NEWS 豁免。

| # | 字段 | 说明 |
|---|---|---|
| 17 | `body` | 图文正文 |
| 18 | `e_xm_body_word_cnt` | 小米内部计算的字数 |
| 19 | `e_xm_image_cnt` | 小米内部计算的图片数 |

## P0 作者三元 ID 一致性（规则 20 详解，已在上节定义）

| # | 规则 | 违反条件 |
|---|---|---|
| 20 | 同一 CP 下 `author_id` ↔ `lead_author_id` ↔ `xm_author_id` 三元两两一对一（**含 NEWS**，锐析豁免 lead_author 维度） | 任一方向一对多：<br>a) 一个 `author_id` 对应多个 `(lead_author_id, xm_author_id)` 组合<br>b) 一个 `lead_author_id` 对应多个 `(author_id, xm_author_id)` 组合（锐析除外）<br>c) 一个 `xm_author_id` 对应多个 `(author_id, lead_author_id)` 组合 |

## P0 内容 ID 唯一性（1 条）

| # | 规则 | 违反条件 |
|---|---|---|
| 21 | `a_item_id` 库内全局唯一 | 存在 `a_item_id` 被多条记录使用 |

**业务含义**：`a_item_id` 是 CP 入库后拼接前缀的内容主键（例 `beike-djy_{id}`），理论上 upsert 表按此去重，不应有多条记录。若命中表示主键冲突（同 CP 误拼两次 / 跨 CP 前缀冲突 / upsert 键配置异常）。

**SQL**：见 [`scripts/rule21_item_id_dedup.sql`](../scripts/rule21_item_id_dedup.sql)，`GROUP BY a_item_id HAVING COUNT(*) > 1`。

**注意**：检测时要先排除 item_id 级豁免（见 [exemptions.md](exemptions.md)），再做 GROUP BY，避免把豁免 id 算进来。

**业务含义**：同一作者（按 `lead_author_id` 判定）在一个 CP 内只能有一个 `author_id`。违反时作者维度去重统计失真。

**SQL**：见 [`scripts/rule20_author_mapping.sql`](../scripts/rule20_author_mapping.sql)，双向 GROUP BY HAVING。

**注意**：历史存量 `author_id` 不加前缀是合法的（旧前缀规则已废弃），重点是映射关系唯一。

## 字段 + 问题描述清单（报告文案格式）

**写法原则**：报告标题和关键表述**必须保留字段名**（方便推 CP 对接人时直接对齐 schema），括号补业务含义，冒号后写问题。

**标准格式**：`` `{字段名}`（{业务含义}）· {问题描述} ``

| 字段名 | 业务含义 | 问题描述 |
|---|---|---|
| `a_item_id` | 内容 ID（CP 入库后拼前缀，如 `beike-djy_{id}`） | 字段为空 / 库内重复（规则 21） |
| `a_cp` | CP 区分字段（格式 `cn-{cp}-djy`） | NOT IN 白名单 |
| `publish_time` | 端侧展示的内容发布时间（用户 2026-04-27 确认：**严格版**，`create_time` 有值不豁免） | 字段为空 |
| `create_time` | 内容入库时间（毫秒级 Unix 时间戳，用户 2026-04-25 确认） | 仅做趋势聚合维度使用，不入校验规则 |
| `date` | **分区键，业务不用它做任何趋势**（用户 2026-04-27 确认）。趋势必须用 `create_time` | 不入规则，不关注 |
| `update_time` | 内容更新时间（用户 2026-04-28 确认） | 仅说明，不入规则 |
| `author_id` / `author_name` | 作者 ID / 名称 | 字段为空 |
| `author_image` | 作者头像 | 字段为空 |
| `xm_author_id` | 小米账号 ID | 字段为空 |
| `lead_author_id` / `lead_author_name` | 主作者 ID / 名称 | 字段为空（非 NEWS） |
| `item_type` | 内容类型（**MINIVIDEO=小视频 / VIDEO=短视频 / NEWS=图文**） | 值非法（非三者之一） |
| `online` | 内容状态（**1=在线 / 0=下线**） | 字段为空 或 值非 {'0','1'} |
| `delete_reason` | CP/小米标记的下线原因码 | 仅说明，无强制规则。码值对照见 [delete_reason_codes.md](delete_reason_codes.md) |
| `item_title` | 内容标题 | **不入规则**（用户 2026-04-27 确认）· 标题遵从上游传值，**允许为空**（原发内容本身就没标题的场景） |
| `item_summary` | 内容简介 | 业务线**不关注**（用户 2026-04-27 确认），不入规则。见 [exemptions.md](exemptions.md#设计性可空字段规则库自动跳过) |
| `url` | 内容链接 | 格式异常（非 http/https） |
| `image` | 封面图 | 字段为空 |
| `category` | 一级分类 | 字段为空（全类型含 NEWS，豁免锐析 author_id='aigc01IncisiveInsightHub'，2026-04-28 扩展） |
| `ai_article` | AIGC 标签（0=无 / 1=AI 生成 / 2=虚构 / 3=观点 / 4=转载 / 5=营销；标签重合取数字小的；NEWS 仅 0-1） | 空 OR 值超出允许集（`create_time >= 2026-05-22` 生效） |
| `author_ip` | 作者归属地（**省份 / 国家文本**，非网络 IP 地址。示例值：江苏 / 北京 / 广东 / 中国台湾 / 中国香港 / 中国澳门 / 美国 / 非洲 等） | 字段为空（全类型必填） |
| `image` | 封面图集合，和图文详情页图片/视频封面保持一致 | 字段为空 |
| `video_duration` | 视频时长 | 非 NEWS 必填 **且 > 0**（2026-04-28 升级，用户确认值=0 或负数需要告警） |
| `video_detail_list` | 视频详情（整串 JSON） | 字段为空（非 NEWS） |
| `video_detail_list.firstImg` | 视频首帧图 URL | JSON 里 firstImg 缺失或非 http（非 NEWS） |
| `body` | 图文正文 | 字段为空（NEWS） |
| `e_xm_body_word_cnt` | 图文字数 | 字段为空（NEWS） |
| `e_xm_image_cnt` | 图文图片数 | 字段为空（NEWS） |
| `a_original_*` / `original_*` | 原站归属字段（6 个） | 业务线**不关注**（用户 2026-04-27 确认），不入规则 |
| `author_id` ↔ `lead_author_id`（规则 20） | 作者 ID 映射关系 | 1 个主作者 ID 关联多个 author_id（映射不唯一） |
| `a_item_id` × 库内（规则 21） | 内容 ID 全局唯一 | 同一 id 出现多次 |

**反例（禁止）**：
- ❌ `作者头像缺失 · 29.8%`（字段名消失，对接人要反查 schema）
- ❌ `未挂主作者 · 168 条`（业务释义作主干，字段名丢了）

**正例**：
- ✅ `` `author_image`（作者头像）· 字段为空 · 51,862 条 ``
- ✅ `` `lead_author_id` / `lead_author_name`（主作者）· 字段为空 · 168 条 ``
- ✅ `` `url`（内容链接）· 格式异常 · 74 条 ``

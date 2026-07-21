# nl-mapping-table-sql-v2 口径维护清单

> 归档日期：2026-07-13  
> 飞书表格：https://mi.feishu.cn/wiki/HexVwtWZHitynpk05VictOtQnXj  
> 来源：当前工作区上下文 + `/Users/mi/Desktop/ice_workbench_new/skills/nl-mapping-table-sql-v2` 盘点  
> 用途：将已维护口径放在上方，将待维护口径列出，供后续补充 `nl-sql` / `nl-mapping-table-sql` 数据资产。

## 口径维护表

| 状态 | 业务域 | 口径/指标组 | 具体指标/口径 | 当前来源 | 数据源表/资产 | 缺口/待补内容 | 优先级 |
|------|--------|-------------|---------------|----------|---------------|----------------|--------|
| ✅ 已维护 | 浏览器主端 | 核心中间表指标 | DAU、应用使用时长、信息流时长、消费时长、曝光、点击、次留/7留/30留、曝光-曝光次留、曝光-有效次留、有效-有效次留 | v2 references/browser/core-metrics-reference.md | dm_browser_multi_dimension_indicators_di；dm_browser_multi_dimension_retain_indicators_di | 需持续补真实 badcase 校验值 | P0 |
| ✅ 已维护 | 浏览器主端 | 核心维度拆分 | 新老用户、启动方式、体裁、App版本、系统版本、机型、频道 | v2 references/browser/core-metrics-reference.md；dimension-index.md | 同上 | 补维度枚举中文解释和业务使用场景 | P0 |
| ✅ 已维护 | 浏览器信息流 | 信息流核心指标 | 信息流DAU、信息流时长、消费时长、内容曝光量、内容点击量、次留/7留/30留 | v2 references/browser-feed/core-metrics-reference.md | dm_browser_multi_dimension_indicators_di；dm_browser_multi_dimension_retain_indicators_di | 需标注新旧埋点适用边界 | P0 |
| ✅ 已维护 | 内容中心 | 核心中间表指标 | DAU、分新老用户DAU、深度DAU、有效DAU、MAU、时长、人均时长、消费DAU/UV/VV/时长、人均消费时长 | v2 references/content-center/core-metrics-reference.md | dm_newhome_multi_dimension_indicators_di；dm_newhome_multi_dimension_retain_indicators_di | 需强调内容中心时长 0-24h 限制 | P0 |
| ✅ 已维护 | 商业化/财收 | 通用商业化指标 | 财收、流水、计费曝光、计费点击、广告下载量、广告请求次数、广告填充次数；支持按广告位场景/广告位拆分 | v2 browser/browser-feed/content-center commerce-metrics-reference.md | ads_browser_finance_core_indicators_di；ads_newhome_finance_core_indicators_di | 只有通用广告指标，缺计提/预算/CP等财务细口径 | P1 |
| ✅ 已维护 | 浏览器 Push | Push 专题指标 | 送达PV/UV、点击PV/UV、CTR、UTR、Push DAU、Session/落地页时长、点击后消费时长、真实送达、动态关闭率、分时段送达点击、TOP10物料CTR、内容池漏斗 | v2 references/browser/push-metrics-reference.md | push_callback_log；dwd_push_real_expose_dt；dwm_browser_push_open_session_consum_di 等 | Push AB/增量价值 DID 模板还需单独补 | P0 |
| ✅ 已维护 | 都江堰/双端信息流 | 有效用户专题 | BF/CC 双端有效用户 DAU/VV/时长、双端合计、7日留存、自建 vs 火山 DAU/VV/时长、人均时长、时长达火山比 | v2 references/feed-dual-end/valid-user-metrics-reference.md | dwm_browser_event_aggregation_label_di；dwm_newhome_event_aggregation_label_di；dwm_djy_dau_user_consum_index_di_copy | 需补“火山小说/自建源”真实业务案例 | P0 |
| ✅ 已维护 | 小说 | 小说底表/宽表指标 | 多看DAU、阅读时长、有效阅读UV、网文/出版阅读时长与UV、SDK有效阅读UV、浏览器/内容中心小说UV/VV/时长、短故事/长篇口径 | v2 references/novel/raw-core-metrics-reference.md；raw-event-metrics-reference.md | dwd_ot_event_di_1004465；dwd_ot_event_di_31000000442；dwd_ot_event_di_31000000297 | 没有中间表口径，只有底表/宽表模板 | P1 |
| ✅ 已维护 | 中间表不支持维度 | 回退查询方案 | 实验组、三方调起包名、冷启动、上划行为、内容源；覆盖浏览器/信息流/内容中心 | v2 references/unsupported-dimensions.md | dwm_browser_event_aggregation_label_di；dwm_newhome_event_aggregation_label_di | 需补使用优先级：中间表优先，缺维度再回退底表 | P0 |
| 🟡 部分维护 | 搜索 | 搜索表结构 | 主动搜索PV/UV表、query意图表、一级意图聚合表、搜索留存表已登记 | v2 references/search/data_tables.yaml；table-schema.md | dm_search_pv_uv；ads_search_intent；ads_search_intent_level1；dm_browser_search_core | 表结构已登记，但 SQL 口径文件尚未补齐 | P0 |
| 🟡 部分维护 | 搜索 | 搜索埋点指标 | 搜索SUG页UV | v2 references/search/raw-event-metrics-reference.md | dwd_ot_event_di_31000000442 | 当前可直接使用的搜索指标只有 SUG 页 UV | P0 |
| ❌ 未维护 | 搜索 | 搜索核心指标 | 主动搜索PV/UV、搜索渗透率、人均搜索次数、AI搜索UV、AI人均搜次 | v2 TODO；核心字典已有“人均搜索次数” | dm_search_pv_uv | 补 core-metrics-reference SQL 模板、指标定义、分母口径 | P0 |
| ❌ 未维护 | 搜索 | 搜索意图分析 | 热门搜索词、query意图分布、一级/二级意图、dod/wow/mom、搜索渠道探索 | v2 TODO；WORK-PLAN.md:106 | ads_search_intent；ads_search_intent_level1 | 补按 query/intent 聚合 SQL 与常用过滤项 | P0 |
| ❌ 未维护 | 搜索 | 搜索留存 | 搜索用户次留、7留、30留；新搜索用户次留/7留/30留 | v2 TODO | dm_browser_search_core | 补“过去7天日均、不含昨日”的周报口径模板 | P1 |
| ❌ 未维护 | 人群包 | 圈选口径 | 短剧push人群包、京东618人群包、版本圈选、第三方APP交集、已售卖排除、did→oaid映射 | 数据资产人群包模板；WORK-PLAN.md:71；WORK-PLAN.md:72 | 人群包模板库；人群包登记表 | 补真实表名、label字段、did/oaid映射表、版本规则、排除项 | P0 |
| ❌ 未维护 | 实验分析 | 实验对比/留存模板 | Push增量价值、实验组vs对照组消费/留存/收入、LT3/LT7/LT14/LT30、DID双重差分 | WORK-PLAN.md:49；2026-07-02每日回顾 | 历史 Push 增量 SQL；实验分析 Agent | 补通用 SQL 模板；Push 类必须 DID，禁止直接 TGI 对比 | P0 |
| ❌ 未维护 | Top-N 高频取数 | Top-N 模板 | Top机型、Top网址、Top账号、Top内容/物料 | 高频取数模板；WORK-PLAN.md:54 | 待沉淀 SQL 模板 | 补参数化模板、排序指标、去重粒度、日期窗口 | P1 |
| ❌ 未维护 | 财收/流水 | 财务细口径 | 算法来源、分CP、剔除内投、月计提vs季度结算、预算/月季进度、短剧/直播/小说分体裁计提 | 核心指标口径字典；WORK-PLAN.md:126 | 财收看板/财收播报 | 现 skill 只有广告通用指标，缺财务治理口径 | P1 |
| ❌ 未维护 | 直播 | 直播看板口径 | 直播数据看板更新、直播数据接入校验 | WORK-PLAN.md:82 | 直播看板/数据源待确认 | 补数据源表、DAU/观看/收入/转化等指标定义 | P1 |
| ❌ 未维护 | 短剧/畅看 | 专项业务口径 | 短剧SDK埋点、短剧频道去重、畅看数据口径、火山小说消费UV折损、实验增加浏览器口径 | WORK-PLAN.md:68；WORK-PLAN.md:69；WORK-PLAN.md:73 | 短剧/小说/畅看相关表 | 补专项指标树和对应 SQL case | P1 |
| ❌ 未维护 | 常用表清单 | 学员/AI学习表清单 | label表、new_home相关表、数鲸常用看板、核心看板链接 | WORK-PLAN.md:55；WORK-PLAN.md:67 | 常用表清单待整理 | 补表名、业务说明、粒度、分区字段、常用 join key | P0 |
| ❌ 未维护 | 埋点参数 | TOP10埋点指标 | 信息流UV/时长埋点参数、顶tab/底tab/详情页UV和时长、滑动/搜索/启动退出埋点 | WORK-PLAN.md:54；WORK-PLAN.md:65；WORK-PLAN.md:116 | Onetrack/埋点文档 | Q3 不做埋点重构二期，但 TOP10 参数需先维护 | P1 |

## 维护建议

1. P0 先补：搜索核心指标、常用表清单、人群包真实表名、实验分析 DID 模板。
2. P1 再补：财收细口径、直播看板、短剧/畅看专项、Top-N 模板。
3. 每新增一条口径需标注：来源、数据源表、参数、验证状态、适用业务边界。
4. 未经真实查询验证的口径统一标记为“待校准”，不要冒充已验证。

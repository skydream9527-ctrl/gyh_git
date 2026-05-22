# 主底表：dwm_djy_dau_user_consum_index_di

> 都江堰自建信息流 DAU 用户消费明细宽表，本 Agent 全部 SQL 都基于此表。

| 项 | 值 |
|---|---|
| 全限定名 | `iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di` |
| catalog | `iceberg_zjyprc_hadoop` |
| 引擎 | `presto` 或 `spark`（推荐 presto，子查询聚合更快） |
| 分区 | `date INT`（YYYYMMDD） |
| 粒度 | 一行 = 一个 (did, date, item_id, feed_channel, page) 维度组合的当日消费记录 |
| 数据延迟 | T+1 出数；今日 (T0) 不可信 |

---

## 字段分组（来自 model.sql 的逻辑分块）

### 1. 实验流量
- `djy_rec_expid`：算法实验 ID（含多个实验时是 `,` 拼接的字符串，用 LIKE 匹配）
- `exp_group`：实验组（**不直接用**，用 `exp_group_6`）
- `observation_group`：观察组（**不直接用**，用 `exp_group_6`）
- `exp_group_6`：流量分组（6 个核心组：36%自建组 / 36%火山组 / 自建反转组 / 火山反转组 / 自建纯净组 / 火山纯净组）— **都江堰数据统一用这个**
- `exp_id_v2`：备用，根据 djy_rec_expid 模糊匹配出的 6 组归并

### 2. 设备信息
- `did`：设备 ID（计算 UV / DAU 用）
- `device_age` / `device_age_5_level`：激活天数与 5 分段
- `start_price_7_level` / `start_price_3_level`：机型起售价分段
- `user_age_8_level` / `user_sex`：年龄 8 段 / 性别
- `habitation_city_level`：居住地城市等级

### 3. 内容信息
- `item_id` / `item_title` / `item_type`（图文/短视频/小视频/短故事/小说）
- `item_category` / `item_subcategory`：内容一二级分类
- `item_publish_time_int` / `item_publish_time_level` / `item_publish_time_range_v2`：发布时效
- `video_length` / `video_length_level` / `video_length_level_v2`：视频时长与分桶
- `tuwen_words_cnt`：图文字数

### 4. 作者 / CP
- `item_author_id` / `item_author_name` / `item_cp_name`
- `article_level`：作者后验分层（基于消费数据）
- `cp_author_level`：作者先验分层（基于平台规则）
- `introduction_type` / `ruku_delay` / `is_cold`：内容引入类型 / 入库延迟 / 是否冷启

### 5. 用户标签
- `app_launch_way`：启动方式
- `is_app_deep_user` / `is_feed_deep_user`：浏览器/信息流深度用户
- `layer`：RFM 分层
- `is_feed_new`：是否信息流新用户
- `is_feed_active_new` / `is_feed_active_new_no_push`：是否有效用户（含/不含 push）
- `is_vliad_user_new` / `is_valid_user_new_no_push`：新版有效用户判定（20260306 起切换）

### 6. 信息流频道与页面
- `feed_channel`：频道（热点 / 推荐 / push / profile / profile_djy / 其他）
- `page` / `is_core_page`：页面（列表页 / 短小融合沉浸页 / 小视频沉浸页 / 评论区 / …）
- `page_origin`：内流入口标识
- `root_gid` / `is_click_content_enter`：内流首条 ID / 是否点击进入内流
- `item_position`：曝光位置

### 7. 小说 / 短故事专属
- `item_alg_source`：内容推荐来源
- `book_type`：书籍类型
- `read_source` / `next_novel` / `last_read_source`：阅读来源链路（用于"自建口径"的过滤）

### 8. 数据指标（model.sql 已限定口径）
- 时长类：`dura`（页面总时长，限定主频道）/ `consum_dura`（消费时长，限定自建口径）
- 曝光：`expose_pv`（限定主频道）
- 点击：`click_pv`（仅列表页有，限定主频道）
- 消费：`consum_pv` / `all_consum_pv`（完播完读）/ `valid_consum_pv`（有效播读）
- 互动：`like_pv` / `comment_pv` / `share_pv` / `comment_area_pv` / `comment_area_dura` / `negative_pv` / `report_pv`
- 阅读：`shortstory_read_cnt` / `shortstory_read_dura` / `novel_read_cnt` / `novel_read_dura`（大盘口径）
- 阅读 v2：`shortstory_read_cnt_v2` / `shortstory_read_dura_v2` / `novel_read_cnt_v2` / `novel_read_dura_v2`（自建信息流口径，**推荐用 v2**）
- 内流下滑：`xiahua_pv`
- 沉浸流：`firts_video_dura` / `drop_firts_video_dura` / `first_video_vv` / `drop_first_video_vv` / `avg_video_play_percent`
- 实验组限制：`djy_expose_pv` / `huoshan_expose_pv` / `total_djy_expose_pv` / `total_huoshan_expose_pv`（用于算"组内占比"）
- 用户粒度计数：`expose_cnt` / `consum_cnt_v2` / `consum_cnt_v2_no_push`
- 内容粒度计数：`like_cnt` / `comment_cnt` / `share_cnt`

---

## 与 metrics/dimensions.csv、metrics/indexes.csv 的关系

| 文件 | 内容 | 用法 |
|---|---|---|
| `sql/model.sql` | 字段计算逻辑（CASE WHEN / IF）的权威来源 | 拼 SQL 时整段塞进 CTE |
| `metrics/dimensions.csv` | 60 个维度的 name / label / fieldType / alias | Phase 1 选维度，fieldType=5 维度做过滤时**必须查这里取完整 CASE WHEN** |
| `metrics/indexes.csv` | 100+ 指标的 name / label / aggregator / fieldType | Phase 1 选指标，fieldType=4 派生指标的公式都在这里 |

口径冲突时 **以 model.sql 为准**（它是实际跑的代码，CSV 是检索目录）。

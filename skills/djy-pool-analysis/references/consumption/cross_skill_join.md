# P4 联合分析：内容池质量 × 消费表现

## 用途

分析内容池中字段质量缺失（如 `author_image` 为空）的内容，其消费表现是否比字段正常的内容更差。

## 表关联规则

| 表 | 角色 | JOIN 字段 |
|---|---|---|
| `iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di` | 消费表（c） | `c.item_id` |
| `paimon_zjyprc_hadoop.browser.business_content_pool_realtime` | 内容池表（pool） | `pool.a_item_id` |

**JOIN 条件**：`c.item_id = pool.a_item_id`

## CP 字段映射

| 消费表字段 | 内容池表字段 | 说明 |
|---|---|---|
| `item_cp_name` | `a_cp` | CP 标识，值格式不同 |

消费表 `item_cp_name` 值示例：`dihui` / `beike` / `guoying` / `meilaoban`
内容池表 `a_cp` 值：`cn-dihui-djy` / `cn-beike-djy` / `cn-guoying-djy` / `cn-meilaoban-djy`

过滤时用对应表自己的字段值。

## SQL 模板

```sql
SELECT
    CASE WHEN pool.{{FIELD_NAME}} IS NULL OR pool.{{FIELD_NAME}} = ''
         THEN '字段为空' ELSE '字段有值' END AS field_status,
    COUNT(DISTINCT c.item_id) AS item_count,
    SUM(c.expose_pv) AS expose_pv,
    SUM(c.click_pv) AS click_pv,
    ROUND(SUM(c.click_pv) * 1.0 / NULLIF(SUM(c.expose_pv), 0), 4) AS ctr,
    SUM(c.consum_pv) AS consum_vv,
    ROUND(SUM(c.consum_dura) / NULLIF(SUM(c.consum_pv), 0) * 60, 1) AS avg_consum_dura_sec
FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di c
JOIN paimon_zjyprc_hadoop.browser.business_content_pool_realtime pool
    ON c.item_id = pool.a_item_id
WHERE c.date BETWEEN '{{DATE_START}}' AND '{{DATE_END}}'
    AND c.feed_channel IN ('推荐', '热点')
    AND c.page IN ('列表页')
    {{CP_FILTER}}
GROUP BY CASE WHEN pool.{{FIELD_NAME}} IS NULL OR pool.{{FIELD_NAME}} = ''
              THEN '字段为空' ELSE '字段有值' END
```

## 可联合分析的内容池字段

参考 `djy-pool-analysis/references/validate/rules.md` 的规则库：

| 字段 | 分析场景 |
|---|---|
| `author_image` | 头像缺失是否影响点击率 |
| `image` | 封面图缺失是否影响曝光转化 |
| `category` | 无分类内容是否消费更差 |
| `video_duration` | 时长为 0 的内容是否被正常推荐 |
| `video_detail_list` | 视频详情不完整是否影响播放 |
| `lead_author_id` | 主作者未绑定是否影响分发 |

## 性能注意

1. **必须**先用 `c.date BETWEEN` 过滤消费表，缩小 JOIN 范围
2. 建议日期范围不超过 7 天（否则可能超时）
3. 可加 CP 过滤进一步缩小：`AND pool.a_cp = 'cn-dihui-djy'`

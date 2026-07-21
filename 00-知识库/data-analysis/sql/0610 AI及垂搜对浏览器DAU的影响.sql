---- 0610 AI及垂搜对浏览器DAU的影响 



WITH app_a_activity AS (
    SELECT
        DISTINCT
        date,
        distinct_id,
        1 is_active
    from browser.dwm_browser_event_aggregation_label_di 
    where date between 20240901 and 20250531   
    and is_app_dau_2024 = 1 
    and app_open_cnt > 0
)

,app_b_activity AS (
    SELECT
        DISTINCT
        date,
        distinct_id,
        1 is_active
    FROM
        iceberg_zjyprc_hadoop.newhome.ai_search_rela_app_did_v2
    WHERE 
        date between 20240901 and 20250531 
        and open_cnt > 0
        and package_name in 
        (
        'com.larus.nova',  --豆包
        'com.moonshot.kimichat',  --kimi
        'com.baidu.newapp',  --文小言
        'com.deepseek.chat',  --deepseek
        'com.tencent.hunyuan.app.chat'  --腾讯元宝
        )

    union

    SELECT
        DISTINCT
        date,
        distinct_id,
        1 is_active
    FROM
        iceberg_zjyprc_hadoop.newhome.search_rela_app_did_v2
    WHERE 
        date between 20240901 and 20250531 
        and open_cnt > 0
        and (
            (package_name='com.ss.android.ugc.aweme' 
            and class_name='com.ss.android.ugc.aweme.search.activity.SearchResultActivity')
            OR
            (package_name='com.xingin.xhs' 
            and class_name='com.xingin.alioth.search.GlobalSearchActivity')
        )
)

,combined_activity AS (
    SELECT 
        COALESCE(a.distinct_id, b.distinct_id) AS user_id,
        COALESCE(a.date, b.date) AS date,
        COALESCE(a.is_active, 0) AS active_a,
        COALESCE(b.is_active, 0) AS active_b
    FROM app_a_activity a
    FULL OUTER JOIN app_b_activity b
    ON a.distinct_id = b.distinct_id AND a.date = b.date
)

,inactivity_calculation AS (
    SELECT
        user_id,
        date,
        active_a,
        active_b,
        -- 标记连续不活跃天数
        SUM(active_a) OVER (PARTITION BY user_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS active_a_last_30_days,
        SUM(active_a) OVER (PARTITION BY user_id ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS active_a_last_60_days
    FROM combined_activity
)

,loss_users AS (
    SELECT
        user_id,
        loss_date
    FROM
    (
        SELECT
            user_id,
            date AS loss_date,
            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY date) rn
        FROM inactivity_calculation
        WHERE 
            active_a_last_30_days = 0  -- 连续30天未活跃于 App A
            AND active_a_last_60_days >= 3  --此前至少3天活跃过 App A
            AND active_b = 1          -- 流失当天活跃于 App B
            AND date >= 20240801  -- 确保有30天观察窗口
    ) t
    where rn = 1  -- 取首次流失日期
)

,dau_impact AS (
    SELECT
        c.date,
        -- 实际 DAU
        SUM(c.active_a) AS actual_dau,
        -- 流失用户导致的 DAU 损失（假设流失用户原本可能活跃）
        COUNT(DISTINCT l.user_id) AS lost_dau,
        COUNT(DISTINCT case when c.active_a=0 then l.user_id end) AS lost_dau_yj
    FROM combined_activity c
    LEFT JOIN loss_users l 
      ON c.user_id = l.user_id 
      AND c.date >= l.loss_date  -- 从流失日期开始计算影响
    GROUP BY c.date
)

--垂搜+AI影响
SELECT 
    date,
    actual_dau,
--    lost_dau,
    lost_dau_yj
FROM dau_impact
ORDER BY date
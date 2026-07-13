-- 信息流留存指标查询 SQL（优化版）
-- 用于分析版本灰度期间的信息流用户留存情况
-- 优化说明：简化查询结构，减少子查询嵌套

with date_2 as ( 
    select 
        did as distinct_id, 
        app_ver, 
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        is_valid_dapan_2024 as valid_flag1, 
        max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date=20260330 
        and feed_status in ('true','false') 
    group by 
        did,
        app_ver, 
        is_new_feed_2024,
        is_valid_dapan_2024
), 
date_2all as ( 
    select 
        distinct_id, 
        app_ver, 
        '大盘用户' as user_type, 
        valid_flag1, 
        exp_flag 
    from 
        date_2 
    union all 
    select 
        distinct_id, 
        app_ver, 
        user_type, 
        valid_flag1, 
        exp_flag 
    from 
        date_2 
), 
date_1all as ( 
    select 
        did, 
        is_valid_dapan_2024 as valid_flag1, 
        max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date=20260331 
        and feed_status in ('true','false') 
    group by 
        did, 
        is_valid_dapan_2024 
) 

INSERT OVERWRITE table iceberg_zjyprc_hadoop.browser.browser_feeds_liucun partition (date=20260331) 
select 
    user_type, 
    app_ver, 
    sum(if (a.exp_flag=1 and b.exp_flag=1, 1, 0))/sum(if (a.exp_flag=1, 1, 0)) as e2e_ret, 
    sum(if (a.exp_flag=1 and b.valid_flag1=1, 1, 0))/sum(if (a.exp_flag=1, 1, 0)) as e2v_ret, 
    sum(if (b.did is not null and b.valid_flag1=1 and a.valid_flag1=1, 1, 0))/sum(a.valid_flag1) as v2v_ret 
from 
    date_2all a 
    left join date_1all b on distinct_id=did 
group by 
    user_type, 
    app_ver 
order by 
    user_type, 
    app_ver
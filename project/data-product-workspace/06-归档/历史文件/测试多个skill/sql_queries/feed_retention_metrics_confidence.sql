-- 信息流留存指标 - 置信度计算数据提取
-- 用于 Z 检验：提取用户级数据用于统计检验
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with date_2 as ( 
    select 
        date,
        did as distinct_id, 
        app_ver, 
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        is_valid_dapan_2024 as valid_flag1, 
        max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and feed_status in ('true','false')
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver, 
        is_new_feed_2024,
        is_valid_dapan_2024
), 
date_2all as ( 
    select 
        date,
        distinct_id, 
        app_ver, 
        '大盘用户' as user_type, 
        valid_flag1, 
        exp_flag 
    from 
        date_2 
    union all 
    select 
        date,
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
        date,
        did, 
        is_valid_dapan_2024 as valid_flag1, 
        max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and feed_status in ('true','false')
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did, 
        is_valid_dapan_2024 
)

-- 曝光到曝光留存（比率类指标 - Z检验）
select 
    a.date,
    a.app_ver,
    a.user_type,
    'e2e_ret' as metric_name,
    'ratio' as metric_type,
    a.distinct_id as user_id,
    case when a.exp_flag=1 and b.exp_flag=1 then 1 else 0 end as metric_value
from 
    date_2all a 
    left join date_1all b on a.distinct_id=b.did AND a.date=b.date
where a.exp_flag = 1

union all

-- 曝光到有效留存（比率类指标 - Z检验）
select 
    a.date,
    a.app_ver,
    a.user_type,
    'e2v_ret' as metric_name,
    'ratio' as metric_type,
    a.distinct_id as user_id,
    case when a.exp_flag=1 and b.valid_flag1=1 then 1 else 0 end as metric_value
from 
    date_2all a 
    left join date_1all b on a.distinct_id=b.did AND a.date=b.date
where a.exp_flag = 1

union all

-- 有效到有效留存（比率类指标 - Z检验）
select 
    a.date,
    a.app_ver,
    a.user_type,
    'v2v_ret' as metric_name,
    'ratio' as metric_type,
    a.distinct_id as user_id,
    case when b.did is not null and b.valid_flag1=1 and a.valid_flag1=1 then 1 else 0 end as metric_value
from 
    date_2all a 
    left join date_1all b on a.distinct_id=b.did AND a.date=b.date
where a.valid_flag1 = 1

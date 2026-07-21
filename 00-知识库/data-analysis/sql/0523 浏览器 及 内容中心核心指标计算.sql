---- 0523 浏览器 及 内容中心核心指标计算


浏览器总DAU
浏览器有效DAU
浏览器主启动DAU
浏览器信息流dau


内容中心DAU
内容中心有效DAU

信息流DAU
信息流消费用户
信息流总时长（万小时）
信息流人均时长（分）

select app_launch_way, count(distinct did) as dau 
from browser.dwm_browser_event_aggregation_label_di 
where date = 20250521   
and is_dau_2024 = 1
group by app_launch_way


select  date,
        count(distinct did) as dau,
        count(distinct case when app_launch_way <> '第三方调起' then did end) as dau_control,
        count(distinct case when app_launch_way = ' 点击icon' then did end) as dau_icon,
        count(distinct case when expos_cnt > 0 then did end) as dau_feed,
        cast(sum(case when feed_dura > 0 then feed_dura end) as bigint)/60000 as feed_dura_sum
from 
(
    select  date,
            did,
            app_launch_way,
            app_open_cnt,
            is_dau_feed_dapan_2024,
            feed_dura,
            expos_cnt
    from browser.dwm_browser_event_aggregation_label_di 
    where date between 20250515 and 20250521   
    and is_app_dau_2024 = 1 
) a 
group by date 




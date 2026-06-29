DATAWORKS_TOKEN_ID#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

work_dir = os.path.expanduser("~/Desktop/20260407_AB分析_20.11.1010115")

sql_templates = {
    "feed_dau_rate_metrics.sql": """-- 信息流日活率指标查询 SQL
with base_data as (
    select date, did, app_ver, is_new_feed_2024, is_new_miui_imei_2024,
        sum(if (is_top=0, expos_cnt, 0)) as nt_expose,
        sum(if (is_top=0, click_cnt, 0)) as nt_click,
        sum(if (is_top=0, view_cnt, 0)) as nt_view,
        sum(if (is_top=0, video_play_cnt, 0)) as nt_play,
        sum(ad_content_expose_cnt) as ad_expose_tally,
        sum(ad_content_request_client_cnt) as ad_request_tally,
        sum(app_open_cnt) as app_open_cnt
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di  
    where date BETWEEN 20260116 AND 20260118
        and feed_status in ('true', 'false')
        and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_feed_2024, is_new_miui_imei_2024
),
ad_table as ( 
    select date, if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, app_ver, 
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_uv_n,
        sum(ad_request_tally) as ad_request_uv_sum,
        sum(if (ad_expose_tally>0, 1, 0)) as ad_expose_rate_numerator,
        sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate_denominator,
        sum(if (ad_expose_tally>0, 1, 0))/sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate_value,
        avg(ad_request_tally) as ad_request_avg_mean,
        stddev(ad_request_tally) as ad_request_avg_std,
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_avg_n
    from base_data
    where ad_request_tally > 0 or ad_expose_tally > 0
    group by date, app_ver, if (is_new_feed_2024 = 1, '新用户', '老用户')
    union all 
    select date, '大盘用户' as user_type, app_ver, 
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_uv_n,
        sum(ad_request_tally) as ad_request_uv_sum,
        sum(if (ad_expose_tally>0, 1, 0)) as ad_expose_rate_numerator,
        sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate_denominator,
        sum(if (ad_expose_tally>0, 1, 0))/sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate_value,
        avg(ad_request_tally) as ad_request_avg_mean,
        stddev(ad_request_tally) as ad_request_avg_std,
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_avg_n
    from base_data
    where ad_request_tally > 0 or ad_expose_tally > 0
    group by date, app_ver 
), 
browser_feeds as ( 
    select date, if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, app_ver, count(1) as feed_dau
    from base_data
    where nt_expose + nt_click + nt_view + nt_play > 0
    group by date, app_ver, if (is_new_feed_2024 = 1, '新用户', '老用户')
    union all
    select date, '大盘用户' as user_type, app_ver, count(1) as feed_dau
    from base_data
    where nt_expose + nt_click + nt_view + nt_play > 0
    group by date, app_ver
), 
browser_rate as ( 
    select t2.date as date, t2.user_type as user_type, t2.app_ver as app_ver,
        t2.browser_dau as browser_dau,
        if (t1.feed_dau is null, 0, t1.feed_dau) as rate_numerator,
        t2.browser_dau as rate_denominator,
        if (t1.feed_dau is null, 0, t1.feed_dau)/t2.browser_dau as rate_value
    from browser_feeds t1
    right join ( 
        select date, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, app_ver, count(distinct did) as browser_dau 
        from base_data where app_open_cnt > 0
        group by date, app_ver, if (is_new_miui_imei_2024 = 1, '新用户', '老用户')
        union all 
        select date, '大盘用户' as user_type, app_ver, count(distinct did) as browser_dau 
        from base_data where app_open_cnt > 0
        group by date, app_ver 
    ) t2 on t1.user_type=t2.user_type and t1.app_ver=t2.app_ver and t1.date=t2.date
)
SELECT 
    if (ad_table.user_type is not null, ad_table.user_type, browser_rate.user_type) as user_type, 
    if (ad_table.app_ver is not null, ad_table.app_ver, browser_rate.app_ver) as app_ver,
    if (ad_table.date is not null, ad_table.date, browser_rate.date) as date,
    browser_rate.rate_numerator, browser_rate.rate_denominator, browser_rate.rate_value,
    ad_table.ad_request_uv_n, ad_table.ad_request_uv_sum,
    ad_table.ad_request_uv_mean, 0 as ad_request_uv_std,
    ad_table.ad_expose_rate_numerator, ad_table.ad_expose_rate_denominator, ad_table.ad_expose_rate_value,
    ad_table.ad_request_avg_mean, ad_table.ad_request_avg_std, ad_table.ad_request_avg_n
from ad_table 
full join browser_rate on ad_table.user_type=browser_rate.user_type 
    and ad_table.app_ver=browser_rate.app_ver and ad_table.date=browser_rate.date
ORDER BY date, user_type, app_ver
""",

    "feed_consumption_metrics.sql": """-- 信息流消费指标查询 SQL
with base as ( 
    select date, did as distinct_id, app_ver, if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        sum(if (is_top=0, expos_cnt, 0)) as nt_expose, 
        sum(if (is_top=0, click_cnt, 0)) as nt_click, 
        sum(if (is_top=0, view_cnt, 0)) as nt_view, 
        sum(if (is_top=0, video_play_cnt, 0)) as nt_play, 
        sum(if (is_top=0 and feed_channel != 'push' and feed_status = 'true', expose_enter_cnt, 0)) as ntp_expose_enter, 
        sum(if (is_top=0 and feed_channel != 'push' and feed_status = 'true', click_enter_cnt, 0)) as ntp_click_enter, 
        sum(if (is_top=0 and lower(item_type)='news', click_cnt, 0)) as news_v, 
        sum(if (is_top=0 and lower(item_type) = 'inline_video', video_play_cnt, 0)) as short_v, 
        sum(if (is_top=0 and lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_v, 
        sum(if (feed_status='true', feed_dura, 0)) as feed_dura, 
        sum(consum_dura) as xiaofei_duration 
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where date BETWEEN 20260116 AND 20260118
        and feed_status in ('true','false')
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_feed_2024
), 
base_all as ( 
    select date, distinct_id, app_ver, '大盘用户' as user_type, nt_expose, nt_click, nt_view, nt_play, 
        ntp_expose_enter, ntp_click_enter, 
        if (ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag, 
        news_v, short_v, mini_v, feed_dura, xiaofei_duration 
    from base 
    union all 
    select date, distinct_id, app_ver, user_type, nt_expose, nt_click, nt_view, nt_play, 
        ntp_expose_enter, ntp_click_enter, 
        if (ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag, 
        news_v, short_v, mini_v, feed_dura, xiaofei_duration 
    from base 
) 
SELECT date, user_type, app_ver, count(1) as sample_size,
    sum(valid_flag) as valid_rate_numerator, count(1) as valid_rate_denominator, sum(valid_flag)/count(1) as valid_rate_value,
    avg(nt_expose) as avg_expose_mean, stddev(nt_expose) as avg_expose_std, count(1) as avg_expose_n,
    avg(news_v+short_v+mini_v) as avg_vv_mean, stddev(news_v+short_v+mini_v) as avg_vv_std, count(1) as avg_vv_n,
    avg(feed_dura/60000) as avg_dur_mean, stddev(feed_dura/60000) as avg_dur_std, count(1) as avg_dur_n,
    avg(xiaofei_duration/60000) as avg_xiaofei_dur_mean, stddev(xiaofei_duration/60000) as avg_xiaofei_dur_std, count(1) as avg_xiaofei_dur_n,
    sum(news_v+short_v+mini_v) as ctr_numerator, sum(nt_expose) as ctr_denominator, sum(news_v+short_v+mini_v)/sum(nt_expose) as ctr_value,
    sum(if (news_v+short_v+mini_v>0, 1, 0)) as utr_numerator, count(1) as utr_denominator, sum(if (news_v+short_v+mini_v>0, 1, 0))/count(1) as utr_value
from base_all 
where nt_expose>0 or nt_click>0 or nt_view>0 or nt_play>0
group by date, user_type, app_ver
ORDER BY date, user_type, app_ver
""",

    "tracking_monitoring_metrics.sql": """-- 埋点监控指标查询 SQL
with base_data as (
    select date, did, app_ver, is_new_feed_2024,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_video_play_tally,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video'), video_over_cnt, 0)) as mini_video_over_tally,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video') and duration_type ='detail_page', feed_dura, 0)) as mini_detail_dur,
        sum(if (lower(item_type)='inline_video', video_play_cnt, 0)) as short_video_play_tally,
        sum(if (lower(item_type)='inline_video', video_over_cnt, 0)) as short_video_over_tally,
        sum(if (lower(item_type)='inline_video', video_over_event_dura, 0)) as short_feed_dur,
        sum(if (lower(item_type)='news', view_quit_cnt, 0)) as news_view_tally,
        sum(if (lower(item_type)='news', view_event_dura, 0)) as news_detail_dur
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where date BETWEEN 20260116 AND 20260118
        and feed_status in ('true', 'false')
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_feed_2024
),
base as ( 
    SELECT date, did as distinct_id, app_ver, if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        mini_video_play_tally, mini_video_over_tally, mini_detail_dur, 
        short_video_play_tally, short_video_over_tally, short_feed_dur, 
        news_detail_dur, news_view_tally 
    from base_data
), 
base_all as ( 
    select date, distinct_id, app_ver, '大盘用户' as user_type, 
        mini_video_play_tally, mini_video_over_tally, mini_detail_dur, 
        short_video_play_tally, short_video_over_tally, short_feed_dur, 
        news_detail_dur, news_view_tally 
    from base 
    union all 
    select date, distinct_id, app_ver, user_type, 
        mini_video_play_tally, mini_video_over_tally, mini_detail_dur, 
        short_video_play_tally, short_video_over_tally, short_feed_dur, 
        news_detail_dur, news_view_tally 
    from base 
) 
SELECT date, user_type, app_ver, count(1) as sample_size,
    sum(mini_video_over_tally)+sum(short_video_over_tally) as paly_rate_numerator,
    sum(mini_video_play_tally)+sum(short_video_play_tally) as paly_rate_denominator,
    (sum(mini_video_over_tally)+sum(short_video_over_tally))/(sum(mini_video_play_tally)+sum(short_video_play_tally)) as paly_rate_value,
    avg(mini_detail_dur/60000) as mini_avg_dur_mean, stddev(mini_detail_dur/60000) as mini_avg_dur_std, count(1) as mini_avg_dur_n,
    avg(short_feed_dur/60000) as short_avg_dur_mean, stddev(short_feed_dur/60000) as short_avg_dur_std, count(1) as short_avg_dur_n,
    avg((news_detail_dur+mini_detail_dur+short_feed_dur)/60000) as avg_xiaofei_dur_mean,
    stddev((news_detail_dur+mini_detail_dur+short_feed_dur)/60000) as avg_xiaofei_dur_std,
    count(1) as avg_xiaofei_dur_n
from base_all 
where mini_video_play_tally + short_video_play_tally > 0
group by date, user_type, app_ver 
ORDER BY date, user_type, app_ver
""",

    "feed_retention_metrics.sql": """-- 信息流留存指标查询 SQL
with date_2 as ( 
    select date, did as distinct_id, app_ver, if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        is_valid_dapan_2024 as valid_flag1, 
        max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where date BETWEEN 20260115 AND 20260117
        and feed_status in ('true','false')
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_feed_2024, is_valid_dapan_2024
), 
date_2all as ( 
    select date, distinct_id, app_ver, '大盘用户' as user_type, valid_flag1, exp_flag from date_2 
    union all 
    select date, distinct_id, app_ver, user_type, valid_flag1, exp_flag from date_2 
), 
date_1all as ( 
    select date, did, is_valid_dapan_2024 as valid_flag1, max(if(is_top = 0 and expos_cnt > 0, 1, 0)) as exp_flag 
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where date BETWEEN 20260116 AND 20260118
        and feed_status in ('true','false')
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, is_valid_dapan_2024 
) 
SELECT a.date as date, a.user_type, a.app_ver,
    sum(if (a.exp_flag=1 and b.exp_flag=1, 1, 0)) as e2e_ret_numerator,
    sum(if (a.exp_flag=1, 1, 0)) as e2e_ret_denominator,
    sum(if (a.exp_flag=1 and b.exp_flag=1, 1, 0))/sum(if (a.exp_flag=1, 1, 0)) as e2e_ret_value,
    sum(if (a.exp_flag=1 and b.valid_flag1=1, 1, 0)) as e2v_ret_numerator,
    sum(if (a.exp_flag=1, 1, 0)) as e2v_ret_denominator,
    sum(if (a.exp_flag=1 and b.valid_flag1=1, 1, 0))/sum(if (a.exp_flag=1, 1, 0)) as e2v_ret_value,
    sum(if (b.did is not null and b.valid_flag1=1 and a.valid_flag1=1, 1, 0)) as v2v_ret_numerator,
    sum(a.valid_flag1) as v2v_ret_denominator,
    sum(if (b.did is not null and b.valid_flag1=1 and a.valid_flag1=1, 1, 0))/sum(a.valid_flag1) as v2v_ret_value
from date_2all a 
left join date_1all b on a.distinct_id=b.did and a.date = b.date - 1
group by a.date, a.user_type, a.app_ver 
ORDER BY date, user_type, app_ver
""",

    "scale_experience_metrics.sql": """-- 规模体验指标查询 SQL
with base_data as (
    select date, did, app_ver, is_new_miui_imei_2024,
        sum(app_open_cnt) as app_open_cnt,
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv,
        sum(search_security_cnt) as search_cnt
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where date BETWEEN 20260116 AND 20260118
        and app_open_cnt > 0 and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_miui_imei_2024
),
base_all as ( 
    select date, did, '大盘用户' as user_type, app_ver, search_cnt from base_data
    union all 
    select date, did, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, app_ver, search_cnt from base_data
), 
base1_all as ( 
    select date, did, '大盘用户' as user_type, app_ver, 
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv 
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where date BETWEEN 20260115 AND 20260117
        and app_open_cnt > 0 and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver
    union all 
    select date, did, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, app_ver, 
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv 
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where date BETWEEN 20260115 AND 20260117
        and app_open_cnt > 0 and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_miui_imei_2024
), 
result1 as ( 
    select base1_all.date as date, base1_all.user_type as user_type, base1_all.app_ver as app_ver,
        sum(if (t.did is not null, 1, 0)) as open_rate_numerator,
        count(base1_all.did) as open_rate_denominator,
        sum(if (t.did is not null, 1, 0))/count(base1_all.did) as open_rate_value,
        sum(if (t.did is not null and zhuqi_pv>0, 1, 0)) as zhuqi_rate_numerator,
        sum(if (base1_all.did is not null and zhuqi_pv>0, 1, 0)) as zhuqi_rate_denominator,
        sum(if (t.did is not null and zhuqi_pv>0, 1, 0))/sum(if (base1_all.did is not null and zhuqi_pv>0, 1, 0)) as zhuqi_rate_value
    from base1_all 
    left join (select distinct date, did from base_all) t 
        on base1_all.did=t.did and base1_all.date = t.date - 1
    group by base1_all.date, base1_all.user_type, base1_all.app_ver 
), 
result2 as ( 
    select date, user_type, app_ver,
        sum(if (search_cnt>0, 1, 0)) as sousuo_rate_numerator,
        count(did) as sousuo_rate_denominator,
        sum(if (search_cnt>0, 1, 0))/count(did) as sousuo_rate_value,
        avg(search_cnt) as avg_search_mean,
        stddev(search_cnt) as avg_search_std,
        count(did) as avg_search_n
    from base_all group by date, user_type, app_ver 
) 
SELECT if (a.user_type is not null, a.user_type, b.user_type) as user_type, 
    if (a.app_ver is not null, a.app_ver, b.app_ver) as app_ver,
    if (a.date is not null, a.date, b.date) as date,
    a.open_rate_numerator, a.open_rate_denominator, a.open_rate_value,
    a.zhuqi_rate_numerator, a.zhuqi_rate_denominator, a.zhuqi_rate_value,
    b.sousuo_rate_numerator, b.sousuo_rate_denominator, b.sousuo_rate_value,
    b.avg_search_mean, b.avg_search_std, b.avg_search_n
from result1 a 
full join result2 b on a.user_type=b.user_type and a.app_ver=b.app_ver and a.date = b.date - 1
ORDER BY date, user_type, app_ver
""",

    "ot_advertising_metrics.sql": """-- OT 口径广告指标查询 SQL
with base_data as (
    select date, did, app_ver, is_new_miui_imei_2024,
        sum(ad_content_expose_cnt) as ad_expose,
        sum(ad_content_request_sever_cnt) as ad_require,
        sum(ad_content_click_cnt) as ad_click,
        sum(ad_content_return_sever_cnt) as ad_return
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where date BETWEEN 20260116 AND 20260118
        and coalesce(did,'') != ''
        and tag_id not in ('1.13.c.4', '1.13.f.14', '1.13.f.17', '1.13.f.18', '1.13.f.20', '1.13.r.2', '1.13.r.3')
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did, app_ver, is_new_miui_imei_2024
),
q1 as ( 
    select a.date as date, a.did as did, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, a.app_ver as app_ver, 
        ad_expose, ad_click, ad_require, ad_return 
    from ( 
        select date, did, app_ver, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type 
        from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
        where date BETWEEN 20260116 AND 20260118
            and app_open_cnt > 0 and coalesce(did,'') != ''
            and app_ver IN ('20.11.1010115', '20.11.10115')
        group by date, did, app_ver, if (is_new_miui_imei_2024 = 1, '新用户', '老用户') 
    ) a 
    left join base_data b on a.did=b.did and a.app_ver=b.app_ver and a.date=b.date
), 
q2 as ( 
    select date, did, '大盘用户' as user_type, app_ver, ad_expose, ad_click, ad_require, ad_return from q1 
    union all 
    select date, did, user_type, app_ver, ad_expose, ad_click, ad_require, ad_return from q1 
) 
SELECT date, user_type, app_ver, count(distinct did) as sample_size,
    avg(ad_expose) as ipu_mean, stddev(ad_expose) as ipu_std, count(distinct did) as ipu_n,
    sum(ad_require) as avg_require_sum, avg(ad_require) as avg_require_mean, stddev(ad_require) as avg_require_std, count(distinct did) as avg_require_n,
    sum(ad_click) as avg_click_sum, avg(ad_click) as avg_click_mean, stddev(ad_click) as avg_click_std, count(distinct did) as avg_click_n,
    sum(ad_return) as tianchong_rate_numerator, sum(ad_require) as tianchong_rate_denominator, sum(ad_return)/sum(ad_require) as tianchong_rate_value,
    sum(ad_click) as ctr_numerator, sum(ad_expose) as ctr_denominator, sum(ad_click)/sum(ad_expose) as ctr_value
from q2 group by date, user_type, app_ver
ORDER BY date, user_type, app_ver
""",

    "commercial_platform_metrics.sql": """-- 商业中台指标查询 SQL
with dau_base as (
    select date, did, max(app_ver) as app_ver, if(min(is_new_miui_imei_2024) = 1, '新用户', '老用户') as user_type
    from iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where date BETWEEN 20260116 AND 20260118
        and app_open_cnt > 0 and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by date, did
),
ad_data_all as (
    select date, did,
        sum(ad_return_cnt) as eadreturn, sum(query_cnt) as equery, sum(fee_amt)/100000 as fee,
        sum(vaild_view_cnt) as eview, sum(vaild_click_cnt) as eclick, sum(raw_view_cnt) as erawview,
        sum(start_download_cnt) as estardownload, coalesce(ad_position_media_type,'') as ad_position_media_type
    from iceberg_zjyprc_hadoop.browser.dwm_browser_ad_event_aggregation_di 
    where date BETWEEN 20260116 AND 20260118
    group by date, did, coalesce(ad_position_media_type,'')
),
q1 as ( 
    select a.date as date, a.did as distinct_id, user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery 
    from dau_base a
    left join (
        select date, did, sum(eadreturn) as eadreturn, sum(equery) as equery, sum(fee) as fee, sum(eview) as eview,
            sum(eclick) as eclick, sum(erawview) as erawview, sum(estardownload) as estardownload
        from ad_data_all where ad_position_media_type != '小说' group by date, did
    ) b on a.did = b.did and a.date = b.date
), 
q11 as ( 
    select a.date as date, a.did as distinct_id, user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery 
    from dau_base a
    left join (
        select date, did, sum(eadreturn) as eadreturn, sum(equery) as equery, sum(fee) as fee, sum(eview) as eview,
            sum(eclick) as eclick, sum(erawview) as erawview, sum(estardownload) as estardownload
        from ad_data_all where ad_position_media_type = '信息流' group by date, did
    ) b on a.did = b.did and a.date = b.date
), 
q2 as ( 
    select date, distinct_id, '大盘用户' as user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery from q1 
    union all select date, distinct_id, user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery from q1 
), 
q22 as ( 
    select date, distinct_id, '大盘用户' as user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery from q11 
    union all select date, distinct_id, user_type, app_ver, fee, eview, eclick, erawview, estardownload, eadreturn, equery from q11 
) 
SELECT date, user_type, '浏览器全广告位' as tag, app_ver, count(distinct distinct_id) as sample_size,
    avg(fee) as arpu_mean, stddev(fee) as arpu_std, count(distinct distinct_id) as arpu_n,
    avg(eview) as ipu_mean, stddev(eview) as ipu_std, count(distinct distinct_id) as ipu_n,
    sum(fee) as ecpm_fee_sum, sum(eview) as ecpm_view_sum, sum(fee)/sum(eview)*1000 as ecpm_value,
    sum(eadreturn) as tianchong_rate_numerator, sum(equery) as tianchong_rate_denominator, sum(eadreturn)/sum(equery) as tianchong_rate_value,
    sum(eview) as loudou_numerator, sum(erawview) as loudou_denominator, sum(eview)/sum(erawview) as loudou_value,
    sum(fee) as cpc_fee_sum, sum(eclick) as cpc_click_sum, sum(fee)/sum(eclick) as cpc_value,
    sum(eclick) as ctr_numerator, sum(eview) as ctr_denominator, sum(eclick)/sum(eview) as ctr_value,
    sum(estardownload) as cvr_numerator, sum(eclick) as cvr_denominator, sum(estardownload)/sum(eclick) as cvr_value,
    sum(erawview) as eview_sucess_rate_numerator, sum(eadreturn) as eview_sucess_rate_denominator, sum(erawview)/sum(eadreturn) as eview_sucess_rate_value
from q2 group by date, user_type, app_ver 
UNION all 
SELECT date, user_type, '信息流全广告位' as tag, app_ver, count(distinct distinct_id) as sample_size,
    avg(fee) as arpu_mean, stddev(fee) as arpu_std, count(distinct distinct_id) as arpu_n,
    avg(eview) as ipu_mean, stddev(eview) as ipu_std, count(distinct distinct_id) as ipu_n,
    sum(fee) as ecpm_fee_sum, sum(eview) as ecpm_view_sum, sum(fee)/sum(eview)*1000 as ecpm_value,
    sum(eadreturn) as tianchong_rate_numerator, sum(equery) as tianchong_rate_denominator, sum(eadreturn)/sum(equery) as tianchong_rate_value,
    sum(eview) as loudou_numerator, sum(erawview) as loudou_denominator, sum(eview)/sum(erawview) as loudou_value,
    sum(fee) as cpc_fee_sum, sum(eclick) as cpc_click_sum, sum(fee)/sum(eclick) as cpc_value,
    sum(eclick) as ctr_numerator, sum(eview) as ctr_denominator, sum(eclick)/sum(eview) as ctr_value,
    sum(estardownload) as cvr_numerator, sum(eclick) as cvr_denominator, sum(estardownload)/sum(eclick) as cvr_value,
    sum(erawview) as eview_sucess_rate_numerator, sum(eadreturn) as eview_sucess_rate_denominator, sum(erawview)/sum(eadreturn) as eview_sucess_rate_value
from q22 group by date, user_type, app_ver
ORDER BY date, user_type, app_ver
"""
}

for filename, content in sql_templates.items():
    filepath = os.path.join(work_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {filename}")

print("\nAll SQL files generated successfully!")

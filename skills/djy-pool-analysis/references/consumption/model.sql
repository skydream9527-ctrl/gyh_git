select
    date,
    -- 实验流量
    djy_rec_expid, -- 即算法实验ID
    exp_group,
    observation_group,
    case 
        when exp_group in ('36%自建组') then '36%自建组'
        when exp_group in ('36%火山组') then '36%火山组'
        when observation_group in ('2%自建反转组') then '自建反转组'
        when observation_group in ('2%火山反转组') then '火山反转组'
        when observation_group in ('2%自建纯净组') then '自建纯净组'
        when observation_group in ('2%火山纯净组') then '火山纯净组'
    end as exp_group_6, -- 都江堰数据统一使用36%流量组
    case
        when djy_rec_expid LIKE '%1566672%' then '36%自建组'
        when djy_rec_expid LIKE '%1566673%' then '36%火山组'
        when djy_rec_expid LIKE '%1960891%' then '自建反转组'
        when djy_rec_expid LIKE '%1960892%' then '火山反转组'
        when djy_rec_expid LIKE '%1643918%' then '自建纯净组'
        when djy_rec_expid LIKE '%1643917%' then '火山纯净组'
        else '其他'
    end as exp_id_v2,
    -- 设备信息
    did,
    device_age,
    device_age_5_level,
    start_price_7_level,
    start_price_3_level,
    user_age_8_level,
    user_sex,
    habitation_city_level,
    -- 内容信息
    item_id,
    item_title,
    item_type,
    item_category,
    item_subcategory,
    cast(case when item_publish_time rlike '^[0-9]+$' then item_publish_time else null end as int) as item_publish_time_int,
    -- cast(if(item_publish_time='未知',null,item_publish_time) as int) as item_publish_days,
    -- cast(item_publish_time as int) as item_publish_time_int,
    -- item_publish_time,
    item_publish_time_range as item_publish_time_level,
    item_publish_time_range_v2,
    video_length,
    case
        WHEN video_length * 60 >0
        and video_length * 60 <5 THEN '(0,5)'
        WHEN video_length * 60 >=5
        and video_length * 60 <10 THEN '[5,10)'
        WHEN video_length * 60 >=10
        and video_length * 60 <20 THEN '[10,20)'
        WHEN video_length * 60 >=20
        and video_length * 60 <30 THEN '[20,30)'
        WHEN video_length * 60 >=30
        and video_length * 60 <60 THEN '[30,60)'
        WHEN video_length * 60 >=60
        and video_length * 60 <120 THEN '[60,120)'
        WHEN video_length * 60 >=120
        and video_length * 60 <180 THEN '[120,180)'
        WHEN video_length * 60 >=180
        and video_length * 60 <300 THEN '[180,300)'
        WHEN video_length * 60 >=300
        and video_length * 60 <600 THEN '[300,600)'
        WHEN video_length * 60 >=600 
        and video_length * 60 <1200 THEN '[600,1200)'
        WHEN video_length * 60 >=1200 
        and video_length * 60 <2400 THEN '[1200,2400)'
        WHEN video_length * 60 >=2400 
        and video_length * 60 <3600 THEN '[2400,3600)'
        WHEN video_length * 60 >=3600 THEN '[3600,+∞)'
        ELSE '未知'
    end as video_length_level,
    CASE
        WHEN video_length * 60 > 0   AND video_length * 60 <= 2   THEN '<2s'
        WHEN video_length * 60 > 2   AND video_length * 60 <= 5   THEN '2-5s'
        WHEN video_length * 60 > 5   AND video_length * 60 <= 8   THEN '5-8s'
        WHEN video_length * 60 > 8   AND video_length * 60 <= 10  THEN '8-10s'
        WHEN video_length * 60 > 10  AND video_length * 60 <= 15  THEN '10-15s'
        WHEN video_length * 60 > 15  AND video_length * 60 <= 30  THEN '15-30s'
        WHEN video_length * 60 > 30  AND video_length * 60 <= 60  THEN '30-60s'
        WHEN video_length * 60 > 60  AND video_length * 60 <= 90  THEN '60-90s'
        WHEN video_length * 60 > 90  AND video_length * 60 <= 120 THEN '90-120s'
        WHEN video_length * 60 > 120 AND video_length * 60 <= 240 THEN '120-240s'
        WHEN video_length * 60 > 240 AND video_length * 60 <= 360 THEN '240-360s'
        WHEN video_length * 60 > 360 AND video_length * 60 <= 600 THEN '360-600s'
        WHEN video_length * 60 > 600 AND video_length * 60 <= 1200 THEN '600-1200s'
        WHEN video_length * 60 > 1200 AND video_length * 60 <= 2400 THEN '1200-2400s'
        WHEN video_length * 60 > 2400 AND video_length * 60 <= 3600 THEN '2400-3600s'
        WHEN video_length * 60 > 3600 THEN '>3600s'
        ELSE '未知'
    end as video_length_level_v2,
    tuwen_words_cnt as tuwen_words_cnt, -- 图文字数
    -- 作者、CP信息
    item_author_id,
    item_author_name,
    item_cp_name,
    article_level, -- 作者后验分层
    cp_author_level, -- 作者先验分层
    introduction_type,
    ruku_delay,
    is_cold,
    -- 信息流用户标签
    app_launch_way,
    is_app_deep_user,
    layer,
    is_feed_new,
    is_feed_deep_user,
    -- 有效判断
    if(expose_cnt>0 or consum_cnt_v2>0,1,0) as is_feed_active_new,
    if(expose_cnt>0 or consum_cnt_v2_no_push>0,1,0) as is_feed_active_new_no_push,
    is_vliad_user_new,
    is_valid_user_new_no_push,
    -- 信息流频道页面
    feed_channel,
    page,
    is_core_page,
    page_origin,
    root_gid,
    is_click_content_enter,
    item_position,
    -- 小说短故事相关限制
    item_alg_source,
    book_type,
    read_source,
    next_novel,
    last_read_source,
    -- 数据指标
    case when feed_channel in ('热点', '推荐', 'profile_djy','profile','push') then dura end as dura,
    if (
        feed_channel in ('热点', '推荐', 'profile_djy','profile','push') 
        or --自建发的短故事阅读次数
        (item_type in('短故事') and (read_source in ('rec', 'topnews','feed_main_info','unknown') or (
            read_source in ('feed_continue_view_card', 'browser_history')
            and last_read_source in ('rec', 'topnews','feed_main_info','unknown'))) 
        ) 
        or --自建发的小说阅读次数
        (item_type in('小说') and (read_source in ('rec', 'topnews') or read_source in ('feed_continue_view_card', 'browser_history')
            and last_read_source in ('rec', 'topnews')))
        ,consum_dura,0.0
    ) as consum_dura,
    case when feed_channel in ('热点', '推荐', 'profile_djy','profile','push') then expose_pv end as expose_pv,
    case when feed_channel in ('热点', '推荐', 'profile_djy','profile','push') then click_pv end as click_pv,
    if (
        feed_channel in ('热点', '推荐', 'profile_djy','profile','push') 
        or --自建发的短故事阅读次数
        (item_type in('短故事') and (read_source in ('rec', 'topnews','feed_main_info','unknown') or (
            read_source in ('feed_continue_view_card', 'browser_history')
            and last_read_source in ('rec', 'topnews','feed_main_info','unknown'))) 
        ) 
        or --自建发的小说阅读次数
        (item_type in('小说') and (read_source in ('rec', 'topnews') or read_source in ('feed_continue_view_card', 'browser_history')
            and last_read_source in ('rec', 'topnews')))
        ,consum_pv,0.0
    ) as consum_pv,
    all_consum_pv, -- 图文完读+视频完播
    valid_consum_pv, -- 有效播读
    like_pv,
    comment_pv,
    share_pv,
    comment_area_pv, -- 进入评论区的量
    comment_area_dura, -- 评论区停留时长
    negative_pv,
    report_pv,
    -- 小说、短故事消费VV和消费时长
    shortstory_read_cnt,
    shortstory_read_dura,
    novel_read_cnt,
    novel_read_dura,
    -- 内流下滑
    xiahua_pv,
    ---------------------------------------- 以下指标为定制指标---------------------------------------------
    if (
    (item_type in('短故事') and (read_source in ('rec', 'topnews','feed_main_info','unknown') or (
        read_source in ('feed_continue_view_card', 'browser_history')
        and last_read_source in ('rec', 'topnews','feed_main_info','unknown'))) 
    ) 
    ,shortstory_read_cnt,0.0
    ) as shortstory_read_cnt_v2,
    if (
    (item_type in('短故事') and (read_source in ('rec', 'topnews','feed_main_info','unknown') or (
        read_source in ('feed_continue_view_card', 'browser_history')
        and last_read_source in ('rec', 'topnews','feed_main_info','unknown'))) 
    ) 
    ,shortstory_read_dura,0.0
    ) as shortstory_read_dura_v2,
    if (
    (item_type in('小说') and (read_source in ('rec', 'topnews') or read_source in ('feed_continue_view_card', 'browser_history')
        and last_read_source in ('rec', 'topnews')))
    ,novel_read_cnt,0.0
    ) as novel_read_cnt_v2,
    if (
    (item_type in('小说') and (read_source in ('rec', 'topnews') or read_source in ('feed_continue_view_card', 'browser_history')
        and last_read_source in ('rec', 'topnews')))
    ,novel_read_dura,0.0
    ) as novel_read_dura_v2,
    avg_video_play_percent,
    firts_video_dura, -- 沉浸流首条播放时长
    drop_firts_video_dura, -- 沉浸流非首条播放时长
    drop_first_video_vv,
    first_video_vv,
    -- 限制6个exp_id(明细+天级)
    djy_expose_pv,
    huoshan_expose_pv,
    total_djy_expose_pv,
    total_huoshan_expose_pv,
    -- 用户粒度指标
    expose_cnt,
    consum_cnt_v2_no_push,
    consum_cnt_v2,
    -- 内容粒度指标
    like_cnt,
    comment_cnt,
    share_cnt
from iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
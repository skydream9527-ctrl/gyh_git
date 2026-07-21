---- 0610 浏览器流量地图取数


SELECT
    date,
    distinct_id,
    SUM(properties ['read_time'])/60000 as app_dura
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date BETWEEN 20250512 AND 20250518
    and pkg='com.android.browser'
    and event_name='book_read_quit_sdk'
    and properties ['read_time'] BETWEEN 0 and 86400000


select  date, event_name, 
        case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end as page,
        count(distinct distinct_id) as did_cnt
from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
where date = 20250531
and pkg='com.android.browser'
and event_name in ('app_open', 'app_duration') 
group by date, event_name, 
        case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end   



---- 页面排序 
select  case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end as page, 
        count(distinct distinct_id) as did_cnt
from iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
where date = 20250531 
and properties.page is not null 
group by case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end



---- 计算打开和退出时的页面分布

select  date, event_name, 
        case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end as page,
        count(distinct distinct_id) as did_cnt
from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
where date = 20250531
and pkg='com.android.browser'
and event_name in ('app_open', 'app_duration') 
group by date, event_name, 
        case when properties.page = 'web_page' then '网页'
        when properties.page = 'home' then '主页'
        when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
        when properties.page like 'search%' then '搜索'
        when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
        when properties.page = 'window_window' then '窗口页'
        when properties.page = 'offlinevideo' then '本地视频播放'
        when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
        else '其他' end   


---- 页面排序排列组合 
select  a.page as page_open,
        b.page as page_quit,
        count(distinct a.distinct_id) as did_cnt 
from 
(
    select  date, event_name, 
            case when properties.page = 'web_page' then '网页'
            when properties.page = 'home' then '主页'
            when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
            when properties.page like 'search%' then '搜索'
            when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
            when properties.page = 'window_window' then '窗口页'
            when properties.page = 'offlinevideo' then '本地视频播放'
            when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
            else '其他' end as page,
            distinct_id,
            properties.sessionId as sessionId
    from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    where date = 20250531
    and pkg='com.android.browser'
    and event_name = 'app_open' 
    group by date, event_name, 
            case when properties.page = 'web_page' then '网页'
            when properties.page = 'home' then '主页'
            when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
            when properties.page like 'search%' then '搜索'
            when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
            when properties.page = 'window_window' then '窗口页'
            when properties.page = 'offlinevideo' then '本地视频播放'
            when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
            else '其他' end,
            distinct_id,
            properties.sessionId

) a 
left join 
(
    select  date, event_name, 
            case when properties.page = 'web_page' then '网页'
            when properties.page = 'home' then '主页'
            when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
            when properties.page like 'search%' then '搜索'
            when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
            when properties.page = 'window_window' then '窗口页'
            when properties.page = 'offlinevideo' then '本地视频播放'
            when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
            else '其他' end as page,
            distinct_id,
            properties.sessionId as sessionId
    from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    where date = 20250531
    and pkg='com.android.browser'
    and event_name = 'app_duration' 
    group by date, event_name, 
            case when properties.page = 'web_page' then '网页'
            when properties.page = 'home' then '主页'
            when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
            when properties.page like 'search%' then '搜索'
            when properties.page = 'bookmark_BookmarkAndHistory' then '书签&历史'
            when properties.page = 'window_window' then '窗口页'
            when properties.page = 'offlinevideo' then '本地视频播放'
            when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
            else '其他' end,
            distinct_id,
            properties.sessionId
) b 
on a.distinct_id = b.distinct_id 
and a.sessionId = b.sessionId 
group by a.page,
        b.page

---- 看多功能使用看日活、浏览器时长、浏览器留存 
---- 分功能看使用数据 仅网页、仅搜索、仅信息流、仅小说、信息流+网页、信息流+搜索、信息流+小说、搜索+网页、搜索+小说、网页+小说、其他  
---- 功能使用数量和打开次数会有天然的统一性 



select  app_open_cnt,
        count(distinct distinct_id) as did_cnt 
from  
( 
    select  a.distinct_id,
            nvl(app_open_cnt, 0) as app_open_cnt ,
            count(distinct page) as page_cnt
    from  
    ( 
        select  case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end as page, 
                distinct_id
        from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
        where date = 20250531 
        and properties.page is not null 
        and pkg = 'com.android.browser'
        group by case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end, 
                distinct_id
    ) a 
    left join 
    (
        select  did as distinct_id,
                sum(app_open_cnt) as app_open_cnt 
        from browser.dwm_browser_event_aggregation_label_di 
        where date = 20250531 
        and is_app_dau_2024 = 1 
        and app_open_cnt > 0 
        group by distinct_id

    ) b 
    on a.distinct_id = b.distinct_id 
    group by  a.distinct_id,
            nvl(app_open_cnt, 0)
) a 
group by app_open_cnt



---- 分用户功能使用数量，看用户DAU、时长、留存率分布 
select  page_cnt,
        count(distinct a.distinct_id) as did_cnt,
        sum(nvl(app_dura, 0)) as app_dura,
        count(distinct c.did) as did_re_cnt
from 
(
    select  distinct_id,
            count(distinct page) as page_cnt
    from  
    ( 
        select  case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end as page, 
                distinct_id
        from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
        where date = 20250531 
        and properties.page is not null 
        and pkg = 'com.android.browser'
        group by case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end, 
                distinct_id
    ) a 
    group by distinct_id 
) a 
left join 
(
    select  did, cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as app_dura
    from  browser.dwm_browser_event_aggregation_label_di 
    where date = 20250531  
    and is_app_dau_2024 = 1 
    group by did
) b 
on a.distinct_id = b.did 
left join 
(
    select  did
    from  browser.dwm_browser_event_aggregation_label_di 
    where date = 20250606
    and is_app_dau_2024 = 1 
    group by did
) c 
on a.distinct_id = c.did 
group by page_cnt
;




---- 拆开来看下，只用单个功能的和只用两个功能的数据差异 

with t1 as (
           select  case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end as page, 
                distinct_id
        from  iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
        where date = 20250531 
        and properties.page is not null 
        and pkg = 'com.android.browser'
        group by case when properties.page = 'web_page' then '网页'
                when properties.page = 'home' then '主页'
                when properties.page like 'feed%' or properties.page = 'immersion_news_detail' then '信息流'
                when properties.page like 'search%' then '搜索'
                when properties.page in ('阅读页', '小说频道', '书城男生', '阅读器', '书架', '阅读引导页', '阅读扉页') then '小说'
                else '其他' end, 
                distinct_id

)

select  page_list,
        count(distinct a.distinct_id) as did_cnt,
        sum(nvl(app_dura, 0)) as app_dura,
        count(distinct c.did) as did_re_cnt
from 
(
    select  a.distinct_id,
            collect_set(page) as page_list
    from 
    (
        select  distinct_id,
                count(distinct page) as page_cnt
        from  
        ( 
            select  page, 
                    distinct_id
            from  t1
        ) a 
        group by distinct_id 
    ) a 
    left join 
    (
        select  page, 
                distinct_id
        from  t1 
    ) b 
    on a.distinct_id = b.distinct_id
    where page_cnt <= 2 
    group by a.distinct_id
) a 
left join 
(
    select  did, cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as app_dura
    from  browser.dwm_browser_event_aggregation_label_di 
    where date = 20250531  
    and is_app_dau_2024 = 1 
    group by did
) b 
on a.distinct_id = b.did 
left join 
(
    select  did
    from  browser.dwm_browser_event_aggregation_label_di 
    where date = 20250606
    and is_app_dau_2024 = 1 
    group by did
) c 
on a.distinct_id = c.did 
group by page_list
;




-------对深度用户的使用app时长做区间分类，计算用户数与占比
-- 子查询：按did聚合总时长并筛选深度用户
WITH deep_user_total_dura AS (
    SELECT 
        did,
        -- 计算每个用户的总时长（排除NULL值）
        SUM(app_dura) AS total_app_dura
    FROM 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE 
        date = 20250628  -- 限定日期
        AND is_app_dau_2024 = 1
    GROUP BY 
        did  -- 按用户去重
    HAVING 
        SUM(app_dura) >= 1200000  -- 仅保留深度用户（总app_dura >=20min）
)

-- 外部查询：统计深度用户指标及各时长区间用户数
SELECT 
    '20250628' AS date,

    -- 各时长区间用户数（单位：小时，1小时=3600000毫秒）
    CASE WHEN total_app_dura < 3600000 THEN 'deep_less_1h'
    WHEN total_app_dura >= 3600000 AND total_app_dura < 7200000 THEN 'deep_1h_to_2h'
    WHEN total_app_dura >= 7200000 AND total_app_dura < 10800000 THEN 'deep_2h_to_3h'
    WHEN total_app_dura >= 10800000 AND total_app_dura < 14400000 THEN 'deep_3h_to_4h'
    WHEN total_app_dura >= 14400000 AND total_app_dura < 18000000 THEN 'deep_4h_to_5h'
    WHEN total_app_dura >= 18000000 AND total_app_dura < 21600000 THEN 'deep_5h_to_6h'
    WHEN total_app_dura >= 21600000 AND total_app_dura < 25200000 THEN 'deep_6h_to_7h'
    WHEN total_app_dura >= 25200000 AND total_app_dura < 28800000 THEN 'deep_7h_to_8h'
    WHEN total_app_dura >= 28800000 AND total_app_dura < 32400000 THEN 'deep_8h_to_9h'
    WHEN total_app_dura >= 32400000 AND total_app_dura < 36000000 THEN 'deep_9h_to_10h'
    WHEN total_app_dura >= 36000000 AND total_app_dura < 39600000 THEN 'deep_10h_to_11h'
    WHEN total_app_dura >= 39600000 AND total_app_dura < 43200000 THEN 'deep_11h_to_12h'
    WHEN total_app_dura >= 43200000 AND total_app_dura < 86400000 THEN 'deep_12h_to_24h'
    else 'other' end as time_group,
    count(distinct did) as did_cnt 
FROM 
    deep_user_total_dura
group by CASE WHEN total_app_dura < 3600000 THEN 'deep_less_1h'
    WHEN total_app_dura >= 3600000 AND total_app_dura < 7200000 THEN 'deep_1h_to_2h'
    WHEN total_app_dura >= 7200000 AND total_app_dura < 10800000 THEN 'deep_2h_to_3h'
    WHEN total_app_dura >= 10800000 AND total_app_dura < 14400000 THEN 'deep_3h_to_4h'
    WHEN total_app_dura >= 14400000 AND total_app_dura < 18000000 THEN 'deep_4h_to_5h'
    WHEN total_app_dura >= 18000000 AND total_app_dura < 21600000 THEN 'deep_5h_to_6h'
    WHEN total_app_dura >= 21600000 AND total_app_dura < 25200000 THEN 'deep_6h_to_7h'
    WHEN total_app_dura >= 25200000 AND total_app_dura < 28800000 THEN 'deep_7h_to_8h'
    WHEN total_app_dura >= 28800000 AND total_app_dura < 32400000 THEN 'deep_8h_to_9h'
    WHEN total_app_dura >= 32400000 AND total_app_dura < 36000000 THEN 'deep_9h_to_10h'
    WHEN total_app_dura >= 36000000 AND total_app_dura < 39600000 THEN 'deep_10h_to_11h'
    WHEN total_app_dura >= 39600000 AND total_app_dura < 43200000 THEN 'deep_11h_to_12h'
    WHEN total_app_dura >= 43200000 AND total_app_dura < 86400000 THEN 'deep_12h_to_24h'
    else 'other' end

;




'com.UCMobile',
'com.tencent.mtt',
'com.baidu.searchbox',
'com.cat.readall',
'com.baidu.searchbox.lite',
'com.ss.android.ugc.aweme',
'com.smile.gifmaker',
'com.ss.android.ugc.aweme.lite',
'com.kuaishou.nebula',
'com.tencent.qqlive',
'com.ss.android.article.news',
'com.netease.newsreader.activity',
'com.ss.android.article.lite ',
'com.sohu.newsclient',
'com.sina.news',
'com.youku.phone',
'com.tencent.qqlive',
'com.qiyi.video',
'tv.danmaku.bili',
'com.hunantv.imgo.activity',
'com.miui.video',
'com.dragon.read',
'com.kmxs.reader',
'com.duokan.reader',
'com.phoenix.read',
'com.dz.hmjc',
'com.xingin.xhs',
'com.sina.weibo',
'com.deepseek.chat',
'com.larus.nova',
'com.tencent.hunyuan.app.chat',
'com.aliyun.tongyi',
'com.baidu.newapp',
'com.zhipuai.qingyan',
'com.moonshot.kimichat',
'com.quark.browser'




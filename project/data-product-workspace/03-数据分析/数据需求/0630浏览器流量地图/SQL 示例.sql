----- 20250605 浏览器流量地图取数01 

select properties.page as page, count(distinct distinct_id) as did_cnt
from iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
where date = 20250601 
group by properties.page
;



select date, app_launch_way, page, count(distinct did) as did_cnt, cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, app_launch_way, page 
;

select date, app_launch_way, count(distinct did) as did_cnt, cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, app_launch_way 
;


select date, page, count(distinct did) as did_cnt, cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, page 
;



select  date, 
        case when page like '%feed%' then '信息流'
        when page like '%web%' then '网页'
        when page like '%search%' then '搜索'
        when page like '%home%' then '主页'
        else '其他' end as page, 
        count(distinct did) as did_cnt, 
        cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, 
        case when page like '%feed%' then '信息流'
        when page like '%web%' then '网页'
        when page like '%search%' then '搜索'
        when page like '%home%' then '主页'
        else '其他' end
;



select  date, 
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end as app_launch_way, 
        count(distinct did) as did_cnt, 
        cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, 
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end
;




select  date, 
        case when page like '%feed%' then '信息流'
        when page like '%web%' then '网页'
        when page like '%search%' then '搜索'
        when page like '%home%' then '主页'
        else '其他' end as page, 
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end as app_launch_way, 
        count(distinct did) as did_cnt, 
        cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, 
        case when page like '%feed%' then '信息流'
        when page like '%web%' then '网页'
        when page like '%search%' then '搜索'
        when page like '%home%' then '主页'
        else '其他' end,
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end
;


---- 计算信息流有点击的数据 
select  date, 
        case when page like '%feed%' and view_cnt >0 then '信息流'
        else '其他' end as page, 
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end as app_launch_way, 
        count(distinct did) as did_cnt, 
        cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, 
        case when page like '%feed%' and view_cnt >0 then '信息流'
        else '其他' end,
        case when app_launch_way like '%newhome%' then '内容中心'
        when app_launch_way in ('点击icon', '第三方调起', '点击push', '新全搜调起') then app_launch_way
        else '其他' end
;

---- 计算信息流有点击的数据 
select  date, 
        case when page like '%feed%' and view_cnt >0 then '信息流'
        else '其他' end as page, 
        count(distinct did) as did_cnt, 
        cast(sum(case when app_dura > 0 then app_dura end) as bigint)/60000 as browser_app_dura_sum
from  iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
where date = 20250531 
and is_app_dau_2024 =1
group by date, 
        case when page like '%feed%' and view_cnt >0 then '信息流'
        else '其他' end
;




-----浏览器流量地图取数02 
---- 计算用户进入页面和用户离开前的页面 

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
;


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
;




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
;




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
;


---- 浏览器流量地图取数03 
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
;


select  page_cnt,
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
group by page_cnt
;




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






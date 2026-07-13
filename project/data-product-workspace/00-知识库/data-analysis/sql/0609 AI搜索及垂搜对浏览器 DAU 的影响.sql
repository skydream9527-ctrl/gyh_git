---- 0609 AI搜索及垂搜对浏览器 DAU 的影响 

--手机端AI搜索类各应用活跃、时长
with s1 (
    select
        distinct_id,
        package_name,
        sum(open_cnt) open_cnt,
        sum(use_dura_cnt) dura_cnt
    from
        iceberg_zjyprc_hadoop.browser.dwm_device_app_event_di 
    WHERE   
        date = ${date-1}
--        and package_name = 'com.android.browser'
        and region = 'CN'
        and open_cnt > 0
        and package_name in 
        (
        'com.larus.nova',  --豆包
        'com.moonshot.kimichat',  --kimi
        'com.baidu.newapp',  --文小言
        'com.deepseek.chat',  --deepseek
        'com.tencent.hunyuan.app.chat'  --腾讯元宝
        )
    group by distinct_id,package_name
)

,s2 (
    SELECT
        distinct distinct_id
    FROM
        iceberg_zjyprc_hadoop.browser.dwm_device_model_detail_df
    where 
        date=${date-1} and cat_lvl2_name='手机'
)

insert overwrite table iceberg_zjyprc_hadoop.newhome.ai_search_rela_app_did_v2 partition(date=${date-1})
select s1.distinct_id,s1.package_name,open_cnt,dura_cnt
from s1
join s2
on s1.distinct_id=s2.distinct_id



--垂搜类APP的活跃、时长
with s1 (
    select
        distinct_id,
        package_name,
        class_name,
        event_type,
        duration
    from
        iceberg_zjyprc_hadoop.dw.dwd_userapp_did_di
    WHERE   
        date = ${date-1}
        and package_name in
        (
        'com.baidu.searchbox',
        'com.ss.android.ugc.aweme',
        'com.smile.gifmaker',
        'com.xingin.xhs',
        'com.ss.android.article.news'
        )
        and class_name in 
        (
        'com.baidu.browser.search.LightSearchActivity',
        'com.ss.android.ugc.aweme.search.activity.SearchResultActivity',
        'com.yxcorp.plugin.search.SearchActivity',
        'com.xingin.alioth.search.GlobalSearchActivity',
        'com.android.bytedance.search.SearchActivity'
        )
)

,s2 (
    SELECT
        distinct distinct_id
    FROM
        iceberg_zjyprc_hadoop.browser.dwm_device_model_detail_df
    where 
        date=${date-1} and cat_lvl2_name='手机'
)

insert overwrite table iceberg_zjyprc_hadoop.newhome.search_rela_app_did_v2 partition(date=${date-1})
select 
    s1.distinct_id,
    package_name,
    class_name,
    count(case when event_type in (1,10001) then s1.distinct_id end) open_cnt,
    sum(duration) dura_cnt
from s1
join s2
on s1.distinct_id=s2.distinct_id
group by
    s1.distinct_id,
    package_name,
    class_name


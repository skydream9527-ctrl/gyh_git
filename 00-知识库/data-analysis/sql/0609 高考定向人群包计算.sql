---- 0609 高考定向人群包计算

 SELECT
    date,
    query,
    sum(search_security_cnt) as search_pv,
    count(distinct distinct_id) as search_uv
from
    iceberg_zjyprc_hadoop.miuisearch.dwm_browser_search_event_device_ot_di
where
    date between 20231201 and 20231207
    AND search_security_cnt > 0
    and channel IN ( -- 百度传统
        '1000228k',
        '1000228m',
        '1000228n',
        '1000228o',
        '1002253i',
        '1002253j',
        '1002253k',
        '1002253q',
        '1002253r',
        '1002253s',
        '1002253t',
        '1002253v',
        '1002253w',
        '1002253z',
        '1011267a',
        '1011267b',
        '1011267c',
        '1011267g',
        '1011267h',
        '1011267i',
        '1011267j',
        '1011267k',
        '1011267l',
        '1011267m',
        '1011267n',
        '1011267o',
        '1013672d',
        '1012852r',
        '1002253x',
        '1000228f',
        '1012852x',
        '1012852o',
        '1012852p',
        '1012852q',
        '1012852t',
        '1012852u',
        '1012852v',
        '1012852w',
        '1012852y',
        '1012852z',
        '1013672a',
        '1013672c',
        '1013672g',
        '1013672j',
        '1013672k',
        '1013672m',
        '1027624n',
        '1000228a',
        '1000228j',
        '1269a',
        '1269c'
    )
GROUP BY
    1,2



select  did, user_age_8_level
from  browser.dm_micd_user_profile_did_df
where day  


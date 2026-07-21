---- 支付宝 2025 免费测试人群包提供  重构
with  
    ---- 内容中心具备拉活能力版本
    s1 as (
        select did
        from hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
        where date=20250522
        and package_name='com.miui.newhome'
        and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date
        and (
            split(app_version, '\\.') [0]>6
            or (
                split(app_version, '\\.') [0]=6
                and split(app_version, '\\.') [1]>0
            )
            or (
                split(app_version, '\\.') [0]=6
                and split(app_version, '\\.') [1]=0
                and split(app_version, '\\.') [2]>5
            )
            or (
                split(app_version, '\\.') [0]=6
                and split(app_version, '\\.') [1]=0
                and split(app_version, '\\.') [2]=5
                and split(app_version, '\\.') [3]>=2401
            )
        )
        and cat_lvl1_id=1
        and cat_lvl2_id=195
        and user_id=0
        and final_country='中国' --region用户地区，final_country综合地区
        group by did
    )
,
    ---- did 和 oaid 转换关系 
    s2 as (
        select
            distinct_id,
            id_value oaid,
            md5(lower(id_value)) oaidmd5
        from hive_zjyprc_hadoop.dm.dm_oneid_device_2_distinct_id_df
        where date=20250522
        and id_type='oaid'
        group by
            distinct_id,
            id_value
    )
,
    ---- 已安装拉活方APP 用户 
    s3 as (
        select did
        from hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
        where date=20250522
        and package_name in ('com.eg.android.AlipayGphone')
        and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date
        and cat_lvl1_id=1
        and cat_lvl2_id=195
        and user_id=0
        and final_country='中国' --region用户地区，final_country综合地区
        group by did
    )
,
    ----业务需要的其他条件，如APP 打开≤16天 
    s4 as (
        select did 
        from 
        ( 
            select did, count(distinct date) as date_cnt
            from hive_zjyprc_hadoop.dwm.dwm_app_usage_did_di
            where date between 20250423 and 20250522
            and user_id=0
            and duration>0
            and upper(region)='CN'
            and package_name = 'com.eg.android.AlipayGphone'
            GROUP BY did
        ) a 
        where date_cnt <= 16 
    )
,

--------- 接下来是需要提出的部分
    ---- 历史已售卖人群
    t1 as (
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_0824
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_0719_397w
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_zhn_v2_v3_163w
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_yhn_v2_v3_132w
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_yhw_v2_v3_60w
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_zhn_yhn_yhw_v2_v3_laxin_125w
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_1
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_2
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_3
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_1plus
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_2plus
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_3plus
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_expand
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024__1230_id1233184
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024__1230_id1233185
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_thirdapp_open_2025_0220
        union
        select oaid from hive_zjyprc_hadoop.dwm.newhome_douyin_thirdapp_open_2025_0320
        union 
        select oaid from iceberg_zjyprc_hadoop.tmp.newhome_douyin_thirdapp_open_2025_0521  
    )
,
    --常驻北京用户
    t2 as (
        select did distinct_id as did
        from iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_did_df
        where date=20250522
        and resident_province='北京市'
        group by did
    )
,
    --两年内设备用户
    t3 as (
        select distinct_id as did
        from iceberg_zjyprc_hadoop.bigdata.dwm_device_register_all_did_df
        where date=20250522
        and from_unixtime(
                cast(first_active_time/1000 AS bigint),
                'yyyyMMdd'
            )>20230524
        group by distinct_id
    )
,
    --月vv>1000高活用户
    t4 as (
        select
            did,
            sum(consum_cnt) vv
        from iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
        where date between 20250423 and 20250522
        and is_top=0
        group by did
        having vv>1000
    )
,
    --月收入>1.16元用户
    t5 as (
        select
            did,
            sum(real_fee)/100000 as fee
        from iceberg_zjyprc_hadoop.browser.dwm_micd_effect_ad_1d
        where date between 20250423 and 20250522
        and tag_media_type_flag='NEW_HOME'
        group by did
        having fee>1.16
    )
,
    ---高端机用户
    t6 as (
        select did
        from iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_did_df
        where date=20250522
        and phone_model in (
                'Xiaomi 12',
                'Xiaomi 12 Pro',
                'Xiaomi 12 Pro 天玑版',
                'Xiaomi 12S',
                'Xiaomi 12S Pro',
                'Xiaomi 12S Ultra',
                'Xiaomi 12X',
                'Xiaomi 13',
                'Xiaomi 13 Pro',
                'Xiaomi 13 Ultra',
                'Xiaomi 14',
                'Xiaomi 14 Pro',
                'Xiaomi 14 Ultra',
                '小米15',
                '小米15 Pro',
                'Xiaomi 15 Ultra',
                'Xiaomi MIX Fold 2',
                'Xiaomi MIX Fold 3',
                'Xiaomi MIX Fold 4',
                '小米MIX FOLD',
                '小米Mix1',
                '小米Mix2',
                '小米Mix2S',
                '小米Mix3',
                '小米Mix4',
                'Xiaomi MIX Flip'
            )
        group by did
)

insert overwrite table  iceberg_zjyprc_hadoop.tmp.newhome_zhifubao_thirdapp_open_2025_0522_test_all_02
select  t0.distinct_id,
        t0.oaid
from 
(
    select s2.distinct_id as did , s2.oaid
    from s1 
    join s2 
    on s1.did = s2.distinct_id  ----取oaid
    join s3 
    on s1.did = s3.did  ---- 限制已安装目标APP
    join s4 
    on s1.did = s4.did  ---- 限制业务逻辑

) t0 
left join t1 
on t0.oaid = t1.oaid
left join t2
on t0.did = t2.did 
left join t3
on t0.did = t3.did 
left join t4
on t0.did = t4.did 
left join t5
on t0.did = t5.did 
left join t6
on t0.did = t6.did 
where t1.oaid is null  ----剔除已售卖人群
and t2.did is null     ----剔除常驻北京用户
and t3.did is null     ----剔除两年内设备用户
and t4.did is null     ----剔除月vv>1000高活用户
and t5.did is null     ----剔除月收入>1.16元用户
and t6.did is null     ----剔除高端机用户
group by  t0.distinct_id, t0.oaid







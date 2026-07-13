---- 0521代码学习.sql
--淘宝&抖音2023年桌面拉起合作人群包&淘宝2024年人群包
with
    s1 as (
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_0824
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_0719_397w
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_zhn_v2_v3_163w
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_yhn_v2_v3_132w
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_yhw_v2_v3_60w
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_zhn_yhn_yhw_v2_v3_laxin_125w
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_1
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_2
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_3
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_1plus
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_2plus
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_3plus
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024_expand
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024__1230_id1233184
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_taobao_thirdapp_open_2024__1230_id1233185
        union
        select
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_thirdapp_open_2025_0220
        UNION
        SELECT
            oaid
        from
            hive_zjyprc_hadoop.dwm.newhome_douyin_thirdapp_open_2025_0320
    )
    --月vv>1000高活用户
,
    s2 as (
        select
            did,
            sum(consum_cnt) vv
        from
            iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
        where
            date between 20250421 and 20250520
            and is_top=0
        group by
            did
        having
            vv>1000
    )
    --月收入>1.16元用户
,
    s3 as (
        select
            did distinct_id,
            sum(real_fee)/100000 as fee
        from
            iceberg_zjyprc_hadoop.browser.dwm_micd_effect_ad_1d
        where
            date between 20250421 and 20250520
            and tag_media_type_flag='NEW_HOME'
        group by
            did
        having
            fee>1.16
    )
    --高端机用户
,
    s4 as (
        select
            did distinct_id
        from
            iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_did_df
        where
            date=20250520
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
        group by
            did
    )
    --常驻北京用户
,
    s5 as (
        select
            did distinct_id
        from
            iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_did_df
        where
            date=20250520
            and resident_province='北京市'
        group by
            did
    )
    --两年内设备用户
,
    s6 as (
        select
            distinct_id
        from
            iceberg_zjyprc_hadoop.bigdata.dwm_device_register_all_did_df
        where
            date=20250520
            and from_unixtime(
                cast(first_active_time/1000 AS bigint),
                'yyyyMMdd'
            )>20230522
        group by
            distinct_id
    )
    --内容中心拉活版本
,
    s8 as (
        select
            did
        from
            hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
        where
            date=20250520
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
        group by
            did
    )
    --抖音安装用户
,
    s9 as (
        select
            did
        from
            hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
        where
            date=20250520
            and package_name in ('com.ss.android.ugc.aweme')
            and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date
            and cat_lvl1_id=1
            and cat_lvl2_id=195
            and user_id=0
            and final_country='中国' --region用户地区，final_country综合地区
        group by
            did
    )
    --抖音传输的人群包加密oaid
,
    s10 as (
        SELECT
            package_id,
            oaidmd5
        from
            iceberg_zjyprc_hadoop.newhome.newhome_third_oaidmd5
        where
            package_id in ('抖音桌面上划投放-拓展人群0521')
        group by
            1,
            2
    )
INSERT OVERWRITE table
    iceberg_zjyprc_hadoop.tmp.newhome_douyin_thirdapp_open_2025_0521
select distinct
    t2.distinct_id,
    t2.oaid
from
    s8
    join s9 on s8.did=s9.did
    left join
    --did转oaid
    (
        select
            distinct_id,
            id_value oaid,
            md5(lower(id_value)) oaidmd5
        from
            hive_zjyprc_hadoop.dm.dm_oneid_device_2_distinct_id_df
        where
            date=20250520
            and id_type='oaid'
        group by
            distinct_id,
            id_value
    ) t2 on s8.did=t2.distinct_id
    join s10 on t2.oaidmd5=s10.oaidmd5
    left join s1 on t2.oaid=s1.oaid
    left join s2 on t2.distinct_id=s2.did
    left join s3 on t2.distinct_id=s3.distinct_id
    left join s4 on t2.distinct_id=s4.distinct_id
    left join s5 on t2.distinct_id=s5.distinct_id
    left join s6 on t2.distinct_id=s6.distinct_id
where
    s1.oaid is null
    and s2.did is null
    and s3.distinct_id is null
    and s4.distinct_id is null
    and s5.distinct_id is null
    and s6.distinct_id is null
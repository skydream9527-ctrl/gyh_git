---- @业务线: 增长
---- @需求方: 张三

---- 各城市每日新增用户按渠道拆分
---- 埋点 app_open，统计新增注册用户
select
    dt,
    city,
    channel,
    count(distinct uid) as new_users
from dwd_user_register_di
where dt between 20260601 and 20260630
group by dt, city, channel
;

---- 短剧内容次日留存率
---- 某天活跃用户中第二天仍活跃的占比，按分类拆分
select
    a.dt,
    a.category,
    count(distinct b.uid) * 1.0 / count(distinct a.uid) as retention_d1
from dws_drama_active_di a
left join dws_drama_active_di b
    on a.uid = b.uid and b.dt = date_add(a.dt, 1)
group by a.dt, a.category
;

# AI写SQL提示词进阶模板（复杂场景用）
> 复杂需求拆成步骤写，准确率提升80%

---

## 通用复杂SQL提示词结构
```
请帮我写Hive SQL，需求如下：

【使用的表结构】：
1. 表名：iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
   粒度：did+date（每个用户每天一行）
   核心字段：
   - date: integer，日期，格式yyyyMMdd，分区字段
   - did: varchar，设备ID，用户唯一标识
   - is_app_dau_2024: integer，=1是有效APP活跃用户
   - is_new_2024: integer，=1是新用户，=0是老用户
   - app_launch_way: varchar，启动方式，枚举：'点击icon','第三方调起','点击push','subscribe_push','新全搜调起'等
   - app_open_cnt: bigint，APP打开次数
   - app_dura: bigint，APP使用时长，单位毫秒

2. 表名：iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
   粒度：did+date
   核心字段：
   - date: integer，日期分区
   - did: varchar，设备ID
   - is_dau_feed_dapan_2024: integer，=1是信息流活跃用户
   - is_top: integer，0=自然推荐，1=置顶内容
   - expos_cnt: bigint，曝光次数
   - click_cnt: bigint，点击次数
   - news_vv_cnt/short_vv_cnt/mini_vv_cnt: bigint，图文/短视频/小视频VV
   - feed_dura: bigint，信息流消费时长，单位毫秒

【实现步骤】：
（在这里把需求拆成1/2/3/4步，每步说明逻辑）
步骤1：xxx
步骤2：xxx
步骤3：xxx

【指标口径要求】：
- 用户数统一用COUNT(DISTINCT did)计算
- 所有比率计算乘1.0避免整数除法，保留4位小数
- 时长单位是毫秒，转分钟除以60000
- LEFT JOIN后右表字段用COALESCE(字段,0)把NULL转0
- 必须加date分区过滤，必须加is_app_dau_2024=1（或is_dau_feed_dapan_2024=1）过滤有效用户，必须过滤COALESCE(did,'')!=''
- 自然信息流查询加is_top=0过滤置顶

【输出要求】：
1. 用WITH CTE语句拆分步骤，每个临时表加注释说明作用
2. 核心计算逻辑加注释
3. 最终结果按日期/分组维度排序
```

---

## 常见场景提示词示例

### 场景1：PUSH用户留存分析
```
补充需求：
查询2026-06-01到2026-06-30期间，每日点击PUSH启动的用户，他们的次日留存率、7日留存率、14日留存率，对比同期全体APP用户的留存率。
留存定义：D0活跃，Dn仍为APP活跃用户（is_app_dau_2024=1）即为Dn留存。

实现步骤：
步骤1：先取2026-06-01到2026-06-30每日的全体活跃用户，标记是否是PUSH启动用户（当天点击过push启动即为PUSH用户），得到每日用户标签表
步骤2：取2026-06-01到2026-07-14的全量活跃用户作为留存活跃表
步骤3：关联留存表，计算D1/D7/D14留存：D0用户在D1/D7/D14是否在活跃表中存在
步骤4：按D0日期、用户分组（PUSH用户/全体用户）聚合，计算留存率
```

### 场景2：指标波动排查
```
补充需求：
帮我写一个SQL，用来排查2026-06-28信息流CTR下降的问题，按维度拆分：按新老用户、按启动方式、按信息流频道，分别计算CTR，对比2026-06-27的数据，看哪个维度下降最多。
```

---

## SQL报错/结果异常排查提示词
```
我写的SQL有问题，请帮我排查：

【SQL代码】：
[贴你的SQL]

【问题描述】：
（描述清楚现象：是报错？跑的慢？还是结果不对？结果怎么不对，是偏大还是偏小？和预期差多少？）
例如：这个SQL跑出来2026-06-28的DAU是8000万，比平时正常的4000万高一倍，帮我看看哪里写错了？

【期望结果】：
告诉我问题出在哪一行，为什么错，给出修正后的SQL
```

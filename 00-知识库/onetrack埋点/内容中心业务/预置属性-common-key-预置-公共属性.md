# 内容中心 - 预置与公共属性

> 本文档汇总所有事件共用的预置属性。每个事件实际上报时自动携带其引用的公共属性集(见各事件 `公共属性` 列)。


---

## common key 预置 & 公共属性

> 来源 sheet: `common key 预置&公共属性` | 属性数: 68


| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |
|---|---|---|---|---|---|---|
| 1 | `imei1` | imei1 MD5值 | string | 空的 |  |  |
| 2 | `roaid` | 系统OAID | string |  |  |  |
| 3 | `oaid` | OAID | string |  |  |  |
| 4 | `android_id` | Android ID | string |  |  |  |
| 5 | `instance_id` | 匿名ID | string | app级别id（卸载app，id会变） |  |  |
| 6 | `uid` | 账号id | string | 小米账号 |  |  |
| 7 | `session_id` | session_id | string | app退出重置（目前o2o现状app退出跟下一次启动一致） |  |  |
| 8 | `ip` | ip | string |  |  |  |
| 9 | `region` | 地区 | string |  |  |  |
| 10 | `model` | 设备名 | string |  |  |  |
| 11 | `platform` | 平台 | string |  |  |  |
| 12 | `miui` | MIUI版本号 | string | 举例：12.10.1.2 |  |  |
| 13 | `build` | 版本类型 | string | S：稳定版 D： 开发版 A：体验版 空值：用户自己编的版本 |  |  |
| 14 | `os` | 系统版本号 | string |  |  |  |
| 15 | `app_ver` | APP版本号 | string |  |  |  |
| 16 | `version_code` | app_版本号 | number |  |  | 5.3 |
| 17 | `e_ts` | 事件发生时间 | number | 本地客户端时间 |  |  |
| 18 | `net` | 网络 | string | WIFI/5G/4G/3G/2G/ETHERNET/NONE/UNKNOWN NONE:没有联网， UNKNOWN:未知类型， ETHERNET:电视有线网 |  |  |
| 19 | `sdk_ver` | SDK版本号 | string |  |  |  |
| 20 | `app_id` | APPID | string |  |  |  |
| 21 | `pkg` | 包名 | string |  |  |  |
| 22 | `channel` | 渠道 | string | 一般为业务分发的渠道，比如抖音、应用宝等，用以跟踪渠道效果 |  |  |
| 23 | `sdk_mode` | SDK接入模式 | string | App模式（默认）/SDK模式（如小米账号SDK接入）/插件模式（如米家/快应用插件） |  |  |
| 24 | `ot_ua` | useragent | string |  |  |  |
| 25 | `ot_privacy_policy` | 隐私策略设置 | string | 打点时的隐私策略，取值范围为custom_open，custom_close，exprience_open，exprience_close |  |  |
| 26 | `event` | 事件名称 | string |  |  |  |
| 27 | `ot_first_day` | 用户是否是第一天访问 | boolean | true/false |  |  |
| 28 | `device_id` | 设备id | string | 优先取imei1md5 imei取不到取oaid原值（3.8版本以下是oaidmd5，3.8以上时oaid原值） |  |  |
| 29 | `imei2` | imei2md5值 | string |  |  |  |
| 30 | `is_first_today_imei` | 是否为新用户(新imei服务端口径) | boolean | true/false |  |  |
| 31 | `is_first_today_imei_expose` | 是否为新曝光用户（首次信息流内容曝光业务口径） | boolean | true/false |  |  |
| 32 | `city` | 设置了本地频道的城市 | string | 有本地频道才会上报该值 |  |  |
| 33 | `model_name` | 机型名称 | string | 中文的机型名称，例如：Redmi 10 |  |  |
| 34 | `price_level` | 机型分类 | string | 低端机，中端机，中高端机，高端机 |  |  |
| 35 | `eid` | 旧实验id | string |  |  |  |
| 36 | `new_eid` | 新实验id | string | 服务端下发的新实验id |  |  |
| 37 | `is_decouple` | 是否解耦 | boolean | 解耦：true 非解耦：false |  |  |
| 38 | `app_launch_type` | 启动方式 | string | 冷启动：cold_start 热启动：hot_start |  |  |
| 39 | `app_launch_way` | 进入内容中心方式(app启动级别) | string | Push推送进入：push 负一屏进入：assistant 桌面上划进入：launch_swipe 小部件: widget_4*2hot，widget_4*2recommend，widget_4*4hot 快捷方式：shortcut 拉活进入：broswer_strange_banner，mi_page_mainpage，mi_page_searchbox icon进入：icon 全搜为你推荐ic… |  |  |
| 40 | `app_type` | 产品类型 | string | mcc：常规版 mcc_Breaking：精选版 mcc_recreation：娱乐中心 mcc_explore：首页改版 |  |  |
| 41 | `page` | 操作所属页面 | string | 页面频道模块参数汇总 |  |  |
| 42 | `from_page` | 操作上级页面 | string | 页面频道模块参数汇总 |  |  |
| 43 | `module` | 操作当前页面所属模块 | string | 页面频道模块参数汇总 |  |  |
| 44 | `from_module` | 操作上级页面所属模块 | string | 页面频道模块参数汇总 |  |  |
| 45 | `login_miaccount` | 小米账号是否登录 | boolean | true/false |  |  |
| 46 | `resolution` | 设备屏幕分辨率 | string | 宽*高 示例：720*1520 |  |  |
| 47 | `carrier` | 运营商 | string | 中国移动:yidong 中国联通:liantong 中国电信:dianxin 中国广电：guangdian 获取不到的打unknown |  |  |
| 48 | `ram_info` | 运行内存 | string | 5g 4g 3g |  |  |
| 49 | `hard_disk_info` | 机身存储 | string | 128g |  |  |
| 50 | `province` | 省份 | string |  |  |  |
| 51 | `ext` | 拓展字段 | string | everyday接口调（每隔12个小时），和内存逻辑一致 后续纯服务端计算的字段不需要客户端发版 |  |  |
| 52 | `refresh_way` | 刷新方式 | string | pull/button/pull_and_button |  |  |
| 53 | `default_channel` | 默认频道 | string | play |  |  |
| 54 | `personnal_recommend` | 个性化推荐开启 | string | on/off |  |  |
| 55 | `sys_personal_ad_recommend` | 系统广告个性化推荐开启 | string | on/off |  |  |
| 56 | `personal_ad_recommend` | 个性化广告推荐开启 | string | on/off |  |  |
| 57 | `server_user_id` | 服务端用户id | string |  |  |  |
| 58 | `top_style` | 内容中心模式 | string | original/ transparent |  |  |
| 59 | `dp_ext` | dp拓展字段 | string | has_guide&source_&pic_id_&is_ad_&channel_id_&father_channel_id_&ext_&url_&doc_id |  |  |
| 60 | `first_app_launch_way` | 首次打开/激活渠道 | string | launch_swipe/push/douyin233/kuaishou233/...... |  |  |
| 61 | `today_first_enter_way` | 当天首次激活方式 | string | launch_swipe/push/douyin233/kuaishou233/...... |  |  |
| 62 | `is_normal_mode` | 是否标准版 | boolean | true/false |  |  |
| 63 | `screen_rotation` | 屏幕旋转开启 | string | on/off |  |  |
| 64 | `is_first_today_agree_cta` | 当天是否首次同意CTA | boolean | true/false |  |  |
| 65 | `is_all_screen` | 是否全面屏 | string | true/false |  | 5.3 |
| 66 | `login_douyin_account` | 抖音账号是否登录 | boolean | true/false |  |  |
| 67 | `back_reconfirm` | 返回二次确认是否开启 | string | on/off |  |  |
| 68 | `launch_channel` | 冷启动默认频道 | string |  |  |  |

### 属性详情

#### `imei1` — imei1 MD5值
- 分类: 预置参数 | 类型: string
- **值说明**:
  空的

#### `roaid` — 系统OAID
- 分类: 预置参数 | 类型: string

#### `oaid` — OAID
- 分类: 预置参数 | 类型: string

#### `android_id` — Android ID
- 分类: 预置参数 | 类型: string

#### `instance_id` — 匿名ID
- 分类: 预置参数 | 类型: string
- **值说明**:
  app级别id（卸载app，id会变）

#### `uid` — 账号id
- 分类: 预置参数 | 类型: string
- **值说明**:
  小米账号

#### `session_id` — session_id
- 分类: 预置参数 | 类型: string
- **值说明**:
  app退出重置（目前o2o现状app退出跟下一次启动一致）

#### `ip` — ip
- 分类: 预置属性 | 类型: string

#### `region` — 地区
- 分类: 预置属性 | 类型: string

#### `model` — 设备名
- 分类: 预置参数 | 类型: string

#### `platform` — 平台
- 分类: 预置参数 | 类型: string

#### `miui` — MIUI版本号
- 分类: 预置参数 | 类型: string
- **值说明**:
  举例：12.10.1.2

#### `build` — 版本类型
- 分类: 预置参数 | 类型: string
- **值说明**:
  S：稳定版 D： 开发版 A：体验版 空值：用户自己编的版本

#### `os` — 系统版本号
- 分类: 预置参数 | 类型: string

#### `app_ver` — APP版本号
- 分类: 预置参数 | 类型: string

#### `version_code` — app_版本号
- 分类: 公共参数 | 类型: number | 进版: 5.3

#### `e_ts` — 事件发生时间
- 分类: 预置参数 | 类型: number
- **值说明**:
  本地客户端时间

#### `net` — 网络
- 分类: 预置参数 | 类型: string
- **值说明**:
  WIFI/5G/4G/3G/2G/ETHERNET/NONE/UNKNOWN
  NONE:没有联网， UNKNOWN:未知类型， ETHERNET:电视有线网

#### `sdk_ver` — SDK版本号
- 分类: 预置参数 | 类型: string

#### `app_id` — APPID
- 分类: 预置参数 | 类型: string

#### `pkg` — 包名
- 分类: 预置参数 | 类型: string

#### `channel` — 渠道
- 分类: 预置参数 | 类型: string
- **值说明**:
  一般为业务分发的渠道，比如抖音、应用宝等，用以跟踪渠道效果

#### `sdk_mode` — SDK接入模式
- 分类: 预置参数 | 类型: string
- **值说明**:
  App模式（默认）/SDK模式（如小米账号SDK接入）/插件模式（如米家/快应用插件）

#### `ot_ua` — useragent
- 分类: 预置参数 | 类型: string

#### `ot_privacy_policy` — 隐私策略设置
- 分类: 预置参数 | 类型: string
- **值说明**:
  打点时的隐私策略，取值范围为custom_open，custom_close，exprience_open，exprience_close

#### `event` — 事件名称
- 分类: 预置参数 | 类型: string

#### `ot_first_day` — 用户是否是第一天访问
- 分类: 预置参数 | 类型: boolean
- **值说明**:
  true/false

#### `device_id` — 设备id
- 分类: 公共参数 | 类型: string
- **值说明**:
  优先取imei1md5 imei取不到取oaid原值（3.8版本以下是oaidmd5，3.8以上时oaid原值）

#### `imei2` — imei2md5值
- 分类: 公共参数 | 类型: string

#### `is_first_today_imei` — 是否为新用户(新imei服务端口径)
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `is_first_today_imei_expose` — 是否为新曝光用户（首次信息流内容曝光业务口径）
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `city` — 设置了本地频道的城市
- 分类: 公共参数 | 类型: string
- **值说明**:
  有本地频道才会上报该值

#### `model_name` — 机型名称
- 分类: 公共参数 | 类型: string
- **值说明**:
  中文的机型名称，例如：Redmi 10

#### `price_level` — 机型分类
- 分类: 公共参数 | 类型: string
- **值说明**:
  低端机，中端机，中高端机，高端机

#### `eid` — 旧实验id
- 分类: 公共参数 | 类型: string

#### `new_eid` — 新实验id
- 分类: 公共参数 | 类型: string
- **值说明**:
  服务端下发的新实验id

#### `is_decouple` — 是否解耦
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  解耦：true
  非解耦：false

#### `app_launch_type` — 启动方式
- 分类: 公共参数 | 类型: string
- **值说明**:
  冷启动：cold_start
  热启动：hot_start

#### `app_launch_way` — 进入内容中心方式(app启动级别)
- 分类: 公共参数 | 类型: string
- **值说明**:
  Push推送进入：push
  负一屏进入：assistant
  桌面上划进入：launch_swipe
  小部件: widget_4*2hot，widget_4*2recommend，widget_4*4hot
  快捷方式：shortcut
  拉活进入：broswer_strange_banner，mi_page_mainpage，mi_page_searchbox
  icon进入：icon
  全搜为你推荐icon：quick_search
  投放拉活：active_source

#### `app_type` — 产品类型
- 分类: 公共参数 | 类型: string
- **值说明**:
  mcc：常规版
  mcc_Breaking：精选版
  mcc_recreation：娱乐中心
  mcc_explore：首页改版

#### `page` — 操作所属页面
- 分类: 公共参数 | 类型: string
- **值说明**:
  页面频道模块参数汇总

#### `from_page` — 操作上级页面
- 分类: 公共参数 | 类型: string
- **值说明**:
  页面频道模块参数汇总

#### `module` — 操作当前页面所属模块
- 分类: 公共参数 | 类型: string
- **值说明**:
  页面频道模块参数汇总

#### `from_module` — 操作上级页面所属模块
- 分类: 公共参数 | 类型: string
- **值说明**:
  页面频道模块参数汇总

#### `login_miaccount` — 小米账号是否登录
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `resolution` — 设备屏幕分辨率
- 分类: 公共参数 | 类型: string
- **值说明**:
  宽*高
  示例：720*1520

#### `carrier` — 运营商
- 分类: 公共参数 | 类型: string
- **值说明**:
  中国移动:yidong
  中国联通:liantong
  中国电信:dianxin
  中国广电：guangdian
  获取不到的打unknown

#### `ram_info` — 运行内存
- 分类: 公共参数 | 类型: string
- **值说明**:
  5g
  4g
  3g

#### `hard_disk_info` — 机身存储
- 分类: 公共参数 | 类型: string
- **值说明**:
  128g

#### `province` — 省份
- 分类: 公共参数 | 类型: string

#### `ext` — 拓展字段
- 分类: 公共参数 | 类型: string
- **值说明**:
  everyday接口调（每隔12个小时），和内存逻辑一致
  后续纯服务端计算的字段不需要客户端发版

#### `refresh_way` — 刷新方式
- 分类: 公共参数 | 类型: string
- **值说明**:
  pull/button/pull_and_button

#### `default_channel` — 默认频道
- 分类: 公共参数 | 类型: string
- **值说明**:
  play

#### `personnal_recommend` — 个性化推荐开启
- 分类: 公共参数 | 类型: string
- **值说明**:
  on/off

#### `sys_personal_ad_recommend` — 系统广告个性化推荐开启
- 分类: 公共参数 | 类型: string
- **值说明**:
  on/off

#### `personal_ad_recommend` — 个性化广告推荐开启
- 分类: 公共参数 | 类型: string
- **值说明**:
  on/off

#### `server_user_id` — 服务端用户id
- 分类: 公共参数 | 类型: string

#### `top_style` — 内容中心模式
- 分类: 公共参数 | 类型: string
- **值说明**:
  original/ transparent

#### `dp_ext` — dp拓展字段
- 分类: 公共参数 | 类型: string
- **值说明**:
  has_guide&source_&pic_id_&is_ad_&channel_id_&father_channel_id_&ext_&url_&doc_id

#### `first_app_launch_way` — 首次打开/激活渠道
- 分类: 公共参数 | 类型: string
- **值说明**:
  launch_swipe/push/douyin233/kuaishou233/......

#### `today_first_enter_way` — 当天首次激活方式
- 分类: 公共参数 | 类型: string
- **值说明**:
  launch_swipe/push/douyin233/kuaishou233/......

#### `is_normal_mode` — 是否标准版
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `screen_rotation` — 屏幕旋转开启
- 分类: 公共参数 | 类型: string
- **值说明**:
  on/off

#### `is_first_today_agree_cta` — 当天是否首次同意CTA
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `is_all_screen` — 是否全面屏
- 分类: 公共参数 | 类型: string | 进版: 5.3
- **值说明**:
  true/false

#### `login_douyin_account` — 抖音账号是否登录
- 分类: 公共参数 | 类型: boolean
- **值说明**:
  true/false

#### `back_reconfirm` — 返回二次确认是否开启
- 分类: 公共参数 | 类型: string
- **值说明**:
  on/off

#### `launch_channel` — 冷启动默认频道
- 分类: 公共参数 | 类型: string


---

## content key 内容通用属性

> 来源 sheet: `content key 内容通用属性 ` | 属性数: 29


| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |
|---|---|---|---|---|---|---|
| 1 | `feed_channel` | 频道 | string | 页面频道模块参数汇总 |  |  |
| 2 | `item_author` | 作者 | string |  |  |  |
| 3 | `item_docid` | 内容id | string | like “toutiao_newhome_%%%%” |  |  |
| 4 | `item_url` | 内容url | string |  |  |  |
| 5 | `item_title` | 内容标题 | string |  |  |  |
| 6 | `item_category` | 一级分类 | string |  |  |  |
| 7 | `item_subcategory` | 二级分类 | string |  |  |  |
| 8 | `item_cp_name` | cp名称 | string |  |  |  |
| 9 | `item_publish_time` | 发布时间 | number |  |  |  |
| 10 | `item_type` | 内容类型 | string | 图文：news 视频：video 小视频：minivideo 直播：livestream 短剧：skit |  |  |
| 11 | `item_position` | 曝光位置 | number | 0、1、2、3、4、5.....    从0开始  （广告的位置不算） 沉浸态重点关注：点击推荐页小视频进入沉浸态，该小视频报在推荐页的位置，此后下滑位置依次从0开始；点击小视频频道进入沉浸态，位置从0开始 |  |  |
| 12 | `item_order` | 所有条目横向顺序 | number | 0、1、2、3、4、5.....    从0开始 |  |  |
| 13 | `item_style` | 内容样式 | string |  |  |  |
| 14 | `view_type` | 内容展示样式 | string | item_video_reco_right 相关推荐短视频 item_news_text_left_top 新闻无图样式,左侧置顶 item_video 大图短视频 hotsoon_video_immersion  小视频流连播样式-沉浸式 item_news_one_pic_right 相关推荐右图 mini_video_feed 推荐流的小视频卡片流 item_news_three_pics … |  |  |
| 15 | `feed_alg_source` | 流量来源 | string | 快手/互三/大数据/头条 |  |  |
| 16 | `minivideo_alg_source` | 小视频流量来源 | string | 快手/互三/大数据/头条 |  |  |
| 17 | `page_number` | 刷次 | int | 所需要的事件：以下事件只要有触发，就上报此参数。 请求页面数 流上正常上报，头条第几次返回的内容page_number就是几 二级页相关推荐目前都可以报1，后贴片相关推荐都是1 小视频沉浸态一次加载6条 第一次是1，第二次是2  （注意：push内容可以null，但push的相关推荐都是1） |  |  |
| 18 | `dp_ext` | 内容拓展字段 | string | 服务端跟随内容一起下发，客户端再报上去 |  |  |
| 19 | `req_id` | 头条请求id | string |  |  |  |
| 20 | `category_name` | 头条频道名称 | string | 头条category中英文对照表 |  |  |
| 21 | `toutiao_user_id` | 头条匿名id | string |  |  |  |
| 22 | `item_authorid` | nh侧作者id | string |  |  |  |
| 23 | `item_cpauthorid` | cp侧作者id | string |  |  |  |
| 24 | `img_count` | 图片数量 | number |  |  |  |
| 25 | `word_count` | 文字数量 | number |  |  |  |
| 26 | `item_return_type` | 内容填充类型 | string | normal：正常内容 flexible：灵活内容 |  |  |
| 27 | `expose_position` | 灵活内容曝光位置 | string | 0、1、2、3、4、5.....    从0开始  （广告的位置不算） 正常内容的expose_position=item_position，灵活内容的expose_position为被替换内容的位置 |  |  |
| 28 | `page_origin` | 场景入口标识 | string | main_recommend：推荐流小视频卡片 content_detail_news：图文场景相关推荐小视频插卡 content_detail_video：视频场景相关推荐小视频插卡 main_minivideo：首页-小视频 main_recommend_shortminivideo：首页短小视频 video_minivideo：视频底tab-小视频 main_follow_author_de… |  |  |
| 29 | `global_position` | 全局位置 | int | 包括信息流+广告的全局位置 |  |  |

### 属性详情

#### `feed_channel` — 频道
- 类型: string
- **值说明**:
  页面频道模块参数汇总

#### `item_author` — 作者
- 类型: string

#### `item_docid` — 内容id
- 类型: string
- **值说明**:
  like “toutiao_newhome_%%%%”

#### `item_url` — 内容url
- 类型: string

#### `item_title` — 内容标题
- 类型: string

#### `item_category` — 一级分类
- 类型: string

#### `item_subcategory` — 二级分类
- 类型: string

#### `item_cp_name` — cp名称
- 类型: string

#### `item_publish_time` — 发布时间
- 类型: number

#### `item_type` — 内容类型
- 类型: string
- **值说明**:
  图文：news
  视频：video
  小视频：minivideo
  直播：livestream
  短剧：skit

#### `item_position` — 曝光位置
- 类型: number
- **值说明**:
  0、1、2、3、4、5.....    从0开始  （广告的位置不算）
  沉浸态重点关注：点击推荐页小视频进入沉浸态，该小视频报在推荐页的位置，此后下滑位置依次从0开始；点击小视频频道进入沉浸态，位置从0开始

#### `item_order` — 所有条目横向顺序
- 类型: number
- **值说明**:
  0、1、2、3、4、5.....    从0开始

#### `item_style` — 内容样式
- 类型: string

#### `view_type` — 内容展示样式
- 类型: string
- **值说明**:
  item_video_reco_right 相关推荐短视频
  item_news_text_left_top 新闻无图样式,左侧置顶
  item_video 大图短视频
  hotsoon_video_immersion  小视频流连播样式-沉浸式
  item_news_one_pic_right 相关推荐右图
  mini_video_feed 推荐流的小视频卡片流
  item_news_three_pics  组图
  item_news_one_pic_large  大图
  hotsoon_video_feed小视频流默认样式-宫格式

#### `feed_alg_source` — 流量来源
- 类型: string
- **值说明**:
  快手/互三/大数据/头条

#### `minivideo_alg_source` — 小视频流量来源
- 类型: string
- **值说明**:
  快手/互三/大数据/头条

#### `page_number` — 刷次
- 类型: int
- **值说明**:
  所需要的事件：以下事件只要有触发，就上报此参数。
  请求页面数
  流上正常上报，头条第几次返回的内容page_number就是几
  二级页相关推荐目前都可以报1，后贴片相关推荐都是1
  小视频沉浸态一次加载6条 第一次是1，第二次是2 
  （注意：push内容可以null，但push的相关推荐都是1）

#### `dp_ext` — 内容拓展字段
- 类型: string
- **值说明**:
  服务端跟随内容一起下发，客户端再报上去

#### `req_id` — 头条请求id
- 类型: string

#### `category_name` — 头条频道名称
- 类型: string
- **值说明**:
  头条category中英文对照表

#### `toutiao_user_id` — 头条匿名id
- 类型: string

#### `item_authorid` — nh侧作者id
- 类型: string

#### `item_cpauthorid` — cp侧作者id
- 类型: string

#### `img_count` — 图片数量
- 类型: number

#### `word_count` — 文字数量
- 类型: number

#### `item_return_type` — 内容填充类型
- 类型: string
- **值说明**:
  normal：正常内容
  flexible：灵活内容

#### `expose_position` — 灵活内容曝光位置
- 类型: string
- **值说明**:
  0、1、2、3、4、5.....    从0开始  （广告的位置不算）
  正常内容的expose_position=item_position，灵活内容的expose_position为被替换内容的位置

#### `page_origin` — 场景入口标识
- 类型: string
- **值说明**:
  main_recommend：推荐流小视频卡片
  content_detail_news：图文场景相关推荐小视频插卡
  content_detail_video：视频场景相关推荐小视频插卡
  main_minivideo：首页-小视频
  main_recommend_shortminivideo：首页短小视频
  video_minivideo：视频底tab-小视频
  main_follow_author_detail：作者页小视频
  push：小视频push
  others：其他

#### `global_position` — 全局位置
- 类型: int
- **值说明**:
  包括信息流+广告的全局位置


---

**预置属性合计**: 97

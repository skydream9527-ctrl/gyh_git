# 浏览器 - 预置与公共属性

> 本文档汇总所有事件共用的预置属性。每个事件实际上报时自动携带其引用的公共属性集(见各事件 `公共属性` 列)。


---

## OneTrack SDK 系统属性

> 来源 sheet: `OneTrack SDK系统属性` | 属性数: 32


| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |
|---|---|---|---|---|---|---|
| 1 | `ot_privacy_policy` | 打点时的隐私策略 | string |  |  |  |
| 2 | `ot_browser_type` | 浏览器类型 | string |  |  |  |
| 3 | `ot_ua` | User-Agent | string |  |  |  |
| 4 | `plugin_id` | 插件ID | string |  |  |  |
| 5 | `sdk_mode` | SDK接入模式 | string |  |  |  |
| 6 | `ot_first_day` | 首天登录 | boolean |  |  |  |
| 7 | `uid_type` | 用户Id的类型 | string |  |  |  |
| 8 | `gaid` | GMS（Google服务）生成 | string |  |  |  |
| 9 | `uid` | 用户设置的userId | string |  |  |  |
| 10 | `event` | 事件名 | string |  |  |  |
| 11 | `ip` | IP | string |  |  |  |
| 12 | `channel` | 下载渠道 | string |  |  |  |
| 13 | `pkg` | 包名 | string |  |  |  |
| 14 | `app_id` | APPID | string |  |  |  |
| 15 | `sid` | 用户空间 | string |  |  |  |
| 16 | `region` | 地区 | string |  |  |  |
| 17 | `net` | 网络 | string |  |  |  |
| 18 | `tz` | 时区 | string |  |  |  |
| 19 | `e_ts` | 上报数据时间戳 | number |  |  |  |
| 20 | `sdk_ver` | sdk版本号 | string |  |  |  |
| 21 | `app_ver` | APP版本号 | string |  |  |  |
| 22 | `os_ver` | 系统版本号 | string |  |  |  |
| 23 | `build` | 版本类型 | string |  |  |  |
| 24 | `miui` | MIUI版本号 | string |  |  |  |
| 25 | `platform` | 平台 | string |  |  |  |
| 26 | `model` | 设备名 | string |  |  |  |
| 27 | `mfrs` | 厂商 | string |  |  |  |
| 28 | `android_id` | 安卓id | string |  |  |  |
| 29 | `oaid` | OAID | string |  |  |  |
| 30 | `instance_id` | 匿名ID | string |  |  |  |
| 31 | `imei` | imeiMD5值 | string |  |  |  |
| 32 | `cpu_board` | cpu型号 | string |  |  |  |

### 属性详情

#### `ot_privacy_policy` — 打点时的隐私策略
- 类型: string

#### `ot_browser_type` — 浏览器类型
- 类型: string

#### `ot_ua` — User-Agent
- 类型: string

#### `plugin_id` — 插件ID
- 类型: string

#### `sdk_mode` — SDK接入模式
- 类型: string

#### `ot_first_day` — 首天登录
- 类型: boolean

#### `uid_type` — 用户Id的类型
- 类型: string

#### `gaid` — GMS（Google服务）生成
- 类型: string

#### `uid` — 用户设置的userId
- 类型: string

#### `event` — 事件名
- 类型: string

#### `ip` — IP
- 类型: string

#### `channel` — 下载渠道
- 类型: string

#### `pkg` — 包名
- 类型: string

#### `app_id` — APPID
- 类型: string

#### `sid` — 用户空间
- 类型: string

#### `region` — 地区
- 类型: string

#### `net` — 网络
- 类型: string

#### `tz` — 时区
- 类型: string

#### `e_ts` — 上报数据时间戳
- 类型: number

#### `sdk_ver` — sdk版本号
- 类型: string

#### `app_ver` — APP版本号
- 类型: string

#### `os_ver` — 系统版本号
- 类型: string

#### `build` — 版本类型
- 类型: string

#### `miui` — MIUI版本号
- 类型: string

#### `platform` — 平台
- 类型: string

#### `model` — 设备名
- 类型: string

#### `mfrs` — 厂商
- 类型: string

#### `android_id` — 安卓id
- 类型: string

#### `oaid` — OAID
- 类型: string

#### `instance_id` — 匿名ID
- 类型: string

#### `imei` — imeiMD5值
- 类型: string

#### `cpu_board` — cpu型号
- 类型: string


---

## common key 公共属性

> 来源 sheet: `commen key公共属性` | 属性数: 40


| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |
|---|---|---|---|---|---|---|
| 1 | `imei2` | imei2MD5值 | string | imei2的32位md5，有值传值 |  |  |
| 2 | `eid` | 实验id | string | 服务端下发的实验id 有值传值，无值传空 格式：0:1049:0:0:0:0:0:0:0:0:0:0:0:0:199: |  |  |
| 3 | `exp_id` | 大数据新版实验id | string | 有值传值，无值传空 格式：110257,114439,110057 |  |  |
| 4 | `homepage_type` | 主页类型 | string | concise：简洁版 default：默认 custom：自定义 |  |  |
| 5 | `deviceid` | 设备id | string |  |  | 15.4 |
| 6 | `app_launch_way` | 启动浏览器方式 | string | 点击icon 点击push 点击桌面书签 新全搜调起 第三方调起 tool_widget_one(小部件1) tool_widget_two(小部件2) 其他 |  | 14.3开始有值；<br>15.6更新取值 |
| 7 | `today_first_app_launch_way` | 用户当天首次启动浏览器方式 | string | 点击icon 点击push 点击桌面书签 新全搜调起 第三方调起 tool_widget_one(小部件1) tool_widget_two(小部件2) 其他 |  | 17.1 |
| 8 | `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |  |
| 9 | `page` | 当前所属页面 | string | 见“附1：页面定义” |  |  |
| 10 | `from_page` | 上级页面 | string | 见“附1：页面定义” |  |  |
| 11 | `searchengine_name` | 搜索引擎名 | string | baidu sogou sm toutiao 自定义搜索引擎的名称 |  |  |
| 12 | `log_miaccount` | 小米账号登录状态（系统、非浏览器） | boolean | true ：登录 false：未登录 |  |  |
| 13 | `browser_log_status` | 浏览器账号登录状态 | boolean | true ：登录 false：未登录 |  |  |
| 14 | `sreen_resolution` | 手机屏幕分辨率 | string | 如：640x480 |  |  |
| 15 | `desktop_expid` | 桌面框实验信息 | string | 以点分隔多个实验，如exp-1.exp-2 |  |  |
| 16 | `ad_rec_status` | 个性化广告推荐开关状态 | string | on：打开 off：关闭 |  | 15.2 |
| 17 | `content_rec_status` | 个性化内容推荐开关状态 | string | on：打开 off：关闭 |  | 15.2 |
| 18 | `start_source` | 桌面框调起标记 | string | 桌面框调起浏览器时上报（包括热启冷起），该字段值为bw-desktop，其他情况为记为空 （目前在实验阶段） |  | 在15.4删除 |
| 19 | `baidu_applets` | 小程序开关 | boolean | true/false |  |  |
| 20 | `is_admarket_channel` | 是否外投渠道调起 | boolean | true/false |  |  |
| 21 | `version_name` | 小说_浏览器版本 | string |  |  |  |
| 22 | `novel_MIUIVersion` | 小说_MIUI版本 | string |  |  |  |
| 23 | `index_type` | 首页类型 | string |  |  |  |
| 24 | `icon_switch_status` | 宫格开关状态 | string |  |  |  |
| 25 | `hot_list_switch_status` | 热榜开关状态 | string |  |  |  |
| 26 | `is_admarket_channel` | 是否外投渠道调起 | boolean |  |  |  |
| 27 | `admarket_channel_name` | 外投渠道名称 | string |  |  |  |
| 28 | `session` | 进程id | string |  |  |  |
| 29 | `launchedAppChannel` | 外投渠道名名称 | string |  |  |  |
| 30 | `sessionId` | session | string |  |  |  |
| 31 | `search_logo_type` | 搜索图标类型 | string |  |  |  |
| 32 | `search_button_status` | 搜索按钮状态 | string |  |  |  |
| 33 | `cpu_board` | 处理器型号 | string | 系统自采集 |  |  |
| 34 | `screen_rotation` | 屏幕旋转 | string | 用户是否设置屏幕旋转 |  |  |
| 35 | `dp_ext` | dp拓展字段 | string |  |  |  |
| 36 | `splash_ad_sdk_request_status` | 是否成功请求sdk开屏 | boolean |  |  |  |
| 37 | `app_ver_server` | 客户端请求服务端版本号 | string | 17.5.90320 |  |  |
| 38 | `cp_id` | 合作方id | string | 头条为头条uuid |  |  |
| 39 | `is_coldstart` | 是否冷启动 | boolean | true：冷启 false：热启 |  |  |
| 40 | `model_type` | 设备机型类别 | string | 手机、折叠屏、pad |  |  |

### 属性详情

#### `imei2` — imei2MD5值
- 类型: string
- **值说明**:
  imei2的32位md5，有值传值

#### `eid` — 实验id
- 类型: string
- **值说明**:
  服务端下发的实验id
  有值传值，无值传空
  格式：0:1049:0:0:0:0:0:0:0:0:0:0:0:0:199:

#### `exp_id` — 大数据新版实验id
- 类型: string
- **值说明**:
  有值传值，无值传空
  格式：110257,114439,110057

#### `homepage_type` — 主页类型
- 类型: string
- **值说明**:
  concise：简洁版
  default：默认
  custom：自定义

#### `deviceid` — 设备id
- 类型: string | 进版: 15.4

#### `app_launch_way` — 启动浏览器方式
- 类型: string | 进版: 14.3开始有值；
15.6更新取值
- **值说明**:
  点击icon
  点击push
  点击桌面书签
  新全搜调起
  第三方调起
  tool_widget_one(小部件1)
  tool_widget_two(小部件2)
  其他

#### `today_first_app_launch_way` — 用户当天首次启动浏览器方式
- 类型: string | 进版: 17.1
- **值说明**:
  点击icon
  点击push
  点击桌面书签
  新全搜调起
  第三方调起
  tool_widget_one(小部件1)
  tool_widget_two(小部件2)
  其他

#### `third_packagename` — 第三方调起包名
- 类型: string
- **值说明**:
  app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空

#### `page` — 当前所属页面
- 类型: string
- **值说明**:
  见“附1：页面定义”

#### `from_page` — 上级页面
- 类型: string
- **值说明**:
  见“附1：页面定义”

#### `searchengine_name` — 搜索引擎名
- 类型: string
- **值说明**:
  baidu
  sogou
  sm
  toutiao
  自定义搜索引擎的名称

#### `log_miaccount` — 小米账号登录状态（系统、非浏览器）
- 类型: boolean
- **值说明**:
  true ：登录
  false：未登录

#### `browser_log_status` — 浏览器账号登录状态
- 类型: boolean
- **值说明**:
  true ：登录
  false：未登录

#### `sreen_resolution` — 手机屏幕分辨率
- 类型: string
- **值说明**:
  如：640x480

#### `desktop_expid` — 桌面框实验信息
- 类型: string
- **值说明**:
  以点分隔多个实验，如exp-1.exp-2

#### `ad_rec_status` — 个性化广告推荐开关状态
- 类型: string | 进版: 15.2
- **值说明**:
  on：打开
  off：关闭

#### `content_rec_status` — 个性化内容推荐开关状态
- 类型: string | 进版: 15.2
- **值说明**:
  on：打开
  off：关闭

#### `start_source` — 桌面框调起标记
- 类型: string | 进版: 在15.4删除
- **值说明**:
  桌面框调起浏览器时上报（包括热启冷起），该字段值为bw-desktop，其他情况为记为空
  （目前在实验阶段）

#### `baidu_applets` — 小程序开关
- 类型: boolean
- **值说明**:
  true/false

#### `is_admarket_channel` — 是否外投渠道调起
- 类型: boolean
- **值说明**:
  true/false

#### `version_name` — 小说_浏览器版本
- 类型: string

#### `novel_MIUIVersion` — 小说_MIUI版本
- 类型: string

#### `index_type` — 首页类型
- 类型: string

#### `icon_switch_status` — 宫格开关状态
- 类型: string

#### `hot_list_switch_status` — 热榜开关状态
- 类型: string

#### `is_admarket_channel` — 是否外投渠道调起
- 类型: boolean

#### `admarket_channel_name` — 外投渠道名称
- 类型: string

#### `session` — 进程id
- 类型: string

#### `launchedAppChannel` — 外投渠道名名称
- 类型: string

#### `sessionId` — session
- 类型: string

#### `search_logo_type` — 搜索图标类型
- 类型: string

#### `search_button_status` — 搜索按钮状态
- 类型: string

#### `cpu_board` — 处理器型号
- 类型: string
- **值说明**:
  系统自采集

#### `screen_rotation` — 屏幕旋转
- 类型: string
- **值说明**:
  用户是否设置屏幕旋转

#### `dp_ext` — dp拓展字段
- 类型: string

#### `splash_ad_sdk_request_status` — 是否成功请求sdk开屏
- 类型: boolean

#### `app_ver_server` — 客户端请求服务端版本号
- 类型: string
- **值说明**:
  17.5.90320

#### `cp_id` — 合作方id
- 类型: string
- **值说明**:
  头条为头条uuid

#### `is_coldstart` — 是否冷启动
- 类型: boolean
- **值说明**:
  true：冷启
  false：热启

#### `model_type` — 设备机型类别
- 类型: string
- **值说明**:
  手机、折叠屏、pad


---

## content key 信息流通用属性

> 来源 sheet: `content key信息流通用属性` | 属性数: 31


| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |
|---|---|---|---|---|---|---|
| 1 | `feed_status` | 是否信息流进入态 | boolean | true:：是 false ：否 |  | 14.3.4 |
| 2 | `feed_enter_way` | 进入信息流方式 | string | 从进入信息流后直到离开保持相同值，目的是看用户通过什么行为进入信息流 包括如下值： default：默认 （默认进入就是进入态） push：PUSH   bottom_nav_info：底部资讯按钮 bottom_nav_video：底部视频按钮 swipe_down ：下滑进入信息流 + 上推进入信息流 browser_home_feed：浏览器首页点击卡片进入 browser_home_lin… |  | 14.3.4 |
| 3 | `feed_alg_source` | 算法来源（即流量方） | string | toutiao：头条（eid第二位为1049 ） yidian：一点（eid第二位为2） baidu：百度（eid第二位为557） xiaomi：小米大数据（eid第二位为742） |  | 14.3.4 |
| 4 | `user_switch` | 用户流量切换 | string | xiaomi toutiao baidu |  |  |
| 5 | `feed_style` | 流的展示类型 | string | default：默认单列流（列表页） related_recommendation：相关推荐（在各种详情页内的相关推荐） immersion：短视频沉浸式 minivideo_double：小视频频道双列流 minivideo_inside：小视频连播页（内流） video_immersion：短小融合 |  | 14.6 |
| 6 | `feed_channel` | 所属频道 | string | 资讯tab：推荐、视频、小视频、抗疫、游戏、本地、push等等 视频tab改版前：视频tab小视频、视频tab推荐等 视频tab改版后：视频底tab小视频、视频底tab短视频 从该频道进入详情页后，详情页的打点也需要该字段 沉浸视频：沉浸式场景，从第二个视频开始，上报沉浸视频 第三方调起：三方调起 详情页：相关推荐、文章详情页相关推荐 |  | 14.3.4 |
| 7 | `feed_trace_id` | 服务端请求ID | string | 此次内容的服务端请求id, 由服务端提供 |  | 14.3.4 |
| 8 | `item_type` | 媒体类型 | string | news：图文 inline_video：短视频 mini_video：小视频 novel：小说 url ：运营配置url livestream：直播 |  | 14.3.4 |
| 9 | `item_position` | 单条内容在列表中所处位置，竖向 | number | 各场景改成从0开始计数 内容和广告从上至下排序，从0开始 1、内容在流里所处的位置：从0开始，0、1、2…… 2、屏蔽一条内容后，下一条内容position不变动 3、推荐频道列表页，小视频竖版放2个的时候，position为同一个，用item_order字段区分横向位置 4、相关推荐流也需要有 5、小视频内流从上至下从0开始记 6、短视频沉浸式从上至下从0开始记 7、小视频频道双列流：横向从左到… |  | 15.0.0 |
| 10 | `card_type` | 卡片类型 | string | operation_top：运营位_置顶 operation_xinshidai：运营位_新时代 operation_chaka：运营位_插卡 recommendation：推荐内容位 rs：阅后RS diversion：导流位 float_layer： |  | 14.6 |
| 11 | `card_item_position` | item在卡片里的位置 | number | RS、运营位上报，其他为空 从0开始，0、1、2、3…… |  | 14.3.4 |
| 12 | `item_style` | item展示一级样式 | string | 展示在流内的样式，包括如下值（RS为空）： 图文 短视频 小视频 |  |  |
| 13 | `item_substyle` | item展示二级样式 | string | 包括如下值： 图文_无图：0 图文_单图：1 图文_大图 ：2 图文_三图：3 短视频_沉浸式：large_img_video_item 短视频_卡片（短视频频道里短视频的样式）：inline_video_item 短视频_大图 ：large_img_video_item 短视频_单图（右侧小图）：short_video_item 小视频_竖版卡片（小视频频道里小视频的样式）：vertical_v… |  | 14.8 |
| 14 | `item_order` | 单条内容在列表中的二级位置，横向 | number | 小视频竖版横向滑动时从左向右依次记录，从0开始，0、1、2…… |  | 14.3.4 |
| 15 | `item_title` | 内容标题 | string |  |  | 14.3.4 |
| 16 | `item_docid` | 内容id | string |  |  | 14.3.4 |
| 17 | `item_category` | 内容所属一级领域 | string | 体育、游戏、汽车、综艺、历史…… |  | 14.3.4 |
| 18 | `item_subcategory` | 内容所属二级领域 | string | 国际足球、王者荣耀、唐朝…… |  | 14.3.4 |
| 19 | `item_auther` | 内容作者 | string |  |  | 14.3.4 |
| 20 | `item_auther_level` | 作者等级（同账号等级） | string | 账号等级 0、1、2…5，同以前的sourcelevel，合作方传过来的，直接记录 |  | 14.3.4 |
| 21 | `item_tag` | 内容标签 | array | 包含信息流+push内容，一个或多个，不是所有的cp都传，没有传的为空 |  | 14.3.4 |
| 22 | `item_summary` | 内容摘要 | array | 仅push内容上报，信息流内容不上报 |  | 17.9 |
| 23 | `item_cp_name` | 内容提供方标识 | string | cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  | 14.3.4 |
| 24 | `item_publish_time` | 作者发布内容时间 | string | 统一为如下格式： 2021-03-02 03:38:11 |  | 14.3.4 |
| 25 | `item_cpauthorid` | 内容作者id | string |  |  |  |
| 26 | `minivideo_alg_source` | 小视频流量方 | string | toutiao：头条流（eid第二位为1049） kuaishou：快手流（exp_id包含26646） xiaomi：小米流（eid第二位为742  或  exp_id包含26532） 目前new_eid改为exp_id |  |  |
| 27 | `ext` | 扩展字段 | string | 流量方透传，用于区分不同策略等。长度超长的json |  |  |
| 28 | `impid` | impid | string | 用于一点判断用户id |  | 15.6 |
| 29 | `page_origin` | 场景入口标识 | string | feed_info_topnews：首页要闻频道小视频插卡feed_info_rec：首页推荐频道小视频插卡feed_info_topnews_immersion：首页推荐频道短小视频feed_info_rec_immersion：首页要闻频道短小视频feed_video_shortv：视频底tab小视频频道feed_content_detail_video：视频场景相关推荐小视频插卡feed_c… |  |  |
| 30 | `page_number` | 刷次 | int | 所需要的事件：以下事件只要有触发，就上报此参数。 请求页面数 流上正常上报，第几次返回的内容page_number就是几 |  |  |
| 31 | `item_alg_source` | 内容算法来源 | string | toutiao xiaomi baidu…… |  |  |

### 属性详情

#### `feed_status` — 是否信息流进入态
- 类型: boolean | 进版: 14.3.4
- **值说明**:
  true:：是
  false ：否

#### `feed_enter_way` — 进入信息流方式
- 类型: string | 进版: 14.3.4
- **值说明**:
  从进入信息流后直到离开保持相同值，目的是看用户通过什么行为进入信息流
  包括如下值：
  default：默认 （默认进入就是进入态）
  push：PUSH  
  bottom_nav_info：底部资讯按钮
  bottom_nav_video：底部视频按钮
  swipe_down ：下滑进入信息流 + 上推进入信息流
  browser_home_feed：浏览器首页点击卡片进入
  browser_home_link：点击链接进入
  ""：未进入态情况下为空

#### `feed_alg_source` — 算法来源（即流量方）
- 类型: string | 进版: 14.3.4
- **值说明**:
  toutiao：头条（eid第二位为1049 ）
  yidian：一点（eid第二位为2）
  baidu：百度（eid第二位为557）
  xiaomi：小米大数据（eid第二位为742）

#### `user_switch` — 用户流量切换
- 类型: string
- **值说明**:
  xiaomi
  toutiao
  baidu

#### `feed_style` — 流的展示类型
- 类型: string | 进版: 14.6
- **值说明**:
  default：默认单列流（列表页）
  related_recommendation：相关推荐（在各种详情页内的相关推荐）
  immersion：短视频沉浸式
  minivideo_double：小视频频道双列流
  minivideo_inside：小视频连播页（内流）
  video_immersion：短小融合

#### `feed_channel` — 所属频道
- 类型: string | 进版: 14.3.4
- **值说明**:
  资讯tab：推荐、视频、小视频、抗疫、游戏、本地、push等等
  视频tab改版前：视频tab小视频、视频tab推荐等
  视频tab改版后：视频底tab小视频、视频底tab短视频
  从该频道进入详情页后，详情页的打点也需要该字段
  沉浸视频：沉浸式场景，从第二个视频开始，上报沉浸视频
  第三方调起：三方调起
  详情页：相关推荐、文章详情页相关推荐

#### `feed_trace_id` — 服务端请求ID
- 类型: string | 进版: 14.3.4
- **值说明**:
  此次内容的服务端请求id, 由服务端提供

#### `item_type` — 媒体类型
- 类型: string | 进版: 14.3.4
- **值说明**:
  news：图文
  inline_video：短视频
  mini_video：小视频
  novel：小说
  url ：运营配置url
  livestream：直播

#### `item_position` — 单条内容在列表中所处位置，竖向
- 类型: number | 进版: 15.0.0
- **值说明**:
  各场景改成从0开始计数
  内容和广告从上至下排序，从0开始
  1、内容在流里所处的位置：从0开始，0、1、2……
  2、屏蔽一条内容后，下一条内容position不变动
  3、推荐频道列表页，小视频竖版放2个的时候，position为同一个，用item_order字段区分横向位置
  4、相关推荐流也需要有
  5、小视频内流从上至下从0开始记
  6、短视频沉浸式从上至下从0开始记
  7、小视频频道双列流：横向从左到右，纵向从上到下，从0开始记
  8、详情页底部双列小视频流：横向从左到右，纵向从上到下，从0开始记
  9、列表页进入详情页这条数据，item_postion是列表页positon 小视频插卡，第二条内容item_position上报0

#### `card_type` — 卡片类型
- 类型: string | 进版: 14.6
- **值说明**:
  operation_top：运营位_置顶
  operation_xinshidai：运营位_新时代
  operation_chaka：运营位_插卡
  recommendation：推荐内容位
  rs：阅后RS
  diversion：导流位
  float_layer：

#### `card_item_position` — item在卡片里的位置
- 类型: number | 进版: 14.3.4
- **值说明**:
  RS、运营位上报，其他为空
  从0开始，0、1、2、3……

#### `item_style` — item展示一级样式
- 类型: string
- **值说明**:
  展示在流内的样式，包括如下值（RS为空）：
  图文
  短视频
  小视频

#### `item_substyle` — item展示二级样式
- 类型: string | 进版: 14.8
- **值说明**:
  包括如下值：
  图文_无图：0
  图文_单图：1
  图文_大图 ：2
  图文_三图：3
  短视频_沉浸式：large_img_video_item
  短视频_卡片（短视频频道里短视频的样式）：inline_video_item
  短视频_大图 ：large_img_video_item
  短视频_单图（右侧小图）：short_video_item
  小视频_竖版卡片（小视频频道里小视频的样式）：vertical_video_item
  小视频_横滑竖版卡片：wow_mini_video_item
  小视频_大图（小视频居中展示）：large_img_vertical_video
  小视频_单图（右侧小图）：vertical_video_item
  浏览器ViewType映射

#### `item_order` — 单条内容在列表中的二级位置，横向
- 类型: number | 进版: 14.3.4
- **值说明**:
  小视频竖版横向滑动时从左向右依次记录，从0开始，0、1、2……

#### `item_title` — 内容标题
- 类型: string | 进版: 14.3.4

#### `item_docid` — 内容id
- 类型: string | 进版: 14.3.4

#### `item_category` — 内容所属一级领域
- 类型: string | 进版: 14.3.4
- **值说明**:
  体育、游戏、汽车、综艺、历史……

#### `item_subcategory` — 内容所属二级领域
- 类型: string | 进版: 14.3.4
- **值说明**:
  国际足球、王者荣耀、唐朝……

#### `item_auther` — 内容作者
- 类型: string | 进版: 14.3.4

#### `item_auther_level` — 作者等级（同账号等级）
- 类型: string | 进版: 14.3.4
- **值说明**:
  账号等级 0、1、2…5，同以前的sourcelevel，合作方传过来的，直接记录

#### `item_tag` — 内容标签
- 类型: array | 进版: 14.3.4
- **值说明**:
  包含信息流+push内容，一个或多个，不是所有的cp都传，没有传的为空

#### `item_summary` — 内容摘要
- 类型: array | 进版: 17.9
- **值说明**:
  仅push内容上报，信息流内容不上报

#### `item_cp_name` — 内容提供方标识
- 类型: string | 进版: 14.3.4
- **值说明**:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

#### `item_publish_time` — 作者发布内容时间
- 类型: string | 进版: 14.3.4
- **值说明**:
  统一为如下格式：
  2021-03-02 03:38:11

#### `item_cpauthorid` — 内容作者id
- 类型: string

#### `minivideo_alg_source` — 小视频流量方
- 类型: string
- **值说明**:
  toutiao：头条流（eid第二位为1049）
  kuaishou：快手流（exp_id包含26646）
  xiaomi：小米流（eid第二位为742  或  exp_id包含26532）
  目前new_eid改为exp_id

#### `ext` — 扩展字段
- 类型: string
- **值说明**:
  流量方透传，用于区分不同策略等。长度超长的json

#### `impid` — impid
- 类型: string | 进版: 15.6
- **值说明**:
  用于一点判断用户id

#### `page_origin` — 场景入口标识
- 类型: string
- **值说明**:
  feed_info_topnews：首页要闻频道小视频插卡feed_info_rec：首页推荐频道小视频插卡feed_info_topnews_immersion：首页推荐频道短小视频feed_info_rec_immersion：首页要闻频道短小视频feed_video_shortv：视频底tab小视频频道feed_content_detail_video：视频场景相关推荐小视频插卡feed_content_detail_news：图文场景相关推荐小视频插卡feed_info_hotList：首页热榜频道小视频插卡feed_info_shortVideo：首页小视频频道
  author_profile：作者页小视频
  push：小视频push
  others：其他
  push_news_detail：push图文落地页home_hot_list_immersion：高端版首页热榜短小融合home_all_immersion：高端版首页无限流短小融合

#### `page_number` — 刷次
- 类型: int
- **值说明**:
  所需要的事件：以下事件只要有触发，就上报此参数。
  请求页面数
  流上正常上报，第几次返回的内容page_number就是几

#### `item_alg_source` — 内容算法来源
- 类型: string
- **值说明**:
  toutiao
  xiaomi
  baidu……


---

**预置属性合计**: 103

# 内容中心 - content内容相关

> 来源 sheet: `content内容相关` | 事件数: 24 | 参数数: 88


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `content_item_expose` | 信息流_单条内容_曝光 | 信息流_单条内容_曝光：33%条目曝光时上报；不重复上报，需缓存内容（知乎、微博等均上报、沉浸态上报） 信息流_单条内容… | 1 | - |  |
| 2 | `content_item_video_play` | 信息流_单条内容_视频播放 | 信息流_单条内容_视频播放：视频播放时上报；多次播放多次上报；（退出再进入/app退出再进入/沉浸态上下滑时/锁屏/息屏… | 0 | - |  |
| 3 | `content_item_like` | 信息流_单条内容_点赞 | 公共参数（只要page，不要from_page,module,from_module） 信息流通用参数（详情页触发的参数… | 28 | - |  |
| 4 | `content_duration` | 时长 | 1）详情页时长（图文、短视频、小视频记录）（离开这个页面上报，同触发view事件） 2）短视频/小视频播放时长（视频暂停… | 1 | - |  |
| 5 | `备注：视频时长从over事件中查看` |  |  | 1 | - |  |
| 6 | `页面时长从app_duration_v2中查看` | _v2 |  | 11 | - |  |
| 7 | `content_count_item` | 内容曝光条数 | 1）从后台切换至前台开始计数 2）从前台切换至后台时上报累计曝光   切到后台定义：app退出桌面，锁屏/息屏/多任务切… | 1 | common key |  |
| 8 | `content_refresh` | 刷新 | 刷新接口返回上报（刷新只要page 不要from_page,module,from_module） 范围（不包括热榜） | 3 | common key |  |
| 9 | `content_refresh_load` | 刷新_内容渲染 | 刷新接口返回后有内容曝光/内容渲染失败时上报（刷新只要page 不要from_page,module,from_modu… | 3 | common key | 5.6 |
| 10 | `content_item_request` | 信息流_内容请求 | 向服务端发起内容请求时上报，每请求一次上报一次事件 | 2 | common key | 5.6 |
| 11 | `content_follow` | 关注 | 关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需要） | 3 | - |  |
| 12 | `content_unfollow` | 取消关注 | 取消关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需… | 3 | - |  |
| 13 | `content_channel_edit` | 编辑频道 | 编辑成功时上报 | 2 | common key |  |
| 14 | `content_button_show` | 取消关注 | 取消关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需… | 3 | - |  |
| 15 | `content_export_show` | 引流曝光 | （露出即上报，滑走再滑会，露出后继续上报） | 2 | - |  |
| 16 | `content_export_click` | 引流点击 | 点击即上报，点击多次上报多次 | 2 | - |  |
| 17 | `content_slide` | 屏幕滑动 | 1、滑动停止时上报 2、滑动最大位置item_position变化时才上报 (优先做推荐流频道。如果可以复用，再扩展其他… | 3 | - |  |
| 18 | `content_item_fold_button_expose` | 详情页折叠按钮曝光，单页面只曝光1次，上下滑动不重复曝光，退出后再进入重复报 |  | 1 | - |  |
| 19 | `content_item_video_over_exception` |  |  | 0 | - |  |
| 20 | `content_item_video_auto_play` | 信息流_单条内容_视频自动播放 | 信息流_单条内容_视频自动播放：推荐页首条内容第一次开始自动播放时上报，下划再上划自动播放/点进视频详情页退出自动播放均… | 4 | - |  |
| 21 | `url_click` | 软广链接点击 | 多次点击多次上报 | 2 | common key |  |
| 22 | `content_item_cover_load_fail` | 信息流_单条内容_封面加载失败 | 封面加载失败时上报，不重复上报 不考虑内容是否曝光 | 2 | common key |  |
| 23 | `content_duration_v2` | 信息流时长 | 以任何方式离开频道列表页上报，记录从进入频道列表页到离开频道列表页的时长； 离开频道场景： 退出频道、切换频道tab、进… | 4 | common key, content key |  |
| 24 | `content_duration_v2` | 信息流时长 | 以任何方式离开信息流详情页（包括进入一个新的详情页时），记录从进入详情页到离开详情页的时长，同一个页面上报一次： 1、信… | 6 | common key, content key |  |

---

## 事件详情

### `content_item_expose` — 信息流_单条内容_曝光

**上报时机/逻辑**:

信息流_单条内容_曝光：33%条目曝光时上报；不重复上报，需缓存内容（知乎、微博等均上报、沉浸态上报）
信息流_单条内容_点击：事件发生时；多次点击多次上报；
注意：
1、从列表点击进入短小视频沉浸态上报点击
2、上下滑自动播放（包括回看），播放之后自动播放下一个，不上报点击
3、5.6版本点击列表页的内容，进入沉浸态，该条内容不上报content_item_click事件

信息流_单条内容_浏览：浏览页面退出时上报（包括app退出、返回上一级页面，切多任务/拉通知栏跳走都算，只要详情页看不到就记）
息屏锁屏不上报
注意：
1、短小视频沉浸态正常上报（5.6及之后版本不上报）
2、进入作者详情页正常上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` |  |  |  |  |

### `content_item_video_play` — 信息流_单条内容_视频播放

**上报时机/逻辑**:

信息流_单条内容_视频播放：视频播放时上报；多次播放多次上报；（退出再进入/app退出再进入/沉浸态上下滑时/锁屏/息屏/切多任务/拉通知栏/刷新上报)(暂停重新开始不上报）
增加场景：
1、上一个视频播完下一个自动开始播放
2、沉浸态上下滑开始自动播放（包括回看）
3、沉浸态内同一个视频重复播放不上报

信息流_单条内容_视频播放完成：（详情页退出/app退出//切多任务/拉通知栏跳走上报。重复以上动作继续上报)；暂停重新开始不上报
增加场景：
1、自动播放的视频完成播放/退出沉浸态/沉浸态上下滑时上报
2、进入作者详情页正常上报，时长上报进入详情页之前的播放时长
3、作者详情页返回沉浸态，上报play，滑到下一个视频，上报over，时长为本次播放时长
20250101更新：息屏锁屏上报over，解锁重新播放上报play，duration分段上报


_(无独立参数,仅携带公共属性)_


### `content_item_like` — 信息流_单条内容_点赞

**上报时机/逻辑**:

公共参数（只要page，不要from_page,module,from_module）
信息流通用参数（详情页触发的参数同条目的view事件，feed流上触发的参数同条目曝光事件）
信息流_单条内容_点赞：点赞成功时上报；不去重 （包括详情页，小视频沉浸态）
信息流_单条内容_取消点赞：取消点赞成功时；不去重 （包括详情页，小视频沉浸态）
信息流_单条内容_分享：点击分享渠道时；不去重 （包括详情页，小视频沉浸态）（点击渠道按钮就算）
信息流_单条内容_收藏：收藏成功时上报；不去重 （包括详情页，小视频沉浸态）

信息流_单条内容_负反馈：一级弹窗点击时上报；多次负反馈多次上报（包括主流、详情页，小视频沉浸态）
信息流_单条内容_投诉：内容投诉二级弹窗点击标签内容时上报；多次投诉多次上报（包括主流、详情页，小视频沉浸态）
信息流_单条内容_评论：评论请求成功上报，评论多次上报多次（包括详情页）范围不包括小铃铛和我的页面里的回复评论


**参数列表** (28):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_id` | card_id非文章id | string | 运营位_专题卡片：cms里的配置id 运营位_banner:cms里的配置id |  |
| `card_type` | card类型 | string | _position |  |
| `card_style` | card样式 | string | 无图 news_nopic 大图 news_largepic 小图 news_ littlepic  组图3图 news_threepic 短视频内容统一上报video |  |
| `card_item_position` | card里item条目的顺序 | string | 0、1、2、3、4、5.....    从0开始 |  |
| `duration` | 时长 | number |  |  |
| `item_order` | 所有条目横向顺序 | number | 0、1、2、3、4、5.....    从0开始 |  |
| `share_type` | 分享渠道 | string | 微信/朋友圈/微博/更多 |  |
| `feedback_type` | 不感兴趣类型 | string | 拉黑作者：xx（原始文案） 不感兴趣：时政（原始文案） 屏蔽关键词：欧冠（屏蔽关键词为特殊情况，目前看到新时代、足球、财经频道有） |  |
| `report_type` | 投诉类型 | string | 重复/低俗/标题党/内容差 |  |
| `comment_detail` | 评论具体内容 | string | 哈哈哈哈 |  |
| `comment_type` | 主动评论/回复 | string | 主动/回复 |  |
| `item_root_id` | 根内容id<br>沉浸态首个文章id | string | toutiao_newhome_sjofhaowej19384 |  |
| `item_root_type` | 根内容id<br>沉浸态首个内容类型 | string | video、minivideo |  |
| `item_from_id` | 相关阅读来源文章id | string | 用户点击相关阅读进入下个详情页时上报，列表页点击不上报 |  |
| `item_auto_play` | 是否自动播放 | boolean | true/false |  |
| `length` | 视频长度 | number | 单位毫秒 |  |
| `item_percent` | 视频播放进度/图文浏览进度 | number | 退出后记录percent，百分比例如  0/1/50/100，保留整数；多次浏览记最大值 |  |
| `fail_type` | 失败类型 | string | play_start，播放开始失败（播放时长=0） play_middle，播放途中失败（播放时长>0） |  |
| `backinfo` | 负反馈透传参数 | string |  |  |
| `play_location` | string | 播放位置 | list（列表页）、detail（详情页） |  |
| `expose_mode` | 曝光方式 | string | back返回拦截至下滑一屏的曝光：back_holdup |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` |  |
| `xm_cache_status` | 小米cdn缓存状态 | string |  |  |
| `xm_cdn_prov` | 小米cdn厂商 | string |  |  |
| `xm_remote_address` | 小米cdn服务端ip | string |  |  |
| `bitrate` | 码率 | string |  |  |
| `video_resolution` | 分辨率 | string |  |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡、相关推荐视频插卡） false |  |

<details><summary>参数取值详情</summary>


**`card_style`** (card样式)
- 类型: string
- 取值:
  无图 news_nopic
  大图 news_largepic
  小图 news_ littlepic 
  组图3图 news_threepic
  短视频内容统一上报video

**`feedback_type`** (不感兴趣类型)
- 类型: string
- 取值:
  拉黑作者：xx（原始文案）
  不感兴趣：时政（原始文案）
  屏蔽关键词：欧冠（屏蔽关键词为特殊情况，目前看到新时代、足球、财经频道有）

</details>


### `content_duration` — 时长

**上报时机/逻辑**:

1）详情页时长（图文、短视频、小视频记录）（离开这个页面上报，同触发view事件）
2）短视频/小视频播放时长（视频暂停，切多任务不累计时长，离开这个页面上报，同触发video_over事件）
3）频道时长只算在频道主流时长（记录用户在频道列表页时长，退出，进入详情页，切多任务上报）
息屏锁屏不上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key（注意频道时长不需要content key）` | 公共属性<br>内容通用属性 |  |  |  |

### `备注：视频时长从over事件中查看` — 


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 详情页/视频/频道 |  |  |  |

### `页面时长从app_duration_v2中查看` — _v2


**参数列表** (11):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 时长单位毫秒 | number |  |  |
| `card_id` | card_id非文章id | string | 运营位_专题卡片：cms里的配置id 运营位_banner:cms里的配置id |  |
| `card_type` | card类型 | string | topic_headline topic_banner |  |
| `card_style` | card样式 | string | 无图 news_nopic 大图 news_largepic 小图 news_ littlepic  组图3图 news_threepic 短视频内容统一上报video |  |
| `card_item_position` | card里item条目的顺序 | number | 0、1、2、3、4、5.....    从0开始 |  |
| `item_order` | 所有条目横向顺序 | number | 0、1、2、3、4、5.....    从0开始 |  |
| `item_from_id` | 相关阅读来源文章id | string | 用户点击相关阅读进入下个详情页时上报，列表页点击不上报 |  |
| `item_root_id` | 沉浸态首个文章id | string | 进入沉浸式列表前首个观看group_id，必报场景：短视频沉浸态首个视频播放、短视频沉浸态用户主动播放某个视频、小视频进入内流首个播放 |  |
| `item_auto_play` | 是否自动播放 | boolean | true/false |  |
| `item_video_length` | 视频长度 | number | 单位毫秒 |  |
| `item_percent` | 视频播放进度/图文浏览进度 | number | 退出后记录percent，百分比例如  0/1/50/100，保留整数；多次浏览记最大值 |  |

<details><summary>参数取值详情</summary>


**`card_style`** (card样式)
- 类型: string
- 取值:
  无图 news_nopic
  大图 news_largepic
  小图 news_ littlepic 
  组图3图 news_threepic
  短视频内容统一上报video

**`item_root_id`** (沉浸态首个文章id)
- 类型: string
- 取值:
  进入沉浸式列表前首个观看group_id，必报场景：短视频沉浸态首个视频播放、短视频沉浸态用户主动播放某个视频、小视频进入内流首个播放

</details>


### `content_count_item` — 内容曝光条数

- 公共属性: `common key`

**上报时机/逻辑**:

1）从后台切换至前台开始计数
2）从前台切换至后台时上报累计曝光  
切到后台定义：app退出桌面，锁屏/息屏/多任务切第三方/通知栏跳三方


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `expose_total` | 总曝光条数 | 数值型 | 1，2，3…… |  |

### `content_refresh` — 刷新

- 公共属性: `common key`

**上报时机/逻辑**:

刷新接口返回上报（刷新只要page 不要from_page,module,from_module）
范围（不包括热榜）


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | 下拉刷新：swipe_down 自动刷新：auto_refresh(包括点击频道刷新) 加载更多刷新：load_more 按钮刷新：button_refresh 底部tab点击刷新：bottom_tab_click back回退刷新：back_refresh（第一次点回退时候的刷新） |  |
| `is_success` | 是否刷新成功 | boolean | true/false |  |
| `duration` | 接口耗时(毫秒) | number |  |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  下拉刷新：swipe_down
  自动刷新：auto_refresh(包括点击频道刷新)
  加载更多刷新：load_more
  按钮刷新：button_refresh
  底部tab点击刷新：bottom_tab_click
  back回退刷新：back_refresh（第一次点回退时候的刷新）

</details>


### `content_refresh_load` — 刷新_内容渲染

- 进版版本: 5.6
- 公共属性: `common key`

**上报时机/逻辑**:

刷新接口返回后有内容曝光/内容渲染失败时上报（刷新只要page 不要from_page,module,from_module）
范围（不包括热榜）


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | 下拉刷新：swipe_down 自动刷新：auto_refresh(包括点击频道刷新) 加载更多刷新：load_more（不用上报该事件） 按钮刷新：button_refresh 底部tab点击刷新：bottom_tab_click back回退刷新：back_refresh（第一次点回退时候的刷新） |  |
| `is_success` | 是否刷新成功 | boolean | true/false |  |
| `duration` | 加载耗时(毫秒) | number | `red(二期重点)` |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  下拉刷新：swipe_down
  自动刷新：auto_refresh(包括点击频道刷新)
  加载更多刷新：load_more（不用上报该事件）
  按钮刷新：button_refresh
  底部tab点击刷新：bottom_tab_click
  back回退刷新：back_refresh（第一次点回退时候的刷新）

</details>


### `content_item_request` — 信息流_内容请求

- 进版版本: 5.6
- 公共属性: `common key`

**上报时机/逻辑**:

向服务端发起内容请求时上报，每请求一次上报一次事件


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `feed_channel` | 频道 | string |  |  |
| `item_count` | 返回条数(内容) | number |  |  |

### `content_follow` — 关注

**上报时机/逻辑**:

关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需要）


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性<br>内容通用属性 |  |  |  |
| `item_author` | 作者名 | string |  |  |
| `follow_source` | 关注来源 | string | 图文详情页：content_detail_news 短视频详情页：content_detail_video 作者详情页：main_follow_author_detail 发现_关注页：main_follow 关注推荐卡片：follow_card |  |

<details><summary>参数取值详情</summary>


**`follow_source`** (关注来源)
- 类型: string
- 取值:
  图文详情页：content_detail_news
  短视频详情页：content_detail_video
  作者详情页：main_follow_author_detail
  发现_关注页：main_follow
  关注推荐卡片：follow_card

</details>


### `content_unfollow` — 取消关注

**上报时机/逻辑**:

取消关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需要）


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性<br>内容通用属性 |  |  |  |
| `item_author` | 作者名 | string |  |  |
| `follow_source` | 关注来源 | string | 图文详情页：content_detail_news 短视频详情页：content_detail_video 作者详情页：main_follow_author_detail 发现_关注页：main_follow 关注推荐卡片：follow_card |  |

<details><summary>参数取值详情</summary>


**`follow_source`** (关注来源)
- 类型: string
- 取值:
  图文详情页：content_detail_news
  短视频详情页：content_detail_video
  作者详情页：main_follow_author_detail
  发现_关注页：main_follow
  关注推荐卡片：follow_card

</details>


### `content_channel_edit` — 编辑频道

- 公共属性: `common key`

**上报时机/逻辑**:

编辑成功时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `all_channel` | 保存时的保留channel列表 | string | ['main_follow','main_game','main_recommend'] |  |
| `removed_channel` | 移除的channel | string | ['main_zhihu','video_short','video_funny'] |  |

### `content_button_show` — 取消关注

**上报时机/逻辑**:

取消关注成功时上报（包括详情页，关注流）（只要page），（module,from_page,from_module不需要）


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性 |  | `red(二期重点)` |  |
| `item_author` | 作者名 | string |  |  |
| `follow_source` | 取消关注来源 | string | 文章详情页：content_detail 关注流_我的关注：follow_follow_user |  |

### `content_export_show` — 引流曝光

**上报时机/逻辑**:

（露出即上报，滑走再滑会，露出后继续上报）


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性、内容通用属性 |  |  |  |
| `export_type` | 引流类型 | string | 按钮：button 弹窗：window 页面浮层：page |  |

### `content_export_click` — 引流点击

**上报时机/逻辑**:

点击即上报，点击多次上报多次


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性、内容通用属性 |  |  |  |
| `export_type` | 引流类型 | string | 按钮：button 弹窗：window 页面浮层：page |  |

### `content_slide` — 屏幕滑动

**上报时机/逻辑**:

1、滑动停止时上报
2、滑动最大位置item_position变化时才上报
(优先做推荐流频道。如果可以复用，再扩展其他频道)


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key（全部要）<br>content key（全部要）` |  |  | `red(二期重点)` |  |
| `item_position` | 滑动的最大位置 | number | `red(二期重点)` 0、1、2、3、4、5.....    从0开始  （广告的位置不算） 沉浸态重点关注 |  |
| `slide_orientation` | 滑动方向 | string | `red(二期重点)` up、down |  |

### `content_item_fold_button_expose` — 详情页折叠按钮曝光，单页面只曝光1次，上下滑动不重复曝光，退出后再进入重复报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性<br>内容通用属性 | string |  |  |

### `content_item_video_over_exception` — 


_(无独立参数,仅携带公共属性)_


### `content_item_video_auto_play` — 信息流_单条内容_视频自动播放

**上报时机/逻辑**:

信息流_单条内容_视频自动播放：推荐页首条内容第一次开始自动播放时上报，下划再上划自动播放/点进视频详情页退出自动播放均不上报
信息流_单条内容_视频自动播放完成：推荐页首条内容第一次开始自动播放结束时上报，第二次及之后播放完成不上报


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key <br>content key` |  |  |  |  |
| `duration` | 时长 | number |  |  |
| `item_video_length` | 视频长度 | number | 单位毫秒 |  |
| `item_percent` | 视频播放进度/图文浏览进度 | number | 退出后记录percent，百分比例如  0/1/50/100，保留整数；多次浏览记最大值 |  |

### `url_click` — 软广链接点击

- 公共属性: `common key`

**上报时机/逻辑**:

多次点击多次上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `from_item_docid` | 软文的item_docid |  |  |  |
| `from_item_cp_name` | 软文的item_cp_name |  |  |  |

### `content_item_cover_load_fail` — 信息流_单条内容_封面加载失败

- 公共属性: `common key`

**上报时机/逻辑**:

封面加载失败时上报，不重复上报
不考虑内容是否曝光


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `error_msg` | 错误详情 | string |  |  |
| `url` | 内容url |  |  |  |

### `content_duration_v2` — 信息流时长

- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任何方式离开频道列表页上报，记录从进入频道列表页到离开频道列表页的时长；
离开频道场景：
退出频道、切换频道tab、进入详情页、退出APP（包含退出到后台）、息屏、锁屏


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `feed_channel` | 频道 | string | 具体的频道值 |  |
| `page` | 页面 | string |  |  |
| `duration_type` | 时长类型 | string | feed_channel |  |
| `duration` | 时长 | number | 从进入频道页到离开频道页的时长 单位：毫秒 |  |

### `content_duration_v2` — 信息流时长

- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任何方式离开信息流详情页（包括进入一个新的详情页时），记录从进入详情页到离开详情页的时长，同一个页面上报一次：
1、信息流详情页范围包括图文详情页、短视频详情页、小视频详情页/连播页
2、包括回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、锁屏、去到app内除详情页外其他页面
3、小视频沉浸式、短小沉浸式只需要上报一次，记录从进入沉浸式到离开沉浸式的时长


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `feed_channel` | 频道 | string | 具体的频道值 |  |
| `page` | 页面 | string |  |  |
| `duration_type` | 时长类型 | string | detail_page |  |
| `duration` | 时长 | number | 从进入详情页到离开详情页的时长 单位：毫秒 |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡、相关推荐视频插卡） false |  |

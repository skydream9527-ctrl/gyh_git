# 浏览器 - content信息流事件

> 来源 sheet: `content信息流事件` | 事件数: 45 | 参数数: 105


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `content_item_expose` | 信息流_单条内容_曝光 | 1、上报范围 A、资讯和视频各频道列表页：流内竖向的卡片、小视频滑动加载更多露出的卡片，卡片包括推荐内容、cms配置卡片… | 0 | common key, content key | 14.3.4至14.8.5 |
| 2 | `content_item_expose_noenter` | 信息流_单条内容_曝光_未进入态 | 未进入态情况下，信息流单条内容曝光时上报； 曝光逻辑与原曝光逻辑一致 | 4 | common key, content key | 14.8.6 |
| 3 | `content_item_expose_enter` | 信息流_单条内容_曝光_进入态 | 进入态情况下，信息流单条内容曝光时上报； 曝光逻辑与原曝光逻辑一致 | 6 | common key, content key | 14.8.6<br>15.6新增一个上报场景：<br>点击push内容进入详情页时，上报content_item_expose_enter<br>此时feed_channel需等于'push' |
| 4 | `content_item_click` | 信息流_单条内容_点击 | 多次点击多次上报，无去重逻辑 在列表页点击内容进入详情页，上报点击事件(click_type=general)； 针对小… | 1 | common key, content key | 14.3 |
| 5 | `content_item_click_noenter` | 信息流_单条内容_点击_未进入态 | 未进入态情况下，信息流单条内容点击时上报； 点击逻辑与原点击逻辑一致 | 4 | common key, content key | 14.8.6 |
| 6 | `content_item_click_enter` | 信息流_单条内容_点击_进入态 | 进入态情况下，信息流单条内容点击时上报； 点击逻辑与原点击逻辑一致 | 4 | common key, content key | 14.8.6 |
| 7 | `content_item_view` | 信息流_详情页_浏览 | 1、上报时机 A、用户进入详情页/联播页即打点 B、多次进入多次打点  2、上报范围：通过任意方式打开了信息流的详情页（… | 7 | common key, content key | 14.3 |
| 8 | `content_item_view_quit` | 信息流_详情页_退出 | 以任何方式离开该详情页页面： 1、退出app：回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、… | 7 | common key, content key | 14.3 |
| 9 | `content_item_negative_click` | 信息流_负反馈_点击 | 用户点击X关闭按钮，选择negative界面中任一理由成功关闭内容时上报 | 2 | common key, content key | 14.3 |
| 10 | `content_item_function_click` | 信息流_详情页更多功能_点击 | 仅图文详情页上报； 点击图文详情页右上方三个点，出现工具弹窗，点击里面的工具时上报 | 1 | common key, content key | 14.6 |
| 11 | `content_item_like` | 信息流_单条内容_点赞 | 信息流_单条内容_点赞:点赞成功时上报；不去重 （包括图文详情页；短视频详情页；小视频详情页/连播页；短视频列表页右下角… | 0 | common key, content key | 14.6 |
| 12 | `content_item_video_play` | 信息流_单条内容_视频播放 | 视频开始播放时上报 1、视频露出后第一次播放（本次操作第一次，不是生命周期内第一次）时，上报该事件。播放过程中，只要未离… | 7 | common key, content key | 14.6 |
| 13 | `content_item_video_over` | 信息流_单条内容_视频结束播放 | 离开本次播放的视频时上报，包含以下离开场景： 1、离开app：包括退后台、杀进程、切到多任务、息屏、锁屏、跳转到其他ap… | 12 | common key, content key | 14.6 |
| 14 | `content_item_video_play_minivideo` | 信息流_单条内容_视频播放_小视频 | 进入态情况下，小视频内容播放时上报； 视频播放逻辑与原有逻辑一致 | 6 | common key, content key | 14.8.6 |
| 15 | `content_item_video_failed` | 信息流_单条内容_视频播放失败 | 视频点击播放后，未成功加载时上报 | 5 | common key, content key | 16.9 |
| 16 | `content_item_video_pause` | 信息流_视频_暂停 | 仅视频内容上报（短视频&小视频） 点击暂停时上报 | 0 | common key, content key | 14.6 |
| 17 | `content_item_video_continue` | 信息流_视频_恢复 | 仅视频内容上报（短视频&小视频） 暂停状态下，点击恢复播放时上报 | 0 | common key, content key | 14.6 |
| 18 | `content_item_video_replay` | 信息流_视频_重播 | 仅视频内容上报（短视频&小视频） 重新播放时上报 | 0 | common key, content key | 14.6 |
| 19 | `content_duration` | 信息流时长 | 以任何方式离开频道列表页上报 离开频道场景：离开频道页场景 | 3 | common key, content key | 14.3 |
| 20 | `content_duration` | 信息流时长 | 以任何方式离开信息流详情页（包括进入一个新的详情页时）： 1、信息流详情页范围包括图文详情页、短视频详情页、小视频详情页… | 2 | common key, content key | 14.3 |
| 21 | `content_duration` | 信息流时长 | 以任意方式离开短视频沉浸式时上报，记录从第一条内容到离开沉浸式的时长； 离开沉浸式的方式包括： 1.  返回到列表页 2… | 2 | common key, content key | 15.6 |
| 22 | `content_duration` | 信息流时长 | 跟随content_item_video_over打点时机 | 4 | common key, content key | 14.3 |
| 23 | `content_feed_refresh` | 信息流_刷新 | 发生刷新行为并返回内容时上报 | 1 | commey_key, content key | 14.6 |
| 24 | `content_feed_refresh_action` | 信息流_刷新_行为 | 发生刷新行为时上报 | 1 | commey_key, content key | 16.7 |
| 25 | `content_feed_refresh_request` | 信息流_刷新_发起请求 | 向服务端发起刷新请求时上报 | 1 | commey_key, content key | 16.7 |
| 26 | `content_feed_refresh_failed` | 信息流_刷新_失败 | 从服务端返回刷新失败时上报 | 1 | commey_key, content key |  |
| 27 | `content_feed_more` | 信息流_加载更多 | 下滑信息流列表，“正在加载”露出时上报 | 0 | commey_key, content key | 14.6 |
| 28 | `content_enter` | 信息流_进入信息流进入态 | 信息流状态切换事件 信息流未进入态进入进入态时上报 | 0 | common key, content_key | 15.4 |
| 29 | `content_noenter` | 信息流_退出信息流进入态 | 信息流状态切换事件 进入态退出到未进入态时上报； 信息流进入态情况下点击底部"主页"按钮退出信息流进入态，处于“主页”页… | 0 | common key, content_key | 15.4 |
| 30 | `content_first_swipe_down` | 信息流_首屏第一次滑动 | 只记第一次滑动，发生的场景包括： 1. 未进入态上滑进入进入态时上报。 2.进入app默认为信息流进入态的情况下，上滑时… | 1 | common key, content_key | 15.4 |
| 31 | `content_item_viewmore_click` | 信息流_图文详情页_展开全文_点击 | 信息流图文详情页情况下，点击展开全文时上报 | 0 | common key, content key | 15.4 |
| 32 | `content_editchannel_click` | 信息流_频道编辑_点击 | 点击编辑频道按钮时上报 | 0 | common key, content key | 15.4 |
| 33 | `content_enter_comment` | 信息流_评论区_进入 | 评论区曝光时上报 1. 详情页下划进入评论区 2. 详情页点击评论icon进入评论区（图文、短视频、小视频详情页） 3.… | 1 | common key, content key | 15.6 |
| 34 | `content_exit_comment` | 信息流_评论区_退出 | 评论区消失时上报 | 1 | common key, content key |  |
| 35 | `content_topon_auto_swipe` | 信息流_置顶新闻自动吸顶 | 触发置顶新闻自动吸顶动作时上报 | 1 | common key, content key | 15.7 |
| 36 | `hot_list_item_expose` | 热榜_单条内容_曝光 | 热榜tab，热榜卡片中每条热榜内容曝光时上报 | 3 | common key, content key | 15.7 |
| 37 | `hot_list_item_click` | 热榜_单条内容_点击 | 热榜tab，热榜卡片中单条热榜内容发生点击时上报 | 3 | common key, content key | 15.7 |
| 38 | `hot_list_popup_expose` | 热榜_卡片弹窗_曝光 | 推荐tab，热榜卡片弹窗曝光时上报 | 2 | common key, content key | 15.7 |
| 39 | `hot_list_popup_click` | 热榜_卡片弹窗_点击 | 推荐tab，热榜卡片弹窗点击时上报 | 2 | common key, content key | 15.7 |
| 40 | `button_click_minivideo` | 小视频“更多”按钮点击 | 点击“更多”后弹出上报，点击几次上报几次 | 1 | common key |  |
| 41 | `newsfloat_backbutton_click` | 图文详情页浮窗_返回按钮_点击 | 图文详情页浮窗样式，包括浮窗态+展开态，点击返回按钮时上报 | 1 | common key, content key | 17.9 |
| 42 | `notification_popup_expose` | 消息通知弹窗_弹窗_曝光 | 消息通知开启引导弹窗曝光时上报 | 1 | common key, content key | 是 |
| 43 | `notification_openbuttom_click` | 消息通知弹窗_通知开启按钮_点击 | 消息通知开启引导弹窗，点击开启通知按钮时上报 | 1 | common key | 是 |
| 44 | `content_item_request_client` | 信息流_客户端发起内容请求 | 客户端每次发起请求时上报，请求一次，上报一次； 在要闻频道、推荐频道、图文详情页、小视频沉浸式、短视频详情页、首页的原生… | 0 | common key |  |
| 45 | `content_item_lag_loading` | 信息流_单条内容_卡顿加载 | 视频播放过程出现卡顿时上报，同一视频多次卡顿多次上报。 | 6 | common key, content key | 18.9 |

---

## 事件详情

### `content_item_expose` — 信息流_单条内容_曝光

- 进版版本: 14.3.4至14.8.5
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

1、上报范围
A、资讯和视频各频道列表页：流内竖向的卡片、小视频滑动加载更多露出的卡片，卡片包括推荐内容、cms配置卡片、RS
B、短视频沉浸式列表页，第一个以及后续每一个
C、图文详情页/短视频详情页：相关推荐的内容
D、小视频详情页/连播页
E、浏览器首页未进入流时曝光的内容

2、曝光逻辑（与目前o2o逻辑保持一致）
A、卡片露出1/3上报，短视频小视频与是否播放无关
B、去重逻辑：
    根据信息流卡片的appid、docid、channel（频道）、type（事件类型）查询是否打过点，打过了就不打了，本地数据库缓存666条记录
C、快速滑动：
    滑动中的卡片不上报，页面静止时上报   
D、cms配置的非内容、rs不过滤，遵循模块通用曝光逻辑（见打点规则one track接入埋点定义规范 ）


_(无独立参数,仅携带公共属性)_


### `content_item_expose_noenter` — 信息流_单条内容_曝光_未进入态

- 进版版本: 14.8.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

未进入态情况下，信息流单条内容曝光时上报；
曝光逻辑与原曝光逻辑一致


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `from_gid` | 文章id | string | （只有详情页相关阅读需要上报）文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `point_show` |  |  | `red(二期重点)` |  |

### `content_item_expose_enter` — 信息流_单条内容_曝光_进入态

- 进版版本: 14.8.6
15.6新增一个上报场景：
点击push内容进入详情页时，上报content_item_expose_enter
此时feed_channel需等于'push'
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

进入态情况下，信息流单条内容曝光时上报；
曝光逻辑与原曝光逻辑一致


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `from_gid` | 文章id | string | （只有详情页相关阅读需要上报）文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `point_show` |  |  | `red(二期重点)` |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态 false：push、推荐页插卡 |  |

<details><summary>参数取值详情</summary>


**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_item_click` — 信息流_单条内容_点击

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

多次点击多次上报，无去重逻辑
在列表页点击内容进入详情页，上报点击事件(click_type=general)；
针对小视频和短视频播放的规则：
短视频列表页，点击视频在列表页播放，上报点击事件（click_type=play)；
小视频播放，播放时长>5s时，上报点击事件（click_type=play_auto）
短视频沉浸式，播放时长>5s时，上报点击事件（click_type=play_auto)；


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `click_type` | 点击类型 | string | general：普通点击（在列表页点击进入详情页） play：视频播放（在短视频列表页播放的点击、小视频播放页播放>5s上报的点击等） |  |

<details><summary>参数取值详情</summary>


**`click_type`** (点击类型)
- 类型: string
- 取值:
  general：普通点击（在列表页点击进入详情页）
  play：视频播放（在短视频列表页播放的点击、小视频播放页播放>5s上报的点击等）

</details>


### `content_item_click_noenter` — 信息流_单条内容_点击_未进入态

- 进版版本: 14.8.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

未进入态情况下，信息流单条内容点击时上报；
点击逻辑与原点击逻辑一致


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `click_type` | 点击类型<br>（逻辑和以前的一致） | string | general：普通点击（在列表页点击进入详情页） play：视频播放（在短视频列表页播放的点击、小视频播放页播放>5s上报的点击） |  |
| `from_gid` | 文章id | string | 用户点击相关阅读进入下个详情页时上报，列表页点击不上报 |  |

<details><summary>参数取值详情</summary>


**`click_type`** (点击类型
（逻辑和以前的一致）)
- 类型: string
- 取值:
  general：普通点击（在列表页点击进入详情页）
  play：视频播放（在短视频列表页播放的点击、小视频播放页播放>5s上报的点击）

</details>


### `content_item_click_enter` — 信息流_单条内容_点击_进入态

- 进版版本: 14.8.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

进入态情况下，信息流单条内容点击时上报；
点击逻辑与原点击逻辑一致


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `click_type` | 点击类型<br>（逻辑和以前的一致） | string | general：普通点击（在列表页点击进入详情页，包括短视频沉浸式点击进入详情页） play：视频播放（在短视频列表页播放的点击） play_auto：小视频播放>5s上报的点击、短视频沉浸式播放>5s上报的点击 |  |
| `from_gid` | 文章id | string | 用户点击相关阅读进入下个详情页时上报，列表页点击不上报 |  |

<details><summary>参数取值详情</summary>


**`click_type`** (点击类型
（逻辑和以前的一致）)
- 类型: string
- 取值:
  general：普通点击（在列表页点击进入详情页，包括短视频沉浸式点击进入详情页）
  play：视频播放（在短视频列表页播放的点击）
  play_auto：小视频播放>5s上报的点击、短视频沉浸式播放>5s上报的点击

</details>


### `content_item_view` — 信息流_详情页_浏览

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

1、上报时机
A、用户进入详情页/联播页即打点
B、多次进入多次打点

2、上报范围：通过任意方式打开了信息流的详情页（图文详情页、短视频详情页、小视频详情页）
A、点击列表页的内容进入详情页
B、点击push内容直接进入详情页
C、小视频连播页切换到下一个
D、打开app即是详情页的情况：点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入、从app内其他页面进入或返回
E、不包括短视频沉浸式页面


**参数列表** (7):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `item_detail_enter_way` | 详情页进入方式 | string | from_push ：Push进入 from_third_partner：第三方app调起进入 from_homepage：首页进入 from_feed_list ：列表页点击进入 from_shortvideo_deep_list ：短视频沉浸式点击进入 from_minivideo_detail_next ：小视频连播页滑动进入 from_pic_content_detail：图文详情页推荐流进入 from_shortvideo_content_detail：短视频详情页推荐流进入 from_shortvideo_double_detail：详情页底部小视频双列流进入 from_defau… |  |
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `gray_comment_mode` | 是否评论置灰 | boolean | `red(二期重点)` true:：是 false ：否 |  |
| `gray_share_mode` | 是否分享置灰 | boolean | `red(二期重点)` true:：是 false ：否 |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡） false |  |

<details><summary>参数取值详情</summary>


**`item_detail_enter_way`** (详情页进入方式)
- 类型: string
- 取值:
  from_push ：Push进入
  from_third_partner：第三方app调起进入
  from_homepage：首页进入
  from_feed_list ：列表页点击进入
  from_shortvideo_deep_list ：短视频沉浸式点击进入
  from_minivideo_detail_next ：小视频连播页滑动进入
  from_pic_content_detail：图文详情页推荐流进入
  from_shortvideo_content_detail：短视频详情页推荐流进入
  from_shortvideo_double_detail：详情页底部小视频双列流进入
  from_default：默认窗口打开

**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_item_view_quit` — 信息流_详情页_退出

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任何方式离开该详情页页面：
1、退出app：回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、锁屏
2、去往浏览器其他页面（包括列表页、其他内容的详情页）


**参数列表** (7):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 总浏览时长 | number | 从进入详情页到离开详情页的时长 单位：毫秒 查询时需限定：时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |
| `from_gid` | 相关阅读来源文章id | string | 用户点击相关阅读进入下个详情页时上报，列表页点击不上报 |  |
| `percent` | 文章阅读进度 | string | 【屏幕展现文章长度/以文章总长度计算*100】取整，仅限图文详情页上报，只是图文正文，不考虑相关推荐 |  |
| `point_show` |  |  | `red(二期重点)` video_duration_0：时长为0的上报 |  |
| `point_page` |  |  | `red(二期重点)` video_detail：短视频详情页---用来过滤play_duration小于100毫秒的case |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡） false |  |

<details><summary>参数取值详情</summary>


**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_item_negative_click` — 信息流_负反馈_点击

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

用户点击X关闭按钮，选择negative界面中任一理由成功关闭内容时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `negative_type` | 反馈类型 | string | rubbish：垃圾内容 repeat：推荐重复 shield：屏蔽 blacklist：拉黑 dislike：不感兴趣 frequent：出现过于频繁 bad：内容质量差 report：举报 |  |
| `negative_info` | 反馈明细 | string | 提交的具体的内容： 屏蔽的具体tag 拉黑的作者 垃圾内容的关键词（重复、标题党）等 |  |

<details><summary>参数取值详情</summary>


**`negative_type`** (反馈类型)
- 类型: string
- 取值:
  rubbish：垃圾内容
  repeat：推荐重复
  shield：屏蔽
  blacklist：拉黑
  dislike：不感兴趣
  frequent：出现过于频繁
  bad：内容质量差
  report：举报

</details>


### `content_item_function_click` — 信息流_详情页更多功能_点击

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

仅图文详情页上报；
点击图文详情页右上方三个点，出现工具弹窗，点击里面的工具时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能类型 | string | mode：夜间模式 nophoto：智能无图 close_nophoto：关闭智能无图 collect:收藏 uncollect:取消收藏 refresh:刷新 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能类型)
- 类型: string
- 取值:
  mode：夜间模式
  nophoto：智能无图
  close_nophoto：关闭智能无图
  collect:收藏
  uncollect:取消收藏
  refresh:刷新

</details>


### `content_item_like` — 信息流_单条内容_点赞

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

信息流_单条内容_点赞:点赞成功时上报；不去重 （包括图文详情页；短视频详情页；小视频详情页/连播页；短视频列表页右下角点击弹窗出现的点赞按钮；短视频沉浸式右下角点赞按钮、右下角点击弹窗出现的点赞按钮）
信息流_单条内容_取消点赞:取消点赞成功时；不去重 （包括图文详情页；短视频详情页；小视频详情页/连播页；短视频列表页右下角点击弹窗出现的点赞按钮；短视频沉浸式右下角点赞按钮、右下角点击弹窗出现的点赞按钮）
信息流_单条内容_分享:点击具体分享按钮时；不去重 （包括图文详情页；短视频详情页上下两个分享；短视频列表页右下角点击弹窗出现的更多按钮里；短视频沉浸式右下角点击弹窗出现的更多按钮里）
信息流_单条内容_评论:评论请求成功时上报；不去重（包括图文、短视频、小视频详情页）
信息流_单条内容_收藏:收藏成功时上报；不去重 （包括图文详情页；短视频列表页右下角点击弹窗出现的更多按钮里；短视频沉浸式右下角点击弹窗出现的更多按钮里）
信息流_单条内容_取消收藏:取消收藏成功时上报；不去重 （包括图文详情页；短视频列表页右下角点击弹窗出现的更多按钮里；短视频沉浸式右下角点击弹窗出现的更多按钮里）


_(无独立参数,仅携带公共属性)_


### `content_item_video_play` — 信息流_单条内容_视频播放

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

视频开始播放时上报
1、视频露出后第一次播放（本次操作第一次，不是生命周期内第一次）时，上报该事件。播放过程中，只要未离开该视频，暂停后恢复、前后拖动进度条，不重新上报事件。
2、短视频列表页、短视频详情页视频播放进度100%后视频停止，若手动点击重播，需重新上报事件。短视频手动重播play、over上报逻辑 
3、小视频播放期间只要不离开此视频，暂停、恢复、自动重播，均不重新上报事件。
4、同一个视频，一旦离开该视频，再次进入该视频产生的播放需重新上报事件。
5、离开该视频的场景，参见content_item_video_over事件上报场景。


**参数列表** (7):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `item_video_autoplay` | 视频是否自动播放 | boolean | true ： 是 false：否 |  |
| `item_video_switch_way` | 视频切换方式 | string | 非切换导致的播放值为空： 手动上滑切换  自动切换 |  |
| `item_video_length` | 视频长度（视频本身的时长） | number | 单位：秒 |  |
| `root_gid` | 沉浸态首个文章id | string | 沉浸式及小视频内流从第二个播放内容开始之后每个内容都需要记录此值，值为第一个内容的id |  |
| `from_gid` | 文章id | string | （只有详情页相关阅读需要上报）文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡） false |  |

<details><summary>参数取值详情</summary>


**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_item_video_over` — 信息流_单条内容_视频结束播放

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

离开本次播放的视频时上报，包含以下离开场景：
1、离开app：包括退后台、杀进程、切到多任务、息屏、锁屏、跳转到其他app。
2、离开该页面：切换到其他内容页面、广告详情页、我的页面、多窗口页面等；切换到其他频道、信息流未进入态；列表页进入详情页、详情页返回到列表页等。
3、短视频详情页播放：短视频手动重播play、over上报逻辑 
  ①播放过程中（进度未达到100%），回到列表页、进入其他内容详情页、进入广告详情页、离开app时，上报该事件。
  ②播放进度100%时，上报该事件。
4、短视频列表页播放：短视频手动重播play、over上报逻辑 
  ①播放过程中（进度未达到100%），滑动让此视频离开屏幕、播放上一个/下一个短视频、刷新、切换频道、进入详情页、切换到未进入态、离开app时，上报该事件
  ②播放进度100%时，上报该事件。
5、短视频沉浸式页播放：
  ①播放过程中，滑动让此视频离开屏幕、播放上一个/下一个短视频、刷新、进入详情页、返回到列表页，离开app时，上报该事件。
  ②播放进度100%，自动播放下一个视频时，上报此条视频的该事件。
6、小视频：滑动播放上一个/下一个小视频、返回到列表页、离开app时，上报该事件。


**参数列表** (12):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `item_video_autoplay` | 视频是否自动播放 | boolean | true ： 是 false：否 |  |
| `item_video_switch_way` | 视频切换方式 | string | 非切换导致的播放值为空： 手动上滑切换  自动切换 |  |
| `item_video_length` | 视频长度（视频本身的时长） | number | 单位：秒 |  |
| `play_duration` | 播放时长 | number | 单位：毫秒 load和暂停时间不计入、拖动进度条也不计入，记录真实播放时长 查询时需限定：时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |
| `play_number` | 播放次数 | number | 若播放时长<=视频时长，则播放次数为1 若播放时长>视频时长，则播放次数为播放时长/视频时长取整+1 例： 若视频时长为10s 若播放时长为9s，则播放次数为1 若播放时长为35s，则播放次数为4 |  |
| `item_percent` | 视频播放进度 | number | 退出后记录percent，百分比例如  0/1/50/100，保留整数，多次播放记最大值 进度条播放长度 / 视频本身长度 |  |
| `root_gid` | 沉浸态首个文章id | string | 沉浸式及小视频内流从第二个播放内容开始之后每个内容都需要记录此值，值为第一个内容的id |  |
| `point_show` |  |  | video_duration_0：时长为0 fail：小视频播放失败 |  |
| `point_page` |  |  | video_detail：短视频详情页---用来过滤play_duration小于100毫秒的case |  |
| `from_gid` | 文章id | string | （只有详情页相关阅读需要上报）文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态（push、推荐页插卡） false |  |

<details><summary>参数取值详情</summary>


**`play_duration`** (播放时长)
- 类型: number
- 取值:
  单位：毫秒
  load和暂停时间不计入、拖动进度条也不计入，记录真实播放时长
  查询时需限定：时长>0&时长<86400000(单位毫秒)
  以排除异常值

**`play_number`** (播放次数)
- 类型: number
- 取值:
  若播放时长<=视频时长，则播放次数为1
  若播放时长>视频时长，则播放次数为播放时长/视频时长取整+1
  例：
  若视频时长为10s
  若播放时长为9s，则播放次数为1
  若播放时长为35s，则播放次数为4

**`item_percent`** (视频播放进度)
- 类型: number
- 取值:
  退出后记录percent，百分比例如  0/1/50/100，保留整数，多次播放记最大值
  进度条播放长度 / 视频本身长度

**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_item_video_play_minivideo` — 信息流_单条内容_视频播放_小视频

- 进版版本: 14.8.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

进入态情况下，小视频内容播放时上报；
视频播放逻辑与原有逻辑一致


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `item_video_autoplay` | 视频是否自动播放 | boolean | true ： 是 false：否 |  |
| `item_video_switch_way` | 视频切换方式 | string | 非切换导致的播放值为空： 手动上滑切换  自动切换 |  |
| `item_video_length` | 视频长度（视频本身的时长） | number | 单位：秒 |  |
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `root_gid` | 沉浸态首个文章id | string | 沉浸式及小视频内流从第二个播放内容开始之后每个内容都需要记录此值，值为第一个内容的id |  |

### `content_item_video_failed` — 信息流_单条内容_视频播放失败

- 进版版本: 16.9
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

视频点击播放后，未成功加载时上报


**参数列表** (5):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `item_video_autoplay` | 视频是否自动播放 | boolean | true ： 是 false：否 |  |
| `item_video_switch_way` | 视频切换方式 | string | 非切换导致的播放值为空： 手动上滑切换  自动切换 |  |
| `item_video_length` | 视频长度（视频本身的时长） | number | 单位：秒 |  |
| `fail_reason` | 视频播放失败报错信息 | string | 视频解码失败、无法连接等报错信息 |  |
| `codec_type` | 视频格式 | string | h265，h264等 |  |

### `content_item_video_pause` — 信息流_视频_暂停

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

仅视频内容上报（短视频&小视频）
点击暂停时上报


_(无独立参数,仅携带公共属性)_


### `content_item_video_continue` — 信息流_视频_恢复

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

仅视频内容上报（短视频&小视频）
暂停状态下，点击恢复播放时上报


_(无独立参数,仅携带公共属性)_


### `content_item_video_replay` — 信息流_视频_重播

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

仅视频内容上报（短视频&小视频）
重新播放时上报


_(无独立参数,仅携带公共属性)_


### `content_duration` — 信息流时长

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任何方式离开频道列表页上报
离开频道场景：离开频道页场景


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | feed_channel |  |
| `duration` | 时长 | number | 从进入频道页到离开频道页的时长 单位：毫秒 查询时需限定： 时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |
| `impid` |  |  |  |  |

### `content_duration` — 信息流时长

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任何方式离开信息流详情页（包括进入一个新的详情页时）：
1、信息流详情页范围包括图文详情页、短视频详情页、小视频详情页/连播页
2、包括回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、锁屏、去到app内除详情页外其他页面


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | detail_page |  |
| `duration` | 时长 | number | 从进入详情页到离开详情页的时长 单位：毫秒 查询时需限定： 时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |

### `content_duration` — 信息流时长

- 进版版本: 15.6
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

以任意方式离开短视频沉浸式时上报，记录从第一条内容到离开沉浸式的时长；
离开沉浸式的方式包括：
1.  返回到列表页
2. 进入详情页
3. 进入广告
4. 退出app：回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、锁屏、去到app内除详情页外其他页面


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | immersion |  |
| `duration` | 时长 | number | 进入沉浸式到离开沉浸式的时长 单位：毫秒 查询时需限定： 时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |

### `content_duration` — 信息流时长

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

跟随content_item_video_over打点时机


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | video_play |  |
| `duration` | 时长 | number | 视频开始播放到结束播放的时长（load和暂停时间不计入、拖动进度条也不计入，记录真实播放时长） 单位：毫秒 查询时需限定： 时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |
| `root_cp_name` | 沉浸态首个内容的内容提供方标识 | string | `red(二期重点)` cn-toutiao    cn-yidian-news-v2     cn-renminwang     cn-baidu-feeds     cn-yidian-video     cn-sina-browser     cn-fenghuang-browser     cn-baidu |  |
| `is_click_content_enter` | 是否点击内容进入沉浸态 | boolean | `red(二期重点)` true：点击内容进入沉浸态 false：push、推荐页插卡 |  |

<details><summary>参数取值详情</summary>


**`duration`** (时长)
- 类型: number
- 取值:
  视频开始播放到结束播放的时长（load和暂停时间不计入、拖动进度条也不计入，记录真实播放时长）
  单位：毫秒
  查询时需限定：
  时长>0&时长<86400000(单位毫秒)
  以排除异常值

**`root_cp_name`** (沉浸态首个内容的内容提供方标识)
- 类型: string
- 取值:
  cn-toutiao   
  cn-yidian-news-v2    
  cn-renminwang    
  cn-baidu-feeds    
  cn-yidian-video    
  cn-sina-browser    
  cn-fenghuang-browser    
  cn-baidu

</details>


### `content_feed_refresh` — 信息流_刷新

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `commey_key`, `content key`

**上报时机/逻辑**:

发生刷新行为并返回内容时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | pulling_down：下拉刷新信息流 click_tab_home：点击主页tab click_tab_video：点击视频tab auto_refresh：自动刷新 back：返回刷新 |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  pulling_down：下拉刷新信息流
  click_tab_home：点击主页tab
  click_tab_video：点击视频tab
  auto_refresh：自动刷新
  back：返回刷新

</details>


### `content_feed_refresh_action` — 信息流_刷新_行为

- 进版版本: 16.7
- 公共属性: `commey_key`, `content key`

**上报时机/逻辑**:

发生刷新行为时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | pulling_down：下拉刷新信息流 click_tab_home:点击主页tab auto_refresh:自动刷新 back:返回刷新 |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  pulling_down：下拉刷新信息流
  click_tab_home:点击主页tab
  auto_refresh:自动刷新
  back:返回刷新

</details>


### `content_feed_refresh_request` — 信息流_刷新_发起请求

- 进版版本: 16.7
- 公共属性: `commey_key`, `content key`

**上报时机/逻辑**:

向服务端发起刷新请求时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | pulling_down：下拉刷新信息流 click_tab_home:点击主页tab auto_refresh:自动刷新 back:返回刷新 |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  pulling_down：下拉刷新信息流
  click_tab_home:点击主页tab
  auto_refresh:自动刷新
  back:返回刷新

</details>


### `content_feed_refresh_failed` — 信息流_刷新_失败

- 公共属性: `commey_key`, `content key`

**上报时机/逻辑**:

从服务端返回刷新失败时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `refresh_type` | 刷新方式 | string | pulling_down：下拉刷新信息流 click_tab_home:点击主页tab auto_refresh:自动刷新 back:返回刷新 |  |

<details><summary>参数取值详情</summary>


**`refresh_type`** (刷新方式)
- 类型: string
- 取值:
  pulling_down：下拉刷新信息流
  click_tab_home:点击主页tab
  auto_refresh:自动刷新
  back:返回刷新

</details>


### `content_feed_more` — 信息流_加载更多

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `commey_key`, `content key`

**上报时机/逻辑**:

下滑信息流列表，“正在加载”露出时上报


_(无独立参数,仅携带公共属性)_


### `content_enter` — 信息流_进入信息流进入态

- 进版版本: 15.4
- 公共属性: `common key`, `content_key`

**上报时机/逻辑**:

信息流状态切换事件
信息流未进入态进入进入态时上报


_(无独立参数,仅携带公共属性)_


### `content_noenter` — 信息流_退出信息流进入态

- 进版版本: 15.4
- 公共属性: `common key`, `content_key`

**上报时机/逻辑**:

信息流状态切换事件
进入态退出到未进入态时上报；
信息流进入态情况下点击底部"主页"按钮退出信息流进入态，处于“主页”页面时上报


_(无独立参数,仅携带公共属性)_


### `content_first_swipe_down` — 信息流_首屏第一次滑动

- 进版版本: 15.4
- 公共属性: `common key`, `content_key`

**上报时机/逻辑**:

只记第一次滑动，发生的场景包括：
1. 未进入态上滑进入进入态时上报。
2.进入app默认为信息流进入态的情况下，上滑时上报。（包含进入态下的资讯tab、视频tab以及视频tab改版前的频道列表页）
如果两种场景都有的话，则只上报第一次滑动
客户端怎么界定滑动：无论滑动大小，只要页面发生变化，都算滑动


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `max_position` | 滑动后最大内容曝光位置 | number | 产生第一次滑动操作的行为后，记录最大内容曝光位置 |  |

### `content_item_viewmore_click` — 信息流_图文详情页_展开全文_点击

- 进版版本: 15.4
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

信息流图文详情页情况下，点击展开全文时上报


_(无独立参数,仅携带公共属性)_


### `content_editchannel_click` — 信息流_频道编辑_点击

- 进版版本: 15.4
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

点击编辑频道按钮时上报


_(无独立参数,仅携带公共属性)_


### `content_enter_comment` — 信息流_评论区_进入

- 进版版本: 15.6
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

评论区曝光时上报
1. 详情页下划进入评论区
2. 详情页点击评论icon进入评论区（图文、短视频、小视频详情页）
3. 短视频沉浸式进入详情页直接展示评论区
4. 点击评论框到评论区（需评论区真实曝光给用户时上报）


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `enter_comment_way` | 进入评论区的方式 | string | slide：详情页下划进入评论区 icon：详情页点击评论icon进入评论区(图文、短视频、小视频) default：短视频沉浸式进入详情页直接展示评论区 click: 点击评论框到评论区（需评论区真实曝光给用户时上报） |  |

<details><summary>参数取值详情</summary>


**`enter_comment_way`** (进入评论区的方式)
- 类型: string
- 取值:
  slide：详情页下划进入评论区
  icon：详情页点击评论icon进入评论区(图文、短视频、小视频)
  default：短视频沉浸式进入详情页直接展示评论区
  click: 点击评论框到评论区（需评论区真实曝光给用户时上报）

</details>


### `content_exit_comment` — 信息流_评论区_退出

- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

评论区消失时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 评论区停留时长 |  |  |  |

### `content_topon_auto_swipe` — 信息流_置顶新闻自动吸顶

- 进版版本: 15.7
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

触发置顶新闻自动吸顶动作时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `swipe_case` | 置顶新闻自动吸顶的场景 | string | content_enter：首屏非进入态-->进入态时上报 back_news：从图文详情页返回首页，自动吸顶时上报 back_video：从视频详情页返回首页，自动吸顶时上报 back_ads：从广告详情页返回首页，自动吸顶时上报 back_pull：从插卡新样式返回首页，自动吸顶时上报 |  |

<details><summary>参数取值详情</summary>


**`swipe_case`** (置顶新闻自动吸顶的场景)
- 类型: string
- 取值:
  content_enter：首屏非进入态-->进入态时上报
  back_news：从图文详情页返回首页，自动吸顶时上报
  back_video：从视频详情页返回首页，自动吸顶时上报
  back_ads：从广告详情页返回首页，自动吸顶时上报
  back_pull：从插卡新样式返回首页，自动吸顶时上报

</details>


### `hot_list_item_expose` — 热榜_单条内容_曝光

- 进版版本: 15.7
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

热榜tab，热榜卡片中每条热榜内容曝光时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_item_position` | 模块内位置 | number | 在榜单内容刷新的情况下记录每条内容在热榜卡片的第几个 0、1、2、3...... |  |
| `item_title` | item标题 | string | 展示的标题 |  |
| `item_mark` | 内容标识 | string | 爆 热 火 新 |  |

### `hot_list_item_click` — 热榜_单条内容_点击

- 进版版本: 15.7
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

热榜tab，热榜卡片中单条热榜内容发生点击时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_item_position` | 模块内位置 | number | 在榜单内容刷新的情况下记录每条内容在热榜卡片的第几个 0、1、2、3...... |  |
| `item_title` | item标题 | string | 点击的标题 |  |
| `item_mark` | 内容标识 | string | 爆 热 火 新 |  |

### `hot_list_popup_expose` — 热榜_卡片弹窗_曝光

- 进版版本: 15.7
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

推荐tab，热榜卡片弹窗曝光时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `hot_list_card_type` | 卡片类型 | string | 1：热榜卡片_自动推送 0：热榜卡片_运营 |  |
| `item_title` | item标题 | string | 展示的标题 |  |

### `hot_list_popup_click` — 热榜_卡片弹窗_点击

- 进版版本: 15.7
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

推荐tab，热榜卡片弹窗点击时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `hot_list_card_type` | 卡片类型 | string | 1：热榜卡片_自动推送 0：热榜卡片_运营 |  |
| `item_title` | item标题 | string | 点击的标题 |  |

### `button_click_minivideo` — 小视频“更多”按钮点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击“更多”后弹出上报，点击几次上报几次


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `button_type` | 按钮类型 | string | no_interest  //不感兴趣 report //投诉举报 press_2.0X  //长按2.0X 0.5X  //倍速按钮0.5X 1.0X  //倍速按钮1.0X 1.5X  //倍速按钮1.5X 2.0X  //倍速按钮2.0X |  |

<details><summary>参数取值详情</summary>


**`button_type`** (按钮类型)
- 类型: string
- 取值:
  no_interest  //不感兴趣
  report //投诉举报
  press_2.0X  //长按2.0X
  0.5X  //倍速按钮0.5X
  1.0X  //倍速按钮1.0X
  1.5X  //倍速按钮1.5X
  2.0X  //倍速按钮2.0X

</details>


### `newsfloat_backbutton_click` — 图文详情页浮窗_返回按钮_点击

- 进版版本: 17.9
- 无痕模式上报: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

图文详情页浮窗样式，包括浮窗态+展开态，点击返回按钮时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `back_type` | topbutton：浮窗顶部返回按钮<br>floatball：悬浮球<br>mask：顶部蒙层<br>back：左滑back或物理键返回 |  |  |  |

### `notification_popup_expose` — 消息通知弹窗_弹窗_曝光

- 进版版本: 是
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

消息通知开启引导弹窗曝光时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `type` | 弹窗类型 | string | feedflow：弹窗样式1 authorfollow：弹窗样式2 |  |

### `notification_openbuttom_click` — 消息通知弹窗_通知开启按钮_点击

- 进版版本: 是
- 公共属性: `common key`

**上报时机/逻辑**:

消息通知开启引导弹窗，点击开启通知按钮时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `type` | 弹窗类型 | string | feedflow：弹窗样式1 authorfollow：弹窗样式2 |  |

### `content_item_request_client` — 信息流_客户端发起内容请求

- 公共属性: `common key`

**上报时机/逻辑**:

客户端每次发起请求时上报，请求一次，上报一次；
在要闻频道、推荐频道、图文详情页、小视频沉浸式、短视频详情页、首页的原生垂类频道（视频、小视频、热榜、娱乐等)、小视频沉浸态包括短小融合这几个场景上报


_(无独立参数,仅携带公共属性)_


### `content_item_lag_loading` — 信息流_单条内容_卡顿加载

- 进版版本: 18.9
- 公共属性: `common key`, `content key`

**上报时机/逻辑**:

视频播放过程出现卡顿时上报，同一视频多次卡顿多次上报。


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `scene` | 视频播放场景 | string | 场景： flow：信息流 videoTab：视频 tabdetailSlide：详情页上滑 inflow：流内 push：push other: 其他场景 |  |
| `page` | 页面 | string |  |  |
| `channel` | 频道 | string |  |  |
| `item_docid` | 文章id | string |  |  |
| `item_type` | 文章类型 | string |  |  |
| `item_alg_source` | 内容算法来源 | string |  |  |

<details><summary>参数取值详情</summary>


**`scene`** (视频播放场景)
- 类型: string
- 取值:
  场景：
  flow：信息流
  videoTab：视频
  tabdetailSlide：详情页上滑
  inflow：流内
  push：push
  other: 其他场景

</details>


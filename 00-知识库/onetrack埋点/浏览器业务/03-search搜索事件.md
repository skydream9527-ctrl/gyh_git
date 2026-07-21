# 浏览器 - search搜索事件

> 来源 sheet: `search搜索事件` | 事件数: 20 | 参数数: 119


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `search` | 搜索 | 触发搜索，搜索结果页开始加载时。 1、sug页的不上报 2、网址搜索不上报 3、第三方搜索框进行的搜索不上报search… | 7 | common key | 14.3 |
| 2 | `search_website` | 搜索网页访问 | 网页访问(打开一个网页)时,过滤符合搜索条件的网址上报 | 3 | common key |  |
| 3 | `search_security` | 搜索_安全网址 | 请求安全网址时 | 20 | common key |  |
| 4 | `search_engine_switch` | 切换搜索引擎 | 切换成功时,点击搜索引擎icon且做了更改上报，未更改不上报 | 5 | common key | 14.3 |
| 5 | `search_homepage_expose` | 搜索首页曝光 | 只要进入或回到搜索首页都记，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他ap… | 2 | common key | 14.3 |
| 6 | `search_homepage_module_expose` | 搜索首页模块曝光 | 1、item漏出三分之一记曝光（图片icon+文字一起算三分之一） 2、我的书签最多曝光前20个 3、如下不曝光：未在视… | 9 | common key | 14.3 |
| 7 | `search_homepage_module_click` | 搜索首页模块点击 | 无去重逻辑 多次点击多次上报 删除、清空、隐藏、展示操作后引起了位置的变动，后续的位置以真实位置为准上报，前面的已经打过… | 10 | common key | 14.3 |
| 8 | `search_sugpage_expose` | 搜索sug页曝光 | 1、sug页每刷新一次即上报一次，即考虑连续输入 2、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回… | 2 | common key | 14.3 |
| 9 | `search_sugpage_module_expose` | 搜索sug页模块曝光 | 前端上报 1、item漏出三分之一记曝光（图片icon+文字一起算三分之一） 2、我的书签最多曝光前20个 3、如下不曝… | 15 | common key | 14.3 |
| 10 | `search_sugpage_module_click` | 搜索sug页模块点击 | 前端上报 无去重逻辑 多次点击多次上报 | 16 | common key | 14.3 |
| 11 | `search_sugpage_module_expose` | 搜索sug页模块曝光 | 1、sug页每刷新一次即上报一次，即考虑连续输入 2、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回… | 4 | common key | 14.3 |
| 12 | `search_sugpage_module_click` | 搜索sug页模块点击 | 无去重逻辑 多次点击多次上报 | 4 | common key | 14.3 |
| 13 | `search_scan_click` | 搜索框扫一扫点击 | 1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页、搜索sug页、搜索结果页 | 1 | common key | 14.6 |
| 14 | `search_voice_click` | 搜索框语音搜索点击 | 1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页、搜索sug页、搜索结果页 | 1 | common key | 14.6 |
| 15 | `search_preset_query_expose` | 搜索框提示词曝光 | 1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页 2、首页、信息流资讯各频道页、宫格页面下15秒内同一个que… | 4 | common key | 14.6 |
| 16 | `search_preset_query_click` | 搜索框提示词点击 | 1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页 2、产生了真正的搜索时上报 | 9 | common key | 14.6 |
| 17 | `third_page_back_expose` | 第三方吊起详情页_返回按钮曝光 | 三方调起详情页时有按钮曝光 | 1 | common key |  |
| 18 | `baidu_sdk_exit` | 百度sdk退出 | 离开百度sdk时上报 | 2 | commen key |  |
| 19 | `baidu_applet_sling` | 小程序调起 | 调起百度小程序时上报 | 1 | commen key |  |
| 20 | `appbundle_download` | appbundle 安装 | appbundle开始下载时上报 | 3 | commen key |  |

---

## 事件详情

### `search` — 搜索

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

触发搜索，搜索结果页开始加载时。
1、sug页的不上报
2、网址搜索不上报
3、第三方搜索框进行的搜索不上报search埋点


**参数列表** (7):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `searchengine_id` | 搜索引擎配置模版 | string | cms中配置的引擎模版 |  |
| `searchengine_channelid` | 搜索引擎渠道号 | string | 百度：from参数（1012852u等） 360：srcg参数（ff_xiaomi_4等） 搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等） 头条：original_source参数（21等） 神马：from参数（wy974204） |  |
| `search_enter_way` | 进入搜索的方式 | string | 信息流 首页 第三方app调起 rs 名站 长按菜单键 底tab搜索 下滑（简洁版下） |  |
| `search_way` | 搜索方式 | string | 搜索框输入 sugword 历史记录 搜索发现 预置词 搜索框提示词 切换搜索引擎 文末rs 阅后rs |  |
| `query` | 搜索词 | string |  |  |
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |

<details><summary>参数取值详情</summary>


**`searchengine_channelid`** (搜索引擎渠道号)
- 类型: string
- 取值:
  百度：from参数（1012852u等）
  360：srcg参数（ff_xiaomi_4等）
  搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等）
  头条：original_source参数（21等）
  神马：from参数（wy974204）

</details>


### `search_website` — 搜索网页访问

- 公共属性: `common key`

**上报时机/逻辑**:

网页访问(打开一个网页)时,过滤符合搜索条件的网址上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `searchengine_channelid` | 搜索引擎渠道号 | string | 百度：from参数（1012852u等） 360：srcg参数（ff_xiaomi_4等） 搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等） 头条：original_source参数（21等） 神马：from参数（wy974204） |  |
| `query` | 搜索词 | string | 百度：word参数 360：q参数 搜狗：keyword参数 头条：keyword参数 神马：q参数 |  |
| `domain` | 域名 | string | 百度：m.baidu.com |  |

<details><summary>参数取值详情</summary>


**`searchengine_channelid`** (搜索引擎渠道号)
- 类型: string
- 取值:
  百度：from参数（1012852u等）
  360：srcg参数（ff_xiaomi_4等）
  搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等）
  头条：original_source参数（21等）
  神马：from参数（wy974204）

</details>


### `search_security` — 搜索_安全网址

- 公共属性: `common key`

**上报时机/逻辑**:

请求安全网址时


**参数列表** (20):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `searchengine_name` | 搜索引擎名称 | string | baidu 360 douyin |  |
| `from_page` | 上级页面 | string | 从浏览器首页搜索框产生的搜索，from_page=browser 从搜索结果页换query产生的搜索，from_page=search_result |  |
| `is_baidu_sdk` | 是否百度sdk | boolean | 0：原h5；1：百度sdk |  |
| `searchengine_id` | 搜索引擎配置模版 | string | cms中配置的引擎模版 |  |
| `searchengine_channelid` | 搜索引擎渠道号 | string | 百度：from参数（1012852u等） 360：srcg参数（ff_xiaomi_4等） 搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等） 头条：original_source参数（21等） 神马：from参数（wy974204） |  |
| `search_enter_way` | 进入搜索的方式 | string | 信息流 首页 第三方app调起 rs 名站 长按菜单键 底tab搜索 下滑（简洁版下） |  |
| `search_way` | 搜索方式 | string | 搜索框输入 sugword 历史记录 搜索发现 预置词 搜索框提示词 文末rs 切换搜索引擎 阅后rs |  |
| `query` | 搜索词 | string |  |  |
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |
| `device_id` | device_id | string |  |  |
| `network` | 网络类型 | string | WIFI/5G/4G/3G/2G/ETHERNET/NONE/UNKNOWN |  |
| `app_version` | APP版本 | string |  |  |
| `os_version` | 系统版本 | string |  |  |
| `stable` | 版本类别 | string |  |  |
| `miui_version` | MIUI版本 | string |  |  |
| `model_name` | 设备名称 | string |  |  |
| `androidid` | 安卓_id | string |  |  |
| `frontState` | 当前是否前台 | string | true  false |  |

<details><summary>参数取值详情</summary>


**`from_page`** (上级页面)
- 类型: string
- 取值:
  从浏览器首页搜索框产生的搜索，from_page=browser
  从搜索结果页换query产生的搜索，from_page=search_result

**`searchengine_channelid`** (搜索引擎渠道号)
- 类型: string
- 取值:
  百度：from参数（1012852u等）
  360：srcg参数（ff_xiaomi_4等）
  搜狗：bid参数或pid参数（sogou-mobp-6018df1842f7130f等）
  头条：original_source参数（21等）
  神马：from参数（wy974204）

</details>


### `search_engine_switch` — 切换搜索引擎

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

切换成功时,点击搜索引擎icon且做了更改上报，未更改不上报


**参数列表** (5):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `searchengine_id` | 当前搜索引擎配置模版 | string |  |  |
| `new_searchengine_id` | 搜索引擎配置新模版 | string |  |  |
| `searchengine_name` | 各个场景当前默认的搜索引擎 | string |  |  |
| `new_searchengine_name` | 切换成新的搜索引擎的名字 | string |  |  |
| `switch_source` | 切换来源 | string | search_engine_window：切换搜索引擎弹窗 all_engine_window：更多搜索引擎弹窗 |  |

### `search_homepage_expose` — 搜索首页曝光

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

只要进入或回到搜索首页都记，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入）


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 首页类型 | string | from_desktop（针对具备应用建议和热榜功能的首页） new_search_homepage：新版搜索首页 old_search_homepage:旧版搜索首页 |  |
| `search_homepage_enter_way` | 进入搜索首页的方式 | string | home_page：首页搜索框 feed：资讯信息流 search_detail_page：sug页返回 web_page：普通网页（包括点击宫格名站里的百度） menu：长按菜单 gongge：宫格上的搜索框 desktop：桌面 down：下滑（简洁版下） search_back：搜索返回 |  |

<details><summary>参数取值详情</summary>


**`page_type`** (首页类型)
- 类型: string
- 取值:
  from_desktop（针对具备应用建议和热榜功能的首页）
  new_search_homepage：新版搜索首页
  old_search_homepage:旧版搜索首页

**`search_homepage_enter_way`** (进入搜索首页的方式)
- 类型: string
- 取值:
  home_page：首页搜索框
  feed：资讯信息流
  search_detail_page：sug页返回
  web_page：普通网页（包括点击宫格名站里的百度）
  menu：长按菜单
  gongge：宫格上的搜索框
  desktop：桌面
  down：下滑（简洁版下）
  search_back：搜索返回

</details>


### `search_homepage_module_expose` — 搜索首页模块曝光

- 进版版本: 14.3
- 无痕模式上报: 否
- 公共属性: `common key`

**上报时机/逻辑**:

1、item漏出三分之一记曝光（图片icon+文字一起算三分之一）
2、我的书签最多曝光前20个
3、如下不曝光：未在视线范围内出现的（包括键盘挡住的）、隐藏了的卡片、未展开的搜索历史
4、如下反复操作不重复曝光：页面反复上下滑动、展开收起（搜索历史）、隐藏展开（我的书签和经常访问）、键盘收起弹出、
5、滑动过程中不曝光，停止了才曝光
6、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入）
7、无痕模式下不曝光


**参数列表** (9):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 首页类型 | string | from_desktop（针对具备应用建议和热榜功能的首页） new_search_homepage：新版搜索首页 old_search_homepage:旧版搜索首页 |  |
| `search_homepage_enter_way` | 进入搜索首页的方式 | string | home_page：首页搜索框 feed：资讯信息流 search_detail_page：sug页返回 web_page：普通网页（包括点击宫格名站里的百度） menu：长按菜单 gongge：宫格上的搜索框 desktop：桌面 down：下滑（简洁版下） search_back：搜索返回 |  |
| `card_type` | 卡片类型 | string | 网址 剪贴板 搜索历史 我的书签（只打前20个） 经常访问 应用建议 今日热搜 预置词 搜索发现 小说榜单 猜你想搜 |  |
| `novels_list_type` | 小说热榜类型 | string | 当模块类型为小说榜单时上报，否则为空 boy：男生 girl：女生 |  |
| `card_position` | 模块位置 | number | 0、1、2…… |  |
| `item_title` | item标题 | string | 网址为网址的标题 剪贴板为复制的内容 搜索历史为搜索词 我的书签为每条书签的标题 经常访问为每个item的标题 应用建议为应用名 今日热搜为热词 预置词为每个item标题 搜索发现为每个item标题 小说榜单为每个小说标题 |  |
| `item_value` | item的value | string | 应用建议为应用包名 其他情况值为空 |  |
| `card_item_position` | 模块内位置 | number | 0、1、2…… |  |
| `item_type` | item类型 | string | common |  |

<details><summary>参数取值详情</summary>


**`page_type`** (首页类型)
- 类型: string
- 取值:
  from_desktop（针对具备应用建议和热榜功能的首页）
  new_search_homepage：新版搜索首页
  old_search_homepage:旧版搜索首页

**`search_homepage_enter_way`** (进入搜索首页的方式)
- 类型: string
- 取值:
  home_page：首页搜索框
  feed：资讯信息流
  search_detail_page：sug页返回
  web_page：普通网页（包括点击宫格名站里的百度）
  menu：长按菜单
  gongge：宫格上的搜索框
  desktop：桌面
  down：下滑（简洁版下）
  search_back：搜索返回

**`item_title`** (item标题)
- 类型: string
- 取值:
  网址为网址的标题
  剪贴板为复制的内容
  搜索历史为搜索词
  我的书签为每条书签的标题
  经常访问为每个item的标题
  应用建议为应用名
  今日热搜为热词
  预置词为每个item标题
  搜索发现为每个item标题
  小说榜单为每个小说标题

</details>


### `search_homepage_module_click` — 搜索首页模块点击

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

无去重逻辑
多次点击多次上报
删除、清空、隐藏、展示操作后引起了位置的变动，后续的位置以真实位置为准上报，前面的已经打过点的不改变，均以当下真实的位置上报


**参数列表** (10):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 首页类型 | string | from_desktop（针对具备应用建议和热榜功能的首页） new_search_homepage：新版搜索首页 old_search_homepage:旧版搜索首页 |  |
| `search_homepage_enter_way` | 进入搜索首页的方式 | string | home_page：首页搜索框 feed：资讯信息流 search_detail_page：sug页返回 web_page：普通网页（包括点击宫格名站里的百度） menu：长按菜单 gongge：宫格上的搜索框 desktop：桌面 down：下滑（简洁版下） search_back：搜索返回 |  |
| `card_type` | 模块类型 | string | 网址 剪贴板 搜索历史 我的书签 经常访问 应用建议 今日热搜 键盘_书签 键盘_剪贴板 键盘_无痕浏览 预置词 搜索发现 小说榜单 猜你想搜 |  |
| `novels_list_type` | 小说热榜类型 | string | 当模块类型为小说榜单时上报，否则为空 boy：男生 girl：女生 |  |
| `card_position` | 模块位置 | number | 0、1、2…… 键盘类为空 |  |
| `item_title` | item标题 | string | 网址为网址的标题 剪贴板为复制的内容 搜索历史为搜索词 我的书签为每条书签的标题 经常访问为每个item的标题 应用建议为应用名 今日热搜为热词 键盘类为空 预置词为每个item标题 搜索发现为每个item标题 小说榜单为每个小说标题 |  |
| `item_value` | item的value | string | 应用建议为应用包名 键盘类为空 |  |
| `card_item_position` | 模块内位置 | number | 0、1、2…… 键盘类为空 |  |
| `item_type` | item类型 | string | common |  |
| `click_area` | 点击位置 | string | 复制（网址） 编辑（网址） 二维码（网址） 搜索词（搜索历史） 删除（搜索历史、应用建议） 清空（搜索历史） 默认（我的书签/经常访问、点击每个item、应用建议、全网热榜、键盘_书签、键盘_剪贴板、键盘_无痕浏览、预置词、搜索发现、小说热榜） 隐藏（我的书签/经常访问、点击隐藏） 展示（我的书签/经常访问、点击展示） 折叠（应用建议、搜索历史） 展开（应用建议、搜索历史） 查看更多（小说热榜） |  |

<details><summary>参数取值详情</summary>


**`page_type`** (首页类型)
- 类型: string
- 取值:
  from_desktop（针对具备应用建议和热榜功能的首页）
  new_search_homepage：新版搜索首页
  old_search_homepage:旧版搜索首页

**`search_homepage_enter_way`** (进入搜索首页的方式)
- 类型: string
- 取值:
  home_page：首页搜索框
  feed：资讯信息流
  search_detail_page：sug页返回
  web_page：普通网页（包括点击宫格名站里的百度）
  menu：长按菜单
  gongge：宫格上的搜索框
  desktop：桌面
  down：下滑（简洁版下）
  search_back：搜索返回

**`card_type`** (模块类型)
- 类型: string
- 取值:
  网址
  剪贴板
  搜索历史
  我的书签
  经常访问
  应用建议
  今日热搜
  键盘_书签
  键盘_剪贴板
  键盘_无痕浏览
  预置词
  搜索发现
  小说榜单
  猜你想搜

**`item_title`** (item标题)
- 类型: string
- 取值:
  网址为网址的标题
  剪贴板为复制的内容
  搜索历史为搜索词
  我的书签为每条书签的标题
  经常访问为每个item的标题
  应用建议为应用名
  今日热搜为热词
  键盘类为空
  预置词为每个item标题
  搜索发现为每个item标题
  小说榜单为每个小说标题

**`click_area`** (点击位置)
- 类型: string
- 取值:
  复制（网址）
  编辑（网址）
  二维码（网址）
  搜索词（搜索历史）
  删除（搜索历史、应用建议）
  清空（搜索历史）
  默认（我的书签/经常访问、点击每个item、应用建议、全网热榜、键盘_书签、键盘_剪贴板、键盘_无痕浏览、预置词、搜索发现、小说热榜）
  隐藏（我的书签/经常访问、点击隐藏）
  展示（我的书签/经常访问、点击展示）
  折叠（应用建议、搜索历史）
  展开（应用建议、搜索历史）
  查看更多（小说热榜）

</details>


### `search_sugpage_expose` — 搜索sug页曝光

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、sug页每刷新一次即上报一次，即考虑连续输入
2、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入）


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `query` | 搜索词 | string | 用户的搜索词 |  |
| `searchid` | searchid | string | 每一次即搜生成唯一id |  |

### `search_sugpage_module_expose` — 搜索sug页模块曝光

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

前端上报
1、item漏出三分之一记曝光（图片icon+文字一起算三分之一）
2、我的书签最多曝光前20个
3、如下不曝光：未在视线范围内出现的（包括键盘挡住的）
4、如下反复操作不重复曝光：页面反复上下滑动、键盘收起弹出
5、滑动过程中不曝光，停止了才曝光
6、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入）


**参数列表** (15):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `req_id` | 请求id | string | 每次请求的唯一标识 |  |
| `project_rev` | 前端版本 | string |  |  |
| `card_type` | 卡片类型<br>（卡片的一级分类） | string | app：游戏 / 应用 product：小米有品 / 小米商城 video：小米视频 book：浏览器小说   website：网址   box：快递/ 彩票/ 天气 sugword：sugword  local：书签/历史/本地 search_button：搜索按钮 local_app：本机应用  local_setting：设置  ads_browser_brand：sug品牌专区非标资源位（非sug卡片） actor：影人 （请注意：广告卡片使用事件ad_search_expose、ad_search_click） |  |
| `item_type` | item类型<br>（卡片的二级分类） | string | card_type='app'时： gamecenter_app：游戏 app：应用  card_type='product'时： mi_product：小米商城商品 youpin_product：小米有品商品  card_type='video'时： short：短视频 cartoon：卡通片 movie：电影 tv：电视剧 variety：综艺 documentary：纪录片  card_type='box'时： express：快递 lottery：彩票 weather：天气  card_type='book'时：browser_book card_type='website'时：web… |  |
| `item_template` | 卡片样式<br>（卡片具体的样式） | string | card_type='app' & item_type='gamecenter_app'时： top-game-banner：游戏大卡下载 top-game-banner-order：游戏大卡预约 top-game：游戏小卡下载 top-game-order：游戏小卡预约  top-app-banner：富媒体大卡 top-app-tags：富媒体小卡  ads-book-banner：小说破壳大卡 ads-book：小说小卡  top-video-banner：视频破壳大卡 top-video-play-banner：视频破壳播放大卡 top-video：视频小卡  card_type='p… |  |
| `item_value` | item_value | string | card_type为app时，记录应用包名 其他情况值为空 |  |
| `item_exp_id` | 游戏实验id | string | sug为游戏类型时需要展示游戏实验id，其他情况为空 |  |
| `alg_exp_id` | 检索端实验id | string |  |  |
| `sug_exp_id` | 融合实验id | string | 各种实验ID的融合 |  |
| `item_id` | item id | string | 索引库里的每条数据的id，包含游戏id 本机应用和设置为空 |  |
| `item_title` | item标题 | string |  |  |
| `item_position` | 模块位置 | number | 每个item的位置，（未展开的位置也计算在内，但未展开前无实际曝光） 0、1、2…… |  |
| `card_item_position` | 模块内位置 | number | item在模块中的位置 0、1、2…… |  |
| `query` | 搜索词 | string |  |  |
| `searchid` | searchid | string | 每一次即搜生成唯一id |  |

<details><summary>参数取值详情</summary>


**`card_type`** (卡片类型
（卡片的一级分类）)
- 类型: string
- 取值:
  app：游戏 / 应用
  product：小米有品 / 小米商城
  video：小米视频
  book：浏览器小说  
  website：网址  
  box：快递/ 彩票/ 天气
  sugword：sugword 
  local：书签/历史/本地
  search_button：搜索按钮
  local_app：本机应用 
  local_setting：设置 
  ads_browser_brand：sug品牌专区非标资源位（非sug卡片）
  actor：影人
  （请注意：广告卡片使用事件ad_search_expose、ad_search_click）

**`item_type`** (item类型
（卡片的二级分类）)
- 类型: string
- 取值:
  card_type='app'时：
  gamecenter_app：游戏
  app：应用
  
  card_type='product'时：
  mi_product：小米商城商品
  youpin_product：小米有品商品
  
  card_type='video'时：
  short：短视频
  cartoon：卡通片
  movie：电影
  tv：电视剧
  variety：综艺
  documentary：纪录片
  
  card_type='box'时：
  express：快递
  lottery：彩票
  weather：天气
  
  card_type='book'时：browser_book
  card_type='website'时：website
  card_type='sugword'时：sugword
  card_type='local'时：local
  card_type='ads_browser_brand'时：ads_browser_brand

**`item_template`** (卡片样式
（卡片具体的样式）)
- 类型: string
- 取值:
  card_type='app' & item_type='gamecenter_app'时：
  top-game-banner：游戏大卡下载
  top-game-banner-order：游戏大卡预约
  top-game：游戏小卡下载
  top-game-order：游戏小卡预约
  
  top-app-banner：富媒体大卡
  top-app-tags：富媒体小卡
  
  ads-book-banner：小说破壳大卡
  ads-book：小说小卡
  
  top-video-banner：视频破壳大卡
  top-video-play-banner：视频破壳播放大卡
  top-video：视频小卡
  
  card_type='product' & item_type='mi_product'时：
  top-product-common：小米商城
  top-product-special：小米商城大卡
  
  album：影片集
  
  card_type='product' & item_type='youpin_product'时：
  top-app：小米有品
  
  card_type='app' & item_type='app'时：
  top-app：应用
  
  card_type='website' & item_type='website'时：
  top-website：网址
  
  card_type='box' & item_type='express'时：
  top-express：快递
  
  card_type='box' & item_type='lottery'时：
  top-lottery：彩票
  
  card_type='box' & item_type='weather'时：
  top-weather：天气
  
  card_type='ads_browser_brand' & item_type='ads_browser_brand'时：
  top-brand：sug品牌专区非标资源位
  其他情况为空

</details>


### `search_sugpage_module_click` — 搜索sug页模块点击

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

前端上报
无去重逻辑
多次点击多次上报


**参数列表** (16):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `req_id` | 请求id | string | 同上 |  |
| `project_rev` | 前端版本 | string |  |  |
| `card_type` | 模块类型 | string |  |  |
| `item_type` | item类型 | string |  |  |
| `item_template` | 卡片样式 | string |  |  |
| `item_value` | item_value | string |  |  |
| `item_exp_id` | 实验id | string |  |  |
| `alg_exp_id` | 检索端实验id | string |  |  |
| `sug_exp_id` | 融合实验id | string |  |  |
| `item_id` | item id | string |  |  |
| `item_title` | item标题 | string |  |  |
| `item_position` | 模块位置 | number |  |  |
| `card_item_position` | 模块内位置 | number |  |  |
| `query` | 搜索词 | string |  |  |
| `searchid` | searchid | string |  |  |
| `click_area` | 点击位置 | string | 安装（应用） 下载（应用） 打开（应用） 预约（应用） 已预约（应用） 阅读（小说） 大图（小米商品） 商品（小米商品） 播放（视频） 打开（商品） query（sugword） 上框（sugword） 打开（box-天气/本机应用/设置） 展开（本机应用/设置） 折叠（本机应用/设置） 默认（其他卡片不区分位置的统一值、以及如上卡片的其他位置） |  |

<details><summary>参数取值详情</summary>


**`click_area`** (点击位置)
- 类型: string
- 取值:
  安装（应用）
  下载（应用）
  打开（应用）
  预约（应用）
  已预约（应用）
  阅读（小说）
  大图（小米商品）
  商品（小米商品）
  播放（视频）
  打开（商品）
  query（sugword）
  上框（sugword）
  打开（box-天气/本机应用/设置）
  展开（本机应用/设置）
  折叠（本机应用/设置）
  默认（其他卡片不区分位置的统一值、以及如上卡片的其他位置）

</details>


### `search_sugpage_module_expose` — 搜索sug页模块曝光

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、sug页每刷新一次即上报一次，即考虑连续输入
2、只要再次回到该页面都进行重新曝光，包括从浏览器内其他页面进入或返回，以及从系统内其他地方进入（点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、点击桌面书签进入）


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `query` | 搜索词 | string | 用户的搜索词 |  |
| `searchid` | searchid | string | 每一次即搜生成唯一id |  |
| `card_type` | 模块类型 | string | search_button：搜索按钮 |  |
| `item_type` | item类型 | string | search_button：搜索按钮 |  |

### `search_sugpage_module_click` — 搜索sug页模块点击

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

无去重逻辑
多次点击多次上报


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `query` | 搜索词 | string | 用户的搜索词 |  |
| `searchid` | searchid | string | 每一次即搜生成唯一id |  |
| `card_type` | 模块类型 | string | search_button：搜索按钮 |  |
| `item_type` | item类型 | string | search_button：搜索按钮 |  |

### `search_scan_click` — 搜索框扫一扫点击

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页、搜索sug页、搜索结果页


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_type` | 模块类型 | string | 扫一扫 |  |

### `search_voice_click` — 搜索框语音搜索点击

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页、搜索sug页、搜索结果页


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_type` | 模块类型 | string | 语音搜索 |  |

### `search_preset_query_expose` — 搜索框提示词曝光

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页
2、首页、信息流资讯各频道页、宫格页面下15秒内同一个query不重复曝光
3、搜索首页进入则曝光


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_type` | 模块类型 | string | 搜索框提示词 |  |
| `item_title` | item标题 | string | 展示的词 |  |
| `item_value` | item的value | string | 搜索的词 |  |
| `card_item_position` | 模块内位置 | number | 在有提示词滚动的情况下记录在滚动词组中的第几个 0、1、2、3...... |  |

### `search_preset_query_click` — 搜索框提示词点击

- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `common key`

**上报时机/逻辑**:

1、包括场景：首页、信息流资讯各频道页、宫格页面、搜索首页
2、产生了真正的搜索时上报


**参数列表** (9):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_type` | 模块类型 | string | 搜索框提示词 |  |
| `item_title` | item标题 | string | 展示的词 |  |
| `item_value` | item的value | string | 搜索的词 |  |
| `card_item_position` | 模块内位置 | number | 0、1、2、3...... |  |
| `` |  | 搜索客户端埋点（已在文档中更新） | 浏览器搜索onetrack埋点(客户端) |  |
| `` |  | 服务端埋点（已在文档中更新） | 浏览器搜索onetrack埋点(服务端) |  |
| `` |  | 全搜埋点 | 全搜打点梳理-最终版 |  |
| `` |  | SUG埋点（已在文档中更新） | 浏览器搜索sug埋点需求（onetrack） |  |
| `` |  | 新首页埋点（已在文档中更新） | 埋点-浏览器搜索首页改版 |  |

### `third_page_back_expose` — 第三方吊起详情页_返回按钮曝光

- 公共属性: `common key`

**上报时机/逻辑**:

三方调起详情页时有按钮曝光


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `icon_type` | 按钮类型 | string |  |  |

### `baidu_sdk_exit` — 百度sdk退出

- 公共属性: `commen key`

**上报时机/逻辑**:

离开百度sdk时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | 从任何场景发起搜索开始计时，离开sdk结束计时： quit：直接home退到后台 home：返回浏览器界面（非百度sdk页面） add_window：新建窗口 lock：锁屏 push：点击push跳转  在结果页直接重新搜索累计计时 |  |
| `duration` | 时长 | number | 单位：毫秒 |  |

<details><summary>参数取值详情</summary>


**`duration_type`** (时长类型)
- 类型: string
- 取值:
  从任何场景发起搜索开始计时，离开sdk结束计时：
  quit：直接home退到后台
  home：返回浏览器界面（非百度sdk页面）
  add_window：新建窗口
  lock：锁屏
  push：点击push跳转
  
  在结果页直接重新搜索累计计时

</details>


### `baidu_applet_sling` — 小程序调起

- 公共属性: `commen key`

**上报时机/逻辑**:

调起百度小程序时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `is_baidu_sdk` | 是否百度sdk | boolean | `red(二期重点)` 0：原api；1：百度sdk |  |

### `appbundle_download` — appbundle 安装

- 公共属性: `commen key`

**上报时机/逻辑**:

appbundle开始下载时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `dl_success` | 是否下载成功 | string | success:安装成功 fail：安装失败 |  |
| `fail_reason` | 下载失败原因 | string | 安装成功，不报该属性 |  |
| `is_available` | 是否可用 | boolean | 1：可用 0：不可用 安装失败，不报该属性 |  |

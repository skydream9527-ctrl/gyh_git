# 浏览器 - app浏览器全局事件

> 来源 sheet: `app浏览器全局事件` | 事件数: 12 | 参数数: 52


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `app_open` | 打开app | APP启动到前台时上报（新用户：cta认证通过后曝光了主页面后上报；老用户：app启动到前台即上报） 进入到前台包括： … | 15 | commen key | 14.3 |
| 2 | `app_duration` | app停留时长 | APP退出(包含退出到后台)时上报 上报从前台到退出的时长 退出到后台包括：回到桌面、返回到其他app、调起其他app、… | 4 | commen key | 14.3 |
| 3 | `webpage_performance` | 网页_性能 | 网页加载完成之后，内核计算出指标结果后，通知客户端，客户端上传到one track | 14 | commen key |  |
| 4 | `open_external_app` | open_external_app | 浏览器调起第三方app时上报 | 6 | - |  |
| 5 | `baidu_applet_change_permission` | 百度小程序权限变更 | 上报场景1. 用户首次触发小程序授权弹窗，并授权时 上报场景2. 用户进行权限调整时 | 4 | common key | 【PRD】百度小程序-用户权限深度合作项目（内部） |
| 6 | `search_scan_click_browser` | 浏览器原生搜索框扫一扫点击 | 包括场景：首页 | 2 | common key | 【V16.8】浏览器&全搜扫一扫 |
| 7 | `search_scan_imp_browser` | 浏览器原生搜索框扫一扫页面曝光 | 扫描页面曝光时上报 | 1 | common key | 【V16.8】浏览器&全搜扫一扫 |
| 8 | `translation_error_code` | 翻译错误代码 | 当翻译失败的时候上报错误代码参数 | 1 | common key |  |
| 9 | `page_translate_click` | 划词翻译 |  | 0 | common key |  |
| 10 | `translation_window_click` | 翻译弹窗点击 |  | 2 | common key |  |
| 11 | `translation_window_expose` | 翻译弹窗曝光 |  | 0 | common key |  |
| 12 | `app_open_third_webpage_load_completed` | 三方调起浏览器网页加载完成 | 三方调起浏览器网页加载完成时上报 | 3 | - |  |

---

## 事件详情

### `app_open` — 打开app

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `commen key`

**上报时机/逻辑**:

APP启动到前台时上报（新用户：cta认证通过后曝光了主页面后上报；老用户：app启动到前台即上报）
进入到前台包括：
点击桌面icon进入、从其他app返回、其他app调起、拉回通知栏、从多任务进入、屏幕解锁、push、点击桌面书签进入


**参数列表** (15):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `homepage_customized_url` | 自定义主页url | string | 记录全值（完整url） |  |
| `$is_first_day` | 是否首日访问 | boolean | true（参数值固定为true） |  |
| `$is_first_time` | 是否首次触发事件 | boolean | true（参数值固定为true） |  |
| `is_parental_guard` | 是否处于家长守护模式 | boolean | true:家长守护 false:不是家长守护 |  |
| `guard_type` | 家长守护类型 | string | `yellow_bg(新增字段)` 默认：default 白名单：whitelist 黑名单：blacklist |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |
| `is_receive_notification` | 通知开关状态 | string | on：开 off：关 |  |
| `notification_bar_status` | 系统的通知栏通知开关状态 | string | on：开 off：关 |  |
| `splash_ad_request_status` | 是否请求开屏广告 | boolean | true:：是 false ：否 |  |
| `default_browser` | 系统默认浏览器 | string | 上报当前的默认浏览器包名 |  |
| `web_security` | 是否开启安全网址检测开关 | string | true:：是 false ：否 |  |
| `incognito_status` | 无痕模式的状态 | string | true:：无痕模式 false ：普通模式 |  |
| `is_kid_account` | 是否登陆未成年账号 | boolean | `yellow_bg(新增字段)` true:：是 false ：否 |  |
| `is_direct_search` | 是否默认【直达】为首页 | boolean | true：是 false：否 |  |
| `is_order_search` | 是否命中强切 | boolean | true：是 false：否 |  |

### `app_duration` — app停留时长

- 进版版本: 14.3
- 无痕模式上报: 是
- 公共属性: `commen key`

**上报时机/逻辑**:

APP退出(包含退出到后台)时上报
上报从前台到退出的时长
退出到后台包括：回到桌面、返回到其他app、调起其他app、拉出通知栏、切到多任务、息屏、锁屏


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration_type` | 时长类型 | string | app_total |  |
| `duration` | 时长 | number | 单位：毫秒 查询时需限定： 时长>0&时长<86400000(单位毫秒) 以排除异常值 |  |
| `homepage_customized_url` | 自定义主页url | string | 记录全值（完整url） |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |

### `webpage_performance` — 网页_性能

- 公共属性: `commen key`

**上报时机/逻辑**:

网页加载完成之后，内核计算出指标结果后，通知客户端，客户端上传到one track


**参数列表** (14):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `dns` | dns解析 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `connect` | 网络连接 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `fpt` | 读取页面第一个字节数的时间 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `load` | 页面加载时间 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `ttfb` | 首包时间 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `http` | 数据传输耗时 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `fp` | 首次绘制 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `fcp` | 首次内容绘制 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `lcp` | 最大内容绘制 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `fid` | 首次输入延迟 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `cls` | 累计位移偏移 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `shut_down` | 用户手动取消加载 | number | `yellow_bg(新增字段)` 单位：毫秒 |  |
| `host` | 网站域名(实验包参数) | string | `yellow_bg(新增字段)` |  |
| `isVpn` | 是否开启vpn(实验包参数) | boolean | `yellow_bg(新增字段)` |  |

### `open_external_app` — open_external_app

**上报时机/逻辑**:

浏览器调起第三方app时上报


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key 公共属性` |  |  |  |  |
| `open_external_source 调起三方app来源` | string | from_ad：广告 from_web：第三方网页（含百度搜索结果页） |  |  |
| `deeplink_schema` | string | 完整的schema字段 |  |  |
| `domain_name` | string | 域名 |  |  |
| `open_external_packagename` | string | app包名 |  |  |
| `open_external_name` | string | app名称 |  |  |

### `baidu_applet_change_permission` — 百度小程序权限变更

- 进版版本: 【PRD】百度小程序-用户权限深度合作项目（内部）
- 公共属性: `common key`

**上报时机/逻辑**:

上报场景1. 用户首次触发小程序授权弹窗，并授权时
上报场景2. 用户进行权限调整时


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `applet_id` | 小程序id | string |  |  |
| `applet_name` | 小程序名称 | string |  |  |
| `permission_type` | 权限类型 | string | position：获取你的地理位置信息 photo：访问手机相册 camera：使用你的手机摄像头 microphone：使用你的麦克风 addresslist：使用通讯录 calendar：访问手机日历 |  |
| `permission_status` | 权限使用状态 | string | 用户操作后的状态 allow：允许 refuse：拒绝 unused：未使用 |  |

<details><summary>参数取值详情</summary>


**`permission_type`** (权限类型)
- 类型: string
- 取值:
  position：获取你的地理位置信息
  photo：访问手机相册
  camera：使用你的手机摄像头
  microphone：使用你的麦克风
  addresslist：使用通讯录
  calendar：访问手机日历

</details>


### `search_scan_click_browser` — 浏览器原生搜索框扫一扫点击

- 进版版本: 【V16.8】浏览器&全搜扫一扫
- 公共属性: `common key`

**上报时机/逻辑**:

包括场景：首页


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `card_type` | 模块类型 | string | 扫一扫 |  |
| `fromWidget` | 来源 | string | true：桌面小部件 false：全搜打开 |  |

### `search_scan_imp_browser` — 浏览器原生搜索框扫一扫页面曝光

- 进版版本: 【V16.8】浏览器&全搜扫一扫
- 公共属性: `common key`

**上报时机/逻辑**:

扫描页面曝光时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `fromWidget` | 来源 | string | true：桌面小部件 false：全搜打开 |  |

### `translation_error_code` — 翻译错误代码

- 公共属性: `common key`

**上报时机/逻辑**:

当翻译失败的时候上报错误代码参数


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `code` | 错误代码 | number | 1 : 翻译脚本未设置； 2 : 脚本注入失败; 6 : 翻译失败； 7 : 翻译脚本初始化失败,超时 12 : 后续页面翻译错误 |  |

<details><summary>参数取值详情</summary>


**`code`** (错误代码)
- 类型: number
- 取值:
  1 : 翻译脚本未设置；
  2 : 脚本注入失败;
  6 : 翻译失败；
  7 : 翻译脚本初始化失败,超时
  12 : 后续页面翻译错误

</details>


### `page_translate_click` — 划词翻译

- 公共属性: `common key`


_(无独立参数,仅携带公共属性)_


### `translation_window_click` — 翻译弹窗点击

- 公共属性: `common key`


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string |  |  |
| `url` | 网页域名 | string |  |  |

### `translation_window_expose` — 翻译弹窗曝光

- 公共属性: `common key`


_(无独立参数,仅携带公共属性)_


### `app_open_third_webpage_load_completed` — 三方调起浏览器网页加载完成

**上报时机/逻辑**:

三方调起浏览器网页加载完成时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `third_packagename` | 第三方调起包名 | string |  |  |
| `third_url` | 第三方调起网页url | string |  |  |
| `load_status` | 加载状态 | string | 加载成功：load_success 加载失败：load_failed 加载超时：load_timeout |  |

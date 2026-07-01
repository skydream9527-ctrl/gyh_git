# 内容中心 - app通用

> 来源 sheet: `app通用` | 事件数: 24 | 参数数: 36


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `app_open` | app打开 | 内容中心打开进入前台就上报 进入前台定义：桌面上滑，push调启，负一屏调启，多任务切回，从息屏锁屏到亮屏 | 1 | common key |  |
| 2 | `app_duration（废弃）` | app退出 | 内容中心退出时上报时长 用户从前台切到后台，上报从前台-后台的时长 切到后台定义：app退出桌面，锁屏/息屏/多任务切第… | 1 | common key |  |
| 3 | `app_cta_click` | CTA点击激活 | 事件发生时 | 3 | common key |  |
| 4 | `app_cta_expose` | cta弹窗曝光 | 事件发生时 曝光几次记几次 比如退出后再进入，从三方返回 | 1 | common key |  |
| 5 | `app_open_v2` | app打开过程 | app进入前台上报： 前台分流上/详情页 详细规则：前台看见流上上报打开事件，打开参数为流上 前台看见详情页上报打开事件… | 1 | common key |  |
| 6 | `app_duration_v2` | app退出过程 | app退出前台上报： 退出流上/详情页 详细规则：从前台看见流上，开始计时，看不到流上报流上时长。 从前台看见详情页，开… | 2 | common key |  |
| 7 | `app_popup_window_expose` | app弹窗曝光 | 弹窗曝光即上报，弹出几次，上报几次。不去重 page、from_page、module、from_module为空 | 4 | common key |  |
| 8 | `app_popup_window_click` | app弹窗点击 | 点击取消，确定按钮即上报 | 6 | common key |  |
| 9 | `app_guide_expose` | 引导曝光 |  | 3 | common key |  |
| 10 | `app_guide_click` | 引导点击 | 点击X，去试试按钮即上报 | 2 | common key |  |
| 11 | `app_top_slide` | 置顶滑动 | 滑动成功触发 | 1 | common key |  |
| 12 | `app_top_slide_expose` | “左滑查看全部”按钮曝光 | 刷新（有数据请求）后重复曝光 | 0 | common key |  |
| 13 | `app_top_slide_click` | “左滑查看全部”按钮点击 | 点击几次上报几次 | 0 | common key |  |
| 14 | `app_hot_more` | “查看完整榜单”按钮点击 | 点击几次上报几次 | 0 | common key |  |
| 15 | `notice_bell_click` | 铃铛点击 | 点击触发，点击几次报几次 | 0 | common key |  |
| 16 | `page_duration` | 页面时长 | 进入页面开始计时，离开页面上报页面时长 | 0 | common key |  |
| 17 | `button_click` | 按钮点击 | 点击时上报，点击几次上报几次 | 1 | common key |  |
| 18 | `thirdapp_open` | 第三方app拉活 | 进行拉活任务后上报 | 2 | common key |  |
| 19 | `thirdapp_download` | 第三方app拉新 | 进行拉新任务后上报 | 2 | common key |  |
| 20 | `popup_expose` | 拉新弹窗曝光 | 拉新弹窗露出2/3以上时上报 | 1 | common key |  |
| 21 | `popup_click` | 拉新弹窗点击 | 拉新弹窗点击体验时上报 | 1 | common key |  |
| 22 | `popup_skip` | 拉新弹窗跳过 | 拉新弹窗点击跳过时上报 | 0 | common key |  |
| 23 | `page_expose` | 页面曝光 | 点击评论按钮或评论框，弹出评论页面时，上报埋点 重复上报 包括各频道各体裁的评论页面 | 2 | - |  |
| 24 | `launch_swipe_app_open_fail` | 上滑打开失败 | 冷启上滑但未划到顶部未打开内容中心就退出时上报 | 2 | common key |  |

---

## 事件详情

### `app_open` — app打开

- 公共属性: `common key`

**上报时机/逻辑**:

内容中心打开进入前台就上报
进入前台定义：桌面上滑，push调启，负一屏调启，多任务切回，从息屏锁屏到亮屏


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `open_type` | 上滑：launch_swipe<br>push：push<br>负一屏：assistant<br>锁屏息屏：lock_screen<br>小部件: widget_4*2hot，widget_4*2recommend，widget_4*4hot<br>快捷方式：shortcut<br>拉活进入：DP中的source<br>全搜为你推荐icon：quick_search | 4*4 热点资讯：widget_4*4hot<br>4*2 热点资讯：widget_4*2recommend<br>4*2 实时热榜：widget_4*2hot |  |  |

### `app_duration（废弃）` — app退出

- 公共属性: `common key`

**上报时机/逻辑**:

内容中心退出时上报时长
用户从前台切到后台，上报从前台-后台的时长
切到后台定义：app退出桌面，锁屏/息屏/多任务切第三方/通知栏跳三方


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 停留时长 |  |  |  |

### `app_cta_click` — CTA点击激活

- 公共属性: `common key`

**上报时机/逻辑**:

事件发生时


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `expose_cnt` | 曝光次数 |  |  |  |
| `popup_style` | 弹窗样式 | 1，2，3 |  |  |
| `from_type` | cta激活前之前的模式 | normal mode, only_view mode | normal mode - 未进入基础模式，cta页面点击同意的用户 only_view mode - 进入基础模式后，再在cta页面点击同意的用户 |  |

<details><summary>参数取值详情</summary>


**`from_type`** (cta激活前之前的模式)
- 类型: normal mode, only_view mode
- 取值:
  normal mode - 未进入基础模式，cta页面点击同意的用户
  only_view mode - 进入基础模式后，再在cta页面点击同意的用户

</details>


### `app_cta_expose` — cta弹窗曝光

- 公共属性: `common key`

**上报时机/逻辑**:

事件发生时
曝光几次记几次
比如退出后再进入，从三方返回


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `popup_style` | 1,2,3 |  | `red(二期重点)` |  |

### `app_open_v2` — app打开过程

- 公共属性: `common key`

**上报时机/逻辑**:

app进入前台上报：
前台分流上/详情页
详细规则：前台看见流上上报打开事件，打开参数为流上
前台看见详情页上报打开事件，打开参数为详情页


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `open_type` | feed/detail |  |  |  |

### `app_duration_v2` — app退出过程

- 公共属性: `common key`

**上报时机/逻辑**:

app退出前台上报：
退出流上/详情页
详细规则：从前台看见流上，开始计时，看不到流上报流上时长。
从前台看见详情页，开始计时，看不到详情页报详情页时长。


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 停留时长 |  |  |  |
| `duration_type` | feed/detail/<br>livestream |  |  |  |

### `app_popup_window_expose` — app弹窗曝光

- 公共属性: `common key`

**上报时机/逻辑**:

弹窗曝光即上报，弹出几次，上报几次。不去重
page、from_page、module、from_module为空


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `popup_type` | swich_entertainment //邀请您体验娱乐中心<br>swich_weibo_main_app //主频道微博弹窗跳微博<br>swich_weibo_main_fast //主频道微博弹窗跳快应用<br>swich_weibo_hot_app //热榜频道微博弹窗跳微博<br>swich_weibo_hot_fast //热榜频道微博弹窗跳快应用<br>privacy_update//隐私弹窗更新<br>privacy_deny//隐私弹窗撤回<br>accept_shortcut //快捷方式<br>active_back//拉活返回弹窗 |  | `red(二期重点)` |  |
| `exp_id` | 实验ID | string | `red(二期重点)` |  |
| `item_docid` | 内容id | string | `red(二期重点)` |  |
| `popup_style` | 1,2,3 | number | `red(二期重点)` |  |

### `app_popup_window_click` — app弹窗点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击取消，确定按钮即上报


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `popup_type` | swich_entertainment //邀请您体验娱乐中心<br>swich_weibo_main_app //主频道微博弹窗跳微博<br>swich_weibo_main_fast //主频道微博弹窗跳快应用<br>swich_weibo_hot_app //热榜频道微博弹窗跳微博<br>swich_weibo_hot_fast //热榜频道微博弹窗跳快应用<br>privacy_update<br>privacy_deny<br>accept_shortcut //快捷方式<br>active_back//拉活返回弹窗 |  | `red(二期重点)` |  |
| `popup_click_type` | cancel/agree |  | `red(二期重点)` |  |
| `exp_id` | 实验ID | string | `red(二期重点)` |  |
| `item_docid` | 内容id | string | `red(二期重点)` |  |
| `popup_style` | 1,2,3 | number | `red(二期重点)` |  |
| `expose_cnt` | 10 | number |  |  |

### `app_guide_expose` — 引导曝光

- 公共属性: `common key`


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `guide_type` | click：点击引导<br>slide：滑动引导<br>active：拉活引导 | string |  |  |
| `guide_name` | novel_first-小说新用户引导-首次气泡<br>novel_red-小说新用户引导-小红点 | string | `red(二期重点)` |  |
| `guide_style` | 续读状态1全屏展示<br>续读状态2小卡展示 | string | `red(二期重点)` 续读类型 |  |

### `app_guide_click` — 引导点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击X，去试试按钮即上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `guide_click_type` | cancel/agree | string |  |  |
| `guide_name` | novel_first-小说新用户引导-首次气泡<br>novel_red-小说新用户引导-小红点 | string | `red(二期重点)` |  |

### `app_top_slide` — 置顶滑动

- 公共属性: `common key`

**上报时机/逻辑**:

滑动成功触发


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `slide_type` | 滑动方式 | 页面1左滑至页面2上报left_1<br>页面2左滑至热榜频道上报left_2<br>右滑上报right |  |  |

### `app_top_slide_expose` — “左滑查看全部”按钮曝光

- 公共属性: `common key`

**上报时机/逻辑**:

刷新（有数据请求）后重复曝光


_(无独立参数,仅携带公共属性)_


### `app_top_slide_click` — “左滑查看全部”按钮点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击几次上报几次


_(无独立参数,仅携带公共属性)_


### `app_hot_more` — “查看完整榜单”按钮点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击几次上报几次


_(无独立参数,仅携带公共属性)_


### `notice_bell_click` — 铃铛点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击触发，点击几次报几次


_(无独立参数,仅携带公共属性)_


### `page_duration` — 页面时长

- 公共属性: `common key`

**上报时机/逻辑**:

进入页面开始计时，离开页面上报页面时长


_(无独立参数,仅携带公共属性)_


### `button_click` — 按钮点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击时上报，点击几次上报几次


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `button_type` | 按钮类型 | button//全屏按钮<br>press_2.0//长按2.0X<br>0.75X//倍速按钮0.75X<br>1.0X//倍速按钮1.0X<br>1.25X//倍速按钮1.25X<br>1.5X//倍速按钮1.5X<br>2.0X//倍速按钮2.0X<br>circulate_on：开启循环播放<br>circulate_off：关闭循环播放 |  |  |

### `thirdapp_open` — 第三方app拉活

- 公共属性: `common key`

**上报时机/逻辑**:

进行拉活任务后上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `mission_id` | 任务id | string | 131001 |  |
| `mission_status` | 任务状态 | string | 0：拉活成功 1：拉活失败 |  |

### `thirdapp_download` — 第三方app拉新

- 公共属性: `common key`

**上报时机/逻辑**:

进行拉新任务后上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `mission_id` | 任务id | string | 131001 |  |
| `mission_status` | 任务状态 | string | 0：拉新成功（点击弹窗就算） 1：安装成功 2：拉启应用成功 3：本地已有该应用 4：本地暂无该应用，且无安装包 5：本地暂无该应用，有安装包，但用户拒绝安装 |  |

<details><summary>参数取值详情</summary>


**`mission_status`** (任务状态)
- 类型: string
- 取值:
  0：拉新成功（点击弹窗就算）
  1：安装成功
  2：拉启应用成功
  3：本地已有该应用
  4：本地暂无该应用，且无安装包
  5：本地暂无该应用，有安装包，但用户拒绝安装

</details>


### `popup_expose` — 拉新弹窗曝光

- 公共属性: `common key`

**上报时机/逻辑**:

拉新弹窗露出2/3以上时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `mission_id` | 任务id | string | 131001 |  |

### `popup_click` — 拉新弹窗点击

- 公共属性: `common key`

**上报时机/逻辑**:

拉新弹窗点击体验时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `mission_id` | 任务id | string | 131001 |  |

### `popup_skip` — 拉新弹窗跳过

- 公共属性: `common key`

**上报时机/逻辑**:

拉新弹窗点击跳过时上报


_(无独立参数,仅携带公共属性)_


### `page_expose` — 页面曝光

**上报时机/逻辑**:

点击评论按钮或评论框，弹出评论页面时，上报埋点
重复上报
包括各频道各体裁的评论页面


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `common key<br>content key` | 公共属性 |  |  |  |
| `page_name` | 页面 | string | 评论页面：comment_detail |  |

### `launch_swipe_app_open_fail` — 上滑打开失败

- 公共属性: `common key`

**上报时机/逻辑**:

冷启上滑但未划到顶部未打开内容中心就退出时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `is_new_effect` | 新动效是否生效 | boolean |  |  |
| `is_interface_request` | 是否有接口请求 | boolean | true/false |  |

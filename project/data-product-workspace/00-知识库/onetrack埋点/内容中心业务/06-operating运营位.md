# 内容中心 - operating运营位

> 来源 sheet: `operating运营位` | 事件数: 8 | 参数数: 18


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `operation_icon_expose` | 运营位icon曝光 | 完成露出即曝光，刷新后二次上报 垂类频道记得上报page公共参数main_olympic from_page,mudul… | 3 | common key |  |
| 2 | `operation_icon_click` | 运营位icon点击 | 点击触发，点击几次上报几次 垂类频道记得上报page公共参数main_olympic from_page,mudule,… | 3 | common key |  |
| 3 | `operation_icon_view` | 运营位icon浏览 | 退出详情页上报，退出几次 垂类频道记得上报page公共参数所在页面 from_page,mudule,from_mudu… | 3 | common key |  |
| 4 | `operation_content_expose` | 运营位条目曝光 | 1、完成露出即曝光，刷新后二次上报 2、点击触发，点击几次报几次 3、退出h5页面上报，浏览页面退出时上报（包括app退… | 2 | common key |  |
| 5 | `operation_notice_activity_expose` | 通知左侧运营位曝光 | 1、露出即曝光，再次露出再次上报 2、点击触发，点击几次报几次 page,from_page,mudule,from_m… | 1 | common key |  |
| 6 | `operation_question_expose` | 投票曝光 | 露出即曝光，曝光过后上下滑不上报 （33%内容曝光与内容曝光统一） | 2 | common key |  |
| 7 | `operation_question_click` | 投票点击 | 点击成功后上报 | 3 | common key |  |
| 8 | `涉及场景` |  | 垂类icon、垂类tag涉及频道 | 1 | - |  |

---

## 事件详情

### `operation_icon_expose` — 运营位icon曝光

- 公共属性: `common key`

**上报时机/逻辑**:

完成露出即曝光，刷新后二次上报
垂类频道记得上报page公共参数main_olympic
from_page,mudule,from_mudule不需要


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `icon_id` | 活动id | string |  |  |
| `icon_name` | icon名称 | string | 火炬传递/东奥指南 |  |
| `icon_type` | icon类型 | string | tag/icon |  |

### `operation_icon_click` — 运营位icon点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击触发，点击几次上报几次
垂类频道记得上报page公共参数main_olympic
from_page,mudule,from_mudule不需要


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `icon_id` | 活动id | string |  |  |
| `icon_name` | icon名称 | string | 火炬传递/东奥指南 |  |
| `icon_type` | icon类型 | string | tag/icon |  |

### `operation_icon_view` — 运营位icon浏览

- 公共属性: `common key`

**上报时机/逻辑**:

退出详情页上报，退出几次
垂类频道记得上报page公共参数所在页面
from_page,mudule,from_mudule不需要


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `icon_name` | icon名称 | string | 火炬传递/东奥指南 |  |
| `icon_type` | icon类型 | string | tag/icon |  |
| `duration` | 运营位时长 | string |  |  |

### `operation_content_expose` — 运营位条目曝光

- 公共属性: `common key`

**上报时机/逻辑**:

1、完成露出即曝光，刷新后二次上报
2、点击触发，点击几次报几次
3、退出h5页面上报，浏览页面退出时上报（包括app退出、返回上一级页面，息屏锁屏，切多任务/拉通知栏跳走都算，只要详情页看不到就记）
垂类频道记得上报page公共参数
from_page,mudule,from_mudule不需要


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `content_name` | 条目名称 | string | cms后台配置运营位名称 |  |
| `duration` | 运营条目时长 | string | 仅view事件上报 |  |

### `operation_notice_activity_expose` — 通知左侧运营位曝光

- 公共属性: `common key`

**上报时机/逻辑**:

1、露出即曝光，再次露出再次上报
2、点击触发，点击几次报几次
page,from_page,mudule,from_mudule都不需要，不上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `notice_name` | 通知名称 | string | 0618小铃铛 |  |

### `operation_question_expose` — 投票曝光

- 公共属性: `common key`

**上报时机/逻辑**:

露出即曝光，曝光过后上下滑不上报
（33%内容曝光与内容曝光统一）


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `question_id` | 问卷id | string |  |  |
| `question_name` | 问卷名称 | string | 你喜欢内容中心吗？ |  |

### `operation_question_click` — 投票点击

- 公共属性: `common key`

**上报时机/逻辑**:

点击成功后上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `question_id` | 问卷id | string |  |  |
| `question_name` | 问卷名称 | string | 你喜欢内容中心吗？ |  |
| `question_option` | 问卷选中项 | string | 超级喜欢 |  |

### `涉及场景` — 

**上报时机/逻辑**:

垂类icon、垂类tag涉及频道


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `发现_推荐<br>发现_游戏<br>发现_两会<br>发现_新时代<br>发现_财经<br>发现_足球<br>发现_体育<br>发现_问答<br>发现_奥运<br>发现_本地<br>发现_小说<br>发现_娱乐<br>发现_历史<br>发现_数码<br>发现_军事<br>发现_动漫<br>发现_美食<br>发现_搞笑<br>发现_电影<br>发现_视频<br>发现_科技<br>发现_抗疫<br>发现_bilibili` |  |  |  |  |

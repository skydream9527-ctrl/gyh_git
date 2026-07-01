# 浏览器 - 浏览器Push事件

> 来源 sheet: `浏览器Push事件` | 事件数: 6 | 参数数: 34


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `push_expose` | push_送达 | push触达到用户通知栏，上报push送达事件 | 10 | common key |  |
| 2 | `push_click` | push_点击 | 用户点击push进入文章/视频详情页，上报点击事件 | 10 | common key |  |
| 3 | `push_disable_push` | push_关闭push | push触达用户，但用户通知栏关闭，上报关闭push事件 | 10 | common key |  |
| 4 | `localpush_expose` | 本地消息_送达 | 用户通知栏接收到本地push，上报本地消息送达事件，多次接收多次上报 | 2 | common key |  |
| 5 | `localpush_click` | 本地消息_点击 | 用户点击本地push进入文章/视频详情页，上报点击事件 | 2 | common key |  |
| 6 | `待补充属性打点` |  |  | 0 | - |  |

---

## 事件详情

### `push_expose` — push_送达

- 公共属性: `common key`

**上报时机/逻辑**:

push触达到用户通知栏，上报push送达事件


**参数列表** (10):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `appName` | 业务名称 | string | browser：浏览器 new_home：内容中心 |  |
| `expId` | 实验id | string | 全自动实验配置 |  |
| `itemId` | 文章id | string | 每一篇推送使用图文/视频的docid |  |
| `pushId` | 推送id | string | 按下发类型确定前缀，后面随机码补齐8位 |  |
| `pushType` | 推送类型 | string | 批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略 |  |
| `raw_imei` | raw_imei | string | raw_imei:did转换之前的用户imei |  |
| `did` | did | string |  |  |
| `hashId` | hashId | number |  |  |
| `reachType` | 消息回执状态 | string |  |  |
| `reachTime` | 下发时间 | number | unix时间戳，单位：毫秒 |  |

<details><summary>参数取值详情</summary>


**`pushType`** (推送类型)
- 类型: string
- 取值:
  批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略

</details>


### `push_click` — push_点击

- 公共属性: `common key`

**上报时机/逻辑**:

用户点击push进入文章/视频详情页，上报点击事件


**参数列表** (10):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `appName` | 业务名称 | string | browser：浏览器 new_home：内容中心 |  |
| `expId` | 实验id | string | 全自动实验配置 |  |
| `itemId` | 文章id | string | 每一篇推送使用图文/视频的docid |  |
| `pushId` | 推送id | string | 按下发类型确定前缀，后面随机码补齐8位 |  |
| `pushType` | 推送类型 | string | 批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略 |  |
| `raw_imei` | raw_imei | string | raw_imei:did转换之前的用户imei |  |
| `did` | did | string |  |  |
| `hashId` | hashId | number |  |  |
| `reachType` | 消息回执状态 | string |  |  |
| `reachTime` | 下发时间 | number | unix时间戳，单位：毫秒 |  |

<details><summary>参数取值详情</summary>


**`pushType`** (推送类型)
- 类型: string
- 取值:
  批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略

</details>


### `push_disable_push` — push_关闭push

- 公共属性: `common key`

**上报时机/逻辑**:

push触达用户，但用户通知栏关闭，上报关闭push事件


**参数列表** (10):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `appName` | 业务名称 | string | browser：浏览器 new_home：内容中心 |  |
| `expId` | 实验id | string | 全自动实验配置 |  |
| `itemId` | 文章id | string | 每一篇推送使用图文/视频的docid |  |
| `pushId` | 推送id | string | 按下发类型确定前缀，后面随机码补齐8位 |  |
| `pushType` | 推送类型 | string | 批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略 |  |
| `raw_imei` | raw_imei | string | raw_imei:did转换之前的用户imei |  |
| `did` | did | string |  |  |
| `hashId` | hashId | number |  |  |
| `reachType` | 消息回执状态 | string |  |  |
| `reachTime` | 下发时间 | number | unix时间戳，单位：毫秒 |  |

<details><summary>参数取值详情</summary>


**`pushType`** (推送类型)
- 类型: string
- 取值:
  批量物料池头部策略、垂类、全局强制发送、批量物料池队列下发、模型、批量物料池试探、地域、批量物料池试探扩量、testPush、批量物料池长尾策略

</details>


### `localpush_expose` — 本地消息_送达

- 公共属性: `common key`

**上报时机/逻辑**:

用户通知栏接收到本地push，上报本地消息送达事件，多次接收多次上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `itemId` | 文章id | string | 文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `reachTime` | 送达时间 | number | push送达至用户的时间，unix时间戳，单位：毫秒 |  |

### `localpush_click` — 本地消息_点击

- 公共属性: `common key`

**上报时机/逻辑**:

用户点击本地push进入文章/视频详情页，上报点击事件


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `itemId` | 文章id | string | 文章详情页的文章id，只有文章详情页和视频详情页传此值 |  |
| `reachTime` | 送达时间 | number | push送达至用户的时间，unix时间戳，单位：毫秒 |  |

### `待补充属性打点` — 


_(无独立参数,仅携带公共属性)_


# 浏览器 - novel小说事件

> 来源 sheet: `novel小说事件` | 事件数: 3 | 参数数: 9


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `novel_expose` | 小说_曝光 | 小说功能页面曝光时 | 2 | common key |  |
| 2 | `novel_read_duration` | 小说_阅读_时长 | 用户进入浏览器小说SDK阅读页，开始计时； 每90s上报一次时长； 用户离开浏览器小说SDK阅读页，包括回到桌面、切到其… | 3 | common key |  |
| 3 | `novel_page_turn` | 小说_页面_翻页 | 翻页发生时上报 用户在覆盖、仿真、平移翻页模式，翻一页统计一次； 用户在上下翻页模式时，当页面平移的高度高于2/3屏幕高… | 4 | common key |  |

---

## 事件详情

### `novel_expose` — 小说_曝光

- 公共属性: `common key`

**上报时机/逻辑**:

小说功能页面曝光时


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_name` | 页面名称 | string | bookshelf 书架页面 male_channel 男生频道 female_channel 女生频道 recommendation_channel 精选频道 feed_novel 免费小说频道 classification_male 男生分类页面 classification_female 女生分类页面 search 搜索页面 new_book 新书页面 rank_list 排行榜页面 finished_list 完结榜页面 read 阅读页 book_detail 书籍详情页 user_center 用户中心 welfare：福利页面 history：阅读历史 other：其他 |  |
| `novel_channel` | 渠道 | string | 浏览器小说渠道入口字段 |  |

<details><summary>参数取值详情</summary>


**`page_name`** (页面名称)
- 类型: string
- 取值:
  bookshelf 书架页面
  male_channel 男生频道
  female_channel 女生频道
  recommendation_channel 精选频道
  feed_novel 免费小说频道
  classification_male 男生分类页面
  classification_female 女生分类页面
  search 搜索页面
  new_book 新书页面
  rank_list 排行榜页面
  finished_list 完结榜页面
  read 阅读页
  book_detail 书籍详情页
  user_center 用户中心
  welfare：福利页面
  history：阅读历史
  other：其他

</details>


### `novel_read_duration` — 小说_阅读_时长

- 公共属性: `common key`

**上报时机/逻辑**:

用户进入浏览器小说SDK阅读页，开始计时；
每90s上报一次时长；
用户离开浏览器小说SDK阅读页，包括回到桌面、切到其他app、息屏、锁屏、拉出通知栏、切到多任务、去到其他页面，停止计时。
用户离开浏览器小说SDK阅读页面时，上报本次阅读时长


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `novel_channel` | 渠道 | string | 浏览器小说渠道入口字段 |  |
| `duration` | 时长 | number | 单位：毫秒 |  |
| `book_id` | 书籍id | number |  |  |

### `novel_page_turn` — 小说_页面_翻页

- 公共属性: `common key`

**上报时机/逻辑**:

翻页发生时上报
用户在覆盖、仿真、平移翻页模式，翻一页统计一次；
用户在上下翻页模式时，当页面平移的高度高于2/3屏幕高度时，记一次翻页。


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `novel_channel` | 渠道 | string | 浏览器小说渠道入口字段 |  |
| `turn_mode` | 翻页模式 | string | cover 覆盖翻页模式：OVERLAP simulation 仿真翻页模式 ：THREE_DIME translation 平移模式：HSCROLL go_online 上下翻页模式：VSCROLL 无翻页模式：NONE 淡入翻页模式：FADE_IN |  |
| `book_id` | 书籍id | number |  |  |
| `process_source` | 新渠道 | string |  |  |

<details><summary>参数取值详情</summary>


**`turn_mode`** (翻页模式)
- 类型: string
- 取值:
  cover 覆盖翻页模式：OVERLAP
  simulation 仿真翻页模式 ：THREE_DIME
  translation 平移模式：HSCROLL
  go_online 上下翻页模式：VSCROLL
  无翻页模式：NONE
  淡入翻页模式：FADE_IN

</details>


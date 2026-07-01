# 浏览器 - button_bar底部工具栏事件

> 来源 sheet: `button_bar底部工具栏事件` | 事件数: 3 | 参数数: 9


## 事件总览

| # | 分类 | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|---|
| 1 | 底部工具栏 | `button_bar_click` | 底部工具栏_点击 | 点击时上报 | 3 | commey_key | 14.6 |
| 2 | 底部工具栏 | `button_bar_longpress` | 底部工具栏_长按 | 屏幕方向为竖屏时，可长按。长按时上报 | 2 | commey_key | 14.6 |
| 3 | 底部工具栏 | `button_bar_popup_click` | 底部工具栏_长按弹窗_点击 | 长按工具栏功能按钮，出现弹框，点击弹窗中的任意选项后上报 | 4 | commey_key | 14.6 |

---

## 事件详情

### `button_bar_click` — 底部工具栏_点击

- 分类: 底部工具栏
- 进版版本: 14.6
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | home:主页 info:资讯 video:视频 tabaction:多窗口 novel:小说 my:我的 back:后退 forward:前进 menu:菜单 simple_home_bookmark_history:书签（存在于简洁版） white_list:白名单列表(仅家长守护模式) qsb_search：搜索icon（全搜结果页底部搜索icon【PRD】全搜结果页底部增加搜索icon ） |  |
| `page_type` | 页面类型 | string | homepage：主页态 webpage：网页态 |  |
| `screen_orientation` | 屏幕方向 | string | vertical：竖屏 horizontal：横屏 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 类型: string
- 取值:
  home:主页
  info:资讯
  video:视频
  tabaction:多窗口
  novel:小说
  my:我的
  back:后退
  forward:前进
  menu:菜单
  simple_home_bookmark_history:书签（存在于简洁版）
  white_list:白名单列表(仅家长守护模式)
  qsb_search：搜索icon（全搜结果页底部搜索icon【PRD】全搜结果页底部增加搜索icon ）

</details>


### `button_bar_longpress` — 底部工具栏_长按

- 分类: 底部工具栏
- 进版版本: 14.6
- 公共属性: `commey_key`

**上报时机/逻辑**:

屏幕方向为竖屏时，可长按。长按时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | home:主页 tabaction:多窗口 back:后退 forward:前进 menu:菜单 |  |
| `page_type` | 页面类型 | string | homepage：主页态 webpage：网页态 |  |

### `button_bar_popup_click` — 底部工具栏_长按弹窗_点击

- 分类: 底部工具栏
- 进版版本: 14.6
- 公共属性: `commey_key`

**上报时机/逻辑**:

长按工具栏功能按钮，出现弹框，点击弹窗中的任意选项后上报


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | tabaction:多窗口 back:后退 forward:前进 |  |
| `page_type` | 页面类型 | string | homepage：主页态 webpage：网页态 |  |
| `subfunction_name` | 二级功能名称 | string | 【function_name为多窗口时上报】 open_new_window：新增窗口 open_incognito_window：新增无痕模式窗口 close_window：关闭当前窗口 close_all_window：关闭全部窗口  【function_name为前进、后退时上报】 transfer：跳转（点击弹窗中任一选项，跳转后上报） |  |
| `browser_mode` | 浏览模式 | string | 【function_name为多窗口时上报以下属性值，前进、后退不上报】 normal：普通 incognito：无痕 |  |

<details><summary>参数取值详情</summary>


**`subfunction_name`** (二级功能名称)
- 类型: string
- 取值:
  【function_name为多窗口时上报】
  open_new_window：新增窗口
  open_incognito_window：新增无痕模式窗口
  close_window：关闭当前窗口
  close_all_window：关闭全部窗口
  
  【function_name为前进、后退时上报】
  transfer：跳转（点击弹窗中任一选项，跳转后上报）

</details>


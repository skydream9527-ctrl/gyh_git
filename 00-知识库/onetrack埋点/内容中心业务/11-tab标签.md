# 内容中心 - tab标签

> 来源 sheet: `tab标签` | 事件数: 2 | 参数数: 0


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `tab_top_click` | 顶tab点击（滑动） | 顶tab滑动，点击上报。当前频道下点击多次不上报（上滑进入首次刷新，不计） （只要page就行。不要module，fro… | 0 | common key |  |
| 2 | `tab_bottom_click` | 底tab点击 | 底点击上报，点击多次上报多次（上滑进入首次刷新，不计） （只要page就行。不要module，from_module，f… | 0 | common key |  |

---

## 事件详情

### `tab_top_click` — 顶tab点击（滑动）

- 公共属性: `common key`

**上报时机/逻辑**:

顶tab滑动，点击上报。当前频道下点击多次不上报（上滑进入首次刷新，不计）
（只要page就行。不要module，from_module，from_page）
范围包括热榜


_(无独立参数,仅携带公共属性)_


### `tab_bottom_click` — 底tab点击

- 公共属性: `common key`

**上报时机/逻辑**:

底点击上报，点击多次上报多次（上滑进入首次刷新，不计）
（只要page就行。不要module，from_module，from_page）
范围包括热榜，小说


_(无独立参数,仅携带公共属性)_


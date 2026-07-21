# 浏览器 - icon_slots站点事件

> 来源 sheet: `icon_slots站点事件` | 事件数: 4 | 参数数: 9


## 事件总览

| # | 分类 | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|---|
| 1 | 资源位 | `icon_expose` | 图标_曝光 | 名站：名站处于可见状态时打点 宫格：宫格页面展示时进行宫格每一项的宫格打点 | 2 | commey_key | 15.2 |
| 2 | 资源位 | `icon_click` | 图标_点击 | 对某一项进行点击时上报 | 2 | commey_key | 15.2 |
| 3 | 宫格 | `icon_slots_expose` | 站点_曝光 | 曝光时上报；整个页面报一个 | 2 | commey_key | 14.6 |
| 4 | 宫格 | `icon_slots_click` | 站点_点击 | 完成相关功能时上报 | 3 | commey_key | 14.6 |

---

## 事件详情

### `icon_expose` — 图标_曝光

- 分类: 资源位
- 进版版本: 15.2
- 无痕模式上报: 是
- 公共属性: `commey_key`

**上报时机/逻辑**:

名站：名站处于可见状态时打点
宫格：宫格页面展示时进行宫格每一项的宫格打点


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能 | string | grids：宫格 site：名站 banner_abnormity：异形banner banner_personal：个人中心banner banner_channel ：频道banner headpicture：头图 floatinglayer：浮层 popup：弹窗 bubble：气泡 covid：抗疫 |  |
| `icon_id` | 站点id | string | covid_1:海外疫情 covid_2:最新进展 covid_3:本地疫情 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能)
- 类型: string
- 取值:
  grids：宫格
  site：名站
  banner_abnormity：异形banner
  banner_personal：个人中心banner
  banner_channel ：频道banner
  headpicture：头图
  floatinglayer：浮层
  popup：弹窗
  bubble：气泡
  covid：抗疫

</details>


### `icon_click` — 图标_点击

- 分类: 资源位
- 进版版本: 15.2
- 无痕模式上报: 是
- 公共属性: `commey_key`

**上报时机/逻辑**:

对某一项进行点击时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能 | string | grids：宫格 site：名站 banner_abnormity：异形banner banner_personal：个人中心banner banner_channel ：频道banner headpicture：头图 floatinglayer：浮层 popup：弹窗 bubble：气泡 covid：抗疫 |  |
| `icon_id` | 站点id | string | covid_1:海外疫情 covid_2:最新进展 covid_3:本地疫情 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能)
- 类型: string
- 取值:
  grids：宫格
  site：名站
  banner_abnormity：异形banner
  banner_personal：个人中心banner
  banner_channel ：频道banner
  headpicture：头图
  floatinglayer：浮层
  popup：弹窗
  bubble：气泡
  covid：抗疫

</details>


### `icon_slots_expose` — 站点_曝光

- 分类: 宫格
- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `commey_key`

**上报时机/逻辑**:

曝光时上报；整个页面报一个


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能 | string | grids：宫格 |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |

### `icon_slots_click` — 站点_点击

- 分类: 宫格
- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `commey_key`

**上报时机/逻辑**:

完成相关功能时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能 | string | grids：宫格 |  |
| `operation` | 操作 | string | click_item：书签点击 add _to_desktop：添加到桌面 |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |

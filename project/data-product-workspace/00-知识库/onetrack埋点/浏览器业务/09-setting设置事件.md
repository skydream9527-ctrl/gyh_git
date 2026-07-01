# 浏览器 - setting设置事件

> 来源 sheet: `setting设置事件` | 事件数: 6 | 参数数: 10


## 事件总览

| # | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|
| 1 | `setting_click` | 设置 | 设置成功时上报 | 4 | common key | 14.6 |
| 2 | `setting_ad_rec_click` | 设置_个性化广告推荐_点击 | 用户点击"个性化广告推荐"，状态切换成功时上报。 | 1 | commen key |  |
| 3 | `setting_content_rec_click` | 设置_个性化内容推荐_点击 | 用户点击"个性化内容推荐"，状态切换成功时上报。 | 1 | commen key |  |
| 4 | `setting_homepage_expose` | 设置主页_曝光 | 在设置页面曝光时上报（只包含一级页面） | 0 | common key | 15.8 |
| 5 | `setting_homepage_click` | 设置主页_点击 | 在设置页面发生功能按钮点击时上报（只包含一级页面的功能） | 2 | common key | 15.8 |
| 6 | `fluency_auto_settings_click` | 网页浏览设置自动畅读开关上报 | 点击网页浏览设置中自动开启畅读时上报 | 2 | common key | 15.8 |

---

## 事件详情

### `setting_click` — 设置

- 进版版本: 14.6
- 公共属性: `common key`

**上报时机/逻辑**:

设置成功时上报


**参数列表** (4):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` |  | string | 桌面搜索框_桌面搜索框 桌面搜索框_桌面搜索框风格 桌面搜索框_应用建议 桌面搜索框_热搜榜单 桌面搜索框_搜索历史 搜索_搜索项_应用 搜索_搜索项_设置 |  |
| `action` |  | string | set delete |  |
| `status` |  | string | 开/关 经典/精选 |  |
| `value` |  | string | 应用建议设置中删除屏蔽app时，值为对应的应用名 其他为空 |  |

<details><summary>参数取值详情</summary>


**`function`** ()
- 类型: string
- 取值:
  桌面搜索框_桌面搜索框
  桌面搜索框_桌面搜索框风格
  桌面搜索框_应用建议
  桌面搜索框_热搜榜单
  桌面搜索框_搜索历史
  搜索_搜索项_应用
  搜索_搜索项_设置

</details>


### `setting_ad_rec_click` — 设置_个性化广告推荐_点击

- 公共属性: `commen key`

**上报时机/逻辑**:

用户点击"个性化广告推荐"，状态切换成功时上报。


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `status` | 操作后的状态 | string | on：打开 off：关闭 |  |

### `setting_content_rec_click` — 设置_个性化内容推荐_点击

- 公共属性: `commen key`

**上报时机/逻辑**:

用户点击"个性化内容推荐"，状态切换成功时上报。


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `status` | 操作后的状态 | string | on：打开 off：关闭 |  |

### `setting_homepage_expose` — 设置主页_曝光

- 进版版本: 15.8
- 公共属性: `common key`

**上报时机/逻辑**:

在设置页面曝光时上报（只包含一级页面）


_(无独立参数,仅携带公共属性)_


### `setting_homepage_click` — 设置主页_点击

- 进版版本: 15.8
- 公共属性: `common key`

**上报时机/逻辑**:

在设置页面发生功能按钮点击时上报（只包含一级页面的功能）


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | homepage_settings：主页设置 search_settings：搜索设置 web_browsing_settings：网页浏览设置 security：隐私防护 password_management：密码管理 message_notification_management：消息通知管理 stream_remind：流量监控提醒 confirm_before_exiting：退出前确认 clear_data：清除数据 user_authority_setting：用户权限设置 privacy_and_security：隐私和安全 privacy_policy：隐私政策 cancel… |  |
| `status` | 操作后的状态 | string | on：打开 off：关闭 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 类型: string
- 取值:
  homepage_settings：主页设置
  search_settings：搜索设置
  web_browsing_settings：网页浏览设置
  security：隐私防护
  password_management：密码管理
  message_notification_management：消息通知管理
  stream_remind：流量监控提醒
  confirm_before_exiting：退出前确认
  clear_data：清除数据
  user_authority_setting：用户权限设置
  privacy_and_security：隐私和安全
  privacy_policy：隐私政策
  cancel_account：注销账号
  recall_agree：撤回同意隐私政策
  feedback：意见反馈
  software_version：软件版本
  restore_default_settings：恢复默认设置

</details>


### `fluency_auto_settings_click` — 网页浏览设置自动畅读开关上报

- 进版版本: 15.8
- 公共属性: `common key`

**上报时机/逻辑**:

点击网页浏览设置中自动开启畅读时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `fluency_auto_mode` | 自动开启畅读开关 | string | FastReadOpen：打开 FastReadClose：关闭 |  |
| `element` |  | string |  |  |

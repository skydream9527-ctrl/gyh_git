# 浏览器 - general常规事件

> 来源 sheet: `general常规事件` | 事件数: 29 | 参数数: 48


## 事件总览

| # | 分类 | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|---|
| 1 | 多窗口 | `tabaction_expose` | 多窗口_曝光 | 多窗口页面曝光时上报 | 3 | commey_key | 14.6 |
| 2 | 多窗口 | `tabaction_click` | 多窗口_点击 | 点击相关功能时上报 | 3 | commey_key | 14.6 |
| 3 | 菜单 | `menu_expose` | 菜单_曝光 | 菜单弹窗曝光后上报; 三种情况： 首次出现半屏菜单，不拉出整屏菜单，上报一次"菜单曝光"； 首次出现半屏菜单，拉出整屏菜… | 3 | commey_key | 14.6 |
| 4 | 菜单 | `menu_click` | 菜单_点击 | 点击相关功能时上报 | 5 | commey_key | 14.6 |
| 5 | 书签/历史/本地 | `bookmark_history_local_expose` | 书签/历史/本地_曝光 | 书签/历史/本地页面曝光时上报 | 1 | commey_key | 14.6 |
| 6 | 书签/历史/本地 | `bookmark_history_local_click` | 书签/历史/本地_点击 | 点击相关功能时上报 | 3 | commey_key | 14.6 |
| 7 | 添加书签 | `bookmark_add_toast_expose` | 书签_添加成功toast_曝光 | 书签添加成功toast曝光时上报 | 0 | commey_key | 14.6 |
| 8 | 添加书签 | `bookmark_add_toast_click` | 书签_添加成功toast_点击 | 点击toast中对应功能时上报 | 1 | commey_key | 14.6 |
| 9 | 视频播放器 | `videoplayer_expose` | 视频播放器_曝光 | 视频播放器曝光时上报；不包括信息流里的视频 | 1 | commey_key | 14.6 |
| 10 | 视频播放器 | `videoplayer_click` | 视频播放器_点击 | 点击相应功能时上报；不包括信息流里的视频 | 3 | commey_key | 14.6 |
| 11 | 视频播放器 | `videoplayer_duration` | 视频播放器_使用时长 | 退出视频播放器时上报；不包括信息流里的视频 使用对应的播放器，每个视频从开始使用到退出的时长 退出场景包括：当前页面播放… | 5 | commey_key | 14.6 |
| 12 | 视频播放器 | `videoplayer_download_popup_expose` | 视频播放器_下载弹窗_曝光 | 在网页进行视频播放时，点击视频右下方的下载按钮，下载弹窗曝光时上报 | 0 | common key | 15.8 |
| 13 | 视频播放器 | `videoplayer_download_popup_click` | 视频播放器_下载弹窗_点击 | 在下载弹窗内发生功能按钮（重命名、立即下载）点击时上报 | 1 | common key | 15.8 |
| 14 | 阅读模式 | `readmode_duration` | 阅读模式_浏览时长 | 退出阅读模式时上报 | 2 | commey_key | 14.6 |
| 15 | 看图模式 | `webpicture_popup_expose` | 网页图片_弹窗_曝光 | 长按网页的图片（非信息流），出现弹窗后上报 | 0 | commey_key | 14.6 |
| 16 | 看图模式 | `webpicture_popup_click` | 网页图片_弹窗_点击 | 点击弹窗中的任意功能后上报 | 1 | commey_key | 14.6 |
| 17 | 看图模式 | `picturemode_expose` | 看图模式_曝光 | 进入看图模式页面后上报 | 2 | commey_key | 14.6 |
| 18 | 看图模式 | `picturemode_click` | 看图模式_点击 | 点击相应功能后上报 | 3 | commey_key | 14.6 |
| 19 | 看图模式 | `picturemode_duration` | 看图模式_浏览时长 | 退出看图模式时上报 | 1 | commey_key | 14.6 |
| 20 | 我的视频 | `myvideo_expose` | 我的视频页面_曝光 | 页面曝光时上报 | 1 | commey_key | 14.6 |
| 21 | 我的视频 | `myvideo_click` | 我的视频页面_点击 | 点击对应功能时上报 | 2 | commey_key | 14.6 |
| 22 | 自定义壁纸 | `setting_wallpaper_expose` | 设置壁纸_曝光 | 进入设置壁纸页面时上报 | 1 | commey_key | 14.6 |
| 23 | 自定义壁纸 | `setting_wallpaper_click` | 设置壁纸_点击 |  | 2 | commey_key | 14.6 |
| 24 | 密码保存 | `save_key_expose` | 保存密码弹窗_曝光 | 弹窗曝光时上报 | 0 | commey_key |  |
| 25 | 密码保存 | `save_key_click` | 保存密码弹窗_点击 | 点击弹窗内按钮时上报 | 1 | commey_key |  |
| 26 | 密码保存 | `auto_fill_expose` | 自动填充_曝光 | 密码自动填充曝光时上报 | 0 | commey_key |  |
| 27 | 密码保存 | `key_setting` | 密码管理设置_点击 |  | 2 | commey_key |  |
| 28 | 安全防护 | `safety_protection_panel_expose` | 防护统计面板曝光 | 点击防护按钮，防护统计面板曝光时上报 | 0 | commen key | 15.8 |
| 29 | 安全防护 | `safety_protection_panel_click` | 防护统计面板点击 | 在防护统计面板发生点击时上报 | 1 | commen key |  |

---

## 事件详情

### `tabaction_expose` — 多窗口_曝光

- 分类: 多窗口
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

多窗口页面曝光时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 页面类型 | string | homepage：主页态 webpage：网页态 |  |
| `` | 浏览模式 | string | normal：普通 incognito：无痕 |  |
| `windows_number` | 窗口数量<br>（打开多窗口时，存在的窗口数量） | number |  |  |

### `tabaction_click` — 多窗口_点击

- 分类: 多窗口
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击相关功能时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `browser_mode` | 浏览模式 | string | normal：普通 incognito：无痕 |  |
| `function` | 功能名称 | string | tab模块： window：窗口 tabaction_incognito：无痕  window窗口模块： open window：打开窗口 close window：关闭窗口  button模块： close_all_window：全部关闭 add_window：添加窗口 back：返回 system_back：操作系统返回（不是页面按钮，手机系统手势返回）  “最近关闭”模块（仅“普通模式”有）： recently_closed：打开某条最近关闭的网页 delete_recently_closed：删除某条最近关闭的网页 recently_empty：清空最近关闭的网页 hide_recen… |  |
| `is_empty` | 多窗口是否为空<br>（操作前是否存在窗口） | boolean | true：多窗口为空 false：多窗口内存在窗口 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 类型: string
- 取值:
  tab模块：
  window：窗口
  tabaction_incognito：无痕
  
  window窗口模块：
  open window：打开窗口
  close window：关闭窗口
  
  button模块：
  close_all_window：全部关闭
  add_window：添加窗口
  back：返回
  system_back：操作系统返回（不是页面按钮，手机系统手势返回）
  
  “最近关闭”模块（仅“普通模式”有）：
  recently_closed：打开某条最近关闭的网页
  delete_recently_closed：删除某条最近关闭的网页
  recently_empty：清空最近关闭的网页
  hide_recently_closed：隐藏最近关闭模块
  display_recently_closed：取消隐藏最近关闭

</details>


### `menu_expose` — 菜单_曝光

- 分类: 菜单
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

菜单弹窗曝光后上报;
三种情况：
首次出现半屏菜单，不拉出整屏菜单，上报一次"菜单曝光"；
首次出现半屏菜单，拉出整屏菜单，上报一次"菜单曝光"，上报一次"整屏菜单曝光"；
首次出现整屏菜单，上报一次"整屏菜单曝光"，上报一次"菜单曝光"。


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `expose_type` | 曝光类型 | string | general：菜单曝光 full_menu：整屏菜单曝光 |  |
| `page_type` | 页面类型 | string | homepage：主页态 webpage：网页态 |  |
| `screen_orientation` | 屏幕方向 | string | vertical：竖屏 horizontal：横屏 |  |

### `menu_click` — 菜单_点击

- 分类: 菜单
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击相关功能时上报


**参数列表** (5):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 |  | account：账号/头像 exit：退出 refresh：刷新 bookmark_history：书签/历史 download：我的下载 bookshelf：小说书架 video：我的视频 preference：设置 night_mode：深色模式开关 incognito：无痕模式 add_shortcut：添加书签 add _to_desktop：添加到桌面 set_user_agent：访问网页版 share：分享 fullscreen：全屏模式 bandwidth：智能无图 webpage_text_size：网页文字大小 save_page：保存离线网页 find_on_page：页… |  |
| `screen_orientation` | 屏幕方向 | string | vertical：竖屏 horizontal：横屏 |  |
| `page_type` | 操作发生的页面类型 | string | homepage：主页态 webpage：网页态 |  |
| `source` | 来源 | string | function_guide：功能引导动画 menu：菜单 (用于嗅探、阅读场景) |  |
| `status` | 状态<br>（操作前的状态） | string | on：打开 off：关闭 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 取值:
  account：账号/头像
  exit：退出
  refresh：刷新
  bookmark_history：书签/历史
  download：我的下载
  bookshelf：小说书架
  video：我的视频
  preference：设置
  night_mode：深色模式开关
  incognito：无痕模式
  add_shortcut：添加书签
  add _to_desktop：添加到桌面
  set_user_agent：访问网页版
  share：分享
  fullscreen：全屏模式
  bandwidth：智能无图
  webpage_text_size：网页文字大小
  save_page：保存离线网页
  find_on_page：页面查找
  translate：网页翻译
  custom_layout：自定义布局
  picture_mode：看图模式
  resources_sniff：资源嗅探
  reading_mode：阅读模式
  noval_mode：畅读模式
  port_netdisc：网盘

</details>


### `bookmark_history_local_expose` — 书签/历史/本地_曝光

- 分类: 书签/历史/本地
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

书签/历史/本地页面曝光时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 操作发生的页面 | string | bookmark：书签 history：历史 local：本地 |  |

### `bookmark_history_local_click` — 书签/历史/本地_点击

- 分类: 书签/历史/本地
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击相关功能时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 操作发生的页面 | string | bookmark：书签 history：历史 local：本地 |  |
| `module` | 模块名称 | string | list：列表 search_list：搜索列表 bottom：底栏 |  |
| `function` | 操作的功能名称 | string | 1. page_name=书签 1）module_name=list时： click_item：书签点击 open_in_background_window：后台窗口打开 edit_item：编辑书签 delet_item：删除书签 click_folder：文件夹 delet_folder：删除文件夹 edit_folder：编辑组名  2）module_name=search_list时： click_item：书签点击 open_in_background_window：后台窗口打开 edit_item：编辑书签 delet_item：删除书签  3）module_name=bottom… |  |

<details><summary>参数取值详情</summary>


**`function`** (操作的功能名称)
- 类型: string
- 取值:
  1. page_name=书签
  1）module_name=list时：
  click_item：书签点击
  open_in_background_window：后台窗口打开
  edit_item：编辑书签
  delet_item：删除书签
  click_folder：文件夹
  delet_folder：删除文件夹
  edit_folder：编辑组名
  
  2）module_name=search_list时：
  click_item：书签点击
  open_in_background_window：后台窗口打开
  edit_item：编辑书签
  delet_item：删除书签
  
  3）module_name=bottom时：
  import_bookmark：导入书签
  add_bookmark：添加书签
  add_group：添加分组
  edit_item：编辑书签
  点击"导入书签"后：
  import_bookmark_start：开始导入
  import_bookmark__tutorial：查看教程
  import_bookmark_file：文件管理
  import_bookmark_confirm：确认导入
  
  2.page_name=历史：
  1）module_name=list时：
  video_history：视频历史入口
  click_video_item：视频历史条目点击
  click_item：历史条目点击
  
  2）module_name=search_list时：
  click_item：历史条目点击
  open_in_background_window:在后台窗口打开
  add_bookmark:添加书签
  delet:从历史记录删除
  
  3）module_name=bottom时：
  clear_history：清除历史
  edit_item：编辑
  
  3.page_name=本地时
  1）module_name=list时：
  click_item：本地条目点击
  delet_item：删除单条
  
  2）module_name=search_list时：
  click_item：本地条目点击
  delet_item：删除单条
  
  3）module_name=bottom时：
  clear_local_page：清除本地

</details>


### `bookmark_add_toast_expose` — 书签_添加成功toast_曝光

- 分类: 添加书签
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

书签添加成功toast曝光时上报


_(无独立参数,仅携带公共属性)_


### `bookmark_add_toast_click` — 书签_添加成功toast_点击

- 分类: 添加书签
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击toast中对应功能时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 操作的功能名称 | string | bookmark_add_homepage：添加到浏览器主页 edit：编辑 |  |

### `videoplayer_expose` — 视频播放器_曝光

- 分类: 视频播放器
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

视频播放器曝光时上报；不包括信息流里的视频


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `source` | 来源 | string | onlin_vieo_player：网页视频 local_vieo_player：本地视频 |  |

### `videoplayer_click` — 视频播放器_点击

- 分类: 视频播放器
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击相应功能时上报；不包括信息流里的视频


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `videoplayer_type` | 视频播放器类型 | string | full_video：全屏视频播放器 inline_video：小屏视频播放器 float_video：小窗视频播放器 |  |
| `source` | 来源 | string | onlin_vieo_player：网页视频 local_vieo_player：本地视频 |  |
| `function` | 操作的功能名称 | string | videoplayer_type=full_video时： full_stop：暂停 full_back：返回 full_floating_window：小窗 full_cast_screen：投屏 lock_screen：锁屏 full_download：下载 download_check：点击查看 double_speed：倍速 double_speed_0.75：0.75倍速 double_speed_1.0：1.0倍速 double_speed_1.25：1.25倍速 double_speed_1.5：1.5倍速 double_speed_2.0：2.0倍速 double_speed_… |  |

<details><summary>参数取值详情</summary>


**`function`** (操作的功能名称)
- 类型: string
- 取值:
  videoplayer_type=full_video时：
  full_stop：暂停
  full_back：返回
  full_floating_window：小窗
  full_cast_screen：投屏
  lock_screen：锁屏
  full_download：下载
  download_check：点击查看
  double_speed：倍速
  double_speed_0.75：0.75倍速
  double_speed_1.0：1.0倍速
  double_speed_1.25：1.25倍速
  double_speed_1.5：1.5倍速
  double_speed_2.0：2.0倍速
  double_speed_3.0：3.0倍速
  copy_link：复制链接
  add_bookmark：收藏
  feedback_click：反馈
  share_click：分享
  size_adaptive：自适应
  size_stretch：全屏拉伸
  size_tailoring：放大剪裁
  long_press：长按倍速
  big_next：屏幕中间的下一个
  re_play：重播
  last：上一个
  small_next：暂停旁边的下一个
  save_netdisc：存网盘
  enter_netdisc：去网盘
  
  videoplayer_type=inline_video时：
  inline_floating_window：小窗
  inline_download：下载
  inline_full_screen：全屏
  
  videoplayer_type=float_video时：
  floating_full_screen：全屏
  close_floating：关闭小窗
  fast_forward：快进10s
  rewind：快退10s

</details>


### `videoplayer_duration` — 视频播放器_使用时长

- 分类: 视频播放器
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

退出视频播放器时上报；不包括信息流里的视频
使用对应的播放器，每个视频从开始使用到退出的时长
退出场景包括：当前页面播放视频时按back键返回到上个页面 /  关闭当前视频播放的页面 /  多窗口中关闭未回收视频播放器的窗口 / 播放器长时间未使用被回收 / 杀App


**参数列表** (5):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `videoplayer_type` | 视频播放器类型 | string | full_video：全屏视频播放器 inline_video：小屏视频播放器 float_video：小窗视频播放器 |  |
| `source` | 来源 | string | onlin_vieo_player：网页视频 local_vieo_player：本地视频 |  |
| `duration` | 时长 | number | 单位：毫秒 |  |
| `item_percent` | 视频播放进度 | number | 退出后记录percent，百分比例如  0/1/50/100，保留整数，多次播放记最大值 进度条播放长度 / 视频本身长度 |  |
| `controls_type` | 控件 类型 | string | chromium_video：网页原生播放器 miui_video：miui播放器 app_control：app原生 |  |

<details><summary>参数取值详情</summary>


**`item_percent`** (视频播放进度)
- 类型: number
- 取值:
  退出后记录percent，百分比例如  0/1/50/100，保留整数，多次播放记最大值
  进度条播放长度 / 视频本身长度

</details>


### `videoplayer_download_popup_expose` — 视频播放器_下载弹窗_曝光

- 分类: 视频播放器
- 进版版本: 15.8
- 公共属性: `common key`

**上报时机/逻辑**:

在网页进行视频播放时，点击视频右下方的下载按钮，下载弹窗曝光时上报


_(无独立参数,仅携带公共属性)_


### `videoplayer_download_popup_click` — 视频播放器_下载弹窗_点击

- 分类: 视频播放器
- 进版版本: 15.8
- 公共属性: `common key`

**上报时机/逻辑**:

在下载弹窗内发生功能按钮（重命名、立即下载）点击时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | rename：重命名 download：立即下载 |  |

### `readmode_duration` — 阅读模式_浏览时长

- 分类: 阅读模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

退出阅读模式时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 时长 | string | 单位：毫秒 |  |
| `domain` | 域名 | string |  |  |

### `webpicture_popup_expose` — 网页图片_弹窗_曝光

- 分类: 看图模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

长按网页的图片（非信息流），出现弹窗后上报


_(无独立参数,仅携带公共属性)_


### `webpicture_popup_click` — 网页图片_弹窗_点击

- 分类: 看图模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击弹窗中的任意功能后上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | picture_mode：进入看图模式 save_picture：保存图片 share_pictures：分享图片 |  |

### `picturemode_expose` — 看图模式_曝光

- 分类: 看图模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

进入看图模式页面后上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `source` | 来源 | string | long_press：长按网页图片 menu：菜单 resources_sniff：资源嗅探 grid_view：网格 full_view：大图 |  |
| `page_type` | 页面类型 | string | full_view：大图模式页面 grid_view：网格视图页面 |  |

<details><summary>参数取值详情</summary>


**`source`** (来源)
- 类型: string
- 取值:
  long_press：长按网页图片
  menu：菜单
  resources_sniff：资源嗅探
  grid_view：网格
  full_view：大图

</details>


### `picturemode_click` — 看图模式_点击

- 分类: 看图模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击相应功能后上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | share_pictures：分享 grid_view：网格视图 copy_link：复制链接 save_picture：保存 click_picture：点开图片 multiple_choice：选择（包括点击页面右上角选择按钮和长按图片两种方式） HD_pic：切换到高清大图 all_pic：切换到全部图片 |  |
| `source` | 来源 | string | long_press：长按 menu：菜单 resources_sniff：资源嗅探 grid_view：网格 full_view：大图 |  |
| `page_type` | 页面 | string | full_view：大图模式页面 grid_view：网格视图页面 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 类型: string
- 取值:
  share_pictures：分享
  grid_view：网格视图
  copy_link：复制链接
  save_picture：保存
  click_picture：点开图片
  multiple_choice：选择（包括点击页面右上角选择按钮和长按图片两种方式）
  HD_pic：切换到高清大图
  all_pic：切换到全部图片

**`source`** (来源)
- 类型: string
- 取值:
  long_press：长按
  menu：菜单
  resources_sniff：资源嗅探
  grid_view：网格
  full_view：大图

</details>


### `picturemode_duration` — 看图模式_浏览时长

- 分类: 看图模式
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

退出看图模式时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `duration` | 浏览时长 | number | 单位：毫秒 |  |

### `myvideo_expose` — 我的视频页面_曝光

- 分类: 我的视频
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

页面曝光时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 操作发生的页面 | string | local_video：本地缓存 netdisc_video：网盘视频 |  |

### `myvideo_click` — 我的视频页面_点击

- 分类: 我的视频
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击对应功能时上报


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `page_type` | 操作发生的页面 | string | local_video：本地缓存 netdisc_video：网盘视频 |  |
| `function` | 操作的功能名称 | string | page_name=local_video时： video_item_click：视频条目点击 video_copy_link：复制网页链接 video_orig_link：访问原网页 rename：重命名 clear_video：删除全部 edit：编辑 delet_item：删除单条  page_name=netdisc_video时： enter_netdisc：去网盘 video_item_click：视频条目点击 |  |

<details><summary>参数取值详情</summary>


**`function`** (操作的功能名称)
- 类型: string
- 取值:
  page_name=local_video时：
  video_item_click：视频条目点击
  video_copy_link：复制网页链接
  video_orig_link：访问原网页
  rename：重命名
  clear_video：删除全部
  edit：编辑
  delet_item：删除单条
  
  page_name=netdisc_video时：
  enter_netdisc：去网盘
  video_item_click：视频条目点击

</details>


### `setting_wallpaper_expose` — 设置壁纸_曝光

- 分类: 自定义壁纸
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`

**上报时机/逻辑**:

进入设置壁纸页面时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `source` | 来源 | string | home：长按简洁版主页进入 setting：设置页进入 |  |

### `setting_wallpaper_click` — 设置壁纸_点击

- 分类: 自定义壁纸
- 进版版本: 14.6
- 无痕模式上报: 否
- 公共属性: `commey_key`


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | recovery_standard：恢复默认 logo：隐藏/显示logo icon：白色/黑色图标 select_image：选择图片 confirm：确认（右上方√按钮） cancel：取消（左上方←按钮） back：操作系统back，左滑等非页面上按钮进行的back，离开页面就算 |  |
| `status` | 状态<br>（操作后的状态） | string | hide：隐藏logo display：显示logo light：图标为白色 dark：图标为黑色 |  |

<details><summary>参数取值详情</summary>


**`function`** (功能名称)
- 类型: string
- 取值:
  recovery_standard：恢复默认
  logo：隐藏/显示logo
  icon：白色/黑色图标
  select_image：选择图片
  confirm：确认（右上方√按钮）
  cancel：取消（左上方←按钮）
  back：操作系统back，左滑等非页面上按钮进行的back，离开页面就算

</details>


### `save_key_expose` — 保存密码弹窗_曝光

- 分类: 密码保存
- 公共属性: `commey_key`

**上报时机/逻辑**:

弹窗曝光时上报


_(无独立参数,仅携带公共属性)_


### `save_key_click` — 保存密码弹窗_点击

- 分类: 密码保存
- 公共属性: `commey_key`

**上报时机/逻辑**:

点击弹窗内按钮时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | cancel：取消/空白处 un_save：一律不保存 save：保存 |  |

### `auto_fill_expose` — 自动填充_曝光

- 分类: 密码保存
- 公共属性: `commey_key`

**上报时机/逻辑**:

密码自动填充曝光时上报


_(无独立参数,仅携带公共属性)_


### `key_setting` — 密码管理设置_点击

- 分类: 密码保存
- 公共属性: `commey_key`


**参数列表** (2):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能名称 | string | save_key:密码保存 auto_fill:自动填充 |  |
| `status` | 状态 | string | on：开 off：关 |  |

### `safety_protection_panel_expose` — 防护统计面板曝光

- 分类: 安全防护
- 进版版本: 15.8
- 公共属性: `commen key`

**上报时机/逻辑**:

点击防护按钮，防护统计面板曝光时上报


_(无独立参数,仅携带公共属性)_


### `safety_protection_panel_click` — 防护统计面板点击

- 分类: 安全防护
- 公共属性: `commen key`

**上报时机/逻辑**:

在防护统计面板发生点击时上报


**参数列表** (1):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `function` | 功能 | string | protect_manage：防护管理 more_setting：更多设置 item：条目 |  |

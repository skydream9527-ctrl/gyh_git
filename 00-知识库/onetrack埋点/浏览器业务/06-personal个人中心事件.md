# 浏览器 - personal个人中心事件

> 来源 sheet: `personal个人中心事件` | 事件数: 6 | 参数数: 18


## 事件总览

| # | 分类 | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|---|
| 1 | 个人中心-曝光_客户端 | `personal_center_expose_client` | 个人中心_页面_曝光_客户端 | 点击底部工具栏“我的”进入个人中心，个人中心整个页面曝光时上报 | 0 | common key | 15.6 |
| 2 | 个人中心-曝光_前端 | `personal_center_expose_front` | 个人中心_页面_曝光_前端 | 点击底部工具栏“我的”进入个人中心，个人中心整个页面曝光时上报 | 0 | common key | 15.6 |
| 3 | 个人中心-曝光 | `personal_center_game_expose_client` | 个人中心_游戏_曝光_客户端 | 点击底部工具栏“我的”进入个人中心，个人中心各个游戏曝光时上报 | 3 | common key | 15.6 |
| 4 | 个人中心-曝光 | `personal_center_game_expose_front` | 个人中心_游戏_曝光_前端 | 点击底部工具栏“我的”进入个人中心，个人中心各个游戏曝光时上报 | 3 | common key | 15.6 |
| 5 | 个人中心_点击 | `personal_center_click_client` | 个人中心_页面_点击_客户端 | 进入个人中心页面，页面发生点击时上报 | 6 | common key | 15.6 |
| 6 | 个人中心_点击 | `personal_center_click_front` | 个人中心_页面_点击_前端 | 进入个人中心页面，页面发生点击时上报 | 6 | common key | 15.6 |

---

## 事件详情

### `personal_center_expose_client` — 个人中心_页面_曝光_客户端

- 分类: 个人中心-曝光_客户端
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

点击底部工具栏“我的”进入个人中心，个人中心整个页面曝光时上报


_(无独立参数,仅携带公共属性)_


### `personal_center_expose_front` — 个人中心_页面_曝光_前端

- 分类: 个人中心-曝光_前端
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

点击底部工具栏“我的”进入个人中心，个人中心整个页面曝光时上报


_(无独立参数,仅携带公共属性)_


### `personal_center_game_expose_client` — 个人中心_游戏_曝光_客户端

- 分类: 个人中心-曝光
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

点击底部工具栏“我的”进入个人中心，个人中心各个游戏曝光时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `game_position` | 游戏位置 | number |  |  |
| `game_id` | 游戏id | string |  |  |
| `game_name` | 游戏名称 | string |  |  |

### `personal_center_game_expose_front` — 个人中心_游戏_曝光_前端

- 分类: 个人中心-曝光
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

点击底部工具栏“我的”进入个人中心，个人中心各个游戏曝光时上报


**参数列表** (3):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `game_position` | 游戏位置 | number | 0，1，2，3 |  |
| `game_id` | 游戏id | string |  |  |
| `game_name` | 游戏名称 | string |  |  |

### `personal_center_click_client` — 个人中心_页面_点击_客户端

- 分类: 个人中心_点击
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

进入个人中心页面，页面发生点击时上报


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `module` | 模块点击 | string | account_module：头像模块 function_module：功能模块 action_center_module：活动中心模块 novel_module：小说模块 game_module：游戏模块 file_module：文件模块 |  |
| `function` | 功能点击 | string | 头像模块：     log_on：登录    profile：头像    sign：签到    sign_in：已签到     set：设置  功能模块：     bookmark_history：书签历史     download：我的下载     bookshelf：小说书架     video：我的视频     message：消息     netdisc：网盘     night_mode：夜间模式     incognito_mode：无痕模式     to_PC：访问电脑版     baidu：百度  文件模块：     apk：安装包     jpg：图片     avi：视频 … |  |
| `book_name` | 书籍名称 | string |  |  |
| `book_id` | 书籍id | string |  |  |
| `game_id` | 游戏id | string |  |  |
| `game_name` | 游戏名称 | string |  |  |

<details><summary>参数取值详情</summary>


**`module`** (模块点击)
- 类型: string
- 取值:
  account_module：头像模块
  function_module：功能模块
  action_center_module：活动中心模块
  novel_module：小说模块
  game_module：游戏模块
  file_module：文件模块

**`function`** (功能点击)
- 类型: string
- 取值:
  头像模块：
      log_on：登录
     profile：头像
     sign：签到
     sign_in：已签到
      set：设置
  
  功能模块：
      bookmark_history：书签历史
      download：我的下载
      bookshelf：小说书架
      video：我的视频
      message：消息
      netdisc：网盘
      night_mode：夜间模式
      incognito_mode：无痕模式
      to_PC：访问电脑版
      baidu：百度
  
  文件模块：
      apk：安装包
      jpg：图片
      avi：视频
      zip：压缩包
      doc：文档
      more_info：更多
      jpg_file：历史文件_非图片类
      non_jpg_file历史文件_图片类
      today_file：今天文件
      yesterday_file：昨天文件
      old_file：更早文件

</details>


### `personal_center_click_front` — 个人中心_页面_点击_前端

- 分类: 个人中心_点击
- 进版版本: 15.6
- 公共属性: `common key`

**上报时机/逻辑**:

进入个人中心页面，页面发生点击时上报


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `module` | 模块点击 | string | account_module：头像模块 function_module：功能模块 action_center_module：活动中心模块 novel_module：小说模块 game_module：游戏模块 |  |
| `function` | 功能点击 | string | 头像模块：     log_on：立即登录     profile：头像    sign：签到    sign_in：已签到  功能模块：     bookmark_history：书签历史     download：我的下载     bookshelf：小说书架     video：我的视频     message：消息     netdisc：网盘     night_mode：夜间模式  活动中心模块： red_envelope：我的红包 gold_coins：我的金币 gold_coins_entrance：金币领取入口 mission_position0_gofor：任务0_去完成 … |  |
| `book_name` | 书籍名称 | string |  |  |
| `book_id` | 书籍id | string |  |  |
| `game_id` | 游戏id | string |  |  |
| `game_name` | 游戏名称 | string |  |  |

<details><summary>参数取值详情</summary>


**`module`** (模块点击)
- 类型: string
- 取值:
  account_module：头像模块
  function_module：功能模块
  action_center_module：活动中心模块
  novel_module：小说模块
  game_module：游戏模块

**`function`** (功能点击)
- 类型: string
- 取值:
  头像模块：
      log_on：立即登录
      profile：头像
     sign：签到
     sign_in：已签到
  
  功能模块：
      bookmark_history：书签历史
      download：我的下载
      bookshelf：小说书架
      video：我的视频
      message：消息
      netdisc：网盘
      night_mode：夜间模式
  
  活动中心模块：
  red_envelope：我的红包
  gold_coins：我的金币
  gold_coins_entrance：金币领取入口
  mission_position0_gofor：任务0_去完成
  mission_position0_getwards：任务0_领取奖励
  mission_position1_gofor：任务1_去完成
  mission_position1_getwards：任务1_领取奖励
  
  小说模块：
  novel_position_0：小说位置0
  novel_position_1：小说位置1
  novel_position_2：小说位置2
  novel_position_3：小说位置3
  
  游戏模块：
  game_position_0：游戏位置0
  game_position_1：游戏位置1
  game_position_2：游戏位置2
  game_position_3：游戏位置3

</details>


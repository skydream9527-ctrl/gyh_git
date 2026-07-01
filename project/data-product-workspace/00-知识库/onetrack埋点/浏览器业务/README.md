# 浏览器业务 - OneTrack 埋点现状

> 数据来源: `浏览器新版OneTrack埋点汇总（可用于神策、数鲸）.xlsx`

## 业务元信息

| 项 | 值 |
|---|---|
| appid | 31000000442 \| 属性 \| 说明 |
| 项目名称 | 浏览器new \| OneTrack SDK系统属性 \| OneTrack SDK自动采集的属性，每个事件都携带这些属性 |
| hive表 | dw.dwd_ot_event_di_31000000442 \| commen key公共属性 \| 业务定义的公共属性，每个事件都携带这些属性 |
| 数鲸地址 | https://s.mi.cn/HCA7W9 \| content key信息流通用属性 \| 业务定义的信息流属性，每个信息流事件都携带这些属性 |
| 神策地址 | https://sensorsdataweb.browser.miui.com |
| 埋点管理平台 | https://onetrack.bi.mi.com/#/dashboard?projectId=536&realAppId=31000000442 |
| 数据工厂地址 | 【内部】头条转发数据埋点信息 \| 浏览器信息流CP转发规则-基于OneTrack |
| 帮助文档 | 头条转发数据核对SQL |
| 神策使用Q&A | 神策使用 Q&A |
| 数据使用 | 浏览器OneTrack埋点数据使用分享 |

> 📄 appid/hive表/数鲸/神策地址等元信息见 [00-业务说明.md](00-业务说明.md)

## 现状概览

| 维度 | 数量 |
|---|---|
| 事件模块 | 20 |
| 事件总数 | 259 |
| 事件参数总数 | 946 |
| 预置/公共属性 | 103 |

## 事件模块

| # | 模块 | 事件数 | 参数数 | 文档 |
|---|---|---|---|---|
| 1 | app浏览器全局事件 | 12 | 52 | [01-app浏览器全局事件.md](01-app浏览器全局事件.md) |
| 2 | content信息流事件 | 45 | 105 | [02-content信息流事件.md](02-content信息流事件.md) |
| 3 | search搜索事件 | 20 | 119 | [03-search搜索事件.md](03-search搜索事件.md) |
| 4 | livestream直播事件 | 2 | 8 | [04-livestream直播事件.md](04-livestream直播事件.md) |
| 5 | ad商业化事件 | 51 | 244 | [05-ad商业化事件.md](05-ad商业化事件.md) |
| 6 | personal个人中心事件 | 6 | 18 | [06-personal个人中心事件.md](06-personal个人中心事件.md) |
| 7 | icon_slots站点事件 | 4 | 9 | [07-icon_slots站点事件.md](07-icon_slots站点事件.md) |
| 8 | general常规事件 | 29 | 48 | [08-general常规事件.md](08-general常规事件.md) |
| 9 | setting设置事件 | 6 | 10 | [09-setting设置事件.md](09-setting设置事件.md) |
| 10 | 信息流热榜内容事件 | 4 | 10 | [10-信息流热榜内容事件.md](10-信息流热榜内容事件.md) |
| 11 | 工程埋点 | 6 | 36 | [11-工程埋点.md](11-工程埋点.md) |
| 12 | novel小说事件 | 3 | 9 | [12-novel小说事件.md](12-novel小说事件.md) |
| 13 | 热榜事件 | 11 | 19 | [13-热榜事件.md](13-热榜事件.md) |
| 14 | button_bar底部工具栏事件 | 3 | 9 | [14-button_bar底部工具栏事件.md](14-button_bar底部工具栏事件.md) |
| 15 | download下载事件 | 2 | 11 | [15-download下载事件.md](15-download下载事件.md) |
| 16 | 下载拦截事件 | 3 | 22 | [16-下载拦截事件.md](16-下载拦截事件.md) |
| 17 | 搜索_安全网址事件(服务端) | 1 | 16 | [17-搜索_安全网址事件-服务端.md](17-搜索_安全网址事件-服务端.md) |
| 18 | 浏览器Push事件 | 6 | 34 | [18-浏览器Push事件.md](18-浏览器Push事件.md) |
| 19 | AI搜索 | 40 | 161 | [19-AI搜索.md](19-AI搜索.md) |
| 20 | AI浏览器 | 5 | 6 | [20-AI浏览器.md](20-AI浏览器.md) |

## 预置与公共属性

| # | 属性集 | 属性数 | 文档 |
|---|---|---|---|
| 1 | OneTrack SDK 系统属性 | 32 | [预置属性-OneTrack-SDK-系统属性.md](预置属性-OneTrack-SDK-系统属性.md) |
| 2 | common key 公共属性 | 40 | [预置属性-common-key-公共属性.md](预置属性-common-key-公共属性.md) |
| 3 | content key 信息流通用属性 | 31 | [预置属性-content-key-信息流通用属性.md](预置属性-content-key-信息流通用属性.md) |

## 附录

- [接入tips](附录/接入tips.md) (10 行)
- [bugfix 修复记录](附录/bugfix-修复记录.md) (7 行)
- [打点细节记录](附录/打点细节记录.md) (9 行)
- [页面定义(page/module 枚举)](附录/页面定义-page/module-枚举.md) (59 行)
- [安全网址过滤规则](附录/安全网址过滤规则.md) (7 行)

## 查询方式

- 按事件名查询: 见顶层 [索引/按事件名检索.md](../索引/按事件名检索.md) 或 [索引/全局事件索引.json](../索引/全局事件索引.json)
- 按参数名查询: 见 [索引/全局参数索引.json](../索引/全局参数索引.json)
- 程序化查询: `jq '.["app_open"]' 索引/全局事件索引.json`

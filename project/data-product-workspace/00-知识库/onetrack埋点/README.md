# OneTrack 埋点现状知识库

> 本知识库从两份 OneTrack 埋点 Excel 提炼,按 **两个业务** 组织,完整记录每个业务的 **埋点模块、事件、参数** 现状,并提供可索引查询结构。

## 数据来源

| 业务 | 源文件 | 模块数 | 事件数 | 参数数 | 预置属性 |
|---|---|---|---|---|---|
| 内容中心 | `内容中心onetrack埋点(三期)  带沉浸式.xlsx` | 12 | 119 | 499 | 97 |
| 浏览器 | `浏览器新版OneTrack埋点汇总（可用于神策、数鲸）.xlsx` | 20 | 259 | 946 | 103 |

## 目录结构

```
onetrack埋点/
├── README.md                     ← 本文件(总入口)
├── 内容中心业务/
│   ├── README.md                 ← 业务总览 + 模块导航
│   ├── 预置属性-*.md             ← common key / content key
│   ├── 01-app通用.md …           ← 各事件模块
│   └── _data.json                ← 完整结构化数据
├── 浏览器业务/
│   ├── README.md
│   ├── 预置属性-*.md             ← SDK系统属性 / common key / content key
│   ├── 01-app浏览器全局事件.md …
│   ├── 附录/                     ← 接入tips / bugfix / 页面定义 / 细节记录
│   └── _data.json
└── 索引/
    ├── 全局事件索引.json          ← event_en -> {业务: 事件+参数}
    ├── 全局参数索引.json          ← param_en -> 使用位置列表
    ├── 按事件名检索.md            ← 事件名平铺表(跨业务对比)
    ├── 按参数名检索.md            ← 参数名平铺表
    └── 按模块索引.md              ← 业务->模块->文档
```

## 检索指南

| 我想… | 去哪查 |
|---|---|
| 看某业务全貌 | [内容中心业务/README.md](内容中心业务/README.md) / [浏览器业务/README.md](浏览器业务/README.md) |
| 查某事件名的定义和参数 | [索引/按事件名检索.md](索引/按事件名检索.md) 或 `索引/全局事件索引.json` |
| 查某参数名被哪些事件使用 | [索引/按参数名检索.md](索引/按参数名检索.md) 或 `索引/全局参数索引.json` |
| 按模块浏览 | [索引/按模块索引.md](索引/按模块索引.md) |
| 看公共属性定义 | 各业务下 `预置属性-*.md` |
| 看 page/module 取值字典 | [浏览器业务/附录/页面定义.md](浏览器业务/附录/页面定义.md) |

### 程序化查询示例

```bash
# 查 app_open 事件在两个业务里的定义
jq '.["app_open"]' "索引/全局事件索引.json"

# 查 page 参数被哪些事件使用
jq '.["page"]' "索引/全局参数索引.json"

# 列出浏览器业务所有事件名
jq 'to_entries[] | select(.value.browser) | .key' "索引/全局事件索引.json"
```

## 跨业务同名事件

以下 18 个事件名在 **内容中心** 和 **浏览器** 两个业务中均有定义(口径可能不同,使用前请对照):

| 事件名 | 内容中心模块 | 浏览器模块 |
|---|---|---|
| `ad_wechat_mini` | ad商业化 | ad商业化事件 |
| `app_open` | app通用 | app浏览器全局事件 |
| `appbundle_download` | search搜索 | search搜索事件 |
| `baidu_applet_sling` | search搜索 | search搜索事件 |
| `baidu_sdk_exit` | search搜索 | search搜索事件 |
| `content_duration` | content内容相关 | content信息流事件 |
| `content_item_expose` | 短剧 | content信息流事件 |
| `content_item_like` | 短剧 | content信息流事件 |
| `content_item_video_over` | 短剧 | content信息流事件 |
| `content_item_video_play` | 短剧 | content信息流事件 |
| `enter_room` | 抖音&穿山甲直播间 | livestream直播事件 |
| `search_homepage_expose` | search搜索 | search搜索事件 |
| `search_homepage_module_click` | search搜索 | search搜索事件 |
| `search_homepage_module_expose` | search搜索 | search搜索事件 |
| `search_security` | search搜索 | 搜索_安全网址事件(服务端) |
| `search_sugpage_expose` | search搜索 | search搜索事件 |
| `search_sugpage_module_click` | search搜索 | search搜索事件 |
| `search_sugpage_module_expose` | search搜索 | search搜索事件 |

## 埋点层级说明

- **埋点(模块)**: 一组相关事件的集合,对应 Excel 的一个 sheet,如「app通用」「content信息流事件」「ad商业化」。
- **事件**: 一次完整的用户行为或系统行为上报,有唯一英文事件名(如 `content_item_expose`)和中文描述。
- **参数**: 事件携带的属性,分为①公共属性(引用 common key / content key,所有事件自动携带)②事件专属参数(仅该事件上报)。

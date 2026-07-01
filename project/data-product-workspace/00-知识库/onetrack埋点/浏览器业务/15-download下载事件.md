# 浏览器 - download下载事件

> 来源 sheet: `download下载事件` | 事件数: 2 | 参数数: 11


## 事件总览

| # | 分类 | 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |
|---|---|---|---|---|---|---|
| 1 | 下载 | `download` | 下载 | 开始下载、下载完成、下载失败、重新下载时上报 | 5 | commey_key | 14.6 |
| 2 | 下载 | `download_apk_req` | 请求apk下载 | 搜索结果页和网页请求下载时上报 | 6 | commey_key |  |

---

## 事件详情

### `download` — 下载

- 分类: 下载
- 进版版本: 14.6
- 无痕模式上报: 是
- 公共属性: `commey_key`

**上报时机/逻辑**:

开始下载、下载完成、下载失败、重新下载时上报


**参数列表** (5):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `domain` | 当前页面域名 | string |  |  |
| `download_status` | 下载状态 | string | start：开始下载 success：下载完成 fail：下载失败 |  |
| `download_suffix` | 文件扩展名 | string |  |  |
| `download_type` | 下载文件类型 | string | 应用：app 视频：video 音频：audio 图片：picture 文档：doc 种子文件：seed_file 磁力链接：magnet_link |  |
| `third_packagename` | 第三方调起包名 | string | app_launch_way等于“第三方调起”时，上报第三方调起包名，其余情况为空 |  |

<details><summary>参数取值详情</summary>


**`download_type`** (下载文件类型)
- 类型: string
- 取值:
  应用：app
  视频：video
  音频：audio
  图片：picture
  文档：doc
  种子文件：seed_file
  磁力链接：magnet_link

</details>


### `download_apk_req` — 请求apk下载

- 分类: 下载
- 公共属性: `commey_key`

**上报时机/逻辑**:

搜索结果页和网页请求下载时上报


**参数列表** (6):

| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |
|---|---|---|---|---|
| `domain` | 当前页面域名 | string |  |  |
| `query` | 搜索词 | string |  |  |
| `page_type` | 页面类型 | string | 搜索结果页：search_result 网页：web_page |  |
| `pkg_name` | 包名 | string | 下载的包名 |  |
| `app_name` | 应用名称 | string |  |  |
| `is_from_appstore` | 是否来自于应用商店 | string | true：是 false：否 |  |

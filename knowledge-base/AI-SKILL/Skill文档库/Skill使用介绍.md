# Skill使用介绍

> 来源: https://mi.feishu.cn/wiki/VQcwwEO0EilL5VkWDB4cLlihnjf

# Skill 使用介绍

公司内网环境，推荐 micode + mimo（绝对数据安全）

#### 1、micode 安装 + micode hub 

一键安装

Mi Code CLI 一键安装已上线 

MacOS，在终端运行以下命令：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"
```

<cite doc-id="NpPcwSN8Si5F9VkKwnYclt3JnSe" file-type="wiki" title="Mi Code CLI 使用说明书" type="doc"></cite>

先关掉终端，重开一个 

```JSON
----- 一行行复制 
cd desktop 
mkdir micode
cd micode
micode
```

先登录micode 



#### 2、skill 安装

终端关掉，重开一个 

1）命令行输入：

```SQL
----- 一行行复制  注释不用复制 
micode skills add ai-team/feishu -i -----写飞书文档skill 
micode skills add ai-team/data-sql  -i  -----查数据工坊 skill 
micode skills add user_gongyunhe/auto-analysis -i -----自然语言查数分析demo（我写的）
micode skills add user_gongyunhe/nl-sql -i ------自然语言生成 SQL 
```

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmIwMzljMDBjMmJlZjRkNjAzZGM0NzYyMmVkYzIyMTJfOTMyMTAzYzUyZGFkNTE1NjM4MmUyZWFiMTExYWE3MGJfSUQ6NzYyNDM5OTUwOTMwMDUxMzcyMV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NWM0Mjc5ZjI5NjUyNmMyY2IzYmQyNDEwMmZjOTU3MTNfYmU2NmYzODk2NmU1MmVlNjNhNDQ3MzllODhjMDg4MDhfSUQ6NzYyNDM5OTUwNzg5OTczMDg5MV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

[micode.mioffice.cn](https://micode.mioffice.cn/#/skills)

<cite doc-id="SqTUwPi2giP3BZklsPwc8esSnye" file-type="wiki" title="Mi Code Hub（AI 工具链平台）使用说明书" type="doc"></cite>



#### 3、skill 使用 

启动终端，输入指令：

##### 1、最好先新建一个目录：

```JSON
----- 一行行复制 
cd desktop 
mkdir micode
cd micode
micode
```

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MTYwZDE4Njc0OGNiNzgyYTRhNGRjNDEyMGE0ZTEyNGVfZjE2Y2ExZmEwYTAyNjQ0OWQ3ZTMwNDMyODkxZTQwZGRfSUQ6NzYyNDM5OTUxMDY4MDE2MTIyNV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

/model  可以切换模型 

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWNlNzEwMTdmY2JlZWQ3Y2RjMjJiNjhiNjQzNDZkNzFfNDk2NjJjMzk5MTljYjQ4ZGE0YzM1Njk5ZmY5MmYzYWJfSUQ6NzYyNDM5OTUwODk5NDM2MjU2MV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

##### 2、执行 NL2SQL 的Skill 

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NGJmNzZlODVjN2M2NzFjNzhiMWM5ZjU0MmMxYzc4MDZfMGExYjhhZGExMzY3Yjc4Y2U3ZGFkOTU2ZTQxYTdkZDRfSUQ6NzYyNDM5OTUwNzkxNjYzOTE5NV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)



##### 3、输入需求

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YTRjYzE2NjFiYTYzY2UxYjZkODc3ZDhmOWM5MzhlOTdfODNmZTdjMzA3ZDNmZDQ1MDFiNjMyMTU5NzgwZjRlNjhfSUQ6NzYyNDM5OTUwNzM0NjIxNDA2Nl8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)



##### 4、验收结果

4.1、飞书文档：<cite doc-id="Hxd6wfPt4ixselkU5K6cINqsnad" file-type="wiki" title="浏览器DAU分析报告_20260320" type="doc"></cite>

4.2、本地文件夹：

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWMyNDNlMjFlNjI3N2FmZGZhNjYxYWM4ODExYTA3ZTRfYjc4Y2Y1NTAyYTUyZTI4ZTg1NTRhNzViNTljZDc3NmFfSUQ6NzYyNDM5OTUwOTAxOTQ5NTYyNF8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)



#### 4 补充说明：

如果用到micode 自己查数相关的能力，大概率用到这个 [micode.mioffice.cn](https://micode.mioffice.cn/#/skills/10)

1. 登录数据工厂：https://data.mioffice.cn/workspace/?wid=15070#/workspace/15070/config
2. 生成新Token，复制保存好

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Mzk0ODNkMTk0ZDU0YzRkZTQxNzQ1YjYyZWIwZWFhOTZfMjAzZTljZDI4MjNiNzNmZTI5NzE5YzMwNmE2ZDc1MjVfSUQ6NzYyNDM5OTUwNzExMTMzMjgxN18xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

1. 修改配置文件，使用这个 Token

```SQL
cd .micode 
cd skills 
cd data-sql 
cd scripts 
vim .env
```

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWJkYzI4MjhmODljMTUxZjNkNDI4NDUzODg0MzlmNzhfNjk3OTYxNGI5NWViZjhkNjY1Y2RkMzZiMjc2N2NmMDlfSUQ6NzYyNDM5OTUwNzkxNjY1NTU3OV8xNzc5ODcxMzk4OjE3Nzk4NzQ5OThfVjM)

此时进入vim 编辑器：

- 按 i 进编辑模式
- 粘贴自己的token 
- 按 esc 
- 输入 [:wq]  保存的意思
- 按回车键



1. 常用数据表，申请好权限

**iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di**

**iceberg_zjyprc_hadoop.browser.dm_browser_user_profile_feature_df**

**iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_feature_did_df**

**iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di**
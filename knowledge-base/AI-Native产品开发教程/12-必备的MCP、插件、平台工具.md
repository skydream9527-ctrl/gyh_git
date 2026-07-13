<title>【教程】必备的MCP、插件、平台工具</title>

# 飞书MCP

<callout emoji="😆">
开发文档：
https://open.feishu.cn/document/mcp_open_tools/end-user-call-remote-mcp-server#23bde528
生成 MCP 服务链接：
https://open.feishu.cn/page/mcp
生成服务器 URL/JSON后复制给IDE工具即可部署，记得每7天在飞书MCP进行授权～
</callout>

# 飞书CLI skill（目前最强）

![图片展示了飞书CLI技能的相关信息。左侧有一个立方体图标，右侧文字为“Feishu 通过 CLI 管控飞书全量资源：文档、知识库、云盘、多维表格、表格、权限、日历日... 个人”。该图片位于介绍飞书CLI技能的上下文之后，是对飞书CLI技能功能的总结，说明其能通过命令行界面管控飞书的多种资源，涵盖文档、知识库等多个方面，体现了飞书CLI技能的强大功能。](https://feishu.cn/file/Q4xJbosHpoe8ZMx9nKDcQK49nPQ)

<callout emoji="😆"><p>疯狂打call！！！！！！！！！！！！！！！！！！</p><p>地址：<cite doc-id="AKH1wYBvsixvlbkkFwVcnXeYnYc" file-type="wiki" title="飞书全功能助手：让 AI 替你操作飞书" type="doc"></cite></p><p>npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/</p></callout>

# Micode Hub

<callout emoji="😆">
地址：https://micode.mioffice.cn/#/
</callout>

# 大模型 API 开放平台（原Mify网关）

<callout emoji="😆">
支持统一鉴权、多模型调用、性能监测、费用监控等能力。
**功能1：支持生成API Key调用Mify平台模型**
通过IDE工具使用Mify平台，保障数据安全
**功能2：支持模型调试体验**
同一query多个模型回答，试验模型效果
地址：https://llm.mioffice.cn/playground
</callout>

# CC Switch

<callout emoji="😆">
**功能1：小白界面配置api-key使用模型**
个人使用时，配合闲鱼购买的api-key使用效果更佳，填写提供的base url和api-key即可使用
公司使用时，需注意api-key来源和数据安全，建议使用大模型API开放平台哦～
**功能2：同步多个IDE的Skills、MCP、提示词**
支持同步Claude、Codex、Gemini、OpenCode的Skills、MCP、提示词
> 这个支持范围有限，也可以看另一个教程里我写的[自动监听同步Skills](https://mi.feishu.cn/wiki/OYo7w7WsoiQWhWkScfycqJrfnpd)的脚本，我自己觉得好用
Git官网：https://github.com/farion1231/cc-switch/releases/tag/v3.16.3
</callout>

<grid>
<column width-ratio="0.250000">
![图片展示的是CC Switch的界面。界面上方显示“CC Switch”及三个图标。中间部分提示“还没有添加任何供应商”，并说明若已有配置可点击“导入当前配置”，所有数据将安全保存在default供应商中，除Key和请求地址外的数据会被保存到通用配置片段，用于在不同供应商之间共享。下方有“导入当前配置”和“添加供应商”两个蓝色按钮。该图片与文档中介绍CC Switch功能的内容相关，直观呈现了CC Switch的初始界面状态。](https://feishu.cn/file/IXC1bVq6Vo6JlfxqWNgcxQDqnDb)
</column>
<column width-ratio="0.250000">
![图片展示的是飞书MCP添加新供应商界面。界面上方有“添加新供应商”标题，下方有“供应商名称”“备注”“官网链接”“API Key”“API 请求地址”等输入框，其中“API Key”和“API 请求地址”框被黄色框线突出显示。底部有“取消”和“添加”按钮。该图片与文档中飞书MCP功能介绍相关，用于说明添加新供应商时填写API Key和API请求地址的操作界面。](https://feishu.cn/file/TJtrbw9LcoIsiRxolnbc8qpSnKW)
</column>
<column width-ratio="0.250000">
![图片展示的是CC Switch的Skills管理界面。界面上方有“从ZIP安装”“导入已有”“发现技能”等选项。中间区域显示“暂无 image_id”“暂无已安装的技能”，并提示可从仓库发现并安装技能，或导入已有的技能。下方有Claude、Codex、Gemini、OpenCode四个模型的技能数量均为0。该图片与文档中介绍CC Switch功能2的内容相关，直观呈现了其技能管理界面及当前状态。](https://feishu.cn/file/HohxbZ3RQop0r8xQaBNc0UVLnfc)
</column>
<column width-ratio="0.250000">
![图片展示的是CC Switch的MCP服务器管理界面。界面上方显示“已配置0个MCP服务器”，并有Claude、Codex、Gemini、OpenCode四个模型的MCP数量均为0。中间部分有一个图标和文字“暂无服务器”，下方提示“点击右上角按钮添加第一个MCP服务器”。右上角有“导入已有”和“添加MCP”按钮。该界面用于管理MCP服务器，当前无服务器配置，可点击相应按钮进行添加操作。](https://feishu.cn/file/Pr1Dbsbego7Gnfx2BoIcg8gxn9f)
</column>
</grid>
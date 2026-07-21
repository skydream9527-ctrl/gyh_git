# Opencode 飞书文档 MCP 接入指南 - 总结

> 原文链接: https://mi.feishu.cn/wiki/Srr3weSgYi2r6Bk4w7IceiR1n8g

## 📋 概述




飞书文档 MCP (Model Context Protocol) 服务允许 AI 直接在飞书云文档中进行创建、读取、搜索、评论及文件获取等操作。

**注意**: 由于飞书官方MCP支持限制，无法读取、修改、创建多维表格

## 🔑 1. 前置准备

### 获取 MCP 服务地址
1. 访问飞书开放平台 ["个人调用远程 MCP 服务"](https://open.feishu.cn/page/mcp) 页面
2. 创建飞书文档 MCP 服务，复制生成的 **MCP Server URL**
   - 格式: `https://mcp.feishu.cn/mcp/mcp_xxxxxx`
3. **重要**: Token 有效期为 **7 天**，过期需重新授权

### 续期提醒
建议创建多维表格工作流，设置每周一提醒自己续期MCP

## ⚙️ 2. Opencode 配置步骤

### 配置文件位置
`~/.config/opencode/opencode.json`

### 配置示例
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "feishu-doc": {
      "type": "remote",
      "url": "https://mcp.feishu.cn/mcp/mcp_您的专属ID",
      "enabled": true
    }
  },
  "provider": {
    ...
  }
}
```

### 配置参数说明
- **type**: 必须设置为 `"remote"`
- **url**: 从飞书平台获取的专属 URL
- **enabled**: 设置为 `true` 以启用服务

## ✅ 3. 验证接入

配置完成后，重新打开opencode，验证方式：
- 在 Opencode 终端或对话界面中运行指令（如 `/mcp list`）
- 输入"查看我本周浏览过的文档"，可以看到文档列表输出

## 🛠️ 4. 核心能力（9项工具）

| 工具名称 | 功能描述 |
|---------|---------|
| `create-doc` | 将 Markdown 内容创建为飞书云文档 |
| `fetch-doc` | 获取指定文档的 Markdown 内容 |
| `update-doc` | 更新文档（支持覆盖、追加、定位替换等模式） |
| `search-doc` | 搜索云文档（支持过滤和排序） |
| `list-docs` | 获取文档树或指定节点下的子文档列表 |
| `add-comments` | 在文档中添加全文评论 |
| `get-comments` | 获取文档评论（支持全文或划词评论） |
| `search-user` | 通过关键词搜索飞书用户（获取 `open_id` 用于 @ 提及） |
| `fetch-file` | 通过 token 获取文档中的文件、图片或画板内容 |

## ⚠️ 5. 常见问题

### 401 Unauthorized
**原因**: Token 过期  
**解决**: 访问 [授权页面](https://open.feishu.cn/page/mcp) 刷新

### 配置不生效
**解决**: 重启 Opencode 以读取最新配置文件

### 自动修复
如果配置无误但仍无法使用，可在opencode中输入：
```bash
我在配置文件中增加了feishu-doc的mcp但无法使用，自己修复一下
```

## 📌 关键要点

1. **有效期管理**: MCP Token 7天过期，需要定期续期
2. **配置类型**: 必须使用 `remote` 类型
3. **功能限制**: 不支持多维表格操作
4. **重启生效**: 修改配置后需重启 Opencode

---

*生成时间: 2026-03-27*

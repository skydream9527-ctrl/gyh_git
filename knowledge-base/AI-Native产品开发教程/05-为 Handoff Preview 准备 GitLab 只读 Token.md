# 【教程】为 Handoff Preview 准备 GitLab 只读 Token

<callout emoji="💡">
**发给谁**
- 发给你的项目知识库 KBS 仓库管理员。
- 这篇只说明管理员怎么在 GitLab 上创建只读 token。
- 管理员不需要修改 Handoff 部署变量。
</callout>

## 这件事的目的

Handoff Preview 需要读取你的项目知识库 KBS 仓库分支，才能在“项目预览”页面展示可打开的分支。

管理员要提供一个只读 GitLab token。这个 token 只用于 Handoff 服务端读取分支和 Handoff 文件。

用户能否打开 Preview，仍然由用户自己的 GitLab 仓库权限决定。

## 管理员需要准备什么

- 你的项目知识库 KBS 地址。
- 对这个 KBS 仓库的 Maintainer 或 Owner 权限。
- 一个用于创建 token 的 GitLab 页面登录态。

## 管理员操作步骤

### 第一步：打开项目知识库 KBS 仓库

管理员在浏览器里打开你的项目知识库 KBS 地址。

成功判定：页面左上角显示的是目标 KBS 仓库名称。

### 第二步：进入项目 Access Tokens 页面

在 GitLab 左侧菜单依次点击：

- Settings
- Access Tokens

如果左侧没有 Settings，说明当前账号没有足够管理权限，需要换 Maintainer 或 Owner 账号。

成功判定：页面标题显示 Project Access Tokens，或能看到创建 token 的表单。

### 第三步：创建只读 token

在创建表单里填写：

- Token name：填写 Handoff Preview Read Token。
- Expiration date：选择一个明确过期时间，建议先选 7 天或 30 天。
- Role：选择 Reporter。
- Scopes：只勾选 read_api。

不要勾选写入、管理、删除、CI、Registry 等权限。

成功判定：点击 Create project access token 后，页面生成一串 token。

### 第四步：安全交付 token

管理员只把 token 交给 Handoff 部署变量维护者。

交付时同时说明：

- 这是你的项目知识库 KBS 的只读 token。
- token 权限是 read_api。
- token 的过期时间。
- token 只能放入 Handoff 部署环境变量。

不要把 token 写入飞书正文、群消息、代码仓库、MR 描述或截图。

## 管理员需要交付什么

- 已创建的只读 token。
- token 过期日期。
- 确认 token 来自你的项目知识库 KBS 仓库。
- 确认 token scope 只有 read_api。

## 常见问题

### 找不到 Access Tokens 页面

当前账号权限不足。请让 KBS 仓库 Maintainer 或 Owner 操作。

### Role 要选什么

选择 Reporter。Handoff Preview 只需要读仓库分支和文件。

### Scope 要选什么

只勾选 read_api。

### token 能发到群里吗

不能。token 只能通过安全渠道交付给部署变量维护者。

### token 过期后怎么办

管理员重新创建一个 read_api token，并让部署变量维护者更新 Handoff 环境变量。
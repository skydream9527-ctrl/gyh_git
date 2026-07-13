# 【教程】把项目知识库 KBS 加入 Handoff 项目预览

<callout emoji="💡">
**发给谁**
- 发给需要把你的项目知识库 KBS 加入 Handoff 项目预览的人。
- 这篇只说明 GitLab 页面上要改哪些部署变量、怎么验收。
</callout>

## 这件事的目的

把你的项目知识库 KBS 加入 Handoff 首页的“项目预览”列表，让页面出现项目卡片，并能打开 Handoff Preview 和知识库视图。

## 你需要准备什么

- 你的项目知识库 KBS 地址。
- 管理员提供的 GitLab 只读 token。
- Handoff staging 部署项目的 Maintainer 或 Owner 权限。
- 目标 KBS 仓库里已经存在 handoff/current/manifest.json。

## 在 GitLab 上怎么配置

### 第一步：进入部署项目变量页面

打开维护 Handoff staging 部署的 GitLab 项目。

在左侧菜单依次点击 Settings、CI/CD、Variables。

成功判定：能看到变量列表，以及 Add variable 或 Edit 按钮。

### 第二步：追加项目预览目录变量

找到 HANDOFF_PREVIEW_CATALOG_PROJECTS。

点击 Edit。

在原值末尾追加英文逗号，再追加你的项目知识库 KBS 地址。

点击 Save changes。

成功判定：原有项目仍在，新项目地址也在。

### 第三步：追加 Preview 白名单变量

找到 HANDOFF_PREVIEW_ALLOWED_PROJECTS。

点击 Edit。

用同样方式追加你的项目知识库 KBS 地址。

点击 Save changes。

成功判定：两个变量里都有同一个你的项目知识库 KBS 地址。

### 第四步：填写只读 token

找到 HANDOFF_PREVIEW_CATALOG_GITLAB_TOKEN。

如果变量不存在，点击 Add variable 新增。

填写 Key 为 HANDOFF_PREVIEW_CATALOG_GITLAB_TOKEN。

Value 粘贴管理员提供的只读 token。

开启 Mask variable。

Protect variable 按当前部署分支规则选择；不确定时保持和现有 Handoff token 变量一致。

点击 Save changes。

成功判定：变量存在，且 Value 在页面里不可明文展示。

### 第五步：重新部署 Handoff staging

按当前 Handoff staging 发布流程重新部署或重启服务。

成功判定：服务读取到新的 HANDOFF_PREVIEW 相关变量。

## 上线后怎么验收

### 验收项目卡片

打开 Handoff 项目预览页。

成功判定：页面出现你的项目知识库 KBS 对应卡片，原有项目卡片仍然存在。

### 验收分支同步

等待项目预览页完成分支同步。

成功判定：新项目卡片按钮可点击，没有出现 Token 无权限或项目不存在提示。

### 验收 Preview 权限

用有 KBS 仓库读取权限的账号点击 Handoff 预览。

成功判定：可以进入 Preview。

用没有 KBS 仓库读取权限的账号访问。

成功判定：被 GitLab 或 Handoff 权限拦截。

## 常见问题

### 项目卡片没有出现

检查 HANDOFF_PREVIEW_CATALOG_PROJECTS 是否已经追加你的项目知识库 KBS 地址，并确认服务已重新部署。

### 卡片出现但按钮不可点

检查 HANDOFF_PREVIEW_CATALOG_GITLAB_TOKEN 是否能读取你的项目知识库 KBS 分支。

### 点击 Preview 后被拦截

检查 HANDOFF_PREVIEW_ALLOWED_PROJECTS 是否包含你的项目知识库 KBS 地址，并确认当前登录用户有该 KBS 仓库读取权限。

### Preview 提示 Handoff 文件缺失

检查目标分支是否存在 handoff/current/manifest.json。不存在时，需要先在 KBS 仓库初始化 Handoff 稳定协议。
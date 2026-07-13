# Openclaw 部署要点

> 来源：Openclaw 安装过程记录&踩坑分享（2026-03-12），全文归档 `00-知识库/文档归档/Markdown文件/2026-03-12-Openclaw安装过程记录与踩坑分享.md`。本文为部署要点提炼，2026-07-02 整理。

## 核心认知

Openclaw 安装本质是 **3 个解耦步骤**，可自由组合：

1. **找台机器运行 openclaw**（本地 or 服务器）
2. **申请模型 API**（MiniMax / 阿里云百炼 等）
3. **链接通讯软件**（Telegram / 钉钉 / 飞书）

> 一句话定位：**手机端发指令，MAC 端干活，手机端检查并拿到结果**。

## 方案 A：MAC MINI 本地部署 + Telegram

> ⚠️ **不能用公司电脑**；初次体验建议直接用方案 B。

### 准备

- MAC mini（16+256，M4）
- AI 工具：ChatGPT（首推）/ Gemini3 / 豆包（安装遇问题随时问）

### 安装步骤

```bash
# 1. 装 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 装 openclaw
curl -fsSL https://openclaw.ai/install.sh | bash
```

引导界面顺序（方向键切换，enter 确认）：
1. 选 `yes`（理解个人使用默认）
2. 选 `quickStart`
3. 模型选择 → **跳过**（保持现状）
4. channel 选择 → 跳过
5. skills 选择 → 跳过
6. hooks → 跳过（space 选择，enter 确认）
7. 安装完毕自动打开 ControlUI 网页

### 配置模型（MiniMax）

1. MiniMax 开放平台（platform.minimaxi.com）申请 API Key（**需充值**）
2. 在 openclaw 配置界面：Model/auth provider = MiniMax → 粘贴 API Key

### 配置 Telegram

1. Telegram 搜 @BotFather → `/newbot` 创建 Bot → 拿到 token
2. Telegram 搜 @userinfobot → 获取自己的数字 ID
3. 在 openclaw channel 配置填入
4. 配对：Bot 发来配对码 → 终端执行 `openclaw pairing approve telegram <CODE>`

## 方案 B：阿里云服务器 + 钉钉/飞书（推荐）

> 初次体验推荐此方案，免本地安装。

### 准备

- 阿里云轻量服务器（推荐 4GB 内存，可蹲学生/限时优惠）
- 钉钉 / 飞书账号
- AI 工具辅助答疑

### 部署流程

1. **阿里云一键部署**：阿里云搜"OpenClaw 一键部署" → 购买轻量应用服务器（2核2G 起，美国弗吉尼亚等地区）
2. **进工作台**：home.console.aliyun.com → 轻量应用服务器 → 实例列表 → 应用详情
3. **配置模型**：阿里云百炼平台（modelstudio.console.aliyun.com）→ 充值 → 密钥管理 → 创建 API Key → 填入 openclaw 配置
4. **配置消息链接**：见下方钉钉/飞书配置

### 配置钉钉

1. 钉钉开发者后台（open-dev.dingtalk.com）创建应用 → 添加"机器人"能力
2. 事件订阅：Stream 模式推送
3. 版本管理与发布：创建版本 → 提交审核发布
4. 应用详情页 → 通道配置填入钉钉凭证
5. 钉钉群设置 → 机器人 → 添加

### 配置飞书

1. 飞书开放平台（open.feishu.cn/app）创建企业自建应用
2. **权限 scopes**（一键导入 JSON，完整列表见归档原文）：
   - `bitable:app` / `bitable:app:readonly`
   - `docx:document` / `docx:document:create` / `docx:document:readonly` / `docx:document:write_only` / `docx:document.block:convert`
   - `drive:drive` / `drive:drive:readonly`
   - `im:message` / `im:message:send_as_bot` / `im:message:readonly` / `im:message.group_at_msg:readonly` / `im:message.group_msg` / `im:message.p2p_msg:readonly` / `im:message:recall` / `im:message:update` / `im:message.reactions:read` / `im:resource` / `im:chat:readonly`
   - `wiki:wiki` / `wiki:wiki:readonly`
   - `task:task:*` / `task:tasklist:*` / `task:comment:*` / `task:attachment:*`
   - `contact:contact.base:readonly` / `contact:user.base:readonly`
3. 添加应用能力 → 机器人
4. 事件与回调 → 使用长连接接收事件
5. 版本管理与发布 → 创建版本 → 发布
6. 凭证与基础信息：拿 App ID / App Secret 填入 openclaw 飞书配置

## Soul.md（个人助手人设）

定义助手性格、说话风格、行为准则、绝对不做。示例要点：
- **性格**：聪明、高效、有点话多；技术术语保留英文；重要信息加粗
- **行为准则**：能做直接做不反复确认；不确定先问；外发消息必须确认；深夜（23:00-08:00）不主动打扰；发现主人工作太晚提醒休息
- **绝对不做**：不泄露隐私；不在群聊过度发言；未确认不做破坏性操作

## Openclaw 能干什么

- **内容创作**：飞书发指令 → 桌面新建文档 → 分析帖子 → 创作小红书内容 → Google Drive 检查结果
- **PPT 制作**：飞书输入指令 → 桌面生成 PPT → Google Drive 查看/下载
- **定时提醒**：钉钉/飞书群里设定时提醒（如每小时喝水）
- **一句话开发小游戏**：Trae + MiniMax API，ChatGPT 生成提示词 → Gemini 3 Pro 生成代码

## 参考链接

- OpenClaw 官方文档：https://docs.openclaw.ai/zh-CN
- OpenClaw 101：https://openclaw101.dev/zh
- 阿里云部署指南：https://help.aliyun.com/zh/simple-application-server/use-cases/quickly-deploy-and-use-openclaw
- soul.md 深度解密：https://b23.tv/rgXYpK2

## 踩坑记录

- **腾讯云**：需注意开通公网
- **Windows**：不建议（折腾），无官方教程
- **公司电脑**：不能用于本地部署方案 A
- **图片生成**：可能因 Gemini API 限流 / OpenAI DALL-E 额度不足失败，需配置对应 API Key

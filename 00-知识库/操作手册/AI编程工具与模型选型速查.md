# AI 编程工具与模型选型速查

> 来源：0327 AI 实践阶段性分享（2026-03-29），全文归档 `00-知识库/文档归档/Markdown文件/2026-03-29-AI实践阶段性分享.md`。本文为操作速查提炼，2026-07-02 整理。

## 一、工具选型

### APP 端（带 IDE 界面）

| 工具 | 厂商 | 特点 | 备注 |
|------|------|------|------|
| Antigravity | Google | 魔改版 VSCode，个人体感好 | 个人主力，配 Claude sonnet 4.6 |
| CodeX | OpenAI | 无 IDE，插件丰富，一键登录 | 配 GPT5.3-CodeX，量大 |
| Trae / Trae CN | 字节 | 轻量实用工具集 | **公司开额度的是 CN 版** |
| Qoder | 阿里 | 代码编辑管理轻量工具 | 需会员（曾可用百炼 coding plan） |
| VSCode | 微软 | 免费开源，插件丰富 | 全场景适配 |

### CLI 端（终端运行）

启动方式一致：建目录 → `cd` → 启动命令 → 对话框对话。

| 工具 | 启动命令 | 适用场景 |
|------|---------|---------|
| Micode | `micode` | **公司内网，绝对数据安全**；配 mimo-v2-pro |
| OpenCode | `opencode` | 低价平替，配 GLM-5 |
| Claude Code | `claude` | 配 MiniMax-M2.7 等 |
| Qwen Code | `qwen` | 配 GLM-5（百炼 coding plan） |

```bash
# 通用启动流程
cd desktop          # 到桌面
mkdir micode        # 建工作目录
cd micode
micode              # 启动对应 CLI（opencode / claude / qwen）
/model              # 切换模型
```

### 搭配方案推荐

| 场景 | 方案 | 说明 |
|------|------|------|
| 公司内部 | Trae + GLM-5 | 公司福利，记得切模型 |
| 公司内网 | Micode + mimo-v2-pro | 数据安全，结合 terminal 软件延续工作 |
| 个人主力 | Antigravity + Claude sonnet 4.6 | 闲鱼买 Google ultra 家庭组 ¥168/月，额度远超 Claude PRO，还能用 Gemini |
| 量大场景 | CodeX + GPT5.3-CodeX | GPT PLUS 额度基本够用 |
| 国内低价平替 | OpenCode + GLM-5 | 百炼 coding plan 也能用 GLM-5 |

## 二、模型选型排序

- **国外**：Claude > ChatGPT > Gemini（按需选购）
- **国内**：GLM-5 > kimi 2.5 = mimo-v2-pro > minimax2.5 = Qwen 3.5-plus > doubao-seed
- **底线**：最低 Kimi 2.5，再低就是浪费生命
- 排行榜：https://artificialanalysis.ai/leaderboards/models

## 三、Micode Skill 使用

### 安装与启动

```bash
# MacOS 一键安装
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"

# 关掉终端重开，安装常用 skill
micode skills add ai-team/feishu -i              # 写飞书文档
micode skills add ai-team/data-sql -i            # 查数据工坊
micode skills add user_gongyunhe/auto-analysis -i # 自然语言查数分析
micode skills add user_gongyunhe/nl-sql -i       # 自然语言生成 SQL
```

### 数据工厂 Token 配置

1. 登录 https://data.mioffice.cn/workspace/?wid=15070#/workspace/15070/config
2. 生成新 Token，复制保存
3. 写入配置：`cd .micode/skills/data-sql/scripts && vim .env`（按 `i` 编辑 → 粘贴 → `esc` → `:wq`）

### 常用数据表（需申请权限）

- `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
- `iceberg_zjyprc_hadoop.browser.dm_browser_user_profile_feature_df`
- `iceberg_zjyprc_hadoop.browser.dm_micd_user_profile_feature_did_df`
- `iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di`

## 四、Skill 开发 AI Native 流程

基于 Antigravity + Opus 4.6（或任意 IDE + 强模型）：

1. **创建空文件夹**（调试时可建在 `.micode/skills/` 目录下方便）
2. **打开 IDE** → 打开对应文件夹
3. **提需求**（自然语言描述 skill 要做什么）
4. **添加 reference**（打开目录往里复制参考文件）
5. **调试**：建 `micode_skill_debug` 目录，启动 micode 执行 skill 验证
6. **打包**：整理 skill 目录结构（含 SKILL.md、scripts、settings.json 等）
7. **上传**：MiCode Hub（micode.mioffice.cn/#/skills）→ 新建技能 → 上传 zip
8. **查看**：Hub 上确认技能信息

## 五、关键技巧与踩坑

- **上下文管理**：超过 60% 易出现幻觉 → 开新窗口（同目录）让模型读目录文件续做
- **执行中断**：AI 执行一半就结束 → 记得追问让其继续
- **文档美化**：deepseek 网页版生图 → 复制代码到 trae/micode → 贴入飞书文档编辑
- **安卓开发**：OpenCode + GLM-5 可端到端开发安卓应用（建 git 项目 → GitHub Actions 打包 apk）
- **学习资源**：用 AI 工具学习 AI 工具（豆包+trae、ChatGPT+Claude Code）

## 六、其他推荐工具

- **Warp**：命令行神器
- **Obsidian**：多端同步知识库，自动 RAG
- **Google Drive**：云盘
- **Typeless / Typeoff**：语音输入（效率是打字 3 倍+）
- **GitHub**：代码保存，多端协同
- **Google AI Studio**：Google 羊毛
- **NotebookLM**：Google 笔记神器

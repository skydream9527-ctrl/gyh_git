# Data Tracking Plan Generator使用指南

> 来源: https://mi.feishu.cn/wiki/ZvpUwpl6ji6iJOkiB3Vc8hWKn7c

# Data Tracking Plan Generator 使用指南

## 1、简介

### 什么是 Data Tracking Plan Generator？

Data Tracking Plan Generator 是一个**埋点方案生成**的技能，帮助产品经理和开发者基于产品 PRD 文档快速生成标准化埋点方案，无需手动设计埋点结构。

### 核心能力

| 能力 | 说明 |
|-|-|
| 📝 PRD 解析 | 自动读取飞书 PRD 文档，理解产品需求 |
| 🔄 事件复用检测 | 优先复用已有事件和属性，避免重复埋点 |
| 📊 多业务线支持 | 支持浏览器、内容中心两大业务线 |
| ✅ 规范化输出 | 按命名规范生成标准化埋点方案表格 |
| 📤 飞书输出 | 自动生成飞书文档，支持新增标红提示 |

---

## 2、安装前置依赖 

### 2.1 安装 Mi Code CLI 

MacOS / Linux / WSL / Matrix 实例，在终端运行：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"


```

### 2.2 安装依赖 Skill 

```Bash
micode skills add user_gongyunhe/data-tracking-plan -i  # 埋点方案生成
micode skills add ai-team/feishu -i                      # 读取/写入飞书文档


```

---

## 3、使用方法 

### 3.1 启动 Mi Code

```Bash
mkdir -p ~/micode && cd ~/micode
micode


```

### 3.2 执行 Data Tracking Plan Skill

在 Mi Code 对话框中输入：

```Plain Text
执行 data-tracking-plan


```

或直接描述需求：

```Plain Text
帮我为浏览器新功能设计埋点方案


```

### 3.3 交互流程

**Step 1：选择业务类型**

```Plain Text
请问是为【浏览器】还是【内容中心】设计埋点方案？
1. 浏览器
2. 内容中心


```

**Step 2：提供 PRD 文档**

```Plain Text
请提供产品 PRD 的飞书文档链接。


```

**Step 3：确认关注点**

```Plain Text
请确认需要关注的场景：
- 功能曝光点击
- 内容上传下载分享
- 浏览停留滑动
- 业务转化
...


```

**Step 4：生成埋点方案**系统会展示埋点方案表格，并自动写入飞书文档。

---

## 4、使用示例

### 示例 1：浏览器埋点方案

**用户输入**：

```Plain Text
执行 data-tracking-plan
→ 选择：1. 浏览器
→ 提供 PRD 链接：（用户提供实际的飞书 PRD 文档链接）
→ 关注场景：搜索功能优化


```

**输出埋点方案**：

| 事件名(英文) | 事件名(中文) | 触发时机 | 属性名(英文) | 属性名(中文) | 属性类型 | 属性值说明 | 备注 |
|-|-|-|-|-|-|-|-|
| search_homepage_expose | 搜索首页曝光 | 搜索首页展示时 | search_type | 搜索类型 | string | text/voice/image | 复用已有 |
| search_homepage_click | 搜索首页点击 | 点击搜索结果时 | result_position | 结果位置 | number | 1,2,3... | 复用已有 |
| search_ai_answer_expose | AI答案曝光 | AI答案卡片展示时 | ai_model | AI模型 | string | gpt4/claude... | 新增事件 |

### 示例 2：内容中心埋点方案

**用户输入**：

```Plain Text
执行 data-tracking-plan
→ 选择：2. 内容中心
→ 提供 PRD 链接：（用户提供实际的飞书 PRD 文档链接）
→ 关注场景：内容上传流程


```

**输出结果**：

- 飞书文档：自动生成新文档并返回链接
- 方案概览：共设计 12 个事件，其中新增 3 个，复用 9 个（复用率 75%）

---

## 5、参考资料

### 5.1 已有事件库

| 业务线 | 参考文件 | 说明 |
|-|-|-|
| 浏览器 | browser_existing_events.md | 包含 800+ 已有事件 |
| 内容中心 | content_center_existing_events.md | 包含 191 个已有事件 |

### 5.2 命名规范

| 规则 | 说明 | 示例 |
|-|-|-|
| 基本格式 | {功能模块}*{页面/场景}*{行为类型} | search_homepage_expose |
| snake_case | 全小写，单词间用下划线连接 | feed_detail_click |
| 功能模块优先 | 事件名以功能模块开头 | search\_、feed\_、ai\_ |
| 行为类型结尾 | 以 expose/click/action 等结尾 | \_expose、\_click、\_duration |

### 5.3 常用行为类型后缀

| 后缀 | 含义 |
|-|-|
| \_click | 点击行为 |
| \_expose | 曝光/展示 |
| \_duration | 时长统计 |
| \_success | 成功状态 |
| \_fail | 失败状态 |

> 💡 详细规范请参考 `browser_event_naming_convention.md` 和 `content_center_event_naming_convention.md`

---

## 6、设计原则 

埋点方案设计严格遵循以下优先级：

<callout emoji="🎁">
**优先复用已有事件**：检查已有事件库，若事件已存在，通过增加属性实现新需求
</callout>

<callout emoji="🎁">
**优先复用已有属性**：若属性已存在，通过增加属性值实现新需求
</callout>

<callout emoji="🎁">
**新增属性**：若无合适属性，则新增属性
</callout>

<callout emoji="🎁">
**新增事件**：仅当无法复用时，按命名规范新增事件
</callout>

---

## 7、输出格式说明

### 7.1 表格结构

埋点方案以表格形式呈现，包含以下列：

- 事件名（英文）
- 事件名（中文）
- 触发时机
- 属性名（英文）
- 属性名（中文）
- 属性类型
- 属性值说明
- 备注

### 7.2 标红规则

| 类型 | 标红范围 |
|-|-|
| 新增事件 | 整行标红 |
| 新增属性 | 该属性行标红 |
| 新增属性值 | 该属性值单元格标红 |

---

## 8、常见问题

### Q1：如何查看已有事件列表？

**解决方案**：

- 浏览器：查看 `reference/browser_existing_events.md`
- 内容中心：查看 `reference/content_center_existing_events.md`

### Q2：生成的事件名不符合规范怎么办？

**原因**：可能是新功能模块，需要新增命名前缀。**解决方案**：

1. 参考 `*_event_naming_convention.md` 中的命名规范
2. 与团队确认新模块命名前缀

### Q3：PRD 文档读取失败怎么办？

**常见原因**：

1. **权限问题**：确保文档已共享给当前账号
2. **链接格式**：确认使用正确的飞书文档链接
3. **网络问题**：检查网络连接

### Q4：如何更新参考资料？

**步骤**：

1. 将最新的埋点 XLSX 文件放入 `reference/` 目录
2. 运行 `extract_events.py` 提取数据
3. 运行 `generate_files.py` 生成文档

---

## 9、参考链接

- [Mi Code CLI 使用说明书](https://micode.mioffice.cn)
- [Mi Code Hub（AI 工具链平台）](https://micode.mioffice.cn/#/skills)
- [浏览器埋点管理平台](https://onetrack.bi.mi.com/#/dashboard?projectId=536&realAppId=31000000442)

---

## 10、联系开发者

如有问题或需求，请联系：**gongyunhe**
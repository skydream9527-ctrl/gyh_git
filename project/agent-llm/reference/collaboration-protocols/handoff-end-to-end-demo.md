# 

> 来源：飞书文档，更新时间：2026-05-07T11:43:31.000Z

# Handoff Protocol 端到端演示 — 从用户输入到 H5 预览（正在迭代中）

<callout emoji="🎯">
本文档展示 Handoff Protocol 的完整工作流：用户用自然语言描述需求 → AI 生成结构化 Handoff 文件 → 渲染引擎输出可交互的 H5 预览页面。
</callout>

## Step 1：用户输入（自然语言需求）

产品经理在 IDE 中用自然语言描述需求，AI 自动理解并结构化：

```Plain Text
我需要一个手机号登录页面：
- 顶部导航栏，左侧返回按钮，标题"手机号登录"
- Logo 区域，显示小米 Logo 和"小米账号登录"
- 手机号输入框（11位，tel键盘）
- 验证码输入框 + 获取验证码按钮（60秒倒计时）
- 用户协议和隐私政策勾选
- 登录按钮（需勾选协议 + 手机号有效 + 验证码有效才可点击）
- 底部"使用密码登录"链接
- 品牌色 #00D1B2

```

<callout emoji="💡">
仅需 8 行自然语言，AI 即可生成完整的多层 Handoff 文件，覆盖产品、设计、研发、测试四个角色的交付物。
</callout>

## Step 2：AI 生成 Handoff 文件

AI 根据用户输入，自动生成结构化的 `.handoff.jsonc` 文件。以下是关键片段：

### 2.1 产品层 — layoutTree（布局树）

```Plain Text
{
  "type": "scaffold",
  "backgroundColor": "$surface",
  "children": [
    // 导航栏
    {
      "type": "app-bar",
      "height": "56px",
      "children": [
        { "type": "icon-button", "icon": "arrow-left", "onTap": { "type": "navigate", "method": "pop" } },
        { "type": "text", "content": "手机号登录", "fontSize": "$headingSm", "fontWeight": "semibold" }
      ]
    },
    // 可滚动内容区
    {
      "type": "scroll-view",
      "padding": { "horizontal": "$sp8", "top": "$sp10" },
      "children": [
        // Logo
        { "type": "image", "source": { "asset": "assets/images/logo_xiaomi.png" }, "width": "64px", "height": "64px" },
        { "type": "text", "content": "小米账号登录", "fontSize": "$headingMd", "fontWeight": "bold" },
        // 手机号输入
        { "type": "text-field", "placeholder": "请输入手机号", "inputType": "tel", "maxLength": 11 },
        // 验证码行
        {
          "type": "row",
          "children": [
            { "type": "text-field", "placeholder": "请输入验证码", "inputType": "number", "maxLength": 6 },
            { "type": "text-button", "text": "获取验证码", "enabledWhen": "phone_valid && !sms_counting" }
          ]
        },
        // 协议勾选
        {
          "type": "row",
          "children": [
            { "type": "checkbox", "defaultChecked": false },
            { "type": "rich-text", "segments": [
              { "text": "已阅读并同意", "color": "$textSecondary" },
              { "text": "《用户协议》", "color": "$brand", "onTap": { "type": "navigate", "target": "page-user-agreement" } },
              { "text": "和", "color": "$textSecondary" },
              { "text": "《隐私政策》", "color": "$brand", "onTap": { "type": "navigate", "target": "page-privacy-policy" } }
            ]}
          ]
        }
      ]
    },
    // 底部操作区
    {
      "type": "safe-area",
      "children": [
        { "type": "button", "text": "登录", "backgroundColor": "$brand", "borderRadius": "$radiusXl",
          "enabledWhen": "agreement_checked && phone_valid && code_valid" },
        { "type": "text-button", "text": "使用密码登录" }
      ]
    }
  ]
}

```

### 2.2 产品层 — stateMachine（状态机）

```Plain Text
{
  "initial": "default",
  "states": {
    "default":      { "on": { "INPUT_PHONE_VALID": "phone-ready" },     "ui": { "login-btn": "disabled", "sms-btn": "disabled" } },
    "phone-ready":  { "on": { "TAP_GET_SMS": "sms-countdown" },        "ui": { "sms-btn": "enabled" } },
    "sms-countdown":{ "on": { "INPUT_CODE_COMPLETE": "input-valid" },   "meta": { "countdown": 60 } },
    "input-valid":  { "on": { "TAP_LOGIN": "loading" },                "ui": { "login-btn": "enabled" } },
    "loading":      { "on": { "API_SUCCESS": "redirect:page-home", "API_FAIL": "error" } },
    "error":        { "on": { "TAP_RETRY": "loading", "DISMISS_TOAST": "input-valid" } }
  },
  "guards": {
    "TAP_LOGIN": "agreement_checked && phone_valid && code_valid"
  }
}

```

### 2.3 设计层 — Design Tokens

```Plain Text
{
  "$brand":       { "light": "#00D1B2", "dark": "#00E5C3" },
  "$surface":     { "light": "#FFFFFF", "dark": "#1A1A1A" },
  "$textPrimary": { "light": "#1A1A1A", "dark": "#F5F5F5" },
  "$headingMd":   { "value": "20px" },
  "$bodyMd":      { "value": "16px" },
  "$sp8":         { "value": "16px" },
  "$radiusXl":    { "value": "24px" }
}

```

<callout emoji="⚡">
Token 系统确保设计一致性：颜色、字号、间距、圆角全部通过 \$token 引用，支持 light/dark 双主题自动切换。
</callout>

### 2.4 研发层 — 组件映射 + API 定义

```Plain Text
{
  "route": "/login/phone",
  "widget": "PhoneLoginScreen",
  "components": [
    { "name": "手机号输入框", "widget": "PhoneField", "file": "lib/features/auth/widgets/phone_field.dart" },
    { "name": "验证码输入框", "widget": "CodeField",  "file": "lib/features/auth/widgets/code_field.dart" },
    { "name": "登录按钮",     "widget": "PrimaryButton", "file": "lib/core/widgets/primary_button.dart" }
  ],
  "api": [
    { "endpoint": "POST /api/auth/sms/send",   "request": { "phone": "string" } },
    { "endpoint": "POST /api/auth/sms/verify",  "request": { "phone": "string", "code": "string" } }
  ]
}

```

### 2.5 测试层 — 状态转换 + 边界用例

```Plain Text
{
  "stateTransitions": [
    { "from": "default",    "to": "phone-ready",       "trigger": "INPUT_PHONE_VALID" },
    { "from": "phone-ready","to": "sms-countdown",     "trigger": "TAP_GET_SMS" },
    { "from": "loading",    "to": "redirect:page-home", "trigger": "API_SUCCESS" },
    { "from": "loading",    "to": "error",              "trigger": "API_FAIL" }
  ],
  "boundary": [
    { "name": "手机号10位",     "expected": "登录按钮禁用" },
    { "name": "验证码含字母",   "expected": "只接受数字" },
    { "name": "连续点击登录",   "expected": "防重复提交" },
    { "name": "网络断开",       "expected": "Toast: 网络不可用" }
  ]
}

```

## Step 3：渲染引擎 → H5 预览

Handoff 渲染引擎读取 `.handoff.jsonc` 文件，执行以下管线：

<whiteboard token="ZhUXwusK2hMaA2bgdTHczqr4n1e"></whiteboard>

### 渲染管线说明

| 阶段 | 输入 | 输出 |
|-|-|-|
| resolveRefs | Handoff 文档（含 \$ref 引用） | 展开后的完整文档 |
| generateCSSVars | design.tokens 定义 | :root CSS 变量声明 |
| renderLayoutTree | layoutTree 节点树 | HTML 元素字符串 |
| generateStateMachineJS | stateMachine 配置 | 浏览器端 JS 代码 |
| assembleHTML | CSS + HTML + JS + 导航 | 单文件 HTML 预览页 |

### 渲染结果

![图片展示的是Handoff渲染引擎输出的H5预览界面。画面中呈现了一个手机登录界面，上方显示“小米账号登录”，下方有“请输入手机号”“请输入验证码”等输入框，还有“登录”“使用微信登录”按钮。界面右侧有状态机交互面板，可点击事件触发状态转换。底部导航跳转面板展示了页面间跳转关系。该图片直观呈现了渲染引擎输出的H5预览结果，与文档中渲染引擎输出包含iPhone模拟器外壳、状态机交互面板等内容的说明相契合。](https://feishu.cn/file/WZRabsCGzoP0NZx4o27ck5CinYe)

渲染引擎输出一个独立的 HTML 文件，包含：

- 📱 iPhone 模拟器外壳（375×812，Dynamic Island 刘海 + iOS 状态栏）
- 🎨 Design Token 自动映射为 CSS 变量（支持 light/dark 主题）
- 🔄 状态机交互面板（右侧，可点击事件触发状态转换）
- 🧭 导航跳转面板（模拟器下方，展示页面间跳转关系）
- 📊 置信度指示器（confirmed/tentative/placeholder 三级标注）
- ▶️ Happy Path 自动播放（一键演示完整用户流程）

### 支持的 21 种内置节点类型

<grid>
<column width-ratio="0.330000">
- scaffold
- app-bar
- scroll-view
- column
- row
- text
- text-field
</column>
<column width-ratio="0.330000">
- button
- text-button
- icon-button
- image
- spacer
- checkbox
- rich-text
</column>
<column width-ratio="0.330000">
- safe-area
- bottom-sheet
- grid
- template
- animation-view
- conditional
- stack
</column>
</grid>

<callout emoji="🔧">
除 21 种内置类型外，还支持 customNodeTypes 扩展机制 — 上游产品定义新节点类型时，Handoff 文件中描述语义和样式，下游自动学习并渲染。
</callout>

## 完整流程总结

<whiteboard token="ZTkSwfiIfhmLNCbj4OXcHowsnuh"></whiteboard>

<callout emoji="🚀">
核心价值：产品用自然语言输入 → AI 生成四层结构化交付物 → 渲染引擎即时预览 → 产品验收后研发直接消费。全程无需 Figma，无需手动写文档，AI 驱动的端到端协作。
</callout>
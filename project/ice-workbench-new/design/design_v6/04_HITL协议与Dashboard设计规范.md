# ICE Workbench v6: HITL协议与Dashboard设计规范

本文档详细定义了 v6 版本中两个核心交互体验的落地规范：**HITL (Human-in-the-loop) 富交互卡片的前端渲染协议**，以及**全新中枢大盘 (Dashboard) 的布局与功能要素**。

---

## 一、 HITL 富交互卡片 (Rich Cards) 渲染协议

在多智能体协同的数据工作流中，Agent 经常需要中途挂起任务，请求人工审批、补充信息或修正数据。我们需要一套前后端约定的 JSON Schema 来渲染这些表单。

### 1. 核心状态流转
- **`pending` (等待操作)**：卡片呈现亮色，输入框可用，操作按钮激活。侧边栏执行树对应的节点显示为 `Paused`。
- **`resolved` (已处理)**：用户点击提交后，前端立刻将卡片置灰 (Disabled 状态)，按钮转为 Spinner 或替换为“已提交”文本。防止重复触发。

### 2. JSON Schema 规范 (Draft)

后端通过 WebSocket 下发的消息类型为 `hitl_card`，其 Payload 结构如下：

```typescript
interface HITLMessage {
  id: string;               // 消息唯一ID
  type: "hitl_card";
  role: "assistant";
  agent_id: string;         // 发起请求的子 Agent (如 "data_cleaner")
  timestamp: string;
  card_data: RichCardData;
}

interface RichCardData {
  card_type: "approval" | "form" | "data_correction";
  status: "pending" | "resolved";
  title: string;            // 卡片主标题
  description: string;      // 详细描述/请求原因
  
  // 上下文数据展示 (可选)，用于辅助决策
  context_data?: {
    type: "table" | "json" | "markdown";
    headers?: string[];
    rows?: string[][];
    content?: string;
  };

  // 用户输入项 (可选)
  inputs?: Array<{
    id: string;
    type: "text" | "number" | "select" | "boolean";
    label: string;
    placeholder?: string;
    required: boolean;
    options?: Array<{ label: string; value: string | number }>; // 用于 select
  }>;

  // 底部操作按钮 (必填，至少一个)
  actions: Array<{
    id: string;
    label: string;
    style: "primary" | "secondary" | "danger";
    value: string; // 传回后端的 action 标识
  }>;
}
```

### 3. 前端回传协议 (Submit Response)

当用户完成卡片交互后，前端将结果发回 WebSocket，后端接收到此消息后将唤醒挂起的 Agent：

```typescript
interface HITLResponse {
  type: "hitl_response";
  message_id: string;       // 对应下发的 HITLMessage ID
  action_value: string;     // 用户点击的按钮 value
  inputs_data: Record<string, any>; // 用户填写的表单数据，Key 为 input.id
}
```

---

## 二、 Dashboard v6 任务控制台设计规范

v6 的 Dashboard 不再是简单的“历史对话列表”，而是**基于数据工作流的任务控制台 (Mission Control)**。它的核心目标是：**暴露状态、管理异常、快速干预**。

### 1. 核心布局区块

Dashboard 从上到下应分为三个主要视觉区块：

#### 区块 A：顶部操作与欢迎区 (Top Bar)
- **Welcome Message**: 友好的问候。
- **Primary Action (New Task)**: 全局最醒目的 `+ New Task` 按钮，随时开启新的数据工作流。支持下拉选择模板（如“飞书数据分析模板”）。

#### 区块 B：高优关注区 (Requires Attention) - ✨ 核心亮点
- 这是整个 Dashboard 最重要的区域。
- 只要有任务处于 `Paused` (等待 HITL 审批) 或 `Failed` (执行异常) 状态，就会以醒目的**卡片形式**在这里置顶。
- **卡片要素**：
  - 醒目的状态标签 (如 `🟡 等待人工确认`)。
  - 任务名称与卡点原因描述 (如 "在执行清洗规则时发现 5 条异常数据")。
  - **Action Button**：直接点击 `去处理 ->`，跳转到 Task 详情页并定位到对应的 HITL 卡片。

#### 区块 C：运行大盘与历史流 (Active & Recent Stream)
分为两栏或上下两部分展示：
- **Running & Scheduled (运行中与定时)**：
  - 正在后台运行的长耗时任务，展示 Progress (如 `Agent: 报表生成中...`)。
  - 即将执行的 Cron 定时任务提示。
- **Recent Tasks (最近任务流)**：
  - 列表形态展现，信息密度更高。
  - 包含关键元数据：
    - **Data Sources** (数据源 Icon)：例如挂载了飞书表格、SQLite等。
    - **Agents** (参与者头像组)：展示主 Agent 和调度了哪些子 Agent。
    - **Time / Duration**：运行耗时（强调工作流属性）。

### 2. 设计风格与色彩 (UI/UX)
- **主题色**：延续 v6 探讨的暖色调/铜橙色 (Copper Orange, 类似 `#F97316` 体系)，传达“工作台”的专注感，区别于冷冰冰的传统开发工具。
- **卡片化 (Card-based)**：信息区块用圆角卡片隔离，带有轻微的阴影 (`shadow-sm`)。
- **空状态 (Empty State)**：当没有需要关注的任务时，隐藏该区域或展示极简的插画，保持界面清爽。

---
*本文档配合同目录下的 `dashboard_v6.html` 原型使用。*
---
name: schedule-send
description: |-
  定时发送日报 Skill：在4月15日凌晨2:00自动运行 have-a-try2 生成 P3升X 项目日报，
  并将日报内容写入飞书多维表格（项目管理部日报周报任务，TPM 闫小雨）。
  触发条件：用户提到"定时发送"、"定时日报"、"设置日报定时"时激活。
argument-hint: "可选：指定项目名，默认 P3升X"
---

# 定时发送 Skill

## 概述

在 **2026年4月15日 凌晨2:00** 自动运行 P3升X 项目日报，并将生成的日报内容写入飞书多维表格。

**目标多维表格：** 项目管理部日报周报任务（TPM 闫小雨）

| 参数 | 值 |
|------|-----|
| Wiki URL | `https://mi.feishu.cn/wiki/D0BYw1MJtits3ZkKkdqcamF8n1b` |
| app_token | `QXnXblgfEaThoCsDwFsc9vkxnJe` |
| table_id | `tbltx0Edan9Up3kN` |
| view_id | `vewZuO7aDp` |

**表格字段：**

| 字段名 | 类型 | 写入内容 |
|--------|------|---------|
| 文本 | 文本（主键） | `P3升X 项目日报-{YYYY-MM-DD}` |
| 日期 | 日期 | 自动填充 |
| TPM | 文本 | `闫小雨` |
| 项目 | 文本 | `P3升X` |
| 日报内容 | 文本 | have-a-try2 生成的简要日报（Step 8B 消息正文版） |
| 项目名称 | 文本 | `P3升X` |

---

## 执行步骤

### Step 1: 创建定时触发器

当用户调用本 skill 时，使用 RemoteTrigger 创建持久化定时任务：

```
RemoteTrigger({
  action: "create",
  body: {
    name: "P3升X日报定时发送",
    cron: "0 2 15 4 *",
    prompt: "P3升X项目日报定时任务：\n1. 使用 have-a-try2 skill 生成 P3升X 项目日报（执行完整10步流程）\n2. 获取生成的飞书文档URL和简要描述（Step 8B消息正文版）\n3. 使用 feishu CLI 将结果写入多维表格：\n   feishu bitable create-record QXnXblgfEaThoCsDwFsc9vkxnJe tbltx0Edan9Up3kN --fields '{\"文本\":\"P3升X 项目日报-{今日YYYY-MM-DD}\",\"TPM\":\"闫小雨\",\"项目\":\"P3升X\",\"项目名称\":\"P3升X\",\"日报内容\":\"{简要日报内容}\"}}'"
  }
})
```

**触发时间：** `0 2 15 4 *`（2026年4月15日 02:00，一次性）

> RemoteTrigger 持久化存储，关闭 Claude 会话后仍然有效。

---

### Step 2: 运行 have-a-try2 生成 P3升X 项目日报

定时触发后（或手动执行时），调用 have-a-try2 skill：

```
/have-a-try2 P3升X项目日报
```

执行完整的 10 步流程，完成后获取：
- `doc_title`：飞书文档标题（如 `P3升X 项目日报-2026-04-15`）
- `doc_url`：飞书文档 URL（Step 9 创建的文档链接）
- `brief_content`：Step 8B 生成的简要描述（群消息正文版本）

---

### Step 3: 写入飞书多维表格

日报生成完成后，立即向目标多维表格新增记录：

```bash
feishu bitable create-record QXnXblgfEaThoCsDwFsc9vkxnJe tbltx0Edan9Up3kN \
  --fields '{
    "文本": "P3升X 项目日报-{今日日期}",
    "TPM": "闫小雨",
    "项目": "P3升X",
    "项目名称": "P3升X",
    "日报内容": "{brief_content}"
  }'
```

**字段值填写说明：**
- `{今日日期}` → 格式 `YYYY-MM-DD`，如 `2026-04-15`
- `{brief_content}` → have-a-try2 Step 8B 输出的简要描述全文
- 日期字段为自动填充，无需手动写入

写入成功后，输出确认信息：
```
✅ 日报已写入「项目管理部日报周报任务」多维表格
   - 文本：P3升X 项目日报-{今日日期}
   - TPM：闫小雨
```

---

## 异常处理

| 异常情况 | 处理方式 |
|---------|---------|
| have-a-try2 执行失败 | 在多维表格日报内容字段写入"日报生成失败，请手动补充" |
| 多维表格写入失败 | 输出错误信息，提示检查 feishu 认证（`feishu auth login`） |
| 飞书文档URL未获取 | 详情链接字段留空，仅写入消息标题、日期、日报内容 |

---

## 触发方式汇总

| 触发方式 | 说明 |
|---------|------|
| 定时自动（RemoteTrigger） | 2026-04-15 02:00 自动执行，持久化，会话关闭后仍有效 |
| 手动调用 | 用户调用本 skill → 立即执行 Step 2 + Step 3 |
| CronCreate（会话内） | 仅限当前 Claude 会话有效，会话关闭后失效 |

---

## 配置信息

```json
{
  "project": "P3升X",
  "schedule": {
    "cron": "0 2 15 4 *",
    "description": "2026年4月15日 凌晨2:00",
    "recurring": false
  },
  "bitable": {
    "wiki_url": "https://mi.feishu.cn/wiki/D0BYw1MJtits3ZkKkdqcamF8n1b",
    "app_token": "QXnXblgfEaThoCsDwFsc9vkxnJe",
    "table_id": "tbltx0Edan9Up3kN",
    "view_id": "vewZuO7aDp",
    "name": "项目管理部日报周报任务"
  },
  "tpm": {
    "name": "闫小雨",
    "email": "yanxiaoyu1@xiaomi.com"
  }
}
```

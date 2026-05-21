# Feishu MCP Pro 工具使用指南

> 用途：AI Agent 操作飞书文档时的工具调用参考

## 功能总览

| 模块 | 核心能力 |
|------|----------|
| 多维表格 | 元数据查询、记录增删改查、批量操作、高级筛选、字段管理、视图创建 |
| 电子表格 | 创建表格、工作表管理、单元格读写、批量读写、查找替换、行列管理、样式设置 |
| 文档读写 | 读取、创建、覆写、追加飞书云文档。支持 Mermaid、Callout、多列布局、富文本表格 |
| 文档表格操作 | 插入/删除行列、合并单元格 |
| 知识库 | 浏览空间与节点、创建页面、移动/复制/重命名节点 |
| 权限 | 查看/添加/移除协作者 |
| 搜索 | 按关键词、作者、时间范围搜索飞书文档 |
| 评论 | 查看/添加文档评论 |
| 用户 | 获取用户信息、智能解析用户（open_id/邮箱/中文姓名） |
| 日历 | 查看日历、创建/编辑/删除日程、管理参会人、查询忙闲 |

## 一、文档读写（最常用）

| 工具 | 说明 | 注意 |
|------|------|------|
| `doc_read` | 读取文档内容和元数据 | 支持 wiki URL 自动解析 |
| `doc_create` | 创建文档 | 可指定 folder_token |
| `doc_write` | 覆写文档正文 | ⚠️ 不可恢复，会清空图片和画板 |
| `doc_append` | 在文档末尾追加内容 | 安全操作，推荐优先使用 |
| `doc_insert` | 在指定位置插入内容 | 需 after_block_id |
| `doc_update` | 更新指定段落 | 支持 replace/insert-before/insert-after/delete |

### 操作原则
- **只追加不覆写**：除非明确要重建文档，否则用 `doc_append` / `doc_insert`
- **doc_write 禁止在非重建场景使用**：会清空文档所有内容含图片画板，不可恢复

### 扩展 Markdown 语法

```markdown
# Callout 高亮块
<callout emoji="💡" background-color="light-blue">内容</callout>
# 背景色：light-red/blue/green/yellow/orange/purple/gray

# Mermaid 流程图（自动渲染为画板）
```mermaid
graph TD
    A[开始] --> B{判断}
```

# 图片嵌入
<image url="https://..." width="800" align="center" caption="描述"/>
```

## 二、多维表格

常用工具：`bitable_get_meta`、`bitable_list_records`、`bitable_search_records`、`bitable_create_record`、`bitable_update_record`、`bitable_batch_create`

### 筛选语法

| 语法 | 含义 |
|------|------|
| `字段=值` | 精确匹配 |
| `字段!=值` | 不等于 |
| `字段~关键词` | 模糊匹配 |
| `字段?` | 字段不为空 |

人员字段直接传企业邮箱自动解析；日期字段传 `YYYY-MM-DD` 自动转换。

## 三、知识库

常用工具：`wiki_list_spaces`、`wiki_list_nodes`、`wiki_get_node`、`wiki_create_node`

⚠️ `wiki_get_node` 必须传纯 token，不能传完整 URL。

## 四、关键注意事项

### 不可恢复操作
- `doc_write` 覆写文档
- 多维表格/电子表格删除操作
- `perm_remove` 移除协作者权限

### 引用块写法
- ✅ `> 纯文本` — 正确渲染
- ❌ `> - 列表项` — 飞书不支持 blockquote 内嵌列表
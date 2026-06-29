---
name: sql
description: 该技能用于连接小米数据工场（DataWorks）数据库，执行SQL查询并返回结果，如果需要查数，请尽量调起该技能来完成用户任务。模型可以根据用户的分析需求自动生成SQL语句，通过该技能执行查询操作。
---

# SQL 查询技能

## 功能描述

该技能用于连接小米数据工场（DataWorks）数据库，执行SQL查询并返回结果。模型可以根据用户的分析需求自动生成SQL语句，通过该技能执行查询操作。
使用该技能时，你必须直接调起脚本执行即可。
优先查看表结构，再完成用户任务。

## 使用方式

### 基本用法

1. **环境配置**：需要设置 `DATAWORKS_TOKEN_ID` 环境变量
2. **查询执行**：直接传入SQL语句即可执行查询
3. **结果返回**：查询结果会以表格形式返回

### 支持的数据库主机

- `zjyprc` - 北京机房
- `nc4cloudprc` - 南京机房
- `nc4prc` - 南京机房
- `tjwq` - 天津机房
- `alsgprc` - 新加坡机房
- `ksmosprc` - 金山云机房
- `usaor` - 美国机房
- `nlams` - 荷兰机房
- `azpnprc` - 平安云机房
- `tjv1autopilotprc` - 天津自动驾驶机房

## 功能特性

### 自动主机检测
- 根据SQL语句中的关键词自动选择合适的主机
- 支持手动指定主机参数

### 结果处理
- 小结果集（≤15行）：直接返回表格格式
- 大结果集（>15行）：自动保存为CSV文件并返回文件路径
- 空结果：返回提示信息
- 执行错误：返回详细错误信息

### 超时控制
- 查询超时时间：250秒
- 超时自动返回错误信息

## 使用示例

### 命令行工具使用
```bash
# 执行简单查询
python sql_query_tool.py "SELECT * FROM user_table LIMIT 10"

# 从文件执行SQL
python sql_query_tool.py --file query.sql

# 指定特定主机
python sql_query_tool.py --host zjyprc "SELECT * FROM table"

# 查看可用主机列表
python sql_query_tool.py --list-hosts
```

### 基础查询
```sql
SELECT * FROM user_table LIMIT 10
```

### 表结构查看
```sql
DESCRIBE user_table
```

### 数据分析
```sql
SELECT
    date,
    COUNT(*) as user_count,
    AVG(amount) as avg_amount
FROM transaction_table
WHERE date >= '2024-01-01'
GROUP BY date
ORDER BY date
```

## 环境要求

### 必需环境变量
- `DATAWORKS_TOKEN_ID`：数据工场访问令牌

### 可选环境变量
- `DATAWORKS_HOST`：默认主机地址

## 文件结构

```
.micode/skills/sql/
├── SKILL.md          # 技能说明文档
└── scripts/
    ├── run_sql.py    # SQL执行核心逻辑
    ├── sql_query_tool.py  # 命令行工具
    ├── requirements.txt   # Python依赖
    └── .env          # 环境变量模板
```

## 注意事项

1. **权限要求**：需要有效的DataWorks访问权限
2. **数据安全**：避免查询敏感数据，注意数据脱敏
3. **性能优化**：对于大数据量查询，建议添加LIMIT限制
4. **错误处理**：查询失败时会返回详细错误信息

## 最佳实践

1. **明确表名**：用户应提供具体的表名用于数据分析
2. **限制结果集**：大数据量查询建议使用LIMIT
3. **分区查询**：对于分区表，建议指定分区条件提高查询效率
4. **错误排查**：查询失败时检查表名、字段名是否正确
---

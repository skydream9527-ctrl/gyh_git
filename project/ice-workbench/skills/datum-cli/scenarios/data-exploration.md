# 数据资产探索

覆盖 catalog、database、table、partition、schema、fileset 的查询操作。

## 典型工作流：查找并了解一张表

```bash
# 场景："帮我看看 xxx 表的字段结构"

# 1. 如果不知道表在哪个 catalog/database，先用关键词搜索
datum table list --keyword "xxx" -o table

# 2. 确认可用的 catalog 列表
datum catalog list -o table

# 3. 找到对应的 database
datum database list --catalog <catalog> -o table

# 4. 获取表的基本元信息（类型、Owner、存储路径等）
datum table get --catalog <catalog> --db <database> --table <table>

# 5. 获取字段详情（名称、类型、注释）
datum table columns --catalog <catalog> --db <database> --table <table>

# 6. 获取建表 DDL（了解完整表结构）
datum table ddl --catalog <catalog> --db <database> --table <table>
```

## 分区查询

```bash
# 列出所有分区
datum partition list --catalog <catalog> --db <database> --table <table>

# 按条件过滤分区（支持 =、>=、<= 等表达式）
datum partition list --catalog <catalog> --db <database> --table <table> \
  --filter "dateint>=20240101"

# 只获取分区名称列表（轻量）
datum partition names --catalog <catalog> --db <database> --table <table>

# 查看某个分区的详情
datum partition get --catalog <catalog> --db <database> --table <table> \
  --partition-name "dateint=20240101"
```

## 表审计日志

```bash
# 查看表的操作记录（谁在什么时间做了什么）
datum table log --catalog <catalog> --db <database> --table <table>

# 指定时间范围（Unix 毫秒时间戳）
datum table log --catalog <catalog> --db <database> --table <table> \
  --start 1704067200000 --end 1704153600000 --page 1 --page-size 50
```

## Schema 查询（Gravitino Fileset 场景）

```bash
# 查看 Schema 详情
datum schema get --name <schema-name>

# 查看指定版本
datum schema get --name <schema-name> --version 2

# 列出所有 Schema
datum schema list --keyword <keyword>

# 查看某 Schema 绑定了哪些 Fileset
datum schema bound-filesets --name <schema-name>
```

## Fileset 查询

```bash
datum fileset get --catalog <catalog> --db <database> --fileset <name>
```

## 数据库 Owner 查询

```bash
datum database owners --catalog <catalog> --database <database>
datum database owners --catalog <catalog> --database <database> --only-admin
```

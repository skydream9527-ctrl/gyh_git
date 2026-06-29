# 任务与工作流管理

覆盖 job、workflow 的完整生命周期，以及 variable（变量）和 group（目录）管理。

## 支持的任务类型

`spark-sql` `spark-jar` `flink-sql` `flink-jar` `flink-sql-batch` `shell`
`hive2doris` `hdfs-sensor` `hive-sensor` `iceberg-sensor` `hdfs-touch`
`hook` `notebook` `cloudml` `data-push` `serverlog` `copy` `integration`

## 任务生命周期

```bash
# 完整生命周期：创建 → 上线 → 启用调度 → 运行 → 停止 → 下线 → 删除

# 1. 创建（需要 JSON 配置文件，见下方说明）
datum job create --type spark-sql --from-file ./job.json

# 2. 查看任务详情，确认创建成功
datum job get --job-id <id>

# 3. 上线（激活任务，使其可被调度）
datum job online --job-id <id>

# 4. 启用调度
datum job enable-schedule --job-id <id>

# 5. 手动触发一次运行
datum job start --job-id <id>

# 6. 停止运行中的任务
datum job stop --job-id <id>

# 7. 重跑（重新执行最近一次）
datum job redo --job-id <id>

# 8. 禁用调度
datum job disable-schedule --job-id <id>

# 9. 下线
datum job offline --job-id <id>

# 10. 删除（先确认已下线）
datum job delete --job-id <id>
# 强制删除（跳过状态检查）
datum job delete --job-id <id> --force
```

## --from-file JSON 文件构造

需要 `--from-file` 的命令（create、update），agent 先将 JSON 写入临时文件：

```bash
# Linux / macOS
cat > ./job_spec.json << 'EOF'
{
  "name": "my_spark_job",
  "description": "说明",
  ...
}
EOF
datum job create --type spark-sql --from-file ./job_spec.json

# Windows (PowerShell)
# '{ "name": "my_spark_job", ... }' | Out-File -Encoding utf8 .\job_spec.json
# datum job create --type spark-sql --from-file .\job_spec.json
```

> **参考模板：** 通过 `datum job get --job-id <已有任务id>` 查看现有任务结构作为参考。

## 流式任务（Flink）特有操作

```bash
datum job online  --job-id <id>   # 上线流式任务（启动运行）
datum job offline --job-id <id>   # 下线流式任务（停止运行）
datum job restart --job-id <id>   # 重启
datum job delete-checkpoint --job-id <id>  # 删除 checkpoint 文件
```

## 工作流管理

```bash
# 列出工作流
datum workflow list --keyword <keyword>

# 查看工作流详情（含节点配置）
datum workflow get --id <id>

# 运行工作流（所有节点）
datum workflow run --id <id>

# 运行指定节点
datum workflow run-partial --id <id> --from-file ./nodes.json

# 上线 / 下线
datum workflow online --id <id>
datum workflow offline --id <id>

# 启用 / 禁用调度
datum workflow enable-schedule --id <id>
datum workflow disable-schedule --id <id>

# 查看工作流中的任务列表
datum workflow jobs --id <id>

# 创建 / 更新
datum workflow create --from-file ./workflow.json
datum workflow update --id <id> --from-file ./workflow_update.json
```

## 根据表血缘查找相关任务

```bash
# 找出写入或读取了某张表的所有任务
datum job search-by-table --catalog <catalog> --db <database> --table <table>
```

## 变量管理

```bash
datum variable list           # 列出所有变量（分页）
datum variable names          # 只列出变量名（Key 列表）
datum variable edit --from-file ./var.json  # 修改变量
```

## 目录分组管理

```bash
# 查看当前目录树（离线任务）
datum group view
datum group view --type realtime    # 实时任务目录树

# 创建新分组
datum group create --from-file ./group.json
datum group create --from-file ./group.json --type realtime

# 批量移动任务到指定分组
datum group move-jobs --from-file ./move.json
datum group move-workflows --from-file ./move_wf.json
```

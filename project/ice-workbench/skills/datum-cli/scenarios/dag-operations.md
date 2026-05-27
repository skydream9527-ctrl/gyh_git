# DAG 运行监控与运维

覆盖 dag、dag-node、batch-dag 的查询与运维操作。本指南旨在协助运维人员快速定位问题。

## 运维巡检工作流

在日常巡检中，通常遵循从宏观到微观的排查路径。

```bash
# 1. 全局概览（查看当前工作空间内所有 DAG 的状态分布汇总）
datum dag overview

# 2. 列出失败的 DAG
# 使用 -o table 参数以表格形式展示更清晰
datum dag list --status FAILED -o table

# 状态候选项还包括: RUNNING / SUCCESS / STOPPED
# 可以根据需要筛选处于运行中或已停止的任务

# 3. 查看某个具体 DAG 的详情
# 该命令会展示 DAG 内所有节点的状态及其依赖关系
datum dag get --dag-id <id>

# 4. 查看失败任务的日志
# 需先从 dag get 的输出中找到对应的 task-id
datum dag task log --task-id <task-id>

# 5. 重试失败的节点
# 仅重跑失败部分，不需要重跑整个 DAG，节省计算资源
datum dag retry-failed --dag-id <id>

# 6. 批量停止多个 DAG
# 如果发现大面积异常，可通过逗号分隔 ID 快速止损
datum dag stop --dag-ids "id1,id2,id3"
```

## DAG 任务详情

当需要深入分析单个任务的执行细节时，可以使用以下命令：

```bash
# 获取任务的完整详情，包括运行环境、配置参数等
datum dag task get --task-id <task-id>

# 获取底层引擎的任务 ID
# 获取 YARN 或 Flink 的 App ID，用于在对应的 Web UI 中查看运行详情
datum dag task app-id --task-id <task-id>

# 获取任务的相关链接
# 快速获取 Spark UI、监控看板或原始日志的链接
datum dag task links --task-id <task-id>

# 获取任务日志内容
# 直接在终端输出日志文本，方便快速 grep 关键字
datum dag task log --task-id <task-id>
```

## DAG 节点级别查看（dag-node）

适用场景：某个节点反复失败，或者需要查看特定节点的历史任务执行记录时使用。

```bash
# 1. 定位节点 ID
# 先通过 dag get 找到目标节点的 node-id
datum dag get --dag-id <id>
# 在输出的节点列表中查找 nodeId 字段

# 2. 查看该节点的历史任务执行列表
# 了解该节点在过去一段时间内的执行表现
datum dag-node tasks --id <node-id>

# 3. 查看节点自身的定义详情
datum dag-node get --id <node-id>

# 4. 全局列出 DAG 节点
# 配合分页参数，在大规模场景下逐步浏览
datum dag-node list --page 1 --page-size 20
```

## 补数据（Backfill）

在数据回溯或补录场景下，使用 batch-dag 命令进行监控。

```bash
# 列出历史补数任务及其总体状态
datum batch-dag list --page 1 --page-size 20

# 查看某次补数任务中包含的所有 DAG 运行状态
# 这能帮助确定补数任务的整体进度
datum batch-dag dags --id <batch-dag-id>
```

## 运维提示

- 优先处理 FAILED 状态的 DAG，防止下游数据延迟。
- 善用 `--page-size` 控制列表输出量，避免终端卡顿。
- 重试操作前，建议先通过 `links` 查看 Spark/Flink UI 确认失败原因。
- 批量停止操作需谨慎，确保 ID 输入正确。

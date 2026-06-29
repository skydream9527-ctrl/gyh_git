# Kestra AI 数据开发

覆盖 Kestra 流程编排引擎的 Flow、Execution、日志、命名空间文件、KV 存储等全链路操作。

## Flow 开发调试工作流

```bash
# 1. 验证 Flow 定义（提交前先验证语法）
datum kestra flow validate --from-file my_flow.json

# 2a. 创建新 Flow
datum kestra flow create --from-file my_flow.json

# 2b. 更新已有 Flow
datum kestra flow update --namespace <ns> --id <flow-id> --from-file my_flow.json

# 3. 手动触发一次执行（无需等待调度）
datum kestra execution trigger --namespace <ns> --id <flow-id>
# 带输入参数
datum kestra execution trigger --namespace <ns> --id <flow-id> --from-file ./inputs.json

# 4. 查看执行状态
datum kestra execution get --execution-id <exec-id>

# 5. 查看执行日志
datum kestra log get --execution-id <exec-id>
datum kestra log get --execution-id <exec-id> --minLevel WARN   # 只看 WARN 及以上

# 6. 失败时重启（只重跑失败的 Task，复用已成功的结果）
datum kestra execution restart --execution-id <exec-id>
```

## Execution 管理

```bash
# 搜索 Execution
datum kestra execution search --namespace <ns> --flowId <flow-id> --state FAILED

# 终止运行中的 Execution
datum kestra execution kill --execution-id <exec-id>

# replay vs restart 的区别：
# replay: 完整重新运行，创建新的 Execution 实例
datum kestra execution replay --execution-id <exec-id>
# restart: 只重跑失败的 Task，在原 Execution 上继续
datum kestra execution restart --execution-id <exec-id>

# 取消排队等待的 Execution
datum kestra execution unqueue --execution-id <exec-id>

# 删除 Execution 记录
datum kestra execution delete --execution-id <exec-id>

# 在 Execution 上下文中测试表达式（调试用）
datum kestra execution eval --execution-id <exec-id> \
  --task-run-id <task-run-id> --expression "{{ inputs.myParam }}"

# 查看 Execution 拓扑图（节点依赖关系）
datum kestra execution graph --execution-id <exec-id>
```

## 批量日志搜索

```bash
# 滚动搜索日志（跨 Execution 搜索）
datum kestra log scroll --namespace <ns> --flowId <flow-id> --minLevel ERROR
datum kestra log scroll --q "关键词" --page 1 --size 50
```

## 执行状态速览

```bash
# 查看每个 Flow 的最新一次执行状态（快速了解整体健康度）
datum kestra status latest --namespace <ns>

# 查看每个 Flow 最近 5 次执行结果（趋势判断）
datum kestra status recent --namespace <ns>
```

## Flow 搜索与管理

```bash
# 搜索 Flow
datum kestra flow search --q "关键词" --namespace <ns>

# 查看 Flow 定义
datum kestra flow get --namespace <ns> --id <flow-id>

# 删除 Flow
datum kestra flow delete --namespace <ns> --id <flow-id>

# 批量更新多个 Flow
datum kestra flow batch-update --from-file ./flows.json
```

## 命名空间文件管理（ETL 脚本）

```bash
# 列出目录内容
datum kestra ns-file ls --namespace <ns>
datum kestra ns-file ls --namespace <ns> --path /scripts

# 查看文件内容
datum kestra ns-file get --namespace <ns> --path /scripts/etl.py

# 查看文件元信息（大小、修改时间）
datum kestra ns-file stat --namespace <ns> --path /scripts/etl.py

# 上传文件
datum kestra ns-file upload --namespace <ns> --from-file ./local_script.py

# 搜索文件
datum kestra ns-file search --namespace <ns> --q "etl"

# 创建目录
datum kestra ns-file mkdir --namespace <ns> --path /new-dir

# 删除文件或目录
datum kestra ns-file delete --namespace <ns> --path /old-dir

# 导出整个命名空间文件为 ZIP
datum kestra ns-file export --namespace <ns>
```

## KV 存储

```bash
datum kestra kv get --namespace <ns> --key <key>
```

## 插件 Schema 查询

```bash
# 获取某个插件类型的 JSON Schema（用于了解配置字段）
datum kestra plugin schema --type io.kestra.plugin.scripts.python.Script
```

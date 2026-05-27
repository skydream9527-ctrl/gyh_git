# 资源、权限与账户管理

覆盖 workspace、token、permission、resource（jar/queue/datasource）、account 的管理操作。

## 权限检查

```bash
# 检查当前 Token 对某张表的权限
datum token check --catalog <catalog> --db <database> --table <table>
# 返回空数组 [] 表示无权限问题；返回权限详情表示有限制

# 检查表的访问控制状态
datum permission check --catalog <catalog> --db <database> --table <table>

# 查看哪些工作空间对某张表有访问权限
datum permission table-workspaces --catalog <catalog> --db <database> --table <table>
```

## 多工作空间切换

```bash
# 查看所有可访问的工作空间
datum workspace list

# 查看已配置的本地 profile
datum config list

# 切换到目标工作空间
datum config use "目标工作空间名"

# 验证切换成功
datum workspace info
```

## 工作空间详情

```bash
# 当前工作空间完整信息
datum workspace info

# 查看成员列表
datum workspace members --workspace-id <id>

# 查看可用区域
datum workspace regions

# 查看 Kerberos 和队列资源
datum workspace resources
```

## Token 管理

```bash
# 查看当前 Token 详情（归属、权限范围等）
datum token info

# 列出工作空间下所有 Token
datum token list --workspace-id <id> --user <username>

# 创建新 Token
datum token create --workspace-id <id> --user <username> --description "用途说明"
```

## 权限授予与撤销

```bash
# 授予 Kerberos 权限（需要 JSON 文件）
datum permission grant --from-file ./grant.json

# 撤销权限
datum permission revoke --from-file ./revoke.json

# 删除表权限记录
datum permission delete --from-file ./delete.json
```

## 资源管理

```bash
# 列出所有计算队列
datum resource queue list

# 按集群查询队列
datum resource queue by-cluster --cluster <cluster-name>

# 列出 Jar 包
datum resource jar list
datum resource jar list --keyword "关键词"

# 查看 Jar 包版本列表
datum resource jar versions --jar-id <id>

# 上传 Jar 包（需要 JSON 描述文件）
datum resource jar upload --from-file ./jar_spec.json

# 列出 MySQL 数据源
datum resource datasource list

# 创建 MySQL 数据源
datum resource datasource create --from-file ./datasource.json

# 导入 MySQL 表到平台
datum resource datasource import-table --from-file ./import.json
```

## 账户与身份

```bash
# 获取飞书用户 Access Token（用于 SSO 场景）
datum account feishu-token
datum account feishu-token --code <auth-code>

# 获取 IAM Access Key / Secret
datum account iam-secret
```

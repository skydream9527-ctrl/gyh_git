# datum CLI 数据工场操作

通过 `datum` CLI 与数据工场交互，结构化 JSON 输出，覆盖数据资产 / SQL 查询 / 任务调度 / DAG 运维 / Kestra 开发 / 权限管理全链路。

**触发场景**：用户提到「数据工场」「datum」「数据资产」「DAG」「Kestra」；要求查表、跑 SQL 调度、看任务运行情况、配权限。
**主要功能**：`datum asset` 资产元信息、`datum sql` 跑 SQL 任务、`datum task` 调度运维、`datum dag` 看 DAG、`datum kestra` Kestra 开发、`datum perm` 权限授予。
**注意**：所有命令输出都是 JSON，便于程序化解析；首次使用先 `datum version` 确认安装，未装走自动安装流程。

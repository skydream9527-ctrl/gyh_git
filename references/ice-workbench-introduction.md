# ICE Data Workbench v3 · 简要介绍

> 源仓库：`https://git.n.xiaomi.com/gongyunhe/ice-workbench`
> 整理时间：2026-05-27

---

## 一句话定位

**面向数据团队的 AI 数据工作流工作台**——把"数据分析、AB 实验、灰度、波动归因、经营洞察"五大业务范式做成 5 个可被 LLM 调度的 Agent，用任务（Task）作为协作原子单元，前后端一体化交付，本地一行命令启动。

## 它解决什么问题

| 痛点 | ICE Workbench 的方案 |
|---|---|
| 数据同学要在多个 BI / SQL / 实验平台间来回切换 | 一个工作空间承接「自然语言 → SQL → 解读 → 经验沉淀」全流程 |
| LLM 单次问答无法承接长任务、定时回放、多轮 Tool Calling | 5 轮 bounded ReAct + cron 调度 + 经验卡片审核闭环 |
| 模型供应商绑死、Anthropic / OpenAI / Vertex 协议各异 | mify 网关按 model id 前缀路由 4 套协议，统一成内部事件流 |
| AI 工具的运行数据、对话、产物难以审计 / 跨机搬运 | G3 文件优先存储——文件系统是 source of truth，SQLite 仅作 cache 索引 |
| Python 数据分析需要安全沙箱 | data-analysis agent 自带 venv-sandbox（CPU/内存/磁盘/网络全限制） |

## 关键能力一览

- **24 个生产路由**：`/dashboard` 任务首页 / `/workspace/:taskId` 三栏工作空间 / `/create-task` 3 步工坊 / `/scheduled-tasks` 定时调度 / `/agent/:agentId` Agent 详情 / `/admin/*` 13 个管理后台。
- **5 个内置 Agent**：`data-analysis`（NL→SQL + 多专家辩论）/ `general`（开放任务）/ `know`（飞书 KB + RAG）/ `learn`（网页抓取 + 知识沉淀）/ `_shared`（共享运行时）。
- **5 大业务范式**：AB 实验 / 经营分析 / 版本灰度 / 数据分析 / 波动归因，前端用 Morandi 配色区分。
- **8 个预设模型**：Claude / GPT / Gemini / GLM / MiMo，全走 mify 网关，支持 Anthropic native streaming + tool_use。
- **三级权限体系**：`super_admin`（必须飞书 OAuth）/ `admin` / `user`，权限矩阵硬编码在 `requirements/SHARED.md`。
- **跨机部署**：`make pack` 打包 → scp → `./deploy.sh --prod` 起单端口（8000）SPA + API + WS 一体伺服。

## 技术栈快照

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy + Pydantic + portalocker（文件锁）+ uvicorn |
| 前端 | React 18（声明 19）+ Vite + TypeScript + Zustand + react-markdown + DOMPurify |
| 模型网关 | mify gateway 统一协议，本地 fallback 到 Anthropic SDK |
| 存储 | 文件系统（JSON/JSONL）为 source of truth + SQLite `/.cache/index.db` cache 索引 |
| 认证 | JWT 双 token + 米盾（Aegis）`X-Proxy-UserDetail` RSA 验签 + 飞书 OAuth |
| 沙箱 | 独立 venv `.venv-sandbox/` + RLIMIT_AS（Linux）+ socket monkey-patch + 白名单包 |
| 部署 | `deploy.sh` 单脚本（`--run` dev / `--prod` 生产单端口） + systemd unit |

## 当前完成度

- ✅ 核心闭环：登录 → 任务列表 → 工作空间 → 流式对话 → 5 轮 Tool Calling → 产物落盘 → 经验沉淀
- ✅ 后台：用户 / Agent / Skill / KB / 文件 / 模板 / 经验卡 / 公共任务 / 审计 / 用量预算 / SQL 审计
- ✅ 调度：scheduler 每 20 秒扫描 cron + 历史回放
- ✅ 飞书登录：真实 OAuth + 自动建号 + 严格白名单互斥开关
- ⏳ 待补：飞书 KB 真实联调 / Mify RAG 集成 / 移动端适配 / WebSocket subprotocol token 升级

## 适用场景

1. **数据团队内部** AI Copilot——SQL 生成 + 解读 + 报告同步飞书
2. **AB 实验同学** 自助查询 + 结论沉淀，避免每次找数据同学跑数
3. **经营分析** 每日定时跑 cron 任务出周报
4. **学习沉淀** 经验卡片审批后自动注入对应 Agent 的 system prompt（D118）

## 快速链接

- 设计文档：`design_decisions.md`（133 决策 + 3 全局约束）
- 全局约束：`requirements/SHARED.md`
- 后端约定：`requirements/BACKEND.md`
- 前端约定：`requirements/FRONTEND.md`
- 路由 ↔ 决策映射：`reference/route-map.md`
- 设计稿：`design_v3/`（14 份 HTML）

详细架构与设计原则见同目录 [`ice-workbench-design.md`](./ice-workbench-design.md)；上手与运维操作见 [`ice-workbench-usage-guide.md`](./ice-workbench-usage-guide.md)。

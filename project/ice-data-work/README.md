# ICE-DATA-WORK

人 + AI 分身 + 工具 Agent 在同一块任务看板上协作的**团队数据工作台**。核心理念 **User → Twin → Agents**：你对自己的数字分身（Wisdom Twin）说话，分身去协调专业 Agent 干活，高风险动作回来请你确认。

底座沿用 ICE Data Workbench（FastAPI + React + G3 文件优先存储），融合 TokenWisdom 的分身与分级授权、Multica 的"Agent 即同事 + 看板 + 运行时"。

## 快速开始

```bash
make install     # 后端 pip + 前端 npm（首次约 2-5 分钟）
make dev         # 后端 :8000 + 前端 :5173
# 健康检查：http://localhost:8000/api/v1/health
```

或自托管（Docker，含 Postgres+pgvector）：

```bash
cp .env.example .env     # 必改 IDW_SECRET_KEY + LLM key
docker compose up -d --build
```

## 仓库结构

```text
ICE-DATA-WORK/
├── README.md            本文件
├── DEV_PLAN.md          开发计划（M0–M6 + 当前状态）
├── Makefile             install/dev/backend/frontend/test/fmt/prod
├── .env.example         环境变量样例
├── docker-compose.yml   app + postgres(pgvector)
├── backend/             FastAPI + SQLAlchemy + G3 存储
│   └── app/{main.py, core/, api/, services/, schemas/, seed/}
├── frontend/            React 18 + Vite + TS + Zustand
│   └── src/{App.tsx, pages/, components/, stores/, api/}
├── agents/ skills/      Agent / Skill 定义（团队/平台共享，G3）
├── teams/               团队/项目共享空间（G3，D-07）
├── users/ tasks/ files/ 用户/任务/文件数据（G3 文件优先）
└── docs/                设计文档 + 原型 + 参考资料
    ├── 2026-06-27-ICE-DATA-WORK-设计方案-v1.md         总纲（决策 D-01~D-14）
    ├── 2026-06-27-ICE-DATA-WORK-01-产品功能与交互设计.md
    ├── 2026-06-27-ICE-DATA-WORK-02-技术实现方案与开发ToDo.md
    ├── 2026-06-27-ICE-DATA-WORK-03-Agent与空间文件区设计.md
    ├── 2026-06-27-ICE-DATA-WORK-介绍与使用文档-v1.md
    ├── prototype/       可点击 HTML 原型（双击 prototype/index.html）
    └── 参考资料/         TokenWisdom 历史材料
```

## 核心架构（G3 · 文件优先）

文件系统是唯一真相源；SQLite 与 pgvector 都是可重建的派生索引。所有持久数据落在四层空间：

- **任务空间** `tasks/{tid}/` — 对话、文件、过程记忆（不跨任务）
- **Agent 空间** `agents/{aid}/` — 手册、技能、经验（定义团队共享，情景记忆按用户分区）
- **用户空间** `users/{uid}/` — Twin 画像、长期记忆（仅本人）
- **团队/项目空间** `teams/{tid}/...` — 共享文件/知识/产物（按团队或项目隔离）

详见 `docs/`。开发顺序见 `DEV_PLAN.md`。

## 安全与治理

三轴权限（平台角色 × 团队/项目成员 × Twin L0-L5）；高风险动作必须用户确认；用户贡献代码一律沙盒执行；全程审计 + 一键暂停。

> 内部部署：飞书 OAuth / Kyuubi / 米盾(Aegis)。缺失外部 CLI 时相关能力返回 `*_NOT_CONFIGURED`，不阻塞启动。

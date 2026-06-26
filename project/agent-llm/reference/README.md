# AI 研发参考资料

本目录收集了来自飞书文档的 AI Native 研发实践参考资料，按主题分类组织。

## 📂 目录结构

### agent-platforms/ — Agent 平台架构与实践
| 文件 | 内容 | 核心要点 |
|------|------|----------|
| [mica-issue-driven-managed-agent.md](./agent-platforms/mica-issue-driven-managed-agent.md) | MiCA - Issue驱动的Managed Agent探索实践 | 多Agent协作平台、5类Agent角色（Clarifier/Executor/ReviewCoordinator/QA/Monitor）、Memory机制、Wiki知识库复利、自进化飞轮、需求交付工作流、Roadmap规划 |
| [migame-bot-ai-agent-practice.md](./agent-platforms/migame-bot-ai-agent-practice.md) | migame-bot - 飞书AI Agent开发实践分享 | ReAct循环架构、插件式工具体系、Prompt宪法式管理、模型路由动态成本优化、安全加固、从零构建Agent的完整指南、踩坑经验 |

### collaboration-protocols/ — 跨角色协作协议
| 文件 | 内容 | 核心要点 |
|------|------|----------|
| [handoff-end-to-end-demo.md](./collaboration-protocols/handoff-end-to-end-demo.md) | Handoff协议端到端演示 | 自然语言需求→四层结构化Handoff文件→H5即时预览完整流程，含layoutTree布局树、stateMachine可执行状态机、Design Token系统、组件映射、测试用例、21种内置节点类型、渲染管线 |
| [handoff-protocol-capabilities.md](./collaboration-protocols/handoff-protocol-capabilities.md) | Handoff协议能力矩阵（七层架构38项功能） | 核心协议层（6项）、智能引擎层（6项）、协作管理层（7项）、渲染与预览层（6项）、CLI工具链（6项）、多IDE适配层（5个IDE）、外部集成层（2项），存量项目扫描能力 |
| [multi-perspective-specification.md](./collaboration-protocols/multi-perspective-specification.md) | 多视角Spec规范 | 6个视角完整需求交付标准：产品视角（做什么）、技术视角（怎么实现）、数据视角（怎么衡量）、评测视角（AI质量怎么评）、测试视角（怎么测）、运维视角（怎么运维） |

### design-systems/ — 设计系统
| 文件 | 内容 | 核心要点 |
|------|------|----------|
| [design-token-practice.md](./design-systems/design-token-practice.md) | Design Token系统落地实践 | Token三层消费架构（theme.css→components.css+shell.js→版本styles.css）、版本隔离物理冻结机制、AI生成色彩比例量化约束、设计角色从"画页面"到"定义规则+审查输出"的转变 |

### development-workflows/ — 研发工作流
| 文件 | 内容 | 核心要点 |
|------|------|----------|
| [ai-native-git-workflow.md](./development-workflows/ai-native-git-workflow.md) | AI Native Git工作流指南 | 0代码基础AI转型操作指南、分支规范（feat/fix/refactor）、GitLab Pages内网预览、5步上手流程 |

## 🔗 关键关联

- **Agent Memory系统**：参考 [../agents/memory-systems.md](../agents/memory-systems.md) 与 MiCA 文档中 Memory/Wiki 机制结合
- **多Agent协作**：参考 [../agents/multi-agent-coordination.md](../agents/multi-agent-coordination.md) 与 Handoff 协议
- **Skills系统设计**：参考 [../agents/skills-system-design.md](../agents/skills-system-design.md) 与 MiCA Skills 技能系统、Handoff 节点类型扩展机制
- **MCP协议**：参考 [../mcp-deep-dive/](../mcp-deep-dive/) 与 migame-bot 工具体系

## 📅 更新记录
- 2026-06-26: 首次整理7份飞书文档入库

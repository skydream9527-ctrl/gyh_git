# 文档归档中心

> 所有生成的文档统一归档管理，便于检索和追溯。支持飞书文档链接、Markdown源文件、HTML导出文件及其他格式。

## 目录结构

```
文档归档/
├── README.md           # 本文件（归档索引）
├── 季度规划复盘/       # 季度OKR规划与复盘文档（Q1/Q2/Q3...）
├── 飞书文档/           # 飞书文档链接归档（.url 或 .md 记录链接+标题+日期）
├── Markdown文件/       # Markdown源文件归档（按日期命名）
├── HTML文件/           # HTML导出文件归档
└── 其他格式/           # PDF、Word、PPT等其他格式文档归档
```

## 归档规则

### 1. 命名规范
- 统一命名格式：`YYYY-MM-DD-文档主题.扩展名`
- 示例：
  - 飞书文档：`2026-06-26-知识库重构方案.url.md`
  - Markdown：`2026-06-26-AB实验方法论总结.md`
  - HTML：`2026-06-26-数据分析报告.html`

### 2. 飞书文档归档格式
飞书文档使用 `.url.md` 文件记录，包含以下信息：
```markdown
# 文档标题
- 创建日期：YYYY-MM-DD
- 飞书链接：https://feishu.cn/docx/xxxxxx
- 文档类型：分析报告/方案/PRD/会议纪要/其他
- 关键词：关键词1, 关键词2, 关键词3
- 关联项目：项目名称（可选）
```

### 3. 归档流程
1. 文档生成完成后，**必须**将文件/链接归档到本目录对应子目录
2. 如果是飞书文档，创建 `.url.md` 索引文件记录链接和元信息
3. 本地MD/HTML/其他文件直接复制/移动到对应子目录
4. 在本README的「归档索引」表格中追加一条记录
5. 跨领域关联文档在对应知识库目录中建立软链接或引用

### 4. 索引维护
每次归档后，在下方「归档索引」表格中追加记录，保持最新在最上方。

## 归档索引

| 日期 | 文档主题 | 类型 | 链接/位置 | 关键词 |
|------|----------|------|-----------|--------|
| 2026-06-28 | ICE DataWork新平台设计 | 产品设计 | [飞书文档](https://mi.feishu.cn/docx/ZOREdrAPtoFD8PxruFqchNYSnbh) | ICE DataWork,平台设计,产品架构,nl-sql,AI工作台 |
| 2026-06-27 | TokenWisdom 产品页面 v11 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-product-prd-pages-v11.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-产品页面-v11.html) | TokenWisdom,Workstation,Workspace,Agent-to-Agent,数字分身,PRD页面 |
| 2026-06-27 | TokenWisdom 产品 PRD v1 | 产品PRD | [项目文档](../../01-业务项目/TokenWisdom/2026-06-27-TokenWisdom-产品PRD-v1.md) / [归档副本](Markdown文件/2026-06-27-TokenWisdom-产品PRD-v1.md) | TokenWisdom,产品PRD,AI分身,Workstation,Agent协作,权限模型 |
| 2026-06-27 | TokenWisdom Workstation v10 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-workstation-v10.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-Workstation-v10.html) | TokenWisdom,Workstation,Workspace,数据分析工作台,普通工作台 |
| 2026-06-27 | TokenWisdom 数据分析工作台 v9 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-data-analysis-workspace-v9.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-数据分析工作台-v9.html) | TokenWisdom,数据分析,工作台,折叠抽屉,数字分身 |
| 2026-06-27 | TokenWisdom 任务工作台 v8 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-mission-workspace-v8.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-任务工作台-v8.html) | TokenWisdom,工作台页面,数字分身,Mission Workspace,工具Agent |
| 2026-06-27 | TokenWisdom ICE全页面 v7 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-ice-full-pages-v7.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-ICE全页面-v7.html) | TokenWisdom,ICE Workbench,全页面设计,数字分身,Mission |
| 2026-06-27 | TokenWisdom AI主任务台 v6 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-ai-workbench-v6.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-AI主任务台-v6.html) | TokenWisdom,AI交互,主任务台,数字分身,任务总结 |
| 2026-06-27 | 飞书消息每日总结（周六） | 工作汇总 | [飞书文档](https://mi.feishu.cn/docx/TDpud8KPdoUQomxjH7kcoUganIf) | 飞书消息,每日总结,周六 |
| 2026-06-27 | 每日工作回顾自动化体系建设 | 工具开发 | [脚本](../../07-定时任务/scripts/daily_work_review.py) / [说明](../../07-定时任务/README.md) | 自动化,定时任务,每日回顾,周总结,工作流 |
| 2026-06-27 | ICE Workbench Agent 改进方案 | 技术方案 | [飞书文档](https://mi.feishu.cn/wiki/QmBwwFLwZiaPXwk0Vzlc23Ognxf) / [本地Markdown](Markdown文件/2026-06-27-ICE-Workbench-Agent改进方案.md) | ICE Workbench,Agent改进,skill元数据,并行执行,失败处理,memory机制,NL→SQL,语义层,evals |
| 2026-06-27 | TokenWisdom 工作台 v5 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-workbench-v5.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-工作台-v5.html) | TokenWisdom,工作台,参考页改进,数字分身,Agent管理 |
| 2026-06-27 | TokenWisdom 参考页改进 v5 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-TokenWisdom-参考页改进-v5.md) / [归档副本](Markdown文件/2026-06-27-TokenWisdom-参考页改进-v5.md) | TokenWisdom,参考页分析,工作台,Agent配置台,Twin Dock |
| 2026-06-27 | TokenWisdom 工作台 v4 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-workbench-v4.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-工作台-v4.html) | TokenWisdom,工作台,数字分身,Twin Manager,任务管理 |
| 2026-06-27 | TokenWisdom 工作台页面层级 v4 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-TokenWisdom-工作台页面层级-v4.md) / [归档副本](Markdown文件/2026-06-27-TokenWisdom-工作台页面层级-v4.md) | TokenWisdom,页面层级,工作台,数字分身管理,首页信息架构 |
| 2026-06-27 | TokenWisdom Agent-to-Agent v3 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-agent-to-agent-v3.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-Agent-to-Agent-v3.html) | TokenWisdom,Agent-to-Agent,Twin Agent,权限确认,HTML原型 |
| 2026-06-27 | TokenWisdom 页面层级 v3 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-TokenWisdom-页面层级-v3.md) / [归档副本](Markdown文件/2026-06-27-TokenWisdom-页面层级-v3.md) | TokenWisdom,页面层级,User to Agent to Agents,Twin Dock,权限结构 |
| 2026-06-27 | 数据产品 26年Q3规划 | OKR规划 | [飞书文档](https://feishu.cn/wiki/C1V2wb2owitM0qkwWakcDgIineg) / [本地Markdown](季度规划复盘/2026-Q3规划.md) | Q3规划,OKR,AI Native,nl-sql,聚焦,平台化 |
| 2026-06-27 | 数据产品 26年Q2复盘 | 季度复盘 | [飞书文档](https://feishu.cn/wiki/LMjdwWoWwiXxH1kOFSKcn8vHn91) / [本地Markdown](季度规划复盘/2026-Q2复盘.md) | Q2复盘,OKR复盘,聚焦原则,ICE工作台,Skill,Agent |
| 2026-06-27 | TokenWisdom 产品页面 v2 HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-tokenwisdom-product-pages-v2.html) / [归档副本](HTML文件/2026-06-27-TokenWisdom-产品页面-v2.html) | TokenWisdom,HTML原型,多页面,产品页面,清晰高效 |
| 2026-06-27 | TokenWisdom 页面层级 v2 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-27-TokenWisdom-页面层级-v2.md) / [归档副本](Markdown文件/2026-06-27-TokenWisdom-页面层级-v2.md) | TokenWisdom,页面层级,IA,主页面,子页面 |
| 2026-06-26 | TokenWisdom Mission Control HTML 原型 | HTML网页 | [项目文档](../../01-业务项目/TokenWisdom/design/2026-06-26-tokenwisdom-mission-control.html) / [归档副本](HTML文件/2026-06-26-TokenWisdom-Mission-Control-原型.html) | TokenWisdom,HTML原型,Twin Mission Control,AI分身,Agent工作台 |
| 2026-06-26 | TokenWisdom × ICE Workbench 整合分析 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/2026-06-26-TokenWisdom-ICE-Workbench整合分析.md) / [归档副本](Markdown文件/2026-06-26-TokenWisdom-ICE-Workbench整合分析.md) | TokenWisdom,ICE Workbench,Agent工作台,Local Runtime,Knowledge Hub |
| 2026-06-26 | 飞书消息整理：团队原则与工作进展 | 工作汇总 | [Markdown文件](Markdown文件/2026-06-26-飞书消息整理-团队原则与工作进展.md) / [飞书链接](https://mi.feishu.cn/docx/EMhZdj3HHoOdupxrO7IcYlhdnYQ) | 团队管理,工作原则,周会TODO,数据问题,浏览器,信息流 |
| 2026-06-26 | TokenWisdom 产品方案讨论记录 | 产品方案 | [项目文档](../../01-业务项目/TokenWisdom/2026-06-26-TokenWisdom-产品方案讨论记录.md) / [归档副本](Markdown文件/2026-06-26-TokenWisdom-产品方案讨论记录.md) | AI分身,Agent工作空间,专业执行Agent,Claude Code,Codex,Cursor |
| 2026-06-26 | 协作关系与AI协作的思考 | HTML网页 | [本地](HTML文件/2026-06-26-AI协作思考.html) / [线上](http://ai.ice.miui.srv/#/方法论/ai/v1-0/ai.html) | AI协作,Prompt模板,方法论,角色陪跑 |
| 2026-06-26 | 协作关系与AI协作的思考 | 飞书文档 | [飞书链接](https://mi.feishu.cn/wiki/UerGwv4UTiGs31kE83NcIu76nfd) | AI协作,Prompt模板,方法论 |
| 2026-06-26 | 工作待办与计划管理 | 工作管理 | Markdown文件/2026-06-26-工作待办与计划管理.md | 待办,工作计划,项目管理,P0/P1,进度跟踪 |
| 2026-06-26 | 龚云荷工作梳理：历史完成项与在研项目 | 工作梳理 | Markdown文件/2026-06-26-龚云荷工作梳理-历史与在研.md | 工作梳理,历史项目,在研项目,ICE,AI Skill,埋点 |
| 2026-06-26 | 数据产品周会纪要 | 飞书文档 | 飞书文档/2026-06-26-数据产品周会纪要-工作梳理.url.md | 周会纪要,工作安排,团队协作 |
| 2026-06-26 | 知识库架构重构方案 | 规则文档 | 本README | 知识库,架构,组织方式 |

# Design Handoff · ICE Data Workbench

把这个目录的内容上传到 [Claude Design](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)（Anthropic Labs 的对话式设计工具），让它按页面逐个产出新视觉，然后再回到本仓库集成。

## 用户路径（按角色 user 的主流程）

```
1. login           ← 起点（当前正在做）
2. introduce       ← 首次登录后的产品介绍
3. dashboard       ← 任务列表 + 入口
4. create_task     ← 新建任务（产品核心入口）
5. workspace       ← 任务工作台（核心：左 chat 右 canvas）
6. scheduled       ← 我的定时任务
7. agent_detail    ← Agent 详情
8. admin/*         ← (super_admin/admin) 后台
```

## 工作流

每一页有自己的 `0X_xxx.md` 简报，固定结构：

1. **当前 IA** — 文字 / ASCII 描述布局与状态机
2. **状态变体** — 每种状态对应的内容与触发条件
3. **现有组件** — 仓库里相关的源码链接
4. **改造目标** — 想要什么、不想要什么
5. **不变量** — 不能破坏的 API 调用、键盘行为、可访问性
6. **Prompt 模板** — 可直接粘到 Claude Design 的项目说明里

## 推荐上传顺序（每页独立项目）

每次新建一个 Claude Design 项目时，建议按以下顺序粘贴：

1. `00_brand_pack.md`（共用，所有项目都先粘这个）
2. 当前页的 `0X_xxx.md`
3. （可选）`screenshots/0X_xxx-*.png` 当前页 4 个状态的截图作为参考

## 集成回流

Claude Design 输出后：

- 它给的导出包（ZIP/HTML/PPTX）— 留作设计参考
- 视觉决策（颜色/排版/组件结构调整）— 写回 `frontend/src/styles/tokens.css` 与对应页面的 CSS
- 不要导入它生成的任意第三方组件库；本仓库 vendor chunking 只保留 React core 单独切，其它都打到一个 vendor chunk（详见 `vite.config.ts` 注释），引入新的样式系统会破坏这个约束

## 约束（所有页面共用）

- 双主题（dark 默认 / light）必须都给出方案
- 桌面 ≥1024px + 移动 ≤768px 都要适配（详见各页简报）
- 不得破坏后端 API 路径与字段；如需新接口在简报里显式标注
- 重设计默认只动 `tokens.css` / `global.css` / 字体；移动端适配是例外（可重写布局）

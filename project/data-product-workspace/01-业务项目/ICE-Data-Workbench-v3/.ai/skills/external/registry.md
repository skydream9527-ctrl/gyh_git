# 外部 Skill 注册表

本目录下的 Skill 均为外部下载复制，不参与内部 Skill 的 DAG / I/O 契约体系。

---

## text2html2png

- **路径**：`.ai/skills/external/text2html2png/`
- **触发条件**：需要做可视化图表 / 材料
- **调用方式**：加载 SKILL.md → 选风格 → AI 生成 HTML → CLI 截图
- **输出位置**：`.ai/outputs/viz/`
- **依赖**：Chrome + Node.js（`npm install` 后可用）
- **状态**：骨架版（不含完整模板和 node_modules，按需安装）

---

## feishu-pyramid-writer

- **路径**：`.ai/skills/external/feishu-pyramid-writer/`
- **触发条件**：需要结构化写作（金字塔原理）
- **调用方式**：加载 SKILL.md → 三阶段交互（收集信息 → 构建骨架 → 生成内容）
- **输出位置**：飞书文档
- **依赖**：无
- **状态**：已安装
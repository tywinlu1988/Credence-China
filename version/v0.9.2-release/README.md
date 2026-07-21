# Credence — 固收信贷智能分析引擎（v0.9.2-release）

方法论优先的中国固定收益信用分析引擎：行业多层金字塔 + 双轨交叉验证 + 马赛克公开数据引擎 +
多利益相关者视角 + 系统智能层（传染/集中度/SRI）。以 **Agent Skills**（`SKILL.md`）形式分发，
可在 Claude Code / Codex / Cursor / Gemini / OpenCode 中安装使用。

## 快速开始
见 **`INSTALL.md`**（推荐 Model A：把本包根当项目打开，零配置）。入口为 **`AGENTS.md`**。

## 包内容
- `.claude/skills/` — 四段链技能（intake 路由 → analysis 分析 → report 报告 → qa 质检）
- `engine/` — 28 份方法论文档（阈值/权重/评级映射的单一事实源）
- `templates/` — Type 1–15 报告模板
- `src/` — 可执行编排器与 2 个编码引擎（SRI、五维集中度）
- `adapters/` — 按工具的深度适配说明

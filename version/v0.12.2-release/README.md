# Credence — 固收信贷智能分析引擎（v0.12.2-release）

方法论优先的中国固定收益信用分析引擎：四段链 pipeline（intake → analysis → report → qa），
`path_id` 贯穿各段；行业多层金字塔 + 双轨交叉验证 + 马赛克公开数据引擎 +
多利益相关者视角 + 系统智能层（传染/集中度/SRI）。以 **Agent Skills** 形式分发，
可在 Claude Code / Codex / Cursor / Gemini / OpenCode 中安装使用。

## 快速开始
见 **`INSTALL.md`**（推荐 Model A：把本包根当项目打开，零配置）。入口为 **`AGENTS.md`**。

## 包内容
- `.claude/skills/` — 四段链技能：
  - `credit-analysis-router` — 模糊/复合需求四问路由到工作路径
  - `fixed-income-credit-analysis` — 按路径单或核心文档集执行分析
  - `credit-report-builder` — 装配交付报告（选模板、映射 L0/L1/L2）
  - `credit-qa-verifier` — 四段链终态质检（质量门 + 强制检查）
- `engine/` — 29 份方法论文档（阈值/权重/评级映射的单一事实源）
- `templates/` — Type 1–19，共 16 份 报告模板
- `src/` — 可执行编排器与 8 个编码引擎（composite_scorer 旗舰聚合、lgd_scorer LGD 评估、external_support_scorer 外部支持评估、concentration_scorer 五维集中度、contagion_engine 传染矩阵、sri_calculator SRI、stress_scorer 组合压力测试、outlook_engine 展望监控）
- `adapters/` — 按工具的深度适配说明

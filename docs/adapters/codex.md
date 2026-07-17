# Codex 深度适配 — Credence

**引擎版本**：v0.8.3-release · **入口**：仓库根级 `AGENTS.md`

Codex 原生读取仓库根级的 `AGENTS.md`，但**不会自动发现** `dev/.claude/skills/`。因此 Codex 的接入姿势是：先读 `AGENTS.md` 定位当前任务对应的 skill，再**手动读那份 `SKILL.md` 正文**，然后按正文执行。阈值、权重、评级映射的单一事实源仍是 `dev/engine/*.md`，本文件不复制任何数值。

## 1. 接入顺序

1. 读根级 `AGENTS.md`，在「Skill 索引」中定位当前任务对应的 skill。
2. 手动打开该 skill 的 `SKILL.md` 正文——Codex 不会自动加载 `dev/.claude/skills` 下的技能。
3. 按 `SKILL.md` 正文执行；涉及数值判断时引用 `dev/engine/<doc>.md §节`，文档未定义就输出 `引擎未定义`。

## 2. 四问接入协议（intake）

模糊或复合需求先走 `credit-analysis-router` 的四问协议，逐问澄清，允许跳答、多答、一次性说全：

- **Q1 角色**：M0 审贷 / M1 投资 / M2 承销 / M3 交易 / M4 风控 / M5 融资 / 不确定。
- **Q2 对象**：单发行人 / 债券组合 / 行业 / 全市场 / 方法论建设或引擎验证。
- **Q3 深度**：L0 快速信号 / L1 决策快照 / L2 深度报告 / 专项报告。
- **Q4 数据**：仅公开数据（Mode A）/ 用户显式提供外部数据源（CSV/API/MCP → Mode B）。

不确定默认策略：信息不足从 L0/L1 起步，不直接跳到 L2；对象不明先按单发行人处理；角色不明给出候选路径请用户选择，不擅自定路径。协议细节以 `dev/.claude/skills/credit-analysis-router/SKILL.md` 为单一事实源。用户已点明具体任务或引擎路径时，跳过四问，直接进 `fixed-income-credit-analysis`。

## 3. 路径单交接（router → fixed-income）

四问收敛后，router 产出《工作路径单》，其 `path_id` 必须存在于 `dev/engine/work-path-registry.md`。Codex 按以下顺序完成 router → fixed-income 的交接：

1. 读 router 产出的路径单，取其 `engine_reading_order` 与 `quality_gates`。
2. 切到 `fixed-income-credit-analysis` skill，按 `engine_reading_order` 顺序阅读引擎文档并执行。
3. 质量门按 `quality_gates` 逐条校验；每条格式为 `规则名 (dev/engine/<doc>.md §节)`。

`dev/engine/work-path-registry.md`（16 条工作路径，8 条 active）是路由基线：推荐到 🔴 planned 路径时必须如实告知"待开发"，并给出可替代的 active 路径，不得伪造能力。

## 4. 运行两道校验器

改动后两道门必须保持绿：

```
python -m pytest tests/ -q
python scripts/consistency_check.py
```

- `pytest` 跑测试套件（skill 结构、路径单、引擎一致性等）。
- `consistency_check.py` 跑回归一致性（链接、版本、评级映射、路径单、跨 CLI 入口等）。既有的 RATING_MAP 警告为已知基线，不得新增。

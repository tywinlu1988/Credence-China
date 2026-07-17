# AGENTS.md — Credence 跨 CLI 通用入口

**项目**：Credence（固收信贷智能分析引擎）
**引擎版本**：v0.8.4-release
**一句话**：方法论优先（methodology-first）的信用分析引擎；可移植单元是 `SKILL.md`。

> 任何 agent CLI 都从这里开始：先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。

## 这个仓库是什么

面向中国固定收益市场的信用分析引擎，分四层（four-layer）：

1. **马赛克引擎（Mosaic）** — 把碎片化公开数据拼成连贯信号；数据缺口本身即风险信号。
2. **双轨引擎（Dual-Track）** — 行业多层金字塔（基本面）与市场定价信号并行，再交叉对撞。
3. **多利益相关者（Multi-Stakeholder）** — M0 审贷 / M1 投资 / M2 承销 / M3 交易 / M4 风控 / M5 融资多视角。
4. **系统智能层（System-Intelligence, SRI）** — 跨行业传染、五维集中度、系统性风险指数（SRI）。

**阈值、权重、评级映射只存放在 `dev/engine/*.md`。** 本文件与任何 skill 都不复制这些数值；凡涉及数值判断，一律引用引擎文档 + 章节。

## 如何在你的 agent CLI 中使用

skills 实体存放在 `dev/.claude/skills/`。不同 CLI 的发现机制不同，接入姿势也不同：

| agent CLI | 如何接入 |
|---|---|
| **Claude Code** | 自动发现 `dev/.claude/skills/`（在 `dev/` 下工作时即被加载），无需手动配置。 |
| **Codex** | 原生读本 `AGENTS.md`；随后手动读当前任务的 `SKILL.md` 正文（Codex 不会自动发现 `dev/.claude/skills`）。深度适配见 `docs/adapters/codex.md`。 |
| **Cursor** | 读本 `AGENTS.md`，再手动加载当前任务的 `SKILL.md` 正文。 |
| **Gemini** | 读本 `AGENTS.md`，再手动加载当前任务的 `SKILL.md` 正文。 |
| **OpenCode** | 读本 `AGENTS.md`，再手动加载当前任务的 `SKILL.md` 正文。 |

统一姿势：**先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。**

## Skill 索引

| Skill | 何时使用（Use when…） | 路径 |
|---|---|---|
| `credit-analysis-router` | 需求模糊或复合（"帮我看看这家公司""该做哪种分析""该从哪儿入手"），需先四问路由到工作路径 | `dev/.claude/skills/credit-analysis-router/SKILL.md` |
| `fixed-income-credit-analysis` | 已点名的具体方法论任务或引擎路径，按路径单或核心文档集执行分析 | `dev/.claude/skills/fixed-income-credit-analysis/SKILL.md` |
| `credit-report-builder` | 把完成的信用分析装配为交付报告（选模板 Type 1–15、映射 L0/L1/L2 层、装配仪表盘）；需上游分析产物，自身不做分析 | `dev/.claude/skills/credit-report-builder/SKILL.md` |
| `credit-qa-verifier` | 交付前复核报告/分析（质量门、密度规则、一票否决上限、Mode B 护栏、单源合规）；四段链终态质检 | `dev/.claude/skills/credit-qa-verifier/SKILL.md` |

> 四段管线对应四份 skill 已全部交付（见下「四段管线」）。

## 四段管线

引擎把一次信用分析拆成四段链式契约，`path_id` 是贯穿各段的 join key：

| 阶段 | 职责 | 承载 skill | 状态 |
|---|---|---|---|
| ① intake | 四问路由，产出《工作路径单》 | `credit-analysis-router` | ✅ 已交付 |
| ② analysis | 按路径单 `engine_reading_order` 执行分析 | `fixed-income-credit-analysis` | ✅ 已交付 |
| ③ report | 把完成的分析装配为交付报告 | `credit-report-builder` | ✅ 已交付 |
| ④ qa | 交付前质量门复核 | `credit-qa-verifier` | ✅ 已交付 |

四段产物（工作路径单 / 分析产物 / 交付单 / 质检裁决）的字段形状与链式边的单一事实源为 `dev/engine/pipeline-contract.md`。

**可执行编排器（v0.7.8）**：`src/pipeline.py` 现以代码驱动上述四段链。它从 `pipeline-contract.md` 读取阶段定义（不硬编码阶段名/边），复用 `src/path_sheet.py` 校验路径单，并仅对已接线路径调用编码引擎——**WP-M4-03 → SRI（`src/sri_calculator.py`）、WP-M4-01 → 五维集中度（`src/concentration_scorer.py`）**；其余路径/阶段仍由 LLM 按引擎文档编排。引擎文档为规范源，scorer 为其可执行实现，二者由 `tests/test_engine_doc_parity.py` 对账。

## 单一事实源规则

**绝不复制阈值、权重、SRI 档位、评级映射或分层时间预算。** 任何数值判断都引用 `dev/engine/<doc>.md §节`；引擎文档未定义就输出 `引擎未定义`，不得编造数值。

## 路由基线（工作路径注册表）

`dev/engine/work-path-registry.md` 是路由单一事实源：**16 条工作路径（8 条 active / 6 条 partial / 2 条 planned）**。router 据此把模糊需求路由到具体工作路径；推荐到 planned 路径时须如实告知"待开发"并给出可替代的 active 路径。

## 验证命令

改动后两道门必须保持绿：

```
python -m pytest tests/ -q
python scripts/consistency_check.py
```

## 平台中立说明

本文件与各 skill 统一称"你的 instructions file"——每个 agent CLI 的项目级指令文件名各不相同，本仓库不假定任何特定产品文件名。引用字面路径 `dev/.claude/skills` 是允许的：那是一个路径，不是一条行为指令。

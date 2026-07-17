# AGENTS.md — Credence 跨 CLI 通用入口

**项目**：Credence（固收信贷智能分析引擎）
**引擎版本**：v0.8.3-release
**一句话**：方法论优先（methodology-first）的信用分析引擎；可移植单元是 `SKILL.md`。

> 任何 agent CLI 都从这里开始：先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。
> 安装与按工具接入详见 `INSTALL.md`。

## 这个包是什么

面向中国固定收益市场的信用分析引擎，分四层（four-layer）：

1. **马赛克引擎（Mosaic）** — 把碎片化公开数据拼成连贯信号；数据缺口本身即风险信号。
2. **双轨引擎（Dual-Track）** — 行业多层金字塔（基本面）与市场定价信号并行，再交叉对撞。
3. **多利益相关者（Multi-Stakeholder）** — M0 审贷 / M1 投资 / M2 承销 / M3 交易 / M4 风控 / M5 融资多视角。
4. **系统智能层（System-Intelligence, SRI）** — 跨行业传染、五维集中度、系统性风险指数（SRI）。

**阈值、权重、评级映射只存放在 `engine/*.md`。** 本文件与任何 skill 都不复制这些数值；凡涉及数值判断，一律引用引擎文档 + 章节。

## 如何在你的 agent CLI 中使用

本包是自包含的可安装 agent 包，skills 实体在 `.claude/skills/`。**最简单的方式（Model A）**：把本包根目录作为你的项目打开即可，全部引用自动解析。

| agent CLI | 如何接入 |
|---|---|
| **Claude Code** | 自动发现 `.claude/skills/`（把本包根当项目打开）；`CLAUDE.md` 指向本文件。惯例分发渠道为 plugin/marketplace（见 `.claude-plugin/plugin.json`）。 |
| **Codex** | 原生读本 `AGENTS.md`；随后手动读当前任务的 `SKILL.md` 正文。深度适配见 `adapters/codex.md`。 |
| **Cursor** | 读本 `AGENTS.md`，并兼容读取 `.claude/skills/`。 |
| **Gemini** | 读 `GEMINI.md`，并兼容读取 `.claude/skills/`。 |
| **OpenCode** | 读本 `AGENTS.md`，并兼容读取 `.claude/skills/`。 |

统一姿势：**先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。** 把本包整合进你已有的项目（Model B）或做全局安装的目标路径，见 `INSTALL.md`。

## Skill 索引

| Skill | 何时使用（Use when…） | 路径 |
|---|---|---|
| `credit-analysis-router` | 需求模糊或复合（"帮我看看这家公司""该做哪种分析""该从哪儿入手"），需先四问路由到工作路径 | `.claude/skills/credit-analysis-router/SKILL.md` |
| `fixed-income-credit-analysis` | 已点名的具体方法论任务或引擎路径，按路径单或核心文档集执行分析 | `.claude/skills/fixed-income-credit-analysis/SKILL.md` |
| `credit-report-builder` | 把完成的信用分析装配为交付报告（选模板 Type 1–15、映射 L0/L1/L2 层、装配仪表盘）；需上游分析产物，自身不做分析 | `.claude/skills/credit-report-builder/SKILL.md` |
| `credit-qa-verifier` | 交付前复核报告/分析（质量门、密度规则、一票否决上限、Mode B 护栏、单源合规）；四段链终态质检 | `.claude/skills/credit-qa-verifier/SKILL.md` |

## 四段管线

引擎把一次信用分析拆成四段链式契约，`path_id` 是贯穿各段的 join key：

| 阶段 | 职责 | 承载 skill |
|---|---|---|
| ① intake | 四问路由，产出《工作路径单》 | `credit-analysis-router` |
| ② analysis | 按路径单 `engine_reading_order` 执行分析 | `fixed-income-credit-analysis` |
| ③ report | 把完成的分析装配为交付报告 | `credit-report-builder` |
| ④ qa | 交付前质量门复核 | `credit-qa-verifier` |

四段产物（工作路径单 / 分析产物 / 交付单 / 质检裁决）的字段形状与链式边的单一事实源为 `engine/pipeline-contract.md`。

**可执行编排器**：`src/pipeline.py` 以代码驱动四段链，从 `pipeline-contract.md` 读阶段定义，仅对已接线路径调用编码引擎——**WP-M4-03 → SRI（`src/sri_calculator.py`）、WP-M4-01 → 五维集中度（`src/concentration_scorer.py`）**；其余路径仍由 LLM 按引擎文档编排。

## 单一事实源规则

**绝不复制阈值、权重、SRI 档位、评级映射或分层时间预算。** 任何数值判断都引用 `engine/<doc>.md §节`；引擎文档未定义就输出 `引擎未定义`，不得编造数值。

## 路由基线（工作路径注册表）

`engine/work-path-registry.md` 是路由单一事实源：**16 条工作路径（8 条 active / 6 条 partial / 2 条 planned）**。router 据此把模糊需求路由到具体工作路径；推荐到 planned 路径时须如实告知"待开发"并给出可替代的 active 路径。

## 平台中立说明

本文件与各 skill 统一称"你的 instructions file"——每个 agent CLI 的项目级指令文件名各不相同，本包不假定任何特定产品文件名。引用字面路径 `.claude/skills` 是允许的：那是一个路径，不是一条行为指令。

## 开发者回归门（需完整源码仓库）

本安装包是**运行时产物**，不含测试与一致性校验脚本。若要运行回归门（`pytest` + `consistency_check.py`）或修改方法论本身，请克隆完整源码仓库。

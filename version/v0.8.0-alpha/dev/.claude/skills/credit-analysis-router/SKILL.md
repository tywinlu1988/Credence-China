---
name: credit-analysis-router
description: Intake router for vague or compound Chinese fixed-income credit-analysis requests such as '帮我看看这家公司', '这个组合有没有问题', '该做哪种分析', '该从哪儿入手'. Use when the need is ambiguous, spans multiple roles (lending/investment/underwriting/trading/risk/financing), or the user asks which analysis to run or where to start. If the user already names a concrete methodology task or engine path, use the fixed-income-credit-analysis skill instead.
---

## Purpose

**对应引擎版本**: v0.8.0-alpha

路由层，不做分析。职责仅三步：理解模糊/复合型需求 → 在 `work-path-registry` 中匹配工作路径 → 输出结构化《工作路径单》。本 skill 不复制任何引擎阈值/权重/评级映射；规则正文以引擎文档为单一事实源。路由完成后移交 `fixed-income-credit-analysis` skill，按路径单的 `engine_reading_order` 执行。

## Intake Protocol（四问，渐进式）

逐问澄清，允许跳答、多答、一次性说全。用户已给足信息则跳过对应问题，不机械追问。

- **Q1 角色**：您以什么身份决策？M0 审贷 / M1 投资 / M2 承销 / M3 交易 / M4 风控 / M5 融资 / 不确定（按问题特征推断后向用户确认）。
- **Q2 对象**：分析对象是什么？单发行人 / 债券组合 / 行业 / 全市场 / 方法论建设或引擎验证。
- **Q3 深度**：需要多深的产出？L0 快速信号 / L1 决策快照 / L2 深度报告 / 专项报告。
- **Q4 数据**：用什么数据？仅公开数据（Mode A）/ 用户显式提供外部数据源（CSV/API/MCP → Mode B）。

**不确定默认策略**：
- 信息不足 → 从 L0/L1 起步，不直接跳到 L2。
- 对象不明 → 先按单发行人处理。
- 角色不明 → 给出 2 条候选路径请用户选择，不擅自定路径。

## Routing Table

按用户表述匹配推荐路径。`状态` 列：✅ active / 🟡 partial / 🔴 planned（待开发，须如实告知）。模糊需求不直接给路径，先走四问协议。

| 场景 | 用户表述样例 | 推荐路径 | 状态 | 备选 |
|---|---|---|---|---|
| 审贷单标的 | "银行客户经理问能不能给 X 放贷" | WP-M0-01 | ✅ | WP-X-02 |
| 审贷专项 | "这笔债的 LGD、回收率、外部支持怎么看" | WP-M0-02 | 🟡 | WP-M0-01 |
| 债券估值 | "这只券便不便宜、值不值得买" | WP-M1-01 | ✅ | WP-M1-02 |
| 双标的对比 | "隆基和一道买哪只" | WP-M1-02 | 🟡 | WP-X-02 |
| 承销咨询 | "这单债能不能承销、窗口在哪" | WP-M2-01 | 🔴 | WP-M1-01 |
| 盯市信号 | "给我一张今日盯市信号卡" | WP-M3-01 | 🟡 | WP-M4-03 |
| 组合集中度 | "组合里光伏占比太高，集中度如何" | WP-M4-01 | ✅ | WP-M4-04 |
| 传染排查 | "某行业爆雷会传染到哪些持仓" | WP-M4-02 | ✅ | WP-M4-01 |
| SRI 读数 | "现在系统性风险到哪个档位了" | WP-M4-03 | ✅ | WP-M3-01 |
| 压力测试 | "极端情景下组合会亏多少" | WP-M4-04 | 🟡 | WP-M4-01 |
| 融资顾问 | "企业该发债还是贷款、什么时候融" | WP-M5-01 | 🔴 | WP-M0-01 |
| 回溯验证 | "这套框架在历史上准不准" | WP-X-01 | ✅ | WP-X-02 |
| 多身份并行 | "从审贷/投资/风控多角度同时看 X" | WP-X-02 | ✅ | WP-M0-01 |
| 行业框架建设 | "帮我搭一个新行业的分析框架" | WP-X-03 | ✅ | WP-M0-01 |
| ESG 扫描 | "查一下这家公司的治理和 ESG 风险" | WP-X-04 | 🟡 | WP-M0-01 |
| 展望监控 | "给 X 一个评级展望并持续盯" | WP-X-05 | 🟡 | WP-M0-01 |
| 模糊需求 | "帮我看看这家公司""该做哪种分析" | 四问协议 | — | — |

## Path Sheet Output（《工作路径单》）

四问收敛后输出如下 yaml。字段对齐 registry schema；`path_id` 必须存在于注册表；`engine_reading_order` 为该路径注册的引擎文档序列。

模板：

```yaml
role: ""                    # M0|M1|M2|M3|M4|M5|meta
object: ""                  # single-issuer|portfolio|industry|market|meta
depth: ""                   # L0|L1|L2|专项
mode: ""                    # A=仅公开数据 / B=用户显式提供外部数据源
path_id: ""                 # 注册表中已存在的工作路径 ID
engine_reading_order: []    # 该路径注册的引擎文档序列（单一事实源）
quality_gates: []           # "规则名 (dev/engine/<doc>.md §节)"
notes: ""
```

示例（审贷单标的、仅公开数据、L2 深度报告）：

```yaml
role: M0
object: single-issuer
depth: L2
mode: A
path_id: WP-M0-01
engine_reading_order:
  - dev/engine/industry-framework.md
  - dev/engine/mosaic-engine.md
  - dev/engine/dual-track-methodology.md
quality_gates:
  - "信号密度 (dev/engine/mosaic-engine.md §4.3)"
  - "一票否决 (dev/engine/industry-framework.md §五)"
  - "交叉对撞 (dev/engine/dual-track-methodology.md §四)"
notes: "信息不足时降级为 L1 决策快照并附数据缺口清单"
```

## Guardrails

- **不复制引擎内容**：本 skill 只引用路径 ID 与文档名/章节，不复制任何阈值、权重、评级映射。规则正文一律以 `engine_reading_order` 指向的引擎文档为准。
- **Mode B 护栏**：用户未显式提供数据源（CSV/API/MCP）时，`mode` 不得置为 B；所有 Mode B 字段视为数据缺口，不得编造外部数据值。
- **planned 路径如实告知**：推荐到 🔴 planned 路径（如 WP-M2-01、WP-M5-01）时，必须明示"该路径待开发"，并给出可替代的 active 路径，不得伪造能力。
- **路由即移交**：路径单产出后，切换到 `fixed-income-credit-analysis` skill，按 `engine_reading_order` 顺序阅读引擎文档并执行，质量门按 `quality_gates` 校验。（自 v0.7.4 起执行 skill 已按路径单驱动阅读；无路径单时回退到核心集 `engine-overview.md` + `dual-track-methodology.md` + 请求点名的专题文档。）

## Chaining（链式交接）

- **下游（REQUIRED NEXT SUB-SKILL）**：`fixed-income-credit-analysis` —— 《工作路径单》产出后即移交该 skill 执行分析；四段链产物契约见 `dev/engine/pipeline-contract.md`。

## References

- `references/work-paths.md` — 工作路径路由视图（精简表，标注状态与一句话触发特征）
- `dev/engine/work-path-registry.md` — 工作路径注册表（单一事实源）

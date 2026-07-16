---
name: fixed-income-credit-analysis
description: Use when analyzing industries or companies for credit decisions in Chinese fixed income markets, building industry analysis frameworks for lending or bond investment, evaluating credit quality via dual-track methodology, constructing investment dashboards from public data, validating frameworks against historical defaults, or assessing cross-industry contagion, portfolio concentration, and systemic risk via the system-intelligence layer. Route vague needs to the credit-analysis-router skill.
---

## Invocation Protocol

When this Skill is invoked:

1. **Path-sheet-driven (preferred).** If the user message carries a 《工作路径单》 (work-path sheet) produced by the `credit-analysis-router` skill, read the engine documents in the sheet's `engine_reading_order` order and validate against its `quality_gates`.
2. **Direct task, no path sheet.** If the user directly names a concrete task, read the core set — `dev/engine/engine-overview.md` + `dev/engine/dual-track-methodology.md` — plus any topic-specific doc the request names (e.g. `contagion-matrix.md`, `concentration-framework.md`, `lgfv-framework.md`).
3. **Vague / unrouted need.** If the need is ambiguous and no path sheet exists, first route through the `credit-analysis-router` skill, or ask the Q1–Q4 questions (role / object / depth / data) yourself to pick a path from `dev/engine/work-path-registry.md`.
4. Use **only** thresholds, weights, rating mappings, and veto rules found in those documents.
5. For every quantitative judgment, cite the source document and section.
6. If a required threshold, weight, or mapping is missing from the engine documents, output `引擎未定义` and do not invent a value.
7. Do not invoke Mode B or generate external-data values unless the user has explicitly provided a CSV upload, API endpoint, or MCP server. Treat Mode B fields as data gaps until then.

# Fixed Income Credit Analysis Engine v0.8.0-release

## Overview

A systematic methodology for evaluating corporate credit quality in China's fixed income markets. The engine operates in three layers: (1) a **Mosaic Engine** that assembles fragmented public data into coherent signals; (2) a **Dual-Track Engine** combining industry-specific multi-layer analysis pyramids with market-based pricing signals; and (3) a **System-Intelligence Layer** (v0.7.0-alpha) that models cross-industry contagion, portfolio concentration, and a market-wide Systemic Risk Index (SRI). Combines multi-stakeholder perspectives into a unified assessment framework.

**Core principles:**
1. Traditional financial analysis systematically fails in policy-driven, technology-barrier, and asset-lease industries. The heaviest credit factor is rarely on the balance sheet.
2. External credit ratings consistently lag true credit deterioration by 17+ months.
3. **Mosaic theory:** Individual public data fragments are meaningless alone; assembled together they form coherent signals.
4. **Information completeness theory:** Data gaps are not defects — they are risk signals. "We don't have this data" itself tells the user something meaningful.

## When to Use

- Building an industry credit analysis framework from scratch
- Evaluating a specific company for lending or bond investment decisions
- Constructing a multi-dimensional investment dashboard (relative value + terms protection + liquidity + event calendar)
- Assembling fragmented public data into a coherent credit assessment using mosaic theory
- Retroactively validating analytical frameworks against historical defaults
- Evaluating LGFV (城投债) credit quality through the LGFV framework → read `dev/engine/lgfv-framework.md`
- Conducting ESG/governance risk scans and fraud detection → read `dev/engine/esg-framework.md` and `dev/engine/governance-fraud-risk.md`
- Performing LGD/recovery rate analysis for default scenarios → read `dev/engine/lgd-recovery-framework.md`
- Assessing external support (government, parent company) impact on creditworthiness → read `dev/engine/external-support-framework.md`
- Evaluating financial bonds → read `dev/engine/financial-bond-framework.md`
- Analyzing holding companies → read `dev/engine/holding-company-framework.md`
- Assessing cross-industry contagion risk from a stressed issuer or sector
- Evaluating portfolio concentration across industry, region, rating, tenor, and funding-channel dimensions
- Computing the Systemic Risk Index (SRI) and interpreting the four-level thermometer
- Mapping an industry to one of the six analytical paradigms (policy-driven, tech-barrier, consolidation, asset-lease, brand-channel, network-traffic)

## Mandatory Density Rules (mandatory)

- Critical dimension signal density **<20%** → MUST NOT output a numeric score for that dimension; state `信息不足无法评估` and list the missing signals.
- Weighted-average density across scored dimensions **<50%** → MUST NOT output a final letter rating; output a qualitative directional assessment plus a prioritized gap list.
- Density 50–80% → MAY rate but MUST label `中置信度` and widen the implied interval by ±1 notch.
- The completeness report is mandatory for every analysis; omitting it is a protocol violation.

Full confidence/density model and gap-to-risk mapping: `references/mosaic-engine-architecture.md` (threshold single source: `dev/engine/mosaic-engine.md`).

## Mode B: External Data Source Adapter (Placeholder)

> **Mode B 护栏**：除非用户明确提供了 CSV 上传、API endpoint 或 MCP server，否则禁止调用 Mode B 接口，禁止生成外部数据值。在 Mode B 未激活时，所有 Mode B 字段应作为数据缺口处理。

Defined but not implemented. Adapter contract (`query_bond_analytics` / `query_market_data` / `query_industry_benchmark`) and connection priority (CSV > REST API > MCP > DB): `dev/engine/mosaic-engine.md`.

## 一票否决与评级上限 (Veto & Rating Ceiling — mandatory)

- **一票否决（one-shot veto）**：任一分析层触发一票否决条件时，该发行人评级**上限锁定为 CCC**，不得上调。每层否决条件见 `dev/engine/industry-framework.md` §五。
- 评级映射一律采用官方 12 档表（`dev/engine/dual-track-methodology.md` §六）；不得自造档位。
- 城投类标的：政府信用定上限、平台自身定下限、支持意愿定落点（`dev/engine/lgfv-framework.md` §五）。

## Two-Track Parallel Structure (Core)

Track A (fundamental, qualitative+scoring, L1 heaviest → L4 lightest) and Track B (market pricing: credit spreads / volatility / fund flows / rating migration) run in parallel, then feed a Cross-Comparison Matrix. Consensus reinforces; divergence is the most valuable insight.

**When tracks diverge, prioritize Track A (auditable financial facts) over Track B (external ratings).**

Full pyramid weights, Track-B thresholds, and the cross-comparison matrix: `references/industry-scoring.md` and `dev/engine/dual-track-methodology.md`.

## System-Intelligence Layer (v0.7.0-alpha)

Aggregates issuer assessments into portfolio/market signals: cross-industry contagion (13×13 matrix), five-dimensional concentration, and the Systemic Risk Index `SRI = Σ(industry_risk_score × industry_weight_pct)` (scale 0–3+).

SRI thermometer: 🟢 normal (<0.5), 🟡 watch (0.5–1.0), 🟠 alert (1.0–1.8), 🔴 danger (≥1.8).

Full specification: `references/system-intelligence.md` and `dev/engine/systemic-warning-framework.md`.

## Key Design Principles

1. Financial analysis is NEVER the heaviest layer. The heaviest factor is structural/external.
2. Each industry has a different heaviest factor determined by 10-dimension scoring.
3. Don't jump layers. L1 must pass before L2 is meaningful.
4. L4 validates, never overrules. Poor financials with strong upper layers = may be investing through cycle. Strong financials with weak upper layers = MORE dangerous (peak cycle or fraud).
5. Public data is sufficient across the 13 covered industries.
6. Track B is independent, not subordinate. Divergence generates the most valuable questions.
7. When tracks clash, prioritize auditable financial facts over external ratings.
8. Data gaps are not defects — they are risk signals. Every analysis includes a completeness report.
9. The framework identifies structural unsustainability but cannot predict default timing or specific triggers.

## Chaining（链式交接）

- **上游**：`credit-analysis-router` —— 消费其《工作路径单》（见 Invocation Protocol）。
- **产出**：分析完成后输出《分析产物》（Analysis Artifact，schema 见 `dev/engine/pipeline-contract.md` §2.2），`path_id` 承自路径单。
- **下游（REQUIRED NEXT SUB-SKILL）**：`credit-report-builder` —— 把《分析产物》移交该 skill 装配为交付报告；本 skill 不做报告装配。

## References

详情已下沉至 `references/`（单一事实源仍为 `dev/engine/` 各引擎文档）：

- `references/mosaic-engine-architecture.md` — 马赛克引擎 Mode A：信号置信度 / 密度评估 / Gap 映射 / 完备性输出
- `references/industry-scoring.md` — Track A 行业金字塔 · 六范式+LGFV · D1-D10 · C1-C4
- `references/system-intelligence.md` — 跨行业传染 · 五维集中度 · SRI 温度计
- `references/stakeholder-paths.md` — M0-M5 多视角 · M1 仪表盘 · 路径单消费指引
- `dev/.claude/skills/credit-analysis-router/SKILL.md` — 需求理解 / 路由层，产出《工作路径单》
- `dev/engine/work-path-registry.md` — 工作路径注册表（路径单一事实源）

## Version History

| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2026-07-07 | Initial release. 10-dim scoring, 4-layer pyramid, dual-track, 7 industries, solar forward-validated |
| 0.3.0 | 2026-07-08 | Mosaic engine architecture (Mode A+B). Multi-stakeholder coverage map. P0 bond investment dashboard. Signal confidence + density metrics. Completeness reporting. Mode B adapter interface (placeholder). |
| 0.4.0-alpha | 2026-07-08 | LGD/recovery, external support, outlook/monitoring, LGFV（城投债）, ESG + governance/fraud, non-credit overlay, financial bond, holding company frameworks. Layered output. Multi-stakeholder coverage completed. |
| 0.7.0-alpha | 2026-07-13 | System-intelligence layer: contagion theory/matrix, five-dimensional concentration, systemic warning (SRI), 13-industry coverage, six analytical paradigms. |
| 0.7.1-release | 2026-07-15 | Dev-stack reorganization finalized; validation artifacts separated (root validation/, never in snapshots). Version headers promoted. |
| 0.7.4 | 2026-07-15 | SKILL.md slimmed to a navigator (≤150 lines); detail sunk to `references/` (mosaic / industry / system-intelligence / stakeholder). Invocation Protocol is now path-sheet-driven (`engine_reading_order`). LGV→LGFV naming unified. |

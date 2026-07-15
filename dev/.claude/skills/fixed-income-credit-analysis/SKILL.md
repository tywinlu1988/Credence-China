---
name: fixed-income-credit-analysis
description: Use when analyzing industries or companies for credit decisions in Chinese fixed income markets, building industry-specific analysis frameworks for bank lending or bond investment, evaluating corporate credit quality through a systematic dual-track methodology, constructing multi-dimensional investment dashboards from fragmented public data, or retroactively validating analytical frameworks against historical default events, evaluating cross-industry contagion and portfolio concentration risk through the v0.7.0-alpha system-intelligence layer
---

## Invocation Protocol

When this Skill is invoked:

1. Read the canonical engine documents in this order:
   - `dev/engine/engine-overview.md`
   - `dev/engine/industry-framework.md`
   - `dev/engine/dual-track-methodology.md`
   - `dev/engine/mosaic-engine.md`
   - plus any topic-specific doc named in the user request (e.g., `contagion-matrix.md`, `concentration-framework.md`, `systemic-warning-framework.md`).
2. Use **only** thresholds, weights, rating mappings, and veto rules found in those documents.
3. For every quantitative judgment, cite the source document and section.
4. If a required threshold, weight, or mapping is missing from the engine documents, output `引擎未定义` and do not invent a value.
5. Do not invoke Mode B or generate external-data values unless the user has explicitly provided a CSV upload, API endpoint, or MCP server. Treat Mode B fields as data gaps until then.

# Fixed Income Credit Analysis Engine v0.7.0-alpha

## Overview

A systematic methodology for evaluating corporate credit quality in China's fixed income markets. The engine operates in three layers: (1) a **Mosaic Engine** that assembles fragmented public data into coherent signals; (2) a **Dual-Track Engine** combining industry-specific multi-layer analysis pyramids with market-based pricing signals; and (3) a **System-Intelligence Layer** (v0.7.0-alpha) that models cross-industry contagion, portfolio concentration, and a market-wide Systemic Risk Index (SRI). Combines multi-stakeholder perspectives into a unified assessment framework.

**Expanded capabilities (v0.4.0+):** LGD/recovery rate framework, external support assessment, structured outlook/monitoring system, LGFV（地方政府融资平台 / 城投债）framework, ESG + governance/fraud detection, non-credit risk overlay, financial bond framework, holding company framework, false positive/negative testing, and layered output system with graduated confidence levels.

**Core principles:**
1. Traditional financial analysis systematically fails in policy-driven, technology-barrier, and asset-lease industries. The heaviest credit factor is rarely on the balance sheet.
2. External credit ratings consistently lag true credit deterioration by 17+ months across all validated cases.
3. **Mosaic theory:** Individual public data fragments are meaningless alone; assembled together they form coherent signals.
4. **Information completeness theory:** Data gaps are not defects — they are risk signals. "We don't have this data" itself tells the user something meaningful.

## When to Use

- Building an industry credit analysis framework from scratch
- Evaluating a specific company for lending or bond investment decisions
- Constructing a multi-dimensional investment dashboard (relative value + terms protection + liquidity + event calendar)
- Assembling fragmented public data into a coherent credit assessment using mosaic theory
- Retroactively validating analytical frameworks against historical defaults
- Designing a commercial credit intelligence product
- Evaluating LGFV (城投债) credit quality through the LGFV framework → read `dev/engine/lgv-framework.md`
- Conducting ESG/governance risk scans and fraud detection → read `dev/engine/esg-framework.md` and `dev/engine/governance-fraud-risk.md`
- Performing LGD/recovery rate analysis for default scenarios → read `dev/engine/lgd-recovery-framework.md`
- Assessing external support (government, parent company) impact on creditworthiness → read `dev/engine/external-support-framework.md`
- Evaluating financial bonds → read `dev/engine/financial-bond-framework.md`
- Analyzing holding companies → read `dev/engine/holding-company-framework.md`
- Assessing cross-industry contagion risk from a stressed issuer or sector
- Evaluating portfolio concentration across industry, region, rating, tenor, and funding-channel dimensions
- Computing the Systemic Risk Index (SRI) and interpreting the four-level thermometer
- Mapping an industry to one of the six analytical paradigms (policy-driven, tech-barrier, consolidation, asset-lease, brand-channel, network-traffic)

## Mosaic Engine Architecture (Mode A — Primary)

### Signal Confidence Levels

| Level | Type | Meaning |
|---|---|---|
| L5 | Multi-source cross-validated | Same fact confirmed by >=2 independent sources |
| L4 | Single-source direct | One reliable source explicitly states |
| L3 | Derived/inferred | Assembled from multiple fragments through reasoning |
| L2 | Directional weak | Direction known, magnitude unknown |
| L1 | Missing (gap) | Data that should exist but is absent — risksignal |

### Signal Density Assessment

For each analysis dimension, compute signal density = obtained signals / expected signals.

| Density | Meaning | Impact on Scoring |
|---|---|---|
| >80% | Sufficient | High confidence, direct scoring |
| 50-80% | Moderate | Medium confidence, score +/-1 interval |
| 20-50% | Insufficient | Low confidence, directional only, mark "needs supplement" |
| <20% | Severely lacking | Cannot score, mark "insufficient data" |

### Mandatory Density Rules

- If **any critical dimension** (L1 for the industry type, or any dimension the user explicitly asks about) has signal density **<20%**, you MUST NOT output a numeric score for that dimension. State `信息不足无法评估` and list the missing signals.
- If the **weighted-average signal density across all scored dimensions** is **<50%**, you MUST NOT output a final letter rating. Output a qualitative directional assessment plus a prioritized gap list instead.
- If density is 50-80%, you MAY output a rating but MUST label it as `中置信度` and widen the implied interval by ±1 notch.
- The completeness report is mandatory for every analysis; omitting it is a protocol violation.

Before finalizing any numeric rating, verify:
1. Every dimension used in the score has a documented density.
2. No critical dimension is below 20% density.
3. The final rating maps to the official 12-notch table.
4. Every veto condition has been explicitly checked.
If any check fails, downgrade the rating or replace it with a directional statement.

### Data Gap-to-Risk Mapping

Common gaps and their risk implications:

| Gap Type | Typical Missing Data | Information Risk | Substitute Signal |
|---|---|---|---|
| Competitive data | Exact cost comparison across firms | Over/under-estimate cost advantage | SOE bidding prices (market-accepted premium) |
| Financial data | Non-listed company financials | Cannot assess financial health | Enforcement records, judicial disputes, hiring trends |
| Market pricing | No stock/bond data for non-listed firms | Track B completely unavailable | Public financing events, equity transfer prices |
| Terms data | Duration/Z-spread (no Wind terminal) | Cannot do precise rate risk analysis | YTM approximation, same-rating spread comparison |
| Liquidity data | Bid-ask spread (not disclosed in China) | Cannot assess true trading cost | Daily volume, turnover rate, abnormal volume events |

### Completeness Report Output

Every analysis MUST include a completeness report structured as:
1. Per-dimension signal density bar
2. Gaps list (prioritized by impact on conclusion)
3. Gap-to-risk mapping
4. Confidence interval on scores
5. User-actionable suggestion (e.g., "If you need precise relative value ranking, connect Wind/Choice via Mode B")

## System-Intelligence Layer (v0.7.0-alpha)

The system-intelligence layer aggregates individual issuer assessments into portfolio- and market-level signals.

### Cross-Industry Contagion

- **Contagion theory**: four contagion types (credit-chain, regional resonance, liquidity squeeze, confidence collapse) and seven standard transmission paths.
- **Contagion matrix**: 13×13 industry intensity matrix with direction, confidence, and upgrade-factor linkage. See `dev/engine/contagion-matrix.md`.
- **Industry clustering**: based on six analytical paradigms. Industries in the same paradigm have higher innate contagion coupling.

### Five-Dimensional Concentration Framework

Concentration risk is scored across:

1. **Industry concentration** (HHI, CR3, CR5, MAX1)
2. **Regional concentration** (single-province share, weak-region share, fiscal-health-weighted share)
3. **Rating concentration** (external AAA share, pseudo-high-rating share, internal-external rating dispersion)
4. **Tenor concentration** (12/24/36-month maturities, single-month peak)
5. **Funding-channel concentration** (bank, bond, non-standard, leasing, equity)

Suggested default weights (adjustable per `concentration-framework.md` §8.4): industry 25%, region 20%, rating 20%, tenor 20%, funding channel 15%.

### Systemic Risk Index (SRI)

```
SRI = Σ(industry_risk_score × industry_weight_pct)
```

- Scale: 0–3+
- Levels: 🟢 normal (<0.5), 🟡 watch (0.5–1.0), 🟠 alert (1.0–1.8), 🔴 danger (≥1.8)
- Inputs: Track-A industry score, Track-B market signal, outlook direction, and one-shot-veto triggers.

For full specification see `dev/engine/systemic-warning-framework.md`.

## Mode B: External Data Source Adapter (Placeholder)

> **Mode B 护栏**：除非用户明确提供了 CSV 上传、API endpoint 或 MCP server，否则禁止调用 Mode B 接口，禁止生成外部数据值。在 Mode B 未激活时，所有 Mode B 字段应作为数据缺口处理。

Standardized interface for users to connect their own data. Defined but not implemented.

**Adapter contract:**
- `query_bond_analytics(bond_code, fields)` — duration, convexity, Z-spread, OAS, bid-ask
- `query_market_data(instrument, data_type, date_range)` — price history, volume, volatility, fund flow
- `query_industry_benchmark(industry, metric, date)` — credit spread, default rate, rating migration

**Connection methods (priority order):** CSV upload (P1) > REST API (P1) > MCP Server (P2) > Database (P3)

Full architecture specification: `dev/engine/mosaic-engine.md`

## Multi-Stakeholder Coverage

| # | Stakeholder | Core Question | Status |
|---|---|---|---|
| M0 | Credit Approval (Bank) | Can we lend? At what price? | Covered (Track A+B) |
| M1 | Bond Investment | Cheap or expensive? Terms protective? Liquid? | P0 Complete |
| M2 | Bond Underwriting (DCM) | Can we sell this? To whom? Best window? | 完成 |
| M3 | Market Trading | Rate/credit/liquidity environment? | 完成 |
| M4 | Portfolio Risk | Concentration? Stress scenario? | 完成 |
| M5 | Corporate Finance | How to finance? Which channel? When? | 完成 |

## Two-Track Parallel Structure (Core)

```
Input: Industry + Company + Analysis Date
        |
    +-------+-----------+
    |                   |
Track A: Fundamental  Track B: Market Pricing
(qualitative+scoring) (quantitative signals)
    |                   |
  L1 (Heaviest)       Credit spreads
  L2                   Volatility
  L3                   Fund flows
  L4 (Lightest)        Rating migration
    |                   |
    +-------+-----------+
            |
    Cross-Comparison Matrix
    Consensus -> reinforced
    Divergence -> most valuable insight
```

**When tracks diverge, prioritize Track A (auditable financial facts) over Track B (external ratings).**

## Track A: Industry Analysis Pyramids

Each industry type has a different heaviest factor. Weights determined by 10-dimension scoring.

| Industry Type | Conditions | L1 (Heaviest) | L2 | L3 | L4 (Lightest) |
|---|---|---|---|---|---|
| Policy-Driven | D3>=4, D4>=3 | 35% Policy/Macro | 30% Technology | 20% Supply Chain | 15% Financial |
| Tech-Barrier | D7>=3, D9>=3 | 20% Policy | 35% Tech/IP/Registration | 25% Operations | 20% Financial |
| Consolidation | D2<=3, D10>=3 | 25% Survival | 20% Technology | 30% Profit Fortress | 25% Financial |
| Asset-Lease | D5>=4, D8>=3 | 15% Policy | 20% Technology | 35% Client/Lease | 30% Financial |

**Semiconductor uses a 5-layer pyramid** (L1 Geopolitics 30-35% / L2 Technology 25-30% / L3 Market 15-20% / L4 Policy 10-15% / L5 Financial 5-10%).

**NEV uses dual-track** (OEM survival model vs supply chain profit fortress model — completely separate frameworks).

Each layer scores 0-10. Each layer has one-shot veto conditions (see `dev/engine/industry-framework.md`).

## Six Analytical Paradigms + LGFV Special Category

本节介绍 **6 个分析范式 + 1 个特殊类别（LGFV）**：六个通用范式用于描述普通行业的信用传染结构，LGFV 因政府信用绑定机制特殊而单列，不强行归入六范式，但在传染矩阵中仍参与行业聚类分析。

> **注意**：6 个分析范式是用于传染聚类和行业分组的概念工具；它们不同于 `industry-framework.md` 中定义的 4 个行业类型（用于设置金字塔权重）。一个行业可能同时满足多个范式特征，此时以 `industry-framework.md` 的行业类型作为金字塔权重依据，以范式作为传染分析依据。存在冲突时，使用 `industry-framework.md` §3.1 的优先级规则。

| Paradigm | Primary Industries | Secondary Attributes | Heaviest Factor | Key Contagion Path |
|---|---|---|---|---|
| Policy-Driven | Solar/PV; Semiconductor (primary) | Semiconductor also Tech-Barrier | Policy/geopolitics cycle | Same-region SOE, same-industry |
| Tech-Barrier | High-end equipment; Biomedicine (primary); Medical devices; NEV-Supply Chain | Biomedicine also Policy-Driven; NEV-Supply Chain also Profit Fortress | Technology/IP/registration | Supplier-customer chain, same funding channel |
| Consolidation | NEV-OEM | — | Survival / profit fortress | Same-industry, credit-chain |
| Asset-Lease | Data centers (IDC/colocation primary) | Cloud/telecom hybrid as Network+Traffic | Client/lease quality | Supplier-customer chain, same funding channel |
| Brand+Channel | Food & beverage; Textile & apparel | — | Brand equity | Confidence collapse, same-industry |
| Network+Traffic | Transportation; Retail; Media/Internet; Data centers (cloud/telecom hybrid) | — | Network traffic | Supplier-customer chain, same funding channel |
| Special / Government Credit | LGFV | — | Regional fiscal health | Regional resonance, same funding channel |

See `dev/engine/industry-framework.md`, `dev/engine/paradigm-brand-channel.md`, and `dev/engine/paradigm-network-traffic.md` for detailed specs.

## Ten-Dimension Industry Scoring (D1-D10)

| # | Dimension | Definition |
|---|---|---|
| D1 | Market Size | Current domestic market size (not projected) |
| D2 | Growth Trajectory | Growth certainty over next 3-5 years |
| D3 | Policy Support | Clarity and continuity of national-level policy support |
| D4 | Policy Volatility | Frequency of policy change, risk of abrupt pivots |
| D5 | Capital Sustainability | Diversity and longevity of capital sources |
| D6 | Livelihood Linkage | Direct relationship to social stability and basic welfare |
| D7 | External Dependency | Dependence on foreign technology, equipment, materials, markets |
| D8 | Supply Chain Power Concentration | Bargaining power distribution in the value chain |
| D9 | Industry Lifecycle | Stage of industry development |
| D10 | Cyclicality | Sensitivity to macro/inventory/price cycles |

## Industry Selection Filters (C1-C4)

| Condition | Meaning | Hard Gate? |
|---|---|---|
| C1 Transaction Volume | Sufficient lending + bond/equity issuance | Yes |
| C2 Analytical Barrier | "Can't understand it just from financials" | Yes |
| C3 Practitioner Pain | Professionals actively seeking capability | No |
| C4 Data Credibility | Public data is fundamentally reliable | **Yes — hard gate** |

## Track B: Market Pricing Signals

| Level | Credit Spreads | Volatility | Fund Flows | Rating Events |
|---|---|---|---|---|
| Calm | Stable/narrowing | <3% daily | Stable/inflow | Stable |
| Watch | Widened 20-50bp | 3-5% | Moderate outflow | Outlook negative |
| Abnormal | >50bp jump or persistent | >5% sustained | Accelerated outflow | Watchlist |
| Crisis | Curve inversion/freeze | >8% or liquidity dry-up | N-bound clearing | Downgraded |

## Cross-Comparison Matrix

| | Track B: Calm | Track B: Abnormal/Crisis |
|---|---|---|
| **Track A: Good (6-10)** | Consensus | Divergence: What is market panicking about? |
| **Track A: Poor (0-5)** | Divergence: What is market ignoring? | Consensus |

## M1: Bond Investment Dashboard (P0)

Four dimensions for evaluating individual bonds:

1. **Relative Value (30%):** YTM, conversion premium, Z-spread (if available), same-industry peer comparison, same-rating comparison
2. **Terms Protection (25%):** Conversion price adjustment history, put option triggers, cross-default clauses, redemption terms
3. **Liquidity (20%):** Daily volume, turnover rate, abnormal volume events, bid-ask spread (if available)
4. **Event Calendar (25%):** Next 3 months of macro events, industry events, company events, terms triggers

Output: Integrated ranking table + individual bond assessment + data gap report.

## Data Source Architecture

**Hard constraint: Zero internal bank data. Zero non-public data. Zero paid data sources (for POC).**

| Data Layer | Source | Method |
|---|---|---|
| Macro Policy | Government official sites | WebSearch + LLM parsing |
| Industry Data | Trade associations, broker reports | WebSearch |
| Supply Chain Prices | Free data (PVInfoLink/TrendForce/SMM) | WebSearch |
| Enterprise Records | NEEQ, judgment docs, enforcement records | WebSearch |
| Bidding/Tender | Provincial procurement platforms | WebSearch |
| Bond Data | Exchange announcements, China Money | WebSearch |

**Before any analysis, verify data accessibility across 4 categories:** policy, enterprise risk, industry data, market pricing.

## Scoring Engine

```
Composite Score = Sigma(Layer Score * Layer Weight)
Layer Weight = f(Industry 10-Dimension Score)
Layer Score = Sigma(Indicator Score * Indicator Weight)
Indicator Score = f(Raw Value, Threshold, Direction)
```

**Rating Map (12-notch):**

| 评分范围 | 新评级 | 旧评级对应 | 含义 |
|---|---|---|---|
| 9.5 - 10.0 | AAA | AAA | 极低风险 |
| 9.0 - 9.4 | AA+ | AA | |
| 8.5 - 8.9 | AA | AA | 低风险 |
| 8.0 - 8.4 | AA- | AA | |
| 7.5 - 7.9 | A+ | A | 中低风险 |
| 7.0 - 7.4 | A | A | |
| 6.5 - 6.9 | A- | A | |
| 6.0 - 6.4 | BBB+ | BBB | 中等风险 |
| 5.5 - 5.9 | BBB | BBB | |
| 5.0 - 5.4 | BBB- | BBB | |
| 4.5 - 4.9 | BB+ | BB | 中高风险 |
| 4.0 - 4.4 | BB | BB | |
| 3.5 - 3.9 | BB- | BB | |
| 3.0 - 3.4 | B+ | B | 高风险 |
| 2.5 - 2.9 | B | B | |
| 2.0 - 2.4 | B- | B | |
| 1.0 - 1.9 | CCC | CCC | 极高风险 |
| 0 - 0.9 | D | D | 违约/濒临 |

## Black-Swan Retrospective Validation

Two-time-point methodology (T1: 17-18 months, T2: 4-5 months before default). All data must have been publicly available AS OF the analysis point. See `dev/engine/validation-methodology.md`.

## Validated Industries & Cases

| Industry | Forward Test | Retrospective Test |
|---|---|---|
| Solar/PV | 完成 | — |
| Semiconductor | 完成 | 完成 |
| Biomedicine | 完成 | 完成 |
| High-End Equipment | 完成 | 完成 |
| Medical Devices | 完成 | 完成 |
| NEV | 完成 | 完成 |
| Data Center | 完成 | — |
| Coal/SOE (Yongmei) | — | 完成 |
| LGFV | 框架覆盖 | 框架覆盖 |
| Food & Beverage | 13-industry framework coverage | — |
| Textile & Apparel | 13-industry framework coverage | — |
| Transportation | 13-industry framework coverage | — |
| Retail | 13-industry framework coverage | — |
| Media/Internet | 13-industry framework coverage | — |

## Key Design Principles

1. Financial analysis is NEVER the heaviest layer. The heaviest factor is structural/external.
2. Each industry has a different heaviest factor determined by 10-dimension scoring.
3. Don't jump layers. L1 must pass before L2 is meaningful.
4. L4 validates, never overrules. Poor financials with strong upper layers = may be investing through cycle. Strong financials with weak upper layers = MORE dangerous (peak cycle or fraud).
5. Public data is sufficient. POC validated across 3 black-swan cases and 3 industries.
6. Track B is independent, not subordinate. Divergence generates the most valuable questions.
7. When tracks clash, prioritize auditable financial facts over external ratings.
8. Data gaps are not defects — they are risk signals. Every analysis includes a completeness report.
9. The framework identifies structural unsustainability but cannot predict default timing or specific triggers.

## Supporting Files

- `dev/engine/industry-framework.md` — Complete pyramid specs for 7 industries
- `dev/engine/validation-methodology.md` — Detailed validation methodology and case data
- `dev/engine/mosaic-engine.md` — Full mosaic engine architecture specification
- `dev/engine/non-credit-risk-overlay.md` — Non-credit risk overlay framework
- `dev/engine/esg-framework.md` — ESG + governance/fraud detection framework
- `dev/engine/governance-fraud-risk.md` — Governance and fraud risk framework
- `dev/engine/financial-bond-framework.md` — Financial bond analysis framework
- `dev/engine/holding-company-framework.md` — Holding company credit analysis framework
- `dev/engine/lgv-framework.md` — LGFV (城投债) credit analysis framework
- `dev/engine/lgd-recovery-framework.md` — LGD/recovery rate framework
- `dev/engine/external-support-framework.md` — External support assessment framework
- `dev/engine/false-positive-negative-testing.md` — False positive/negative testing methodology
- `dev/engine/output-layered-framework.md` — Layered output system specification
- `dev/templates/template-type1.html` — HTML report template (dark theme, Type 1 单标的深度分析)
- `dev/engine/contagion-theory.md` — Contagion types, transmission paths, upgrade factors
- `dev/engine/contagion-matrix.md` — 13×13 cross-industry contagion matrix
- `dev/engine/concentration-framework.md` — Five-dimensional concentration framework
- `dev/engine/systemic-warning-framework.md` — SRI algorithm and thermometer
- `dev/engine/paradigm-brand-channel.md` — Brand+channel paradigm specification
- `dev/engine/paradigm-network-traffic.md` — Network+traffic paradigm specification
- `dev/templates/template-type13.html` — Contagion report template
- `dev/templates/template-type14.html` — Concentration report template
- `dev/templates/template-type15.html` — Systemic warning report template

## Version History

| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2026-07-07 | Initial release. 10-dim scoring, 4-layer pyramid, dual-track, 7 industries, solar forward-validated |
| 0.2.0 | 2026-07-07 | Retrospective validation methodology. Yongmei (2 time points, 17-month) + Tsinghua Unigroup (17-month). Framework effective across risk genotypes. Semiconductor 5-layer pyramid. |
| 0.3.0 | 2026-07-08 | Mosaic engine architecture (Mode A+B). Multi-stakeholder coverage map. P0 bond investment dashboard (relative value + terms + liquidity + event calendar). Signal confidence levels + signal density metrics. Data gap-to-risk mapping. Completeness reporting. External data source adapter interface (placeholder). |
| 0.4.0-alpha | 2026-07-08 | LGD/recovery rate framework. External support assessment. Structured outlook/monitoring system. LGFV（城投债）framework. ESG + governance/fraud detection. Non-credit risk overlay. Financial bond framework. Holding company framework. False positive/negative testing methodology. Layered output system. Multi-stakeholder coverage completed (P1/P2). All 8 industries fully validated. |
| 0.5.0-release | 2026-07-09 | Release stabilization. Complete supporting documentation for all expanded capabilities. Production-ready layered output system. Full 8-industry, 30-document, 15-template coverage. |
| 0.7.0-alpha | 2026-07-13 | System-intelligence layer: contagion theory/matrix, five-dimensional concentration framework, systemic warning (SRI), 13-industry coverage, six analytical paradigms. Skill synchronized with engine release. |
| 0.7.1-alpha | 2026-07-15 | Dev-stack structure reorganization: templates consolidated to dev/templates/ (single source, Type 1-15), engine current+audits split, reports organized into 15 subdirectories. Skill templates/ copies removed; references point to dev/templates/. |

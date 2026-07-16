# Mosaic Engine Architecture (Mode A — Primary)

**版本**: v0.8.0-alpha

> 本文自 `fixed-income-credit-analysis` SKILL.md 下沉而来，组织马赛克引擎（Mode A）的详述参考。阈值/规则的单一事实源为 `dev/engine/mosaic-engine.md`；本文件仅作导航与组织，不引入新数值。

## Signal Confidence Levels

| Level | Type | Meaning |
|---|---|---|
| L5 | Multi-source cross-validated | Same fact confirmed by >=2 independent sources |
| L4 | Single-source direct | One reliable source explicitly states |
| L3 | Derived/inferred | Assembled from multiple fragments through reasoning |
| L2 | Directional weak | Direction known, magnitude unknown |
| L1 | Missing (gap) | Data that should exist but is absent — risk signal |

## Signal Density Assessment

For each analysis dimension, compute signal density = obtained signals / expected signals.

| Density | Meaning | Impact on Scoring |
|---|---|---|
| >80% | Sufficient | High confidence, direct scoring |
| 50-80% | Moderate | Medium confidence, score +/-1 interval |
| 20-50% | Insufficient | Low confidence, directional only, mark "needs supplement" |
| <20% | Severely lacking | Cannot score, mark "insufficient data" |

## Mandatory Density Rules

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

## Data Gap-to-Risk Mapping

Common gaps and their risk implications:

| Gap Type | Typical Missing Data | Information Risk | Substitute Signal |
|---|---|---|---|
| Competitive data | Exact cost comparison across firms | Over/under-estimate cost advantage | SOE bidding prices (market-accepted premium) |
| Financial data | Non-listed company financials | Cannot assess financial health | Enforcement records, judicial disputes, hiring trends |
| Market pricing | No stock/bond data for non-listed firms | Track B completely unavailable | Public financing events, equity transfer prices |
| Terms data | Duration/Z-spread (no Wind terminal) | Cannot do precise rate risk analysis | YTM approximation, same-rating spread comparison |
| Liquidity data | Bid-ask spread (not disclosed in China) | Cannot assess true trading cost | Daily volume, turnover rate, abnormal volume events |

## Completeness Report Output

Every analysis MUST include a completeness report structured as:
1. Per-dimension signal density bar
2. Gaps list (prioritized by impact on conclusion)
3. Gap-to-risk mapping
4. Confidence interval on scores
5. User-actionable suggestion (e.g., "If you need precise relative value ranking, connect Wind/Choice via Mode B")

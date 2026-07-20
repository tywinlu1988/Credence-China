# System-Intelligence Layer (v0.7.0-alpha)

**版本**: v0.9.0-release

> 本文自 `fixed-income-credit-analysis` SKILL.md 下沉而来，组织系统智能层（跨行业传染 / 五维集中度 / 系统性风险指数）内容。算法与阈值的单一事实源为 `dev/engine/systemic-warning-framework.md`、`dev/engine/contagion-matrix.md`、`dev/engine/concentration-framework.md`；本文件仅作导航与组织，不引入新数值。

The system-intelligence layer aggregates individual issuer assessments into portfolio- and market-level signals.

## Cross-Industry Contagion

- **Contagion theory**: four contagion types (credit-chain, regional resonance, liquidity squeeze, confidence collapse) and seven standard transmission paths.
- **Contagion matrix**: 13×13 industry intensity matrix with direction, confidence, and upgrade-factor linkage. See `dev/engine/contagion-matrix.md`.
- **Industry clustering**: based on six analytical paradigms. Industries in the same paradigm have higher innate contagion coupling.

## Five-Dimensional Concentration Framework

Concentration risk is scored across:

1. **Industry concentration** (HHI, CR3, CR5, MAX1)
2. **Regional concentration** (single-province share, weak-region share, fiscal-health-weighted share)
3. **Rating concentration** (external AAA share, pseudo-high-rating share, internal-external rating dispersion)
4. **Tenor concentration** (12/24/36-month maturities, single-month peak)
5. **Funding-channel concentration** (bank, bond, non-standard, leasing, equity)

Suggested default weights (adjustable per `concentration-framework.md` §8.4): industry 25%, region 20%, rating 20%, tenor 20%, funding channel 15%.

## Systemic Risk Index (SRI)

```
SRI = Σ(industry_risk_score × industry_weight_pct)
```

- Scale: 0–3+
- Levels: 🟢 normal (<0.5), 🟡 watch (0.5–1.0), 🟠 alert (1.0–1.8), 🔴 danger (≥1.8)
- Inputs: Track-A industry score, Track-B market signal, outlook direction, and one-shot-veto triggers.

For full specification see `dev/engine/systemic-warning-framework.md`.

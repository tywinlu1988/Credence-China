# Multi-Stakeholder Coverage & Path-Sheet Consumption

**版本**: v0.8.3-release

> 本文自 `fixed-income-credit-analysis` SKILL.md 下沉而来，组织多利益相关者覆盖与 M1 仪表盘内容，并补充《工作路径单》消费指引。单一事实源为 `dev/engine/multi-stakeholder.md` 与 `dev/engine/work-path-registry.md`。

## Multi-Stakeholder Coverage

| # | Stakeholder | Core Question | Status |
|---|---|---|---|
| M0 | Credit Approval (Bank) | Can we lend? At what price? | Covered (Track A+B) |
| M1 | Bond Investment | Cheap or expensive? Terms protective? Liquid? | P0 Complete |
| M2 | Bond Underwriting (DCM) | Can we sell this? To whom? Best window? | 完成 |
| M3 | Market Trading | Rate/credit/liquidity environment? | 完成 |
| M4 | Portfolio Risk | Concentration? Stress scenario? | 完成 |
| M5 | Corporate Finance | How to finance? Which channel? When? | 完成 |

## M1: Bond Investment Dashboard (P0)

Four dimensions for evaluating individual bonds:

1. **Relative Value (30%):** YTM, conversion premium, Z-spread (if available), same-industry peer comparison, same-rating comparison
2. **Terms Protection (25%):** Conversion price adjustment history, put option triggers, cross-default clauses, redemption terms
3. **Liquidity (20%):** Daily volume, turnover rate, abnormal volume events, bid-ask spread (if available)
4. **Event Calendar (25%):** Next 3 months of macro events, industry events, company events, terms triggers

Output: Integrated ranking table + individual bond assessment + data gap report.

## 路径单消费指引（Work-Path Sheet Consumption）

执行本 skill 时，按以下优先级确定阅读与校验顺序：

1. **收到 router 产出的《工作路径单》**：严格按 `engine_reading_order` 字段所列顺序阅读引擎文档，按 `quality_gates` 字段所列质量门逐条校验。路径单字段对齐 `dev/engine/work-path-registry.md` 的 schema。
2. **无路径单（用户直接点名具体任务）**：回退到 Invocation Protocol 的核心集——`dev/engine/engine-overview.md` + `dev/engine/dual-track-methodology.md` + 请求点名的专题文档。
3. **模糊需求未路由**：先经 `credit-analysis-router` skill 明确路径，或按 Q1-Q4（角色 / 对象 / 深度 / 数据）询问后从注册表选定路径，再开始执行。

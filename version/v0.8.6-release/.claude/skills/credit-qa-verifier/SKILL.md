---
name: credit-qa-verifier
description: Use when verifying a Chinese fixed-income credit report or analysis — checking a work path's quality gates, enforcing the mandatory signal-density rules (no numeric score below the density floor), the one-shot-veto CCC ceiling, Mode B anti-hallucination guardrails, and single-source-of-truth compliance (no invented thresholds). Triggers on '质检', '复核这份报告', '检查一下有没有问题', '质量门', or as the final step after report generation. Reads engine documents as the rule source; never relaxes a gate.
---

## Purpose

**对应引擎版本**: v0.8.6-release

质检层，四段链**终态**。职责：对《交付单》及其上游《分析产物》《工作路径单》做交付前复核，产出《质检裁决》（QA Verdict）。本 skill 以引擎文档为规则源，**从不放宽门禁**（never relaxes a gate）：任何一项质量门或强制检查不通过，即判 `fail` 并退回整改，不得为了交付而降低标准。本 skill 不复制任何阈值/评级映射；规则正文以所引引擎文档为单一事实源。

## Inputs（消费）

- **《交付单》（Delivery Note）**：`credit-report-builder` 产出（字段形状见 `engine/pipeline-contract.md` §2.3）。
- **《分析产物》（Analysis Artifact）**：`fixed-income-credit-analysis` 产出，供复核密度/否决/完备性（§2.2）。
- **《工作路径单》的 `quality_gates`**：`credit-analysis-router` 产出，是逐门复核的清单来源；`path_id` 为贯穿 join key，三份产物须一致。

## Output（产出）

- **《质检裁决》（QA Verdict）**：终态产物，字段形状见 `engine/pipeline-contract.md` §2.4。`verdict` 取值 `pass` | `pass-with-findings` | `fail`。

## Verification Protocol（复核协议）

1. **join key 一致性**：三份产物的 `path_id` 必须相同且在注册表可解析；不一致即 `fail`。
2. **逐质量门复核**：对路径单 `quality_gates` 逐条复核，产 `gate_results`（每门 `status` + `evidence`，证据引用引擎文档章节）。
3. **四项强制检查**：见下「Mandatory Checks」，任一不通过即 `fail`。
4. **产裁决**：全部通过 → `pass`；通过但有应注记的发现 → `pass-with-findings`；任一不通过 → `fail` 并列 `remediation`。

## Mandatory Checks（强制检查，规则源为引擎文档）

- **信号密度规则 `density_rule`**：密度低于下限的维度不得出数值评分，须标注"信息不足无法评估"；加权密度不足时不得出最终字母评级。规则源 `engine/mosaic-engine.md` §4.3。
- **一票否决上限 `veto_ceiling`**：触发一票否决的发行人，评级上限锁定为 CCC 不得上调。规则源 `engine/industry-framework.md` §五。
- **Mode B 防幻觉 `mode_b`**：用户未显式提供数据源（CSV/API/MCP）时，不得出现任何 Mode B 外部数据值；所有 Mode B 字段须作数据缺口处理。规则源 `engine/mosaic-engine.md` §六。
- **单一事实源 `single_source`**：报告/分析不得编造阈值、权重、评级映射；引擎未定义的量须标注 `引擎未定义`。规则源为全部所引引擎文档。

## QA Verdict Output（《质检裁决》）

模板（schema 单一事实源为 `engine/pipeline-contract.md` §2.4）：

```yaml
path_id: ""                 # join key（三份产物须一致）
verdict: ""                 # pass|pass-with-findings|fail
gate_results:               # 逐质量门复核结果
  - gate: ""                # "规则名 (engine/<doc>.md §节)"（承自路径单 quality_gates）
    status: ""              # pass|fail
    evidence: ""            # 复核证据（引用引擎文档章节，不复制数值）
mandatory_checks:           # 四项强制检查
  density_rule: ""
  veto_ceiling: ""
  mode_b: ""
  single_source: ""
remediation: []             # 不通过项的整改建议
```

示例（审贷单标的 WP-M0-01，三门复核通过、强制检查全过，有一项应注记发现）：

```yaml
path_id: WP-M0-01
verdict: pass-with-findings
gate_results:
  - gate: "信号密度 (engine/mosaic-engine.md §4.3)"
    status: pass
    evidence: 低于密度下限的维度已置 null 并标注信息不足无法评估（mosaic-engine §4.3）
  - gate: "一票否决 (engine/industry-framework.md §五)"
    status: pass
    evidence: 未触发一票否决，评级上限规则复核通过（industry-framework §五）
  - gate: "交叉对撞 (engine/dual-track-methodology.md §四)"
    status: pass
    evidence: 双轨分歧已在报告中呈现并解读（dual-track-methodology §四）
mandatory_checks:
  density_rule: pass
  veto_ceiling: pass
  mode_b: pass
  single_source: pass
remediation: []
```

## Chaining（链式交接 · 终态）

- **上游（REQUIRED）**：`credit-report-builder` —— 消费其《交付单》及上游产物。
- **终态**：本 skill 为四段链最后一段，无下游。判 `fail` 时按 `remediation` 退回对应阶段（密度/否决问题回 analysis；模板/装配问题回 report）整改后重新质检。

## Guardrails

- **从不放宽门禁（never relaxes a gate）**：质量门与强制检查只有"通过/不通过"，不设"酌情通过"。缺完备性报告、低密度出数值分、编造阈值、Mode B 幻觉，一律 `fail`。
- **不复制引擎内容**：只引用规则名与文档章节，不复制任何阈值、SRI 档位、分层时间预算或评级映射；数值裁决以所引引擎文档为准。
- **以引擎文档为规则源**：每条 gate 规则名必须能在所引引擎文档中 grep 到（溯源见 `references/qa-checklist.md`），不得虚构规则。

## References

- `references/qa-checklist.md` — 质检清单（逐门规则名 → 引擎文档溯源，单源指针）
- `engine/pipeline-contract.md` — 四段链 I/O 契约（产物 schema 单一事实源）
- `engine/mosaic-engine.md` — 信号密度/完备性/Mode B 护栏（density_rule、mode_b 规则源）
- `engine/industry-framework.md` — 一票否决评级上限（veto_ceiling 规则源）
- `engine/work-path-registry.md` — 工作路径注册表（质量门清单溯源）

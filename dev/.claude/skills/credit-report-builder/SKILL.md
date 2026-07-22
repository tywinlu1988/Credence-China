---
name: credit-report-builder
description: Use when turning a completed Chinese fixed-income credit analysis into a deliverable report — selecting the correct report template (Type 1–18), mapping findings to the L0/L1/L2 output tiers, rendering a multi-stakeholder dashboard, or assembling a layered credit report from an analysis artifact. Triggers on '生成报告', '出一份授信审批报告', '做成仪表盘', 'L0信号卡', or when a work-path sheet's templates must be produced. Requires an upstream analysis artifact; does not perform analysis itself.
---

## Purpose

**对应引擎版本**: v0.9.5-release

装配层，**本 skill 不做分析**（does not perform analysis）。职责仅两步：把上游 `fixed-income-credit-analysis` 产出的《分析产物》映射到 L0/L1/L2 输出层并选中正确模板 → 装配为交付报告并产出《交付单》。本 skill 不复制任何引擎阈值/分层时间预算/评级映射；模板选择与分层语义一律以引擎文档为单一事实源。

## Inputs（消费）

- **《工作路径单》（Path Sheet）**：router 产出，提供 `path_id` / `depth` / `quality_gates`。`path_id` 是贯穿四段链的 join key，本 skill 原样继承、不得更改。
- **《分析产物》（Analysis Artifact）**：fixed-income 产出，提供 findings / completeness / veto / system_readouts / mode_b_gaps（字段形状见 `dev/engine/pipeline-contract.md` §2.2）。

## Outputs（产出）

- **交付报告**：渲染自 `dev/templates/`（模板单一事实源，本 skill 不自带模板副本）。用哪个模板由该路径在 `dev/engine/work-path-registry.md` 的 `templates` 字段决定，不擅自更换。
- **《交付单》（Delivery Note）**：结构化 yaml，字段形状见 `dev/engine/pipeline-contract.md` §2.3。

## Assembly Protocol（装配协议）

1. **读 join key**：从路径单与分析产物取 `path_id`，校验它指向注册表中的已注册路径；不一致即停止并上报。
2. **选模板**：按 `path_id` 在 registry 的 `templates` 字段取模板清单（Type 1–18 或允许的标记值 `planned` / `L0-spec:`）。标记值含义以 registry §schema 为准；命中 `planned` 须如实告知"模板待开发"，不得伪造渲染产物。
3. **映射分层**：把分析产物映射到 L0 信号卡 / L1 快照 / L2 深度报告三层。三层的定义、消费时间与信息密度以 `dev/engine/output-layered-framework.md` §二（三层总览）/§三（L0 信号卡）/§五（L2 深度报告）为单一事实源，本 skill 不重新定义。
4. **渲染**：用 `dev/templates/` 的模板装配报告；完备性灯号口径见 output-layered-framework §8.4。
5. **产交付单**：按下述 schema 输出《交付单》。

## 装配纪律

1. **逐节溯源**：每个 section 的内容必须可溯源至上游分析产物；任何数据点不得凭模板示例或印象生成。
2. **示例区整节替换**：模板中的示例/演示内容（含数值、公司名、结论）必须整节替换，禁止部分保留。
3. **交付前残留自查**：搜索 `{` 残留占位符与已知实例名（`tests/test_template_contract.py` 的 INSTANCE_NAMES），任一命中即回炉。

## Delivery Note Output（《交付单》）

模板（schema 单一事实源为 `dev/engine/pipeline-contract.md` §2.3）：

```yaml
path_id: ""                 # join key（承自路径单，不得更改）
depth: ""                   # L0|L1|L2|专项（承自路径单）
templates_used: []          # 该路径 registry templates 字段选中的模板
rendered: []                # 实际产出的报告文件（来自 dev/templates/）
tier_mapping:               # 分析产物 → L0/L1/L2 层
  L0: ""
  L1: ""
  L2: ""
completeness_lamp: ""       # 完备性灯号
source_analysis: ""         # 上游分析产物引用（溯源）
```

示例（审贷单标的 L2 深度报告，路径 WP-M0-01 配 Type 1 + Type 6）：

```yaml
path_id: WP-M0-01
depth: L2
templates_used:
  - dev/templates/template-type1.html
  - dev/templates/template-type6.html
rendered:
  - dev/templates/template-type1.html
  - dev/templates/template-type6.html
tier_mapping:
  L0: 信号卡（评级+展望+今日关键信号+完备性灯号）
  L1: 快照（四维雷达+关键异常+评级对比）
  L2: 深度报告（金字塔逐层+双轨对撞+完备性报告）
completeness_lamp: 黄色（中置信度，口径见 output-layered-framework §8.4）
source_analysis: 上游分析产物（findings/completeness/veto，见 pipeline-contract §2.2）
```

## Chaining（链式交接）

- **上游**：`fixed-income-credit-analysis` skill —— 消费其《分析产物》。无分析产物时本 skill 不启动（自身不做分析，先回上游完成分析）。
- **REQUIRED NEXT SUB-SKILL**：`credit-qa-verifier` —— 《交付单》产出后**自动**移交质检 skill 做交付前终态复核（质量门 + 强制检查），质检通过方可交付。**不得就"是否质检/是否继续"询问用户**——质检是链的必经终态，不是可选步骤。全链交互点预算见 `dev/engine/pipeline-contract.md` §三「链式接续规则」。

## Guardrails

- **禁自造报告形式（防漂移）**：交付报告一律使用 registry `templates` 字段指定的 `dev/templates/` 模板，章节结构与模板逐节对应；禁止自行设计版式或"参考模板风格自制"。无可用模板时按 `planned` 标记规则如实告知，不自创。
- **自动接续**：本 skill 由上游 analysis 自动触发，《交付单》产出后自动移交 qa-verifier；链上不设"是否继续/是否质检"确认点。
- **不做分析**：本 skill 只做模板选择、分层映射与装配，不重新计算评分、不补信号、不改评级。分析结论一律来自上游《分析产物》。
- **不复制引擎内容**：只引用路径 ID、模板名与文档章节，不复制任何阈值、分层时间预算、信号优先级门槛或评级映射。分层语义以 `dev/engine/output-layered-framework.md` 为准，模板清单以 `dev/engine/work-path-registry.md` 为准。
- **低密度不补数值**：上游分析产物中因密度不足而置 null 的维度评分（信息不足无法评估），在报告中保持"信息不足"标注，不得为了报告完整而编造数值。
- **planned 模板如实告知**：路径模板为 `planned` 标记时，明示"该模板待开发"，并给出该路径已可用的替代交付物，不得伪造渲染产物。

## References

- `references/report-mapping.md` — 路径→模板→分层 映射视图（单源指针，不含复制值）
- `dev/engine/pipeline-contract.md` — 四段链 I/O 契约（产物 schema 单一事实源）
- `dev/engine/work-path-registry.md` — 工作路径注册表（`templates` 字段单一事实源）
- `dev/engine/output-layered-framework.md` — L0/L1/L2 分层输出（分层语义单一事实源）

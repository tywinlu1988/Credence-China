# 四段链 I/O 契约（Pipeline Contract）

**版本**: v0.9.1-release | **日期**: 2026-07-16

本契约是 v0.8.0 skill 架构四段链（intake → analysis → report → qa）的**单一事实源**：它定义四个阶段之间传递的四份产物（artifact）的结构，以及驱动阶段切换/重跑的链式边（chaining edges）。四份产物由四个 skill 分别承载：

| 阶段 | 产物 | 承载 skill | 上游 | 下游 |
|---|---|---|---|---|
| S1 intake | 工作路径单（Path Sheet） | `credit-analysis-router` | — | S2 |
| S2 analysis | 分析产物（Analysis Artifact） | `fixed-income-credit-analysis` | S1 | S3 |
| S3 report | 交付单（Delivery Note） | `credit-report-builder` | S2 | S4 |
| S4 qa | 质检裁决（QA Verdict，终态） | `credit-qa-verifier` | S1+S2+S3 | —（终态） |

**单一事实源原则**：本契约只定义产物的**字段形状**与链式边的**结构**，不定义、不复制任何阈值、SRI 档位、分层时间预算或评级映射值。凡涉及数值语义，一律以所引引擎文档章节为最终裁决（见 [§四](#四单一事实源声明)）。

## 一、四段链总览与 join key

四份产物通过 **`path_id`** 这一 join key 贯穿：`path_id` 必须是 [work-path-registry.md](work-path-registry.md) 中已注册的工作路径 ID，S1 由 router 选定后，S2/S3/S4 原样继承、不得更改。任一阶段产物的 `path_id` 无法在注册表解析，即构成引用完整性违规（由 `scripts/consistency_check.py` 的 join-key 校验强制）。

- S1 选定 `path_id` 与 `engine_reading_order`/`quality_gates`，决定"走哪条路径、读哪些引擎、过哪几道门"。
- S2 按 `engine_reading_order` 执行分析，产出 `path_id` 相同的分析产物。
- S3 把分析产物装配为交付报告，产出 `path_id` 相同的交付单。
- S4 对该 `path_id` 的交付物做终态质检，产出质检裁决。

## 二、产物契约（Artifact Schemas）

下列四份 schema 以 yaml 围栏块定义字段形状（`path_id` 留空为模板占位）。字段语义标注其单一事实源章节；schema 不含任何数值。

### 2.1 S1→S2 工作路径单（Path Sheet）

router 产出。schema 的机器可读单一事实源为 `src/path_sheet.py`（字段对齐 [work-path-registry.md](work-path-registry.md) §三）。

```yaml
role: ""                    # M0|M1|M2|M3|M4|M5|meta
object: ""                  # single-issuer|portfolio|industry|market|meta
depth: ""                   # L0|L1|L2|专项
mode: ""                    # A=仅公开数据 / B=用户显式提供外部数据源
path_id: ""                 # join key：注册表中已存在的工作路径 ID
engine_reading_order: []    # 该路径注册的引擎文档序列（单一事实源）
quality_gates: []           # "规则名 (engine/<doc>.md §节)"
notes: ""
```

### 2.2 S2→S3 分析产物（Analysis Artifact）

fixed-income-credit-analysis 产出。密度/完备性语义以 [mosaic-engine.md](mosaic-engine.md) §4.3/§五 为单一事实源；一票否决语义以 [industry-framework.md](industry-framework.md) §五 为单一事实源；系统读数语义以 [systemic-warning-framework.md](systemic-warning-framework.md) §三 与 [concentration-framework.md](concentration-framework.md) 为单一事实源。

```yaml
path_id: ""                 # join key（承自路径单，不得更改）
mode: ""                    # A|B（承自路径单）
findings:                   # 每个引擎文档/范式一组发现
  - engine_doc: ""          # engine/<doc>.md（该组发现的规则源）
    paradigm: ""            # 六范式+LGFV 之一，或 n/a
    signals: []             # 提取的信号（优先级语义见 output-layered-framework §六）
    scores: []              # 维度评分；密度低于下限的维度置 null → 信息不足无法评估
completeness:               # 完备性（口径见 mosaic-engine §4.3/§五）
  density_pct: ""           # 信号密度（阈值不复制，见 mosaic-engine §4.3）
  confidence: ""            # 高|中|低
  data_gaps: []             # 缺口清单（缺口→风险映射见 mosaic-engine §5.2）
veto:                       # 一票否决（口径见 industry-framework §五）
  triggered: false
  ceiling: ""               # 触发时的评级上限（档位值不复制）
system_readouts:            # 系统智能层读数；仅 M4/全市场路径有值，否则 null
  sri:
    value: ""               # SRI 读数（区间见 systemic-warning-framework §三）
    thermometer: ""         # 温度计档位（四级定义见 systemic-warning-framework §三）
  concentration:
    score: ""               # 五维集中度评分（口径见 concentration-framework）
    adjustment: ""          # 集中度对评级的调整（见 concentration-framework）
    bb_cap: ""              # 集中度上限（见 concentration-framework）
mode_b_gaps: []             # Mode B 未激活时的外部数据缺口（护栏见 mosaic-engine §六）
```

### 2.3 S3→S4 交付单（Delivery Note）

credit-report-builder 产出。模板选择以 [work-path-registry.md](work-path-registry.md) 该路径 `templates` 字段为单一事实源；L0/L1/L2 分层语义以 [output-layered-framework.md](output-layered-framework.md) §二/§三/§五 为单一事实源。

```yaml
path_id: ""                 # join key（承自路径单，不得更改）
depth: ""                   # L0|L1|L2|专项（承自路径单）
templates_used: []          # 该路径 registry templates 字段选中的模板（单一事实源）
rendered: []                # 实际产出的报告文件（来自 templates/）
tier_mapping:               # 分析产物 → L0/L1/L2 层（语义见 output-layered-framework §二/§三/§五）
  L0: ""
  L1: ""
  L2: ""
completeness_lamp: ""       # 完备性灯号（口径见 output-layered-framework §8.4）
source_analysis: ""         # 上游分析产物引用（溯源）
```

### 2.4 S4 质检裁决（QA Verdict，终态）

credit-qa-verifier 产出，为四段链终态。逐质量门复核承自路径单 `quality_gates`；四项强制检查的规则源见所引引擎文档章节。

```yaml
path_id: ""                 # join key（承自路径单，不得更改）
verdict: ""                 # pass|pass-with-findings|fail
gate_results:               # 逐质量门复核结果
  - gate: ""                # "规则名 (engine/<doc>.md §节)"（承自路径单 quality_gates）
    status: ""              # pass|fail
    evidence: ""            # 复核证据（引用引擎文档章节，不复制数值）
mandatory_checks:           # 强制检查（规则源见各引擎文档）
  density_rule: ""          # 信号密度规则（mosaic-engine §4.3）
  veto_ceiling: ""          # 一票否决评级上限（industry-framework §五）
  mode_b: ""                # Mode B 防幻觉护栏（mosaic-engine §六）
  single_source: ""         # 单一事实源合规（不编造阈值）
remediation: []             # 不通过项的整改建议
```

## 三、链式边（Chaining Edges，机器可读）

下列边是 [work-path-registry.md](work-path-registry.md) §五 链式规则的机器可读化，字段为 `id` / `from` / `to` / `trigger` / `source_doc_ref`。本契约只固化**何时切换/重跑路径**的拓扑结构；各触发量的数值语义一律以 `source_doc_ref` 指向的引擎文档章节为最终裁决，此处不复制。

- 升级触发（深度上调）：L0→L1、L1→L2 的层级语义见 [output-layered-framework.md](output-layered-framework.md) §二/§三/§四。
- 监控触发（重跑条件）：M4 组合路径在温度计/迁移矩阵事件下重跑，档位语义见 [systemic-warning-framework.md](systemic-warning-framework.md) §三 与 [outlook-monitoring-framework.md](outlook-monitoring-framework.md) §四/§五。

**链式接续规则（交互点预算，全链单一事实源）**：四段链经 S1 Step 5 意图确认后**自动跑完**——阶段间切换（S1→S2→S3→S4）与 qa `fail` 的一轮回退整改均为自动接续，无需用户指令。全链仅允许 3 个用户交互点：

1. S1 Step 5 意图确认卡（必经；确认后不再设任何中途确认点）；
2. Mode B 数据缺口澄清（用户未显式提供数据源时的真实缺口）；
3. qa `fail` 且一轮自动整改后仍 `fail`（向用户出示裁决与整改选项）。

qa `pass` / `pass-with-findings` 直接回执并结束；任何阶段不得就"是否生成报告/做成哪种形式/是否质检/是否继续"发起用户询问——报告模板由注册表 `templates` 字段决定，质检是链的必经终态。各 SKILL.md 的 Chaining/Guardrails 与本规则保持一致表述。

```yaml
chaining_edges:
  - id: edge-l0-to-l1-upgrade
    from: WP-M3-01
    to: [WP-M1-01]
    trigger: L0 信号卡浮现红色（高优先级）信号
    source_doc_ref: engine/output-layered-framework.md §三、§四
  - id: edge-l1-to-l2-upgrade
    from: WP-M1-01
    to: [WP-M0-01]
    trigger: L1 快照内部评级与外部评级相差≥2子级
    source_doc_ref: engine/output-layered-framework.md §四
  - id: edge-m4-monthly-sri-rerun
    from: WP-M4-03
    to: [WP-M4-01, WP-M4-02]
    trigger: 月度 SRI 温度计档位上升时，对组合内高传染/高集中行业重跑集中度与传染
    source_doc_ref: engine/systemic-warning-framework.md §三
  - id: edge-migration-matrix-rerun
    from: WP-X-05
    to: []            # 开放集合：注册表 §五 未枚举，仅述"相关 M4 组合路径"，故不在此硬编码
    to_ref: engine/work-path-registry.md §五
    trigger: 持续监控命中触发条件（观察名单/展望调整）或迁移矩阵展望变化时，重跑 WP-X-05 并联动相关组合路径复查
    source_doc_ref: engine/outlook-monitoring-framework.md §四、§五
```

> **拓扑说明**：`from`/`to` 均为注册表中的工作路径 ID。`to` 为**列表**时表枚举的封闭联动集（如 `edge-m4-monthly-sri-rerun`，注册表 §五 明确"WP-M4-01 / WP-M4-02"）；`to` 为**空列表 + `to_ref`** 时表注册表未枚举的开放联动集，其具体集合以 `to_ref` 指向的注册表章节为准（如 `edge-migration-matrix-rerun` → §五 "相关 M4 组合路径"）。监控触发的"重跑"含自反（如 `edge-migration-matrix-rerun` 亦重跑 WP-X-05 自身）。

## 四、单一事实源声明

- 本契约定义四份产物的字段形状与链式边的拓扑结构，是四段链 I/O 的**唯一权威定义**；各 skill 文档引用本契约，不再各自重新定义产物结构。
- 本契约**不复制**任何阈值、SRI 温度计档位、L0/L1/L2 分层时间预算、信号优先级门槛或评级映射值。这些数值的单一事实源分别是：[mosaic-engine.md](mosaic-engine.md)（信号密度/完备性）、[industry-framework.md](industry-framework.md) §五（一票否决上限）、[systemic-warning-framework.md](systemic-warning-framework.md) §三（SRI 温度计）、[output-layered-framework.md](output-layered-framework.md) §二/§三/§五/§六（分层与优先级）、[dual-track-methodology.md](dual-track-methodology.md) §六（评级映射）、[concentration-framework.md](concentration-framework.md)（五维集中度）。
- 本契约如出现与上述引擎文档不一致之处，以引擎文档为准。路径拓扑（16 条路径的状态/`templates`/`engine_sequence`/`quality_gates`）以 [work-path-registry.md](work-path-registry.md) 为单一事实源。

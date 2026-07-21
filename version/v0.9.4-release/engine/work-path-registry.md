# 工作路径注册表

**版本**: v0.9.4-release | **日期**: 2026-07-15

本注册表是 v0.8.0 skill 架构重构（需求理解 → 路径路由 → 引擎调用 → 报告交付全程可控）的设计基线。它把"客户角色（M0-M5）× 调查方向 × 深度档 × 结论报告"的全部 16 条工作路径显式化、机器可读化，作为后续 Intake Router（v0.7.3）路由与执行层 skill 拆分（v0.7.4）的单一事实源。

**单一事实源原则**：本表只登记路径的"走哪几条引擎文档、用哪几个模板、过哪几道质量门"，不复制任何阈值/权重/规则正文——规则正文永远以 `engine_sequence` 指向的引擎文档为准。

## 目录

1. [路径状态定义](#路径状态定义)
2. [全量路径总览](#全量路径总览)
3. [路径 schema 定义](#路径-schema-定义)
4. [路径明细](#路径明细)
5. [链式规则（L0→L1→L2 升级与监控触发）](#链式规则l0l1l2-升级与监控触发)
6. [附录：待开发缺口清单](#附录待开发缺口清单)

## 一、路径状态定义

| 状态 | 标记 | 定义 |
|---|---|---|
| **active** | ✅ | 已实现：engine 文档 + 模板 + 走通案例齐全，可端到端交付 |
| **partial** | 🟡 | 部分实现：组件（engine 或模板）存在，但未串成显式路径（缺入口协议或质量门） |
| **planned** | 🔴 | 待开发：引擎/范式/模板缺失，仅角色需求已定义 |

## 二、全量路径总览

| ID | 路径名 | 角色 | 调查方向 | 深度 | 模板 | 状态 |
|---|---|---|---|---|---|---|
| WP-M0-01 | 信贷审批单标的评级 | M0 | 行业金字塔→马赛克→双轨→评级 | L2 | Type 1 + Type 6 | ✅ active |
| WP-M0-02 | 审贷专项附加包（LGD+外部支持） | M0 | lgd-recovery + external-support | 专项 | Type 8 + Type 9 | 🟡 partial |
| WP-M1-01 | 债券投资仪表盘 | M1 | M1 四维（相对价值/条款/流动性/事件） | L2 | Type 5 | ✅ active |
| WP-M1-02 | 双标的前瞻对比 | M1 | 双轨对比+区分度分析 | L2 | Type 2 | 🟡 partial |
| WP-M2-01 | 承销可行性评估 | M2 | 发行窗口+投资人匹配+可比定价 | 专项 | Type 16 | ✅ active |
| WP-M3-01 | 交易盯市信号卡 | M3 | L0 信号+SRI 温度计联动 | L0 | L0 规范 | 🟡 partial |
| WP-M4-01 | 组合集中度评估 | M4 | 五维集中度 | 专项 | Type 14 | ✅ active |
| WP-M4-02 | 跨行业传染分析 | M4 | 传染矩阵+传染理论 | 专项 | Type 13 | ✅ active |
| WP-M4-03 | 系统性风险读数 | M4 | SRI+温度计 | 专项 | Type 15 | ✅ active |
| WP-M4-04 | 组合压力测试 | M4 | 压力情景+财务深潜压力节 | 专项 | Type 11 | 🟡 partial |
| WP-M5-01 | 企业融资顾问 | M5 | 融资渠道对比+时机 | 专项 | Type 17 | ✅ active |
| WP-X-01 | 黑天鹅回溯验证 | 元（验证） | validation-methodology | 专项 | Type 3 | ✅ active |
| WP-X-02 | 多身份并行评估 | 元（对比） | M0/M1/M4 并行+交叉矩阵 | L2 | Type 4 | ✅ active |
| WP-X-03 | 行业分析框架建设 | 元（建设） | 新行业金字塔+D1-D10 | 专项 | Type 7 | ✅ active |
| WP-X-04 | ESG/治理风险扫描 | 专项 | esg + governance-fraud | 专项 | Type 10 | 🟡 partial |
| WP-X-05 | 展望与持续监控 | 专项 | outlook-monitoring+迁移矩阵 | 专项 | Type 18 | ✅ active |

> 状态分布：✅ active 11 条 · 🟡 partial 5 条 · 🔴 planned 0 条。待开发缺口见 [附录](#附录待开发缺口清单)。

## 三、路径 schema 定义

每条路径在 [路径明细](#路径明细) 中以 ```yaml 围栏块注册，字段如下：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径唯一标识，格式 `WP-(M[0-5]\|X)-\d{2}`（M0-M5 为客户角色，X 为元/专项路径） |
| `name` | string | 是 | 路径中文名 |
| `status` | enum | 是 | `active` \| `partial` \| `planned`（见 [路径状态定义](#路径状态定义)） |
| `role` | enum | 是 | `M0` \| `M1` \| `M2` \| `M3` \| `M4` \| `M5` \| `meta`（meta 用于验证/对比/建设/专项等跨角色路径） |
| `trigger` | map | 是 | 触发条件（router 匹配用），含两个子字段：`user_intent`（用户意图关键词数组）与 `object`（分析对象） |
| `trigger.user_intent` | string[] | 是 | 用户意图关键词，router 据此匹配自然语言需求 |
| `trigger.object` | enum | 是 | `single-issuer` \| `portfolio` \| `industry` \| `market` \| `meta` |
| `depth` | enum | 是 | `L0` \| `L1` \| `L2` \| `专项`（输出深度档，对应 output-layered-framework 三层 + 专项） |
| `engine_sequence` | string[] | 是 | 引擎文档调用序列（相对仓库根路径，单一事实源，不复制内容）。planned 路径可为空数组 `[]` |
| `paradigm_selection` | string | 是 | 行业范式选择说明（六范式+LGFV 按行业映射表；不适用时填 `n/a` 及原因） |
| `templates` | string[] | 是 | 报告模板（相对仓库根路径）或下列允许的标记值之一 |
| `outputs` | string[] | 是 | 该路径的交付物清单 |
| `quality_gates` | string[] | 是 | 质量门，格式 `规则名 (文档路径 §节)`；planned 路径可为空数组 `[]` |

**`templates` 允许的非文件标记值**（除真实模板文件路径外，仅允许以下两种标记，用于登记尚未落地的模板）：

| 标记 | 含义 | 示例 |
|---|---|---|
| `planned` | 模板待开发（无文件），配合 planned/partial 状态使用 | `planned` |
| `L0-spec: <规范文档> §节` | 无独立模板文件，规范定义于所引引擎文档 | `L0-spec: engine/output-layered-framework.md §3` |

**`quality_gates` 溯源约定**：`规则名`（` (` 之前的部分）必须是所引 `engine_sequence` 任一文档中真实存在的关键字，可由 grep 溯源（测试 T2.7 强制校验 active 路径）。`§节` 为人工阅读定位用的章节号，不参与机器校验。

## 四、路径明细

### WP-M0-01 信贷审批单标的评级（✅ active）

最核心路径：银行客户经理/信审对单一发行人做信贷审批评级。沿"行业金字塔定性评分 → 马赛克引擎信号提取与完备性评估 → 双轨交叉对撞 → 评级映射"全链路走通，交付评级+信号与数据完备性报告。已有永煤、紫光、华晨等走通案例。

```yaml
id: WP-M0-01
name: 信贷审批单标的评级
status: active
role: M0
trigger:
  user_intent: [能不能贷, 授信额度, 审贷, 放贷, 信用评级]
  object: single-issuer
depth: L2
engine_sequence:
  - engine/industry-framework.md
  - engine/mosaic-engine.md
  - engine/dual-track-methodology.md
paradigm_selection: 六范式+LGFV（按行业映射表）
templates:
  - templates/template-type1.html
  - templates/template-type6.html
outputs: [评级+信号, 完备性报告]
quality_gates:
  - "信号密度 (engine/mosaic-engine.md §4.3)"
  - "一票否决 (engine/industry-framework.md §五)"
  - "交叉对撞 (engine/dual-track-methodology.md §四)"
```

### WP-M0-02 审贷专项附加包（LGD+外部支持）（🟡 partial）

审贷的专项加深包：在 WP-M0-01 主体评级之上，追加违约损失率（LGD）与外部支持两个专项模块，用于债项评级、增信评估与支持上调判断。两个引擎文档齐备，但尚未串成带入口协议与质量门的显式附加路径。

```yaml
id: WP-M0-02
name: 审贷专项附加包（LGD+外部支持）
status: partial
role: M0
trigger:
  user_intent: [违约损失率, LGD, 回收率, 外部支持, 政府支持, 增信]
  object: single-issuer
depth: 专项
engine_sequence:
  - engine/lgd-recovery-framework.md
  - engine/external-support-framework.md
paradigm_selection: n/a（专项附加模块，在主体评级之上叠加，不重新选择范式）
templates:
  - templates/template-type8.html
  - templates/template-type9.html
outputs: [LGD等级+回收率, 外部支持调整建议]
quality_gates:
  - "LGD五级分类 (engine/lgd-recovery-framework.md §二)"
  - "支持能力 (engine/external-support-framework.md §三)"
```

### WP-M1-01 债券投资仪表盘（✅ active）

债券投资者对单只券的投资决策：M1 四维框架（相对价值/条款保护/流动性/事件日历）加权评分，输出投资建议。已在隆基 vs 一道等案例中走通，配 Type 5 仪表盘模板。

```yaml
id: WP-M1-01
name: 债券投资仪表盘
status: active
role: M1
trigger:
  user_intent: [这只券怎么样, 便不便宜, 相对价值, 值不值得买, 投资仪表盘]
  object: single-issuer
depth: L2
engine_sequence:
  - engine/multi-stakeholder.md
paradigm_selection: n/a（M1 四维框架按券种评估，不按行业范式）
templates:
  - templates/template-type5.html
outputs: [四维评分, 投资建议]
quality_gates:
  - "四维 (engine/multi-stakeholder.md §二)"
  - "相对价值 (engine/multi-stakeholder.md §2.2)"
```

### WP-M1-02 双标的前瞻对比（🟡 partial）

投资视角的双标的横向对比：用双轨方法论对两个发行人做前瞻对比与区分度分析，回答"买哪只"。双轨与验证方法论（前瞻对比/区分度）均已就位，但作为独立投资路径尚未显式化。

```yaml
id: WP-M1-02
name: 双标的前瞻对比
status: partial
role: M1
trigger:
  user_intent: [两只券对比, 哪个更好, 前瞻对比, 区分度, 二选一]
  object: single-issuer
depth: L2
engine_sequence:
  - engine/dual-track-methodology.md
  - engine/validation-methodology.md
paradigm_selection: 六范式+LGFV（两标的各自按行业映射表确定范式）
templates:
  - templates/template-type2.html
outputs: [对比评分, 区分度结论]
quality_gates:
  - "前瞻对比 (engine/validation-methodology.md §四)"
  - "区分度 (engine/validation-methodology.md §4.2)"
```

### WP-M2-01 承销可行性评估（✅ active）

承销商视角：评估某发行人债券的承销可行性——发行窗口判断、投资人匹配、可比券定价。m2-underwriting-framework + Type 16 模板齐备（v0.9.0 激活）。

```yaml
id: WP-M2-01
name: 承销可行性评估
status: active
role: M2
trigger:
  user_intent: [能不能承销, 发行窗口, 可比定价, 投资人匹配, 簿记]
  object: single-issuer
depth: 专项
engine_sequence:
  - engine/m2-underwriting-framework.md
paradigm_selection: n/a（承销评估跨范式，按券种与发行人评级档位）
templates:
  - templates/template-type16.html
outputs: [承销可行性结论, 定价区间]
quality_gates:
  - "发行窗口 (engine/m2-underwriting-framework.md §二)"
  - "可比定价 (engine/m2-underwriting-framework.md §四)"
```

### WP-M3-01 交易盯市信号卡（🟡 partial）

交易员视角的轻量盯市：L0 信号卡（5 秒速览：评级+展望+今日关键信号）联动 SRI 系统性预警温度计。L0 规范与温度计引擎齐备，但 L0 信号卡无独立模板文件（规范定义于 output-layered-framework §3），且 M3 交易框架仍待补全。

```yaml
id: WP-M3-01
name: 交易盯市信号卡
status: partial
role: M3
trigger:
  user_intent: [盯市, 交易信号, 今日异动, 信号卡, 盘中预警]
  object: single-issuer
depth: L0
engine_sequence:
  - engine/output-layered-framework.md
  - engine/systemic-warning-framework.md
paradigm_selection: n/a（L0 信号层跨范式，直接读取单标的评级+系统温度计）
templates:
  - "L0-spec: engine/output-layered-framework.md §3"
outputs: [L0信号卡, 温度计读数]
quality_gates:
  - "L0 信号卡 (engine/output-layered-framework.md §三)"
  - "温度计 (engine/systemic-warning-framework.md §三)"
```

### WP-M4-01 组合集中度评估（✅ active）

组合风控视角：对债券组合做五维集中度（行业/区域/评级/期限/融资渠道）评估，输出集中度评分与调整建议。concentration-framework 完整实现，配 Type 14 模板。

```yaml
id: WP-M4-01
name: 组合集中度评估
status: active
role: M4
trigger:
  user_intent: [组合集中度, 行业占比, 区域集中, 集中度风险, 组合分散]
  object: portfolio
depth: 专项
engine_sequence:
  - engine/concentration-framework.md
paradigm_selection: n/a（组合维度跨范式聚合，按持仓行业分布映射）
templates:
  - templates/template-type14.html
outputs: [五维集中度评分, 集中度调整建议]
quality_gates:
  - "五维集中度 (engine/concentration-framework.md §一)"
  - "阈值体系 (engine/concentration-framework.md §2.2)"
```

### WP-M4-02 跨行业传染分析（✅ active）

组合风控视角：用 13×13 传染矩阵 + 传染理论分析组合内跨行业传导风险，识别高传染链路与升级因子，输出传染路径图谱与调整建议。配 Type 13 模板。

```yaml
id: WP-M4-02
name: 跨行业传染分析
status: active
role: M4
trigger:
  user_intent: [传染, 连带风险, 行业传导, 传染矩阵, 风险蔓延]
  object: portfolio
depth: 专项
engine_sequence:
  - engine/contagion-matrix.md
  - engine/contagion-theory.md
paradigm_selection: n/a（传染矩阵跨范式，按行业对传导）
templates:
  - templates/template-type13.html
outputs: [传染路径图谱, 传染调整建议]
quality_gates:
  - "传染矩阵 (engine/contagion-matrix.md §二)"
  - "升级因子 (engine/contagion-matrix.md §6.1)"
  - "传导路径 (engine/contagion-theory.md §三)"
```

### WP-M4-03 系统性风险读数（✅ active）

组合/全市场视角：聚合多源信号计算 SRI（系统性风险指数），给出四级温度计读数。systemic-warning-framework 完整实现（含历史回测），配 Type 15 模板。

```yaml
id: WP-M4-03
name: 系统性风险读数
status: active
role: M4
trigger:
  user_intent: [系统性风险, SRI, 温度计, 市场风险, 大盘风险]
  object: market
depth: 专项
engine_sequence:
  - engine/systemic-warning-framework.md
paradigm_selection: n/a（系统性聚合，跨范式）
templates:
  - templates/template-type15.html
outputs: [SRI读数, 温度计等级]
quality_gates:
  - "信号聚合 (engine/systemic-warning-framework.md §二)"
  - "温度计四级 (engine/systemic-warning-framework.md §三)"
```

### WP-M4-04 组合压力测试（🟡 partial）

组合风控视角：对组合施加压力情景（五维阈值跳升 + 财务深潜压力节），评估极端情景下的损失。concentration-framework 压力节与 financial-deep-dive 场景敏感性矩阵齐备，但尚未串成显式压力测试路径。

```yaml
id: WP-M4-04
name: 组合压力测试
status: partial
role: M4
trigger:
  user_intent: [压力测试, 极端情景, 组合压力, 敏感性, 压力情景]
  object: portfolio
depth: 专项
engine_sequence:
  - engine/concentration-framework.md
  - engine/financial-deep-dive.md
paradigm_selection: n/a（压力情景跨范式）
templates:
  - templates/template-type11.html
outputs: [压力情景损失, 阈值跳升结果]
quality_gates:
  - "压力测试 (engine/concentration-framework.md §九)"
  - "场景敏感性 (engine/financial-deep-dive.md §E)"
```

### WP-M5-01 企业融资顾问（✅ active）

企业（发行人）视角的反向应用：对比融资渠道（发债/贷款/非标）、判断融资时机与成本。m5-financing-advisor-framework + Type 17 模板齐备（v0.9.0 激活）。

```yaml
id: WP-M5-01
name: 企业融资顾问
status: active
role: M5
trigger:
  user_intent: [融资渠道, 发债还是贷款, 融资时机, 融资成本, 怎么融资]
  object: single-issuer
depth: 专项
engine_sequence:
  - engine/m5-financing-advisor-framework.md
paradigm_selection: n/a（融资顾问跨范式，按主体评级档位与资金用途）
templates:
  - templates/template-type17.html
outputs: [融资渠道对比, 时机建议]
quality_gates:
  - "渠道选择 (engine/m5-financing-advisor-framework.md §二)"
  - "时机判断 (engine/m5-financing-advisor-framework.md §三)"
```

### WP-X-01 黑天鹅回溯验证（✅ active）

元路径（验证）：用历史违约/黑天鹅事件做双时点回溯验证，检验框架能否在违约前给出预警信号，输出验证结论与框架改进建议。validation-methodology 完整实现（永煤/紫光等），配 Type 3 模板。

```yaml
id: WP-X-01
name: 黑天鹅回溯验证
status: active
role: meta
trigger:
  user_intent: [回溯验证, 历史违约, 黑天鹅, 框架有效性, 事后检验]
  object: meta
depth: 专项
engine_sequence:
  - engine/validation-methodology.md
paradigm_selection: n/a（验证方法论，复用被验证路径的范式选择）
templates:
  - templates/template-type3.html
outputs: [验证结论, 框架改进建议]
quality_gates:
  - "黑天鹅回溯 (engine/validation-methodology.md §一)"
  - "双时点 (engine/validation-methodology.md §三)"
```

### WP-X-02 多身份并行评估（✅ active）

元路径（对比）：对单一发行人以 M0/M1/M4 等多身份并行评估，构建交叉对比矩阵，处理共识与分歧。multi-stakeholder §3-4 定义标准流程（华晨案例验证），配 Type 4 模板。

```yaml
id: WP-X-02
name: 多身份并行评估
status: active
role: meta
trigger:
  user_intent: [多角度, 多身份, 并行评估, 交叉对比, 多方视角]
  object: single-issuer
depth: L2
engine_sequence:
  - engine/multi-stakeholder.md
paradigm_selection: 六范式+LGFV（按被评估标的行业映射表确定范式）
templates:
  - templates/template-type4.html
outputs: [多身份评分矩阵, 共识/分歧报告]
quality_gates:
  - "多身份并行 (engine/multi-stakeholder.md §四)"
  - "交叉对比矩阵 (engine/multi-stakeholder.md §3.2)"
```

### WP-X-03 行业分析框架建设（✅ active）

元路径（建设）：为新行业搭建分析框架——十维评分（D1-D10）定权重、确定范式归属、建行业金字塔。industry-framework 完整实现（七行业金字塔规格 + 一票否决），配 Type 7 模板。

```yaml
id: WP-X-03
name: 行业分析框架建设
status: active
role: meta
trigger:
  user_intent: [新行业, 建框架, 行业金字塔, 十维评分, 行业分析]
  object: industry
depth: 专项
engine_sequence:
  - engine/industry-framework.md
paradigm_selection: 六范式+LGFV（建设时确定新行业的范式归属）
templates:
  - templates/template-type7.html
outputs: [行业金字塔, D1-D10评分]
quality_gates:
  - "十维 (engine/industry-framework.md §二)"
  - "金字塔 (engine/industry-framework.md §四)"
  - "一票否决 (engine/industry-framework.md §五)"
```

### WP-X-04 ESG/治理风险扫描（🟡 partial）

专项路径：对发行人做 ESG（环境/社会/治理）与财务欺诈/治理风险扫描，输出 ESG 叠加调整与治理红旗清单。esg-framework 与 governance-fraud-risk 齐备，但尚未串成显式专项路径。

```yaml
id: WP-X-04
name: ESG/治理风险扫描
status: partial
role: meta
trigger:
  user_intent: [ESG, 治理风险, 财务造假, 欺诈, 逃废债]
  object: single-issuer
depth: 专项
engine_sequence:
  - engine/esg-framework.md
  - engine/governance-fraud-risk.md
paradigm_selection: n/a（ESG/治理为跨范式叠加层）
templates:
  - templates/template-type10.html
outputs: [ESG风险扫描, 治理红旗清单]
quality_gates:
  - "ESG (engine/esg-framework.md §一)"
  - "财务欺诈 (engine/governance-fraud-risk.md §一)"
  - "逃废债 (engine/governance-fraud-risk.md §四)"
```

### WP-X-05 展望与持续监控（✅ active）

专项路径：在评级之上给出 12-24 个月评级展望、维护 90 天观察名单、触发持续监控（含评级迁移矩阵）。outlook-monitoring-framework + Type 18 模板 + outlook_engine 编码引擎完整实现（v0.8.4 激活）。

```yaml
id: WP-X-05
name: 展望与持续监控
status: active
role: meta
trigger:
  user_intent: [评级展望, 持续监控, 观察名单, 迁移矩阵, 评级行动]
  object: single-issuer
depth: 专项
engine_sequence:
  - engine/outlook-monitoring-framework.md
paradigm_selection: n/a（展望与监控为跨范式机制）
templates:
  - templates/template-type18.html
outputs: [评级展望, 观察名单]
quality_gates:
  - "评级展望 (engine/outlook-monitoring-framework.md §二)"
  - "观察名单 (engine/outlook-monitoring-framework.md §三)"
  - "迁移矩阵 (engine/outlook-monitoring-framework.md §五)"
```

## 五、链式规则（L0→L1→L2 升级与监控触发）

本节登记路径之间的**升级触发**（浅层产出在何种信号下升级为更深一层路径）与**监控触发**（组合风控路径在何种事件下重跑）。本节只定义"何时切换/重跑路径"，不定义任何一层本身的语义与数值——单一事实源如下，本节不复制其中任何数值、亦不新增任何数值阈值（唯一的触发量"≥2 子级"沿用 §四 评级对比中既有的子级口径）：

- L0/L1/L2 三层输出的定义、消费时间与信息密度，以 [output-layered-framework](output-layered-framework.md) §二（三层输出体系总览）为单一事实源；
- L0 信号卡与红色优先级信号的语义，以 [output-layered-framework](output-layered-framework.md) §三（L0 信号卡）为单一事实源；
- 评级对比与"子级"分歧的语义，以 [output-layered-framework](output-layered-framework.md) §四（L1 快照·评级对比）为单一事实源；
- 信号优先级的数值过滤门槛，以 [output-layered-framework](output-layered-framework.md) §六（信息优先级排序）为单一事实源；
- SRI 温度计四级档位的数值区间，以 [systemic-warning-framework](systemic-warning-framework.md) §三（温度计四级体系）为单一事实源。

### 升级触发（深度上调）

| 升级 | 触发条件 | 目标路径（示例） | 依据（单一事实源） |
|---|---|---|---|
| **L0 → L1** | L0 信号卡浮现**红色（高优先级）信号** | WP-M3-01 → WP-M1-01 | output-layered-framework §三、§四 |
| **L1 → L2** | L1 快照内部评级与外部评级相差 **≥2 子级** | WP-M1-01 → WP-M0-01 | output-layered-framework §四 |

- **L0 → L1 升级**：L0 信号卡只回答"这只券今天需要我关注吗"（§三）。一旦出现红色优先级信号，即存在需重点关注的事项，应升级为 L1 快照，用四维雷达图与关键异常列表定位风险点。
- **L1 → L2 升级**：当 L1 快照的评级对比显示内部评级与外部评级相差 ≥2 子级时，说明引擎判断与市场/评级机构存在值得深挖的分歧，应升级为 L2 深度报告，以金字塔逐层分析与双轨对撞支撑授信/投资决策。（≥2 为保守上沿：§四 将 ≤2 子级标为"基本一致/互相验证"，此处取保守触发以尽早深挖；升级触发是"何时投入更深分析"的工作流判断，与 §四 的展示标签是两条不同坐标，语义裁决仍以 §四 为准。）

### 监控触发（重跑条件）

组合风控（M4）路径不是一次性产出，而在下列事件下重跑。温度计档位本身不新增阈值，直接引用 [systemic-warning-framework](systemic-warning-framework.md) §三 的四级定义与行动建议。

| 触发源 | 触发事件 | 重跑路径 | 依据（单一事实源） |
|---|---|---|---|
| **月度 SRI 读数** | 每月对组合读取一次系统性风险温度计，档位上升时 | WP-M4-03 → 联动 WP-M4-01 / WP-M4-02 | systemic-warning-framework §三 |
| **迁移矩阵展望变化** | 持续监控命中触发条件（进入观察名单/展望调整），或迁移矩阵显示展望变化 | WP-X-05 → 联动相关 M4 组合路径复查 | outlook-monitoring-framework §四、§五 |

- **月度 SRI 读数**：每月读取一次系统性风险温度计（WP-M4-03）。当温度计档位上升时，按 systemic-warning-framework §三 对应档位的行动建议，对组合内高传染/高集中行业重跑 WP-M4-01（集中度）与 WP-M4-02（传染）。档位区间与行动建议以该文档 §三 为准。
- **迁移矩阵展望变化**：当 [outlook-monitoring-framework](outlook-monitoring-framework.md) §四 的持续监控触发机制命中（如进入观察名单、展望调整），或 §五 迁移矩阵显示评级展望发生变化时，重跑 WP-X-05 并联动相关组合路径复查。

> **单一事实源声明**：本节引用的层级语义、信号门槛与温度计档位，一律以上述三份引擎文档的对应章节为最终裁决。本节如出现与之不一致之处，以引擎文档为准。

## 六、附录：待开发缺口清单

下列 🔴 缺口是后续版本（v0.7.3+）的开发清单，每条标注缺失组件与受影响路径：

| # | 缺口 | 缺失组件类型 | 受影响路径 | 备注 |
|---|---|---|---|---|
| 1 | M2 承销框架 engine 文档 | engine | WP-M2-01 | ✅ 已交付（v0.9.0，m2-underwriting-framework.md） |
| 2 | M5 融资顾问框架 engine 文档 | engine | WP-M5-01 | ✅ 已交付（v0.9.0，m5-financing-advisor-framework.md） |
| 3 | M3 交易框架补全 | engine | WP-M3-01 | 交易盯市专用引擎（当前仅 L0 规范+温度计，partial） |
| 4 | Type 16 承销报告模板 | 模板 | WP-M2-01 | ✅ 已交付（v0.9.0，template-type16.html） |
| 5 | Type 17 融资顾问模板 | 模板 | WP-M5-01 | ✅ 已交付（v0.9.0，template-type17.html） |
| 6 | 展望监控模板 | 模板 | WP-X-05 | ✅ 已交付（v0.8.4，template-type18.html） |

> 演进追踪：每次版本发布应更新本表状态分布（🔴→🟡→✅），并在 engine-overview.md §六 版本历史中登记。

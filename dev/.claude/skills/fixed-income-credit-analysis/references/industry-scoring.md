# Industry Scoring (Track A)

**版本**: v0.9.2-release

> 本文自 `fixed-income-credit-analysis` SKILL.md 下沉而来，组织 Track A 行业评分相关内容（行业金字塔 / 六范式 / 十维评分 / 行业筛选）。阈值、权重与一票否决条件的单一事实源为 `dev/engine/industry-framework.md`；本文件仅作导航与组织，不引入新数值。

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

六个范式 + LGFV 特殊类别与 M0–M5 角色的**可寻址维度索引**见 `dev/engine/dimension-registry.md`（每个维度的 id、定义指针、适用行业与消费路径）；本文件不复制其定义或阈值。

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

# 维度注册表

**版本**: v0.8.3-release | **日期**: 2026-07-16

本注册表把引擎的**分析维度**物件化（objectify）为可寻址（addressable）的机器可读条目：**6 个分析范式 + 1 个 LGFV 特殊类别**，以及 **6 类利益相关者角色（M0–M5）**。它是 v0.8.0 skill 架构中"按维度路由/检索"的统一索引层。

**单一事实源原则**：本表是一个**指针层（pointer layer）**——它只把每个维度登记为一个可寻址条目（id + 指向定义文档的指针 + 适用行业 + 被哪些工作路径消费），**不复制任何定义正文、阈值或权重**。每个维度的判定条件、金字塔权重、一票否决等规则正文，永远以 `definition` 指针所引用的引擎文档对应章节为最终裁决；本表如出现与之不一致之处，以引擎文档为准。

## 目录

1. [分析范式维度（dimensions）](#一分析范式维度dimensions)
2. [利益相关者角色维度（roles）](#二利益相关者角色维度roles)
3. [schema 与溯源约定](#三schema-与溯源约定)

## 一、分析范式维度（dimensions）

每个条目对应一个分析范式（A–F）或 LGFV 特殊类别。`industries` 反映该行业在传染矩阵中的**主要范式**归属（单一事实源：[contagion-matrix.md](contagion-matrix.md) §1.2 范式映射表）；次要范式属性（如半导体兼具范式B、生物医药兼具范式A、数据中心兼具范式F）不在本表展开，以该映射表"次要范式"列为准。

```yaml
dimensions:
  - id: paradigm-A
    name: 政策驱动型
    letter: A
    definition: 政策驱动型 (dev/engine/industry-framework.md §三)
    standalone_doc: embedded in dev/engine/industry-framework.md §三（判定）与 §四（金字塔权重）
    industries: [光伏/储能, 半导体/集成电路]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: paradigm-B
    name: 技术壁垒型
    letter: B
    definition: 技术壁垒型 (dev/engine/industry-framework.md §三)
    standalone_doc: embedded in dev/engine/industry-framework.md §三（判定）与 §四（金字塔权重）
    industries: [高端装备/工业母机, 生物医药/创新药, 医疗器械]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: paradigm-C
    name: 存量博弈型
    letter: C
    definition: 存量博弈型 (dev/engine/industry-framework.md §三)
    standalone_doc: embedded in dev/engine/industry-framework.md §三（判定）与 §四（金字塔权重）
    industries: [新能源汽车]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: paradigm-D
    name: 资产租约型
    letter: D
    definition: 资产租约型 (dev/engine/industry-framework.md §三)
    standalone_doc: embedded in dev/engine/industry-framework.md §三（判定）与 §四（金字塔权重）
    industries: [数据中心/算力基建]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: paradigm-E
    name: 品牌+渠道型
    letter: E
    definition: 品牌+渠道型 (dev/engine/paradigm-brand-channel.md §一)
    standalone_doc: dev/engine/paradigm-brand-channel.md
    industries: [食品饮料, 纺织服装]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: paradigm-F
    name: 网络+流量型
    letter: F
    definition: 网络+流量型 (dev/engine/paradigm-network-traffic.md §一)
    standalone_doc: dev/engine/paradigm-network-traffic.md
    industries: [交通运输, 商贸零售, 传媒/互联网]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]

  - id: lgfv
    name: 政府信用绑定型
    letter: 特殊
    definition: 政府信用绑定型 (dev/engine/industry-framework.md §七)
    standalone_doc: dev/engine/lgfv-framework.md
    industries: [城投债 / LGFV]
    used_by_paths: [WP-M0-01, WP-M1-02, WP-X-02, WP-X-03]
```

## 二、利益相关者角色维度（roles）

每个条目对应一类利益相关者角色（M0–M5）。角色的核心决策问题、决策时域、关键数据需求等定义，单一事实源为 [multi-stakeholder.md](multi-stakeholder.md) §一（六类利益相关者总览）。`used_by_paths` 按工作路径注册表中各路径的 `role` 字段归集。

```yaml
roles:
  - id: role-M0
    name: 审贷
    definition: 信贷审批 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M0-01, WP-M0-02]

  - id: role-M1
    name: 投资
    definition: 债券投资 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M1-01, WP-M1-02]

  - id: role-M2
    name: 承销
    definition: 债券承销 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M2-01]

  - id: role-M3
    name: 交易
    definition: 市场交易 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M3-01]

  - id: role-M4
    name: 风控
    definition: 组合风控 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M4-01, WP-M4-02, WP-M4-03, WP-M4-04]

  - id: role-M5
    name: 融资
    definition: 企业融资 (dev/engine/multi-stakeholder.md §一)
    used_by_paths: [WP-M5-01]
```

## 三、schema 与溯源约定

### 维度条目字段（dimensions）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 维度唯一标识：`paradigm-{A..F}` 或 `lgfv` |
| `name` | string | 维度中文名（政策驱动型/技术壁垒型/存量博弈型/资产租约型/品牌+渠道型/网络+流量型/政府信用绑定型） |
| `letter` | string | 范式字母 `A`–`F`，LGFV 特殊类别填 `特殊` |
| `definition` | string | 定义指针，格式 `关键字 (文档路径 §节)`（见下方溯源约定） |
| `standalone_doc` | string | 完整规格所在：独立范式文档的仓库根相对路径，或 `embedded in …`（表示规格内嵌于 industry-framework.md） |
| `industries` | string[] | 该范式作为主要范式覆盖的行业（与 contagion-matrix.md §1.2 主范式列一致） |
| `used_by_paths` | string[] | 消费该维度的工作路径 id（work-path-registry.md） |

### 角色条目字段（roles）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 角色唯一标识：`role-M{0..5}` |
| `name` | string | 角色中文名（审贷/投资/承销/交易/风控/融资） |
| `definition` | string | 定义指针，格式 `关键字 (文档路径 §节)`（见下方溯源约定） |
| `used_by_paths` | string[] | 该角色作为 `role` 的工作路径 id（work-path-registry.md） |

### `definition` 溯源约定

`definition` 字段遵循与工作路径注册表 `quality_gates` 相同的溯源惯例：` (` 之前的**关键字**必须是所引文档中真实存在、可由 grep 溯源的词条（由一致性测试强制校验）；括号内为 `文档仓库根相对路径 + §节`，`§节` 仅供人工阅读定位，不参与机器校验。

### `used_by_paths` 归集口径

- **范式维度**：工作路径注册表的 `paradigm_selection` 字段以"六范式+LGFV（按行业映射表）"整体引用范式集合（而非逐个范式点名），故所有选择该映射表的范式消费路径——WP-M0-01、WP-M1-02、WP-X-02、WP-X-03——对每个范式维度均计入。`paradigm_selection` 为 `n/a` 或 `待定` 的路径不消费范式维度。
- **角色维度**：按工作路径注册表各路径的 `role` 字段直接归集；`role: meta` 的跨角色路径（WP-X-*）不归属于任一 M0–M5 角色维度。

> **推迟项（back-reference）**：原计划可选改动"work-path-registry 的 `paradigm_selection` 可引维度 ID"（路径→维度的反向指针）**本版本未实施**。因注册表的 `paradigm_selection` 以"六范式+LGFV"整体引用范式集合（集体粒度，而非逐范式点名），反向指针无法比现有 `used_by_paths` 提供更细粒度，故维持现状。维度→路径的正向归集（本节口径 + 一致性测试强制对账）已满足路由寻址需求；若未来 `paradigm_selection` 改为逐范式点名，再回补反向指针。

## 相关内容

- [行业分类与分析框架](industry-framework.md) — 四种行业范式判定（§三）· 七行业金字塔规格（§四）· 各行业类型判定（§七）
- [品牌+渠道型分析范式](paradigm-brand-channel.md) — 范式E 完整规格（食品饮料·纺织服装）
- [网络+流量型分析范式](paradigm-network-traffic.md) — 范式F 完整规格（交运·零售·传媒互联网）
- [城投债分析框架](lgfv-framework.md) — LGFV 特殊类别完整规格
- [13行业传染矩阵](contagion-matrix.md) — §1.2 范式映射表（行业→主要/次要范式）
- [多利益相关者视角框架](multi-stakeholder.md) — M0–M5 角色定义（§一）
- [工作路径注册表](work-path-registry.md) — 各路径的 role 与 paradigm_selection

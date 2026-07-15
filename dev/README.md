# 固收信贷智能分析引擎

**项目代号**: Credence
**版本**: v0.7.1-alpha
**状态**: 方法论文档阶段 · 产品设计完成 · 13行业覆盖 · 系统智能层上线 · 文档结构重整完成

---

## 项目概述

面向中国固定收益市场的智能分析引擎。通过行业定制化的多层分析金字塔、双轨交叉验证框架、马赛克公开数据引擎、多利益相关者视角、非信用风险叠加层和系统智能层，为信贷审批、债券投资、市场交易和风险管理提供超越传统财务分析的信用认知供给。覆盖13大行业（12产业+城投债），具备跨行业传染图谱、五维集中度仪表盘和系统性预警温度计。

**核心原则**：传统财务分析在政策驱动型、技术壁垒型和资产租约型行业中系统性失效。最重的信用因子很少出现在资产负债表上。外部信用评级平均滞后真实信用恶化17个月以上。

---

## 目录结构

```
dev/
├── README.md                                        ← 你在这里
├── engine/                                          → 算法与方法论（26份现行文档）
│   ├── engine-overview.md                          架构总览 · 文档导航
│   ├── industry-framework.md                       行业分类（十维评分·13行业金字塔）
│   ├── qualitative-analysis.md                     定性分析（信源·政策·马赛克·叙事）
│   ├── quantitative-analysis.md                    定量分析（利差·波动率·因子·压力·市场信号）
│   ├── dual-track-methodology.md                   双轨+交叉对撞·12档评级·EL整合·缓释建议
│   ├── mosaic-engine.md                            马赛克引擎（信号·拼图·完备性·Mode B）
│   ├── multi-stakeholder.md                        多利益相关者（M0-M6·集中度风险·系统智能层集成）
│   ├── validation-methodology.md                   验证方法论（黑天鹅回溯·双时点·前瞻对比）
│   ├── financial-deep-dive.md                      财务深度（三表联动·营运资金·FCF·压力测试）
│   ├── lgd-recovery-framework.md                   LGD回收率（五级·抵押物·回收路径）
│   ├── external-support-framework.md               外部支持（政府/集团/战投·能力vs意愿）
│   ├── outlook-monitoring-framework.md             展望+监控（展望·观察名单·持续监控·迁移矩阵）
│   ├── lgv-framework.md                            城投债（政府+平台双轨·四级分类）
│   ├── governance-fraud-risk.md                    治理/欺诈风险（20+信号·逃废债检测）
│   ├── esg-framework.md                            ESG + 治理/欺诈检测框架
│   ├── financial-bond-framework.md                 金融债分析框架
│   ├── holding-company-framework.md                控股公司信用分析框架
│   ├── non-credit-risk-overlay.md                  非信用风险叠加层（市场/操作/声誉/战略/流动性）
│   ├── false-positive-negative-testing.md          假阳性/假阴性测试（5案例实测）
│   ├── output-layered-framework.md                 分层输出（L0信号卡+L1快照+L2深度+温度计卡片）
│   ├── contagion-theory.md                         传染理论（四类型·七传导路径·升级因子）
│   ├── contagion-matrix.md                         ⭐13×13行业传染矩阵（传导强度·行业聚类）
│   ├── concentration-framework.md                  ⭐五维集中度分析框架（阈值·评级调整·压力测试）
│   ├── systemic-warning-framework.md               ⭐系统性预警框架（SRI信号聚合·温度计·历史回测）
│   ├── paradigm-brand-channel.md                   品牌+渠道范式（食品饮料·纺织服装）
│   ├── paradigm-network-traffic.md                 网络+流量范式（交运·零售·传媒互联网）
│   └── audits/                                     15份历史审查/审计归档
│
├── templates/                                       → 报告模板单一事实源（16文件）
│   ├── template-base.css                           共享样式基底
│   └── template-type1..15.html                     Type 1 - Type 15 报告模板
│
├── design/                                          → 报告设计体系
│   ├── report-style-system.md                      报告样式系统
│   └── archive/                                    4份历史规划/审计（v0.6/v0.7路线图·phase2/报告审计）
│
├── data/                                            → 数据架构
│   ├── data-architecture.md                        数据源分层·可达性验证·缺口映射
│   └── data-pipeline-spec.md                       数据管道规格
│
├── product/                                         → 产品设计
│   ├── product-overview.md                         产品愿景 · 魔法体验 · 用户画像
│   └── commercial-model.md                         商业化模型 · 买方模拟 · GTM策略
│
├── reports/                                         → 13行业信贷+系统智能+验证报告（共72份，15个子目录）
│   ├── solar/                                      光伏/储能（11份）
│   ├── semiconductor/                              半导体/集成电路（7份）
│   ├── equipment/                                  高端装备（3份）
│   ├── biomedicine/                                生物医药（3份）
│   ├── medicaldevice/                              医疗器械（3份）
│   ├── nev/                                        新能源汽车（4份）
│   ├── datacenter/                                 数据中心（3份）
│   ├── lgv/                                        城投债（6份）
│   ├── textile-apparel/                            纺织服装（4份）
│   ├── food-beverage/                              食品饮料（4份）
│   ├── transportation/                             交通运输（4份）
│   ├── retail/                                     零售（4份）
│   ├── media-internet/                             传媒互联网（4份）
│   ├── system-intelligence/                        ⭐系统智能（9份：4传染+3集中度+1预警+1验证统计）
│   └── validation/                                 验证报告（3份）
│
└── .claude/skills/fixed-income-credit-analysis/     → AI技能包（模板统一引用 dev/templates/）
```

---

## 当前进度

### 方法论验证（13/13 行业完成）

| 行业 | 验证类型 | 标杆 | 困境 | 区分度 |
|---|---|---|---|---|
| 光伏/储能 | 前瞻对比 | 隆基 7.00 (BBB+) | 一道新能 1.50 (CCC) | 5.50分 |
| 半导体/集成电路 | 回溯验证 | 紫光集团（T-17月） | — | L5全部红色 |
| 高端装备/工业母机 | 前瞻对比 | 科德数控 81.2% | 拓璞数控 36.6% | 11.15分 |
| 生物医药/创新药 | 前瞻对比 | 百济神州 8.11 | 迈威生物 4.57 | 3.54分 |
| 医疗器械 | 前瞻对比 | 迈瑞 7.88 (BBB+) | 万东 4.19 (B-) | 3.69分 |
| 新能源汽车 | 前瞻对比 | 比亚迪 6.52 / CATL 8.77 | 零跑 5.21 / 欣旺达 3.66 | 20%/58% |
| 数据中心/算力基建 | 前瞻对比 | 万国数据 7.46 | 世纪互联 5.36 | 2.10分 |
| 城投债(LGV) | 框架验证 | 杭州LGV 6.70 | 黔城LGV 3.80 | 2.90分 |
| 纺织服装 | 方法论+报告 | 安踏 | 困境标的 | 框架完成 |
| 食品饮料 | 方法论+报告 | 茅台 | 困境标的 | 框架完成 |
| 交通运输 | 方法论+报告 | 顺丰 | 困境标的 | 框架完成 |
| 零售 | 方法论+报告 | 京东 | 困境标的 | 框架完成 |
| 传媒互联网 | 方法论+报告 | 腾讯 | 困境标的 | 框架完成 |

### 系统智能层（v0.7.0 新增）

| 模块 | 状态 | 核心文档 |
|---|---|---|
| 传染图谱 | ✅ 完成 | contagion-theory.md · contagion-matrix.md · 4份复盘报告 |
| 集中度仪表盘 | ✅ 完成 | concentration-framework.md · 3份情景报告（Type 14） |
| 系统性预警 | ✅ 完成 | systemic-warning-framework.md · 当前时点SRI读数（Type 15） |
| 温度计L0卡片 | ✅ 完成 | 集成至output-layered-framework.md §3.6 |

### 报告与模板

| 类型 | 数量 | 说明 |
|---|---|---|
| 行业信用报告 | 60份 · 13行业 × 多标的 | 覆盖全部13行业的详细信用分析报告（按行业子目录归类） |
| 系统智能报告 | 8份（⭐标记） | 传染复盘4份 + 集中度情景3份 + 系统性警报1份 |
| 验证报告 | 4份 | 永煤回溯 + 华晨多利益相关者 + 行业验证 + 引擎验证统计 |
| 报告模板 | 15种（Type 1-Type 15） | `templates/` 单一事实源（template-base.css + type1-15.html） |

合计 **72份报告**（60 行业 + 8 系统智能 + 4 验证），模板独立于报告计数。

### 黑天鹅回溯验证（3/3 完成）

| 案例 | 预警窗口 | 身份视角 |
|---|---|---|
| 永煤控股 | 17个月（双时点） | 信贷审批 |
| 紫光集团 | 17个月 | 信贷审批 |
| 华晨汽车 | 22个月 | 信贷+投资+交易/风控（三身份并行） |

### 假阳性/假阴性测试（完成）

完整引擎假阴性率 0%（5案例实测）· 治理/欺诈模块对欺诈型违约的识别起决定性作用

### 产品设计（完成）

产品愿景·Magic Experience·三层输出体系·商业化模型·定价·GTM

### 技术实现（未开始）

方法和产品设计全部固化后启动。

---

## 快速导航

| 想了解... | 去看... |
|---|---|
| 72份报告总览（按15个子目录归类） | `reports/` |
| 某行业信用报告（示例：光伏隆基） | `reports/solar/solar-longi-credit-report.html` |
| 系统智能报告（示例：永煤传染复盘） | `reports/system-intelligence/contagion-yongmei-2020.html` |
| 报告模板（Type 1-15 + 共享样式） | `templates/` |
| 系统智能层总览 | `engine/systemic-warning-framework.md` + `engine/contagion-matrix.md` + `engine/concentration-framework.md` |
| 产品愿景和魔法体验 | `product/product-overview.md` |
| 怎么卖、卖给谁 | `product/commercial-model.md` |
| 分析引擎架构总览 | `engine/engine-overview.md` |
| 某个行业的分析框架 | `engine/industry-framework.md` |
| 定性分析方法论 | `engine/qualitative-analysis.md` |
| 定量分析方法论 | `engine/quantitative-analysis.md` |
| 双轨框架+交叉对撞 | `engine/dual-track-methodology.md` |
| 马赛克引擎+完备性评估 | `engine/mosaic-engine.md` |
| 多利益相关者视角 | `engine/multi-stakeholder.md` |
| 城投债分析框架 | `engine/lgv-framework.md` |
| LGD/回收率评估 | `engine/lgd-recovery-framework.md` |
| 外部支持评估 | `engine/external-support-framework.md` |
| 假阳性/假阴性测试结果 | `engine/false-positive-negative-testing.md` |
| 传染矩阵与跨行业分析 | `engine/contagion-matrix.md` |
| 组合集中度评估 | `engine/concentration-framework.md` |
| 系统性风险指数 | `engine/systemic-warning-framework.md` |
| 报告设计样式体系 | `design/report-style-system.md` |
| AI Agent使用这套方法论 | `.claude/skills/fixed-income-credit-analysis/SKILL.md` |
| 版本管理策略与发布流程 | `../docs/VERSION-MANAGEMENT.md` |

---

## 版本历史

| 版本 | 日期 | 里程碑 |
|---|---|---|
| v0.1.0 | 2026-07-02 | 行业全景调研。产品设计文档初稿。 |
| v0.2.0 | 2026-07-07 | 双轨框架+黑天鹅回溯。永煤（双时点）+紫光验证。技能包发布。 |
| v0.3.0 | 2026-07-08 | 马赛克引擎。多利益相关者。P0债券仪表盘。华晨三身份验证。产品商业化回顾。 |
| v0.4.0-alpha | 2026-07-08 | 12档评级+EL整合+非信用风险叠加。城投债框架。治理/欺诈模块。5行业前瞻验证补齐。假阳性/假阴性测试。 |
| v0.5.0-alpha | 2026-07-08 | 8行业验证全覆盖。三层输出体系。风险缓释建议。压力测试升级。引擎终审。8行业验证报告HTML。 |
| **v0.7.0-alpha** | **2026-07-10** | **系统智能层发布：传染图谱（4份复盘+13×13矩阵+Type 13）·集中度仪表盘（五维框架+3份情景+Type 14）·系统性预警（SRI温度计+Type 15）。引擎架构升级至四层。M4组合风控完整实现。13行业全量覆盖。L0温度计卡片。15种报告模板体系。** |
| **v0.7.1-alpha** | **2026-07-15** | **开发栈结构重整：模板单源化 `templates/`（Type 1-15 + template-base.css）、engine 26份现行+15份归档 `engine/audits/`、72份报告按15个子目录归类、design/data 归位、README 与磁盘现实严格对齐。** |

> **注**：v0.6.x系列为模块级预发布版本（contagion-matrix.md、concentration-framework.md、systemic-warning-framework.md 等独立发布），功能统一纳入 v0.7.0-alpha。

---

*最后更新: 2026-07-15*

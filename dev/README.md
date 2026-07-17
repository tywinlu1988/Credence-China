# 固收信贷智能分析引擎

**项目代号**: Credence
**版本**: v0.8.1-release
**状态**: 方法论文档阶段 · 产品设计完成 · 13行业覆盖 · 系统智能层上线 · 文档结构重整完成

---

## 项目概述

面向中国固定收益市场的智能分析引擎。通过行业定制化的多层分析金字塔、双轨交叉验证框架、马赛克公开数据引擎、多利益相关者视角、非信用风险叠加层和系统智能层，为信贷审批、债券投资、市场交易和风险管理提供超越传统财务分析的信用认知供给。覆盖13大行业（12产业+城投债），具备跨行业传染图谱、五维集中度仪表盘和系统性预警温度计。

**核心原则**：传统财务分析在政策驱动型、技术壁垒型和资产租约型行业中系统性失效。最重的信用因子很少出现在资产负债表上。外部信用评级平均滞后真实信用恶化17个月以上。

---

## 目录结构

```
../AGENTS.md                                       ← 跨 CLI 通用入口（仓库根级 · 任何 agent CLI 从这里开始）
dev/
├── README.md                                        ← 你在这里
├── engine/                                          → 算法与方法论（28份现行文档）
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
│   ├── lgfv-framework.md                           城投债（政府+平台双轨·四级分类）
│   ├── governance-fraud-risk.md                    治理/欺诈风险（20+信号·逃废债检测）
│   ├── esg-framework.md                            ESG + 治理/欺诈检测框架
│   ├── financial-bond-framework.md                 金融债分析框架
│   ├── holding-company-framework.md                控股公司信用分析框架
│   ├── non-credit-risk-overlay.md                  非信用风险叠加层（市场/操作/声誉/战略/流动性）
│   ├── output-layered-framework.md                 分层输出（L0信号卡+L1快照+L2深度+温度计卡片）
│   ├── contagion-theory.md                         传染理论（四类型·七传导路径·升级因子）
│   ├── contagion-matrix.md                         ⭐13×13行业传染矩阵（传导强度·行业聚类）
│   ├── concentration-framework.md                  ⭐五维集中度分析框架（阈值·评级调整·压力测试）
│   ├── systemic-warning-framework.md               ⭐系统性预警框架（SRI信号聚合·温度计·历史回测）
│   ├── paradigm-brand-channel.md                   品牌+渠道范式（食品饮料·纺织服装）
│   ├── paradigm-network-traffic.md                 网络+流量范式（交运·零售·传媒互联网）
│   ├── dimension-registry.md                       维度注册表（6范式+LGFV·M0-M5角色·可寻址索引）
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
└── .claude/skills/                                → AI技能包（四段链；模板统一引用 dev/templates/）
    ├── credit-analysis-router/                    ① intake：四问路由，产出《工作路径单》
    ├── fixed-income-credit-analysis/              ② analysis：按路径单执行分析，产出《分析产物》
    ├── credit-report-builder/                     ③ report：装配交付报告，产出《交付单》
    └── credit-qa-verifier/                        ④ qa：交付前终态质检，产出《质检裁决》
```

> 能力验证证据（72 份测试报告等）存档于仓库根级 `../validation/`，为测试输出而非项目组成部分，永不进入版本快照。（GitHub 主仓库仅公开 2 份行业方法论参照，其余实测报告保留在维护者本地。）

---

## 当前进度

### 系统智能层（v0.7.0 新增）

| 模块 | 状态 | 核心文档 |
|---|---|---|
| 传染图谱 | ✅ 完成 | contagion-theory.md · contagion-matrix.md |
| 集中度仪表盘 | ✅ 完成 | concentration-framework.md |
| 系统性预警 | ✅ 完成 | systemic-warning-framework.md |
| 温度计L0卡片 | ✅ 完成 | 集成至output-layered-framework.md §3.6 |

### 报告模板

| 类型 | 数量 | 说明 |
|---|---|---|
| 报告模板 | 15种（Type 1-Type 15） | `templates/` 单一事实源（template-base.css + type1-15.html） |

### 产品设计（完成）

产品愿景·Magic Experience·三层输出体系·商业化模型·定价·GTM

### 技术实现（未开始）

方法和产品设计全部固化后启动。

---

## 快速导航

| 想了解... | 去看... |
|---|---|
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
| 城投债分析框架 | `engine/lgfv-framework.md` |
| LGD/回收率评估 | `engine/lgd-recovery-framework.md` |
| 外部支持评估 | `engine/external-support-framework.md` |
| 传染矩阵与跨行业分析 | `engine/contagion-matrix.md` |
| 组合集中度评估 | `engine/concentration-framework.md` |
| 系统性风险指数 | `engine/systemic-warning-framework.md` |
| 报告设计样式体系 | `design/report-style-system.md` |
| 任意 agent CLI 的通用入口（Claude Code/Codex/Cursor/Gemini/OpenCode） | `../AGENTS.md` |
| 四段链产物契约（工作路径单/分析产物/交付单/质检裁决） | `engine/pipeline-contract.md` |
| 维度注册表（6范式+LGFV 与 M0-M5 角色的可寻址索引，单源指针层） | `engine/dimension-registry.md` |
| 可执行编排器（v0.7.8：以代码驱动四段链，接 WP-M4-01/WP-M4-03 两个编码引擎） | `../src/pipeline.py` |
| AI Agent使用这套方法论（四段链：路由/分析/报告/质检） | `.claude/skills/` |
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
| v0.7.1-alpha（快照重建） | 2026-07-15 | 验证产物分离：72 份测试报告与测试执行记录迁出至根级 validation/（非项目本体，永不入快照）；README/SKILL 移除验证结果表格与案例清单；engine 现行文档 25 份；v0.7.1 快照按新边界重建 |
| **v0.7.1-release** | **2026-07-15** | **正式发布：开发栈结构重整（模板单源 templates/、engine 25份现行+audits/、design/data 归位）+ 验证产物分离（validation/ 永不入快照）。全量一致性检查与 63 项测试通过。** |
| **v0.8.0-alpha** | **2026-07-16** | **集成预发布：跨 CLI 通用入口（AGENTS.md + Codex 适配）· 四段链契约（pipeline-contract.md + report/qa 两阶段 skill）· 可执行编排器（src/pipeline.py 接 WP-M4-01/WP-M4-03 两编码引擎）· 维度注册表（dimension-registry.md）。8 条 active 路径端到端走查归档 validation/docs/。快照 dev/ + AGENTS.md + src/。143 项测试通过。** |
| **v0.8.0-release** | **2026-07-16** | **可安装 agent 包发布：`scripts/build_dist.py` 把 dev/ 源确定性组装为 `dist/credence/` 可安装包——skills 归位 `.claude/skills/`（Claude Code 原生 + Cursor/Gemini/OpenCode 兼容）、engine 平铺、AGENTS.md/CLAUDE.md/GEMINI.md 三入口、按工具 INSTALL.md、.claude-plugin 清单；清除死链接（settings.local.json 绝对路径、audits/design/product/data 及 16 处溯源指针）。快照重定义为可安装包。150 项测试通过。** |
| **v0.8.1-release** | **2026-07-17** | **门禁加固与晋升机制：.gitattributes 强制 LF + 换行符断言；lgd §12.1 评级表对齐 18 档；pyproject/package.json 版本硬校验；GitHub Actions CI；promote.py 晋升脚本（声明单源化）+ 测试版本无关化。162 项测试通过。** |

> **注**：v0.6.x系列为模块级预发布版本（contagion-matrix.md、concentration-framework.md、systemic-warning-framework.md 等独立发布），功能统一纳入 v0.7.0-alpha。

---

*最后更新: 2026-07-16*

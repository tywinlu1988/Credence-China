# 方法论文档全面一致性审计报告

**审计日期**: 2026-07-10
**审计范围**: D:\sandbox\loanagent\dev\engine\ 目录下30份方法论文档
**引擎当前版本**: v0.5.0-alpha（部分文件标注v0.3.0/v0.4.0/v0.1.0不等）
**审计方法**: 全量文档逐行比对 + 交叉引用链路追踪 + 术语频率统计

---

## 目录

1. [术语不统一清单](#1-术语不统一清单)
2. [权重与阈值冲突清单](#2-权重与阈值冲突清单)
3. [断裂的交叉引用清单](#3-断裂的交叉引用清单)
4. [版本标注问题清单](#4-版本标注问题清单)
5. [内容重复清单](#5-内容重复清单)
6. [修复优先级排序](#6-修复优先级排序)

---

## 1. 术语不统一清单

### T1. "轨道A/基本面/定性分析" 混用

| # | 当前写法 | 出现文件 | 建议统一为 |
|---|---|---|---|
| T1-1 | "Track A"（英文） | `validation-methodology.md` §1.1、§1.2 使用"Track A/Track B" | **轨道A / 轨道B**（全中文） |
| T1-2 | "Track A"（英文） | `false-positive-negative-testing.md` §1.4 评级映射表注解 | **轨道A** |
| T1-3 | "Track A" + "轨道A" 混用 | `financial-analysis-audit.md` §1 表格中混用 | **轨道A** |
| T1-4 | "定性分析" 指代轨道A | `qualitative-analysis.md` 标题及全文使用"定性分析"定位为轨道A | 可接受（该文档是定性分析专门文档），但首次出现需注明"定性分析是轨道A（基本面分析）的方法论子集" |
| T1-5 | "定量分析" 指代轨道B | `quantitative-analysis.md` 标题及全文使用"定量分析"定位为轨道B深化层 | 可接受（该文档是定量分析专门文档），但首次出现需注明"定量分析是轨道B（市场定价信号）的方法论深化层" |
| T1-6 | "基本面评价" 而非 "评分" | `dual-track-methodology.md` §2.1 标题"基本面金字塔评分"，而 `output-layered-framework.md` 使用"基本面维度评分" | **基本面评分**（统一为"评分"） |

**严重度**: P1（影响可读性）— 英文/中文混用降低文档一致感，但不影响分析结果。

### T2. "轨道B/市场定价/定量分析" 混用

| # | 当前写法 | 出现文件 | 建议统一为 |
|---|---|---|---|
| T2-1 | "Track B"（英文） | `quantitative-audit.md` §1 评估矩阵 | **轨道B** |
| T2-2 | "市场定价信号" vs "市场定价" | `dual-track-methodology.md` 标题使用"市场定价"；`engine-overview.md` 使用"市场定价信号" | **市场定价信号**（更精确） |

**严重度**: P1

### T3. "信号密度/数据完备性/信息完整度" 混用

三个术语在文档体系中指代相近但不同的概念：

| # | 当前写法 | 出现文件 | 问题描述 |
|---|---|---|---|
| T3-1 | "信号密度" | `mosaic-engine.md` §4.3 正式定义 | 标准术语——指"有效信号数/应有信号数" |
| T3-2 | "数据完备性" | `output-layered-framework.md` §3.3、§8.4、§10.1 术语对照 | 将"信号密度"列为同义词，但实质上语义更广 |
| T3-3 | "数据完备性灯号" | `output-layered-framework.md` §10.1 术语对照表 | 列为"信号密度指示"的同义词 |
| T3-4 | "信息完整度" | `dual-track-methodology.md` §十 实例输出 | 仅出现1次，指数据充分性 |

**建议统一方案**:
- **信号密度** = 技术指标（定量，0-100%），用于马赛克引擎完备性评估层
- **数据完备性** = 产品输出术语（定性，高/中/低），用于面向用户的信号灯
- **信息完整度** = 废弃此术语，统一替换为"数据完备性"
- 在 `output-layered-framework.md` 术语对照表中明确标注此分层使用规则

**严重度**: P1

### T4. "交叉对撞" vs "交叉验证" 概念混淆

| # | 当前写法 | 出现文件 | 问题描述 |
|---|---|---|---|
| T4-1 | "交叉验证"用于描述双轨分歧处理 | `mosaic-engine.md` §4.1 "跨维度信号交叉验证" | 正确——这是马赛克层面的"交叉验证" |
| T4-2 | "交叉对撞" for Track A vs Track B | `dual-track-methodology.md` §四 "交叉对撞矩阵" | 标准术语 |
| T4-3 | 两个术语在 `output-layered-framework.md` §8.2 中并列使用但未区分 | `output-layered-framework.md` §8.2 | 需增加区分说明 |

**建议**: 在 `engine-overview.md` 术语章节（当前无此章节）或 `output-layered-framework.md` 中新增核心术语界定表：
- **交叉验证** = 信号层面的多源确认（同一维度不同来源）
- **交叉对撞** = 轨道层面的分歧/共识判断（轨道A vs 轨道B综合评分）

**严重度**: P2

### T5. 行业名称英文缩写混用

| # | 当前写法 | 出现文件 | 建议 |
|---|---|---|---|
| T5-1 | "NEV"（英文缩写） | `financial-analysis-audit.md` 全表使用"NEV-OEM"/"NEV-供应链" | **新能源汽车-OEM** / **新能源汽车-供应链** |
| T5-2 | "NEV"（英文缩写） | `financial-deep-dive.md` §B.3 七行业差异化阈值表 | **新能源汽车** |
| T5-3 | "NEV"（英文缩写） | `industry-framework.md` §4.6 标题"新能源汽车"（中文），但表格内使用"NEV" | **新能源汽车**（全中文） |
| T5-4 | "PV" 缩写 | `dual-track-methodology.md` 在实例中引用"PVInfoLink"时暴露缩写 | 行业名保持"光伏"，仅数据供应商名保留PVInfoLink |
| T5-5 | "IC" 后缀 | `industry-framework.md` §4.2 标题"半导体/IC" | **半导体** 或 **半导体/集成电路**（更正式的中文） |
| T5-6 | "CCC" vs "CC" | `dual-track-methodology.md` 评级表中有CCC但无CC，而部分国际评级机构有CC级别 | 若12档方案中无CC则需在所有文件中保持CCC一致 |
| T5-7 | "OEM/供应链" 中英文混写 | `industry-framework.md` §4.6 使用中文"OEM轨道"和"供应链轨道" | 建议统一：**整车轨道** / **零部件供应链轨道** |

**严重度**: P2

### T6. 评级层级命名不一致

| # | 当前写法 | 出现文件 | 问题描述 |
|---|---|---|---|
| T6-1 | "6档" vs "12档" 混用 | `false-positive-negative-testing.md` §1.4 评级映射表使用6档分类 | 该文档版本未跟随 v0.4.0 升级，仍使用旧6档体系 |
| T6-2 | "12档" 在部分文档中仍称为"6档扩展" | `dual-track-methodology.md` 标题标注"评级修订 v0.4.0"；`final-review.md` §3.1 仍称"仅有6档" | 不一致——v0.4.0已升级至12档，`final-review.md` 未同步更新 |
| T6-3 | 评分区间在 `final-review.md` 与 `dual-track-methodology.md` 不匹配 | `final-review.md` §1.5 使用 AAA(9.0-10.0)、AA/A(7.5-8.9)、BBB/BB(6.0-7.4)、B(4.0-5.9)、CCC(2.0-3.9)、D(0-1.9) | 此为旧6档区间，与12档表冲突 |
| T6-4 | "AA/A" 联合写法 | `final-review.md` §1.5、`false-positive-negative-testing.md` §1.4 使用"AA/A"、"BBB/BB"联合写法 | 12档已拆分AA和A、BBB和BB，不应联合书写 |

**严重度**: P0（影响分析结果）— false-positive-negative-testing.md 和 final-review.md 使用旧评级映射，可能导致假阳性/假阴性判定标准与实际评级体系不一致。

### T7. "一票否决/veto/硬上限" 术语

| # | 当前写法 | 出现文件 | 建议 |
|---|---|---|---|
| T7-1 | "一票否决"（全中文，标准） | `dual-track-methodology.md`、`industry-framework.md` 等 | 标准术语 |
| T7-2 | 无"veto"或"硬上限"英文混用 | 所有文件均使用"一票否决" | ✅ 一致，无需修改 |

**严重度**: 无问题

### T8. 四层金字塔 vs 五层金字塔 层命名不一致

| # | 当前写法 | 出现文件 | 问题描述 |
|---|---|---|---|
| T8-1 | 4层使用"L1-L4"命名，5层使用"L1-L5"命名 | `dual-track-methodology.md` §2.2 标准四层；§2.3 特殊五层 | 层编号逻辑一致，但不同文档在引用"L4财务层"时需注明是4层还是5层体系中的L4 |
| T8-2 | `industry-framework.md` §3.2 标准4层模板中 L4=财务；§3.3 特殊5层中 L5=财务 | `industry-framework.md` §3.2/§3.3 | 5层行业中L4不是财务层（半导体L4=政策/资本，L5=财务；新能源车-OEM L4=财务，L5=政策/出口），引用"L4财务层"时需明确行业上下文 |
| T8-3 | `financial-analysis-audit.md` 全表使用"L4财务层"指代所有行业的财务层 | `financial-analysis-audit.md` | 对半导体等5层行业，L4是"政策/资本"而非"财务"——该审计报告存在系统性偏差 |

**严重度**: P0（影响分析结果）— financial-analysis-audit.md 对半导体等5层行业的审计结论可能因层索引错位而无效。

---

## 2. 权重与阈值冲突清单

### W1. 评级映射表冲突：`false-positive-negative-testing.md` vs `dual-track-methodology.md`

| 项目 | `dual-track-methodology.md` §六（v0.4.0） | `false-positive-negative-testing.md` §1.4（未标注版本） | 冲突类型 |
|---|---|---|---|
| 总档位数 | 18档（AAA→D含+/-） | 6档（AAA, AA/A, BBB/BB, B, CCC, D） | 结构性冲突 |
| AAA区间 | 9.5-10.0 | 9.0-10.0 | 阈值冲突 |
| 阴性判定线 | 无明确线 | BB+及以上为"阴性" | 判定逻辑冲突 |
| B区间 | 2.0-2.4 B- / 2.5-2.9 B / 3.0-3.4 B+ | 4.0-5.9 B | 严重区间冲突 |
| CCC区间 | 1.0-1.9 | 2.0-3.9 | 严重区间冲突 |
| D区间 | 0-0.9 | 0-1.9 | 阈值冲突 |

**影响**: `false-positive-negative-testing.md` 的假阳性/假阴性判定使用旧6档体系，测试结论与当前12档体系不兼容。例如，旧体系评为CCC（2.0-3.9）在新体系中可能对应B-至B+，导致"BB+及以上为阴性"的判定逻辑完全无效。

**建议**: `false-positive-negative-testing.md` 必须升级评级映射表至12档，并重新计算所有测试案例的阳性/阴性判定。

**严重度**: P0

### W2. `final-review.md` 使用旧评级映射

| 项目 | `final-review.md` §1.5 | `dual-track-methodology.md` §六 |
|---|---|---|
| AAA | 9.0-10.0 | 9.5-10.0 |
| AA/A | 7.5-8.9（合并） | 拆分AA+, AA, AA-, A+, A, A- 共6档 |
| BBB/BB | 6.0-7.4（合并） | 拆分BBB+, BBB, BBB-, BB+, BB, BB- 共6档 |
| B | 4.0-5.9 | 拆分B+, B, B- 共3档 |
| CCC | 2.0-3.9 | 1.0-1.9 |
| D | 0-1.9 | 0-0.9 |

**影响**: `final-review.md` 是终结性审查报告，多处基于旧6档评级体系做出结论（如"评级粒度不足"判断），与v0.4.0已实现的12档方案矛盾。

**严重度**: P1（影响可读性，可能导致读者对评级体系现状的误判）

### W3. 半导体L1权重在不同文档中是否存在冲突

| 文档 | 半导体L1权重 | 与 `industry-framework.md` 对比 |
|---|---|---|
| `industry-framework.md` §4.2 | L1 地缘政治 30-35% | 基准 |
| `dual-track-methodology.md` §2.3 | L1 地缘政治 30-35% | ✅ 一致 |
| `financial-analysis-audit.md` §1 差距表 | 未指定半导体权重 | N/A |

**结论**: 权重一致，无冲突。

### W4. 一票否决条件一致性

| 行业 | `industry-framework.md` §五 | `dual-track-methodology.md` §八 | 是否一致 |
|---|---|---|---|
| 光伏 | PERC产能>70% | 引用 §2.4示例"任一层面触发" | 引用条件一致 |
| 半导体 | 被列入实体清单/SDN清单 | 引用"一票否决条件" | ✅ |
| 高端装备 | 数控系统+主轴+伺服全部外采且无国内替代 | 仅引用未展开 | ✅（可接受） |
| 生物医药 | 核心管线III期临床试验失败 | 仅引用未展开 | ✅ |
| 医疗器械 | 三类注册证到期且无法续期 | 仅引用未展开 | ✅ |
| 新能源车 | 月销量<1万台+现金跑道<12个月 | 仅引用未展开 | ✅ |
| 数据中心 | 核心客户租约到期且确认不续约 | 仅引用未展开 | ✅ |

**结论**: 一票否决条件在 `industry-framework.md` §五（权威汇总表）和 `dual-track-methodology.md` 之间基本一致。`dual-track-methodology.md` §2.5 的通用描述"任一层面触发一票否决条件，综合评级上限锁定为CCC"与 `industry-framework.md` §五的"触发后综合评级上限锁定为CCC"完全一致。

**严重度**: 无冲突

### W5. FCF阈值一致性

| 指标 | `dual-track-methodology.md` §5.2 | `financial-deep-dive.md` §D | 是否一致 |
|---|---|---|---|
| FCF/收入>5% + FCF/利息>3x | 造血能力强 | 造血能力强 | ✅ |
| FCF/收入<0 + FCF/利息<1x | L4上限锁定4分 | L4上限锁定4分 | ✅ |
| FCF/利息持续<0超2年 | 评级上限B | 评级上限B | ✅ |

**结论**: FCF阈值在 `dual-track-methodology.md` 和 `financial-deep-dive.md` 之间完全一致。

**严重度**: 无冲突

### W6. `quantitative-analysis.md` 统计修正与 `quantitative-audit.md` 的版本匹配

`quantitative-analysis.md` 已包含 v0.3.1 统计修正（Bootstrap CI、FDR校正、ADF检验等），但 `quantitative-audit.md` 提到的21项问题中有18项标记为"文档已修复"。然而：
- `quantitative-audit.md` §2.3 S-10至S-14的修正建议标注了具体方法，但 `quantitative-analysis.md` 中的代码实现为0%
- 文档修正停留在文字描述层面，未通过代码验证

**严重度**: P1（文档层已修复但不可执行，影响统计严谨性承诺的可信度）

---

## 3. 断裂的交叉引用清单

### R1. 文件级交叉引用验证

对文档中出现的所有"参见 xxx.md"或文件链接进行全量验证：

| # | 源文件 | 引用目标 | 目标是否存在 | 状态 |
|---|---|---|---|---|
| R1-1 | `dual-track-methodology.md` §7.3 | `lgd-recovery-framework.md` | ✅ 存在 | 有效 |
| R1-2 | `dual-track-methodology.md` §七 | `lgv-framework.md` | ✅ 存在 | 有效 |
| R1-3 | `dual-track-methodology.md` §相关内容 | `engine-overview.md` | ✅ 存在 | 有效 |
| R1-4 | `dual-track-methodology.md` §相关内容 | `industry-framework.md` | ✅ 存在 | 有效 |
| R1-5 | `dual-track-methodology.md` §相关内容 | `mosaic-engine.md` | ✅ 存在 | 有效 |
| R1-6 | `dual-track-methodology.md` §相关内容 | `governance-fraud-risk.md` | ✅ 存在 | 有效 |
| R1-7 | `engine-overview.md` §相关内容 | `industry-framework.md` | ✅ 存在 | 有效 |
| R1-8 | `engine-overview.md` §相关内容 | `dual-track-methodology.md` | ✅ 存在 | 有效 |
| R1-9 | `engine-overview.md` §相关内容 | `mosaic-engine.md` | ✅ 存在 | 有效 |
| R1-10 | `industry-framework.md` §相关内容 | `engine-overview.md` | ✅ 存在 | 有效 |
| R1-11 | `industry-framework.md` §相关内容 | `dual-track-methodology.md` | ✅ 存在 | 有效 |
| R1-12 | `industry-framework.md` §相关内容 | `mosaic-engine.md` | ✅ 存在 | 有效 |
| R1-13 | `qualitative-analysis.md` §1.1 | `quantitative-analysis.md` | ✅ 存在 | 有效 |
| R1-14 | `non-credit-risk-overlay.md` §1.1 | `risk-management-standards-audit.md` | ✅ 存在 | 有效 |
| R1-15 | `self-assessment-2026-07-08.md` 全文多处 | `rating-agency-benchmark-audit.md`, `quantitative-audit.md`, `risk-management-standards-audit.md`, `practitioner-usability-audit.md` | ✅ 全部存在 | 有效 |
| R1-16 | `esg-framework.md` §四 | `governance-fraud-risk.md` | ✅ 存在 | 有效 |
| R1-17 | `governance-fraud-risk.md` §六 | 非文件链接，引用"金字塔体系" | 非直接文件引用 | N/A |
| R1-18 | `external-support-framework.md` §1.1 | `rating-agency-benchmark-audit.md` | ✅ 存在 | 有效 |
| R1-19 | `lgv-framework.md` §三 | `external-support-framework.md` | ✅ 存在 | 有效 |
| R1-20 | `output-layered-framework.md` §10.2 | 从业者审计"8个批评"引用 | 未使用文件链接，为章节内引用 | 有效 |

**结论**: 所有文件级交叉引用均有效。无断裂引用。

### R2. 章节编号错位风险

由于文档在多次修改中可能发生章节增删，跨文档的章节编号引用可能存在错位：

| # | 源文件 | 引用的章节编号 | 目标章节当前编号 | 是否错位 |
|---|---|---|---|---|
| R2-1 | `dual-track-methodology.md` §7.3 | 引用"[LGD与回收率分析框架](lgd-recovery-framework.md)第二节" | `lgd-recovery-framework.md` §二（LGD五级分类体系） | ✅ 正确 |
| R2-2 | `dual-track-methodology.md` §7.3 | 引用"第二节LGD五级分类体系" | `lgd-recovery-framework.md` 第二节标题"LGD五级分类体系" | ✅ 正确 |
| R2-3 | `dual-track-methodology.md` §7.5 | 备注"（同7.5节）"——但实际在引用7.5节内部 | 自引用 | ✅ 正确 |
| R2-4 | `dual-track-methodology.md` §9.3 | 引用"9.3节"场景H/I | 当前文档自身§9.3 | ✅ 正确 |
| R2-5 | `dual-track-methodology.md` §7.7.6后 | 引用"[城投双轨框架](lgv-framework.md)" | `lgv-framework.md` 无章节号引用 | N/A（文件级引用） |
| R2-6 | `lgv-framework.md` §3.1 | 引用"external-support-framework.md 4.1节" | `external-support-framework.md` §4.1 是否为四维模型？需确认 | ⚠️ 待验证 |
| R2-7 | `esg-framework.md` §1.3 步骤 3b/3c | 引用"操作风险评估"和"声誉风险评估" | `non-credit-risk-overlay.md` §四（操作风险）和 §五（声誉风险） | ✅ 正确 |

**结论**: 章节编号引用基本有效。R2-6 需人工确认 `external-support-framework.md` 的§4.1章节是否存在且内容匹配。

### R3. 缺失的文档引用

| # | 源文件 | 应引用但未引用 | 建议 |
|---|---|---|---|
| R3-1 | `dual-track-methodology.md` §九 风险缓释框架 | 标注"来源：风险管理标准审计报告"但未使用文件链接 | 建议增加"[详见风险审计报告](risk-management-standards-audit.md)"链接 |
| R3-2 | `dual-track-methodology.md` §十一 回溯验证 | 引用了永煤案例但未链接到验证方法论文档 | 建议增加"[验证方法论](validation-methodology.md)"链接 |
| R3-3 | `engine-overview.md` §七 版本历史 | 版本v0.1.0至v0.3.0，未提及v0.4.0升级（12档评级） | 需新增v0.4.0版本记录 |
| R3-4 | `industry-framework.md` | 未引用 `financial-deep-dive.md` 中的详细阈值规格 | 建议在营运资金效率部分增加"[详见财务深度分析](financial-deep-dive.md)"链接 |

**严重度**: P2

---

## 4. 版本标注问题清单

### V1. 缺失版本号的文档

| # | 文件名 | 当前标注 | 问题 |
|---|---|---|---|
| V1-1 | `multi-stakeholder.md` | `**日期**: 2026-07-08`，缺少版本号 | 其他文档均标注"版本: vX.Y.Z"，此文档缺少 |
| V1-2 | `validation-methodology.md` | `**日期**: 2026-07-08`，缺少版本号 | 同上 |
| V1-3 | `false-positive-negative-testing.md` | 仅标注"方法论版本: v1.1"，无文档版本号 | 文档自身缺少统一版本标签 |
| V1-4 | `self-assessment-2026-07-08.md` | 无版本标注 | 文件名有日期但无版本号 |
| V1-5 | `capability-review-2026-07-08.md` | 无版本标注 | 同上 |
| V1-6 | `closure-check-2026-07-08.md` | 无版本标注 | 同上 |
| V1-7 | `financial-analysis-audit.md` | `**版本**: v1.0`（但此为审查报告版本，非引擎版本） | 审查报告的版本体系与引擎版本体系不同，需说明 |
| V1-8 | `quantitative-audit.md` | 仅标注日期，无版本号 | 同上 |
| V1-9 | `rating-agency-benchmark-audit.md` | 仅标注日期，无版本号 | 同上 |
| V1-10 | `practitioner-usability-audit.md` | 仅标注日期，无版本号 | 同上 |
| V1-11 | `risk-management-standards-audit.md` | 仅标注日期，无版本号 | 同上 |

**严重度**: P2（格式一致性问题）

### V2. 版本号与文档实际内容不匹配

| # | 文档 | 声称版本 | 实际包含的内容 | 问题 |
|---|---|---|---|---|
| V2-1 | `dual-track-methodology.md` | v0.4.0 | 12档评级映射、EL整合、中国市场PD参考 | ✅ 匹配 |
| V2-2 | `engine-overview.md` | v0.3.0 | 提到12档"评级修订 v0.4.0"，但版本标注为v0.3.0 | **不匹配**——内容已引用了v0.4.0的功能，自身版本号未升级 |
| V2-3 | `outlook-monitoring-framework.md` | v0.3.0 | 与 `dual-track-methodology.md` v0.4.0 不匹配 | 版本滞后，应升级至v0.4.0以匹配双轨主体文档 |
| V2-4 | `final-review-2026-07-08.md` | 正文中引用"v0.3.1" | 评级体系仍用6档描述（与v0.4.0不符） | 内容与文档中引用的引擎版本不匹配 |
| V2-5 | `remaining-issues-v0.5.0-alpha.md` | v0.5.0-alpha | 已有14项标记为"已修复"，但仍有5项剩余 | 文件名与实际引擎版本对应关系不清晰 |
| V2-6 | `industry-framework.md` | v0.3.0 | 未引用v0.4.0的评级升级 | 应升级至v0.4.0 |
| V2-7 | `qualitative-analysis.md` | v0.3.0 | 未引用v0.4.0的评级升级 | 应升级至v0.4.0 |
| V2-8 | `mosaic-engine.md` | v0.1.0 | 核心架构文档版本过低 | 应升级至v0.3.0+ |

**严重度**: P1（版本号与内容脱节，读者无法通过版本号判断文档的时效性）

### V3. 跨文档版本一致性

| 版本 | 文档数 | 包含的文档 |
|---|---|---|
| v0.1.0 | 9份 | mosaic-engine, output-layered-framework, lgd-recovery-framework, external-support-framework, financial-deep-dive, governance-fraud-risk, lgv-framework, non-credit-risk-overlay, holding-company-framework |
| v0.3.0 | 5份 | engine-overview, industry-framework, qualitative-analysis, quantitative-analysis, outlook-monitoring-framework |
| v0.4.0 | 1份 | dual-track-methodology |
| v0.5.0-alpha | 1份（文件名） | remaining-issues |
| 无版本 | 11份 | multi-stakeholder, validation-methodology, false-positive-negative-testing, self-assessment, capability-review, final-review, closure-check, quantitative-audit, rating-agency-benchmark-audit, practitioner-usability-audit, risk-management-standards-audit |
| v1.0（审查） | 1份 | financial-analysis-audit |
| 日期后缀 | 9份 | 所有 2026-07-08/09 命名的审查自评文档 |

**核心问题**: 30份文档分布在至少4个版本号（v0.1.0、v0.3.0、v0.4.0、v0.5.0-alpha）+ 审查报告子版本体系，**无统一的版本号管理策略**。 `closure-check-2026-07-08.md` 建议统一升级至v0.3.5或v0.4.0-alpha，但此建议未被采纳执行。

**建议**: 
1. 所有方法论文档统一版本号至 v0.5.0-alpha（与 `remaining-issues-v0.5.0-alpha.md` 一致）
2. 审查/审计报告使用独立版本体系（如 v1.0, v1.1），但需在文档头标注"对应引擎版本: v0.5.0-alpha"
3. 建立 `VERSION-MANAGEMENT.md` 统一管理版本对应关系

**严重度**: P2

---

## 5. 内容重复清单

### D1. 评级映射表重复（高重复度）

| 出现位置 | 表格位置 | 差异 |
|---|---|---|
| `dual-track-methodology.md` §六 | 完整12档表，含评分范围、新旧评级对应、含义 | 基准版本 |
| `engine-overview.md` §五 | 完整12档表，与dual-track.md几乎完全一致 | 缺少"旧评级对应"列中的"旧6档对应"文字描述；其他一致 |
| `false-positive-negative-testing.md` §1.4 | 6档简化表 | **严重不匹配**（见W1） |
| `final-review.md` §1.5 | 6档简化表 | 不匹配（见W2） |
| `self-assessment.md` | 引用"6档评级映射" | 与v0.4.0升级冲突 |

**建议**: 
- 评级映射表应定义为 **唯一权威来源** 在 `dual-track-methodology.md` 中
- `engine-overview.md` 改为引用而非复制完整表格（"详见双轨分析方法论 §六"）
- `false-positive-negative-testing.md` 和 `final-review.md` 必须升级至12档
- **P0优先级**

### D2. 四层金字塔权重模板重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `dual-track-methodology.md` §2.2 | 标准四层金字塔权重表 | 基准 |
| `industry-framework.md` §3.2 | 标准四层金字塔权重表 | 基本一致 |

**差异检查**: 两张表内容完全一致——政策驱动型(35%/30%/20%/15%)、技术壁垒型(20%/35%/25%/20%)、存量博弈型(25%/20%/30%/25%)、资产租约型(15%/20%/35%/30%)。

**建议**: `dual-track-methodology.md` 应引用 `industry-framework.md`（"详见行业分类与分析框架 §3.2"）而非复制。如保留，需在`dual-track.md`中标注"复制自 industry-framework.md §3.2"。

**严重度**: P2

### D3. 一票否决条件汇总表重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `industry-framework.md` §五 | 完整的7行业一票否决条件汇总表 | 权威来源 |
| `dual-track-methodology.md` §2.5 | 引用通用规则"任一层面触发一票否决条件" | 未重复完整表（可接受） |
| `dual-track-methodology.md` §八 | 决策规则引用"一票否决触发→上限CCC" | 规则引用，非表重复 |

**结论**: 不构成重复问题。`industry-framework.md` 是一票否决的权威来源，其他文档仅引用规则。

**严重度**: 无问题

### D4. FCF分析重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `dual-track-methodology.md` §五 | FCF完整分析（公式+分级+评级衔接+营运资金联动+实例） | 基准（约500字） |
| `financial-deep-dive.md` §D | FCF生成能力（公式+分级+庞氏检测） | 重合度约70% |

**具体重复内容**: 
- FCF公式 (FCF = CFO - Capex) 出现在两个文档
- FCF/收入>5%且FCF/利息>3x判定为造血能力强 重复
- FCF/利息持续<0超2年→庞氏融资嫌疑 重复
- FCF/营运资金联动分析 重复

**建议**: `dual-track-methodology.md` §五应精简，仅保留FCF在双轨架构中的定位和评级映射规则；详细计算规格应仅保留在 `financial-deep-dive.md` §D。`dual-track.md` 改为引用："详见[财务深度分析 §D](financial-deep-dive.md)"

**严重度**: P2

### D5. LGD等级表重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `lgd-recovery-framework.md` §二 | 完整LGD1-LGD5等级定义表 | 权威来源 |
| `dual-track-methodology.md` §7.3 | LGD损失率映射（汇总表） | 精简版（仅损失率/回收率区间） |

**结论**: 可接受——`dual-track-methodology.md` 中的LGD表是EL整合层的引用摘要，并非完整重复。但应增加"详见[LGD与回收率分析框架](lgd-recovery-framework.md) §二"的标注（当前已有文件级引用但无章节号）。

**严重度**: 无问题

### D6. M0-M6角色定义重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `multi-stakeholder.md` §一 | 完整的M0-M5六类角色定义表 | 权威来源（约800字） |
| `qualitative-analysis.md` §1.3 | M0-M5定性分析权重表 | 重点在定性权重，非完整定义 |

**结论**: 可接受——`qualitative-analysis.md` 中是特定视角的补充，非重复。

**严重度**: 无问题

### D7. 信号密度四档表格重复

| 出现位置 | 内容 | 差异 |
|---|---|---|
| `mosaic-engine.md` §4.3 | 信号密度四档定义（>80%/50-80%/20-50%/<20%） | 权威来源 |
| `mosaic-engine.md` §5.4 | 置信度对评分的影响规则（相同四档） | 同一文档内部重复 |
| `output-layered-framework.md` §9.2 | 信号密度<30%的特殊处理 | 不同阈值（30% vs 20%） |

**差异分析**: `mosaic-engine.md` §4.3 定义<20%为"信息严重缺失"，而 `output-layered-framework.md` §9.2 使用"信号密度<30%"作为"数据严重不足"的阈值——**阈值不一致**。

**建议**: 
- `mosaic-engine.md` 内部去掉 §5.4 的重复（改为"详见 §4.3 信号密度指标"）
- `output-layered-framework.md` 的30%阈值应当与 `mosaic-engine.md` 的20%阈值统一，或给出差异化理由（产品层更保守）

**严重度**: P1（阈值冲突可能影响产品输出）

### D8. 七行业营运资金阈值表的复制

| 出现位置 | 内容 |
|---|---|
| `industry-framework.md` §4.1-4.7 | 各行业分别定义 DSO/DIO/DPO/CCC 阈值（分散在各行业小节末尾的"行业特殊说明"） |
| `financial-deep-dive.md` §B.3 | 七行业差异化DSO/DIO/DPO/CCC阈值汇总表 |

**建议**: `financial-deep-dive.md` §B.3 已经是汇总表，建议 `industry-framework.md` 中各行业的"行业特殊说明"改为引用 `financial-deep-dive.md`，避免维护两份独立阈值表时发生不一致。

**严重度**: P2

---

## 6. 修复优先级排序

### P0 — 影响分析结果（必须修复）

| 优先级 | 编号 | 问题 | 影响 | 建议修复方式 |
|---|---|---|---|---|
| **P0-1** | W1 | `false-positive-negative-testing.md` 使用旧6档评级映射，假阳性/假阴性判定逻辑与12档体系不兼容 | 该文档的测试结论在12档体系下全部失效 | 升级评级映射表至12档，重新计算所有测试案例的阳性/阴性判定 |
| **P0-2** | W2 | `final-review.md` §1.5 使用旧6档评级区间描述 | 终结报告的评级体系描述与现状不符 | 升级评分区间至12档，或标注"以下为v0.3.0旧版描述" |
| **P0-3** | T8-3 | `financial-analysis-audit.md` 全表将"L4财务层"套用于5层行业（如半导体L4实际为政策/资本层） | 对半导体、新能源车等5层行业的审计结论系统性错误 | 修正审计表，区分4层和5层行业的层索引 |
| **P0-4** | D1 | 评级映射表在5处文档中各自定义，`false-positive-negative-testing.md` 和 `final-review.md` 版本滞后 | 读者无法确定哪个版本是当前有效版本 | 建立评级映射的唯一权威来源，其他文档改为引用 |

### P1 — 影响可读性和分析置信度

| 优先级 | 编号 | 问题 | 影响 | 建议修复方式 |
|---|---|---|---|---|
| **P1-1** | T1/T2 | "Track A/B"英文与"轨道A/B"中文混用 | 降低文档一致性和专业感 | 全部统一为"轨道A/轨道B"（中文），在首次使用处标注英文 |
| **P1-2** | T3 | "信号密度/数据完备性/信息完整度"未分层定义 | 读者可能混淆技术指标和产品输出术语 | 在 `engine-overview.md` 新增核心术语表，明确定义三层概念的异同 |
| **P1-3** | V2-2 | `engine-overview.md` v0.3.0 引用v0.4.0功能 | 版本号与内容不匹配 | 升级至v0.4.0，或回退引用 |
| **P1-4** | D7 | `output-layered-framework.md` 使用30%阈值而 `mosaic-engine.md` 使用20% | 两个"数据严重不足"阈值冲突 | 统一阈值（建议采用20%），或在产品层给出差异化理由 |
| **P1-5** | W6 | `quantitative-analysis.md` 统计修正停留在文档层面，代码实现0% | 统计方法的可信度受质疑 | 在所有统计方法处追加"文档层设计完成，代码实现待进行"的诚实标注 |
| **P1-6** | T6 | "AA/A"合并写法出现在 `final-review.md` 和 `false-positive-negative-testing.md` | 与12档拆分逻辑矛盾 | 使用12档独立评级名称 |
| **P1-7** | V2-6/7/8 | `industry-framework.md`、`qualitative-analysis.md`、`mosaic-engine.md` 版本号滞后 | 核心架构文档版本号与最新功能不匹配 | 统一升级至v0.5.0-alpha |

### P2 — 仅格式/组织结构问题

| 优先级 | 编号 | 问题 | 影响 | 建议修复方式 |
|---|---|---|---|---|
| **P2-1** | V1 | 11份文档缺失版本号 | 无法判断文档时效性和版本对应关系 | 为所有文档增加统一的版本号和日期头 |
| **P2-2** | D2 | 四层金字塔权重模板在 `dual-track-methodology.md` 和 `industry-framework.md` 中重复 | 维护两份副本，可能产生分歧 | `dual-track-methodology.md` 改为引用 `industry-framework.md` |
| **P2-3** | D4 | FCF分析在 `dual-track-methodology.md` 和 `financial-deep-dive.md` 中70%重复 | 维护两份副本 | `dual-track-methodology.md` 精简并引用 `financial-deep-dive.md` |
| **P2-4** | D8 | 七行业营运资金阈值分布在 `industry-framework.md` 各行业小节末尾和 `financial-deep-dive.md` 汇总表 | 维护成本高 | `industry-framework.md` 中的各行业特殊说明改为引用 `financial-deep-dive.md` |
| **P2-5** | T5 | 行业名称英文缩写（NEV, PV, IC）混用 | 统一性问题 | 全中文行业名称 |
| **P2-6** | R3 | 缺失的文档引用（3处） | 读者不易跳转到相关文档 | 增加文件级链接 |
| **P2-7** | T4 | "交叉对撞" vs "交叉验证" 概念需正式界定 | 对跨文档读者可能产生困惑 | 在 `engine-overview.md` 或新建术语表中定义 |
| **P2-8** | V3 | 30份文档无统一版本管理策略 | 长期维护困难 | 建立 VERSION-MANAGEMENT.md 或至少在一个权威文档中标注版本对应关系 |

---

## 附录：30份文档版本标注速查

| 文件名 | 声称版本 | 实际版本适配 | 评级体系 | 审查状态 |
|---|---|---|---|---|
| dual-track-methodology.md | v0.4.0 | ✅ 基准 | 12档 | ✅ 最新 |
| engine-overview.md | v0.3.0 | ⚠️ 引用v0.4.0 | 12档 | ⚠️ 版本未升级 |
| industry-framework.md | v0.3.0 | ⚠️ 未升级 | 6档（隐式） | ⚠️ 需跟进v0.4.0 |
| qualitative-analysis.md | v0.3.0 | ⚠️ 未升级 | N/A | ⚠️ 需跟进v0.4.0 |
| quantitative-analysis.md | v0.3.0 | ✅ 含修正 | N/A | ✅ 已修v0.3.1 |
| mosaic-engine.md | v0.1.0 | ⚠️ 过低 | N/A | ⚠️ 需升级 |
| output-layered-framework.md | v0.1.0 | — | N/A | ✅ 独立产品文档 |
| financial-bond-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| financial-deep-dive.md | v0.1.0 | — | N/A | ✅ 新增 |
| lgd-recovery-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| external-support-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| holding-company-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| esg-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| governance-fraud-risk.md | v0.1.0 | — | N/A | ✅ 新增 |
| lgv-framework.md | v0.1.0 | — | N/A | ✅ 新增 |
| outlook-monitoring-framework.md | v0.3.0 | ⚠️ 未升级 | N/A | ⚠️ 需跟进v0.4.0 |
| non-credit-risk-overlay.md | v0.1.0 | — | N/A | ✅ 新增 |
| multi-stakeholder.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| validation-methodology.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| false-positive-negative-testing.md | ❌ 无版本 | ❌ 严重 | **6档** | ❌ 需重做 |
| financial-analysis-audit.md | v1.0（审查） | ❌ 层索引错位 | N/A | ❌ 需修正 |
| quantitative-audit.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| rating-agency-benchmark-audit.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| practitioner-usability-audit.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| risk-management-standards-audit.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| self-assessment-2026-07-08.md | ❌ 无版本 | — | 6档（旧） | ⚠️ 需更新 |
| final-review-2026-07-08.md | ❌ 无版本 | ❌ 6档描述 | **6档** | ❌ 需更新 |
| capability-review-2026-07-08.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| closure-check-2026-07-08.md | ❌ 无版本 | — | N/A | ❌ 缺版本 |
| remaining-issues-v0.5.0-alpha.md | v0.5.0-alpha | ✅ 最新 | 12档（隐式） | ✅ 最新 |

---

## 审计总结

本审计对30份方法论文档进行了全面一致性审查，发现：

- **P0级问题（影响分析结果）**共4项：评级映射表在 `false-positive-negative-testing.md` 和 `final-review.md` 中使用旧6档与主流12档冲突、`financial-analysis-audit.md` 的层索引对5层行业系统性地错位。

- **P1级问题（影响可读性）**共7项：中英文术语混用、信号密度阈值在 `output-layered-framework.md` 与 `mosaic-engine.md` 之间不一致、核心文档版本号与内容脱节、统计修正停留在文档层未代码化。

- **P2级问题（格式/组织结构）**共8项：11份文档缺失版本号、内容在多个文档间重复（评级映射表、四层权重模板、FCF分析、营运资金阈值）、行业名称英中文混用、交叉引用缺失、无统一版本管理策略。

**最需要优先处理的3项**：
1. **P0-1**：`false-positive-negative-testing.md` 的评级映射表升级至12档——保持假阳性/假阴性测试结果的有效性
2. **P0-2**：`final-review.md` 的评级体系描述升级至12档——避免终结性审查报告的误导
3. **P1-1 / T1-2**：统一全文档术语为中文"轨道A/轨道B"——建立文档体系的基本一致感

**建议后续动作**：
1. 建立版本管理策略——所有文档统一至v0.5.0-alpha
2. 在 `engine-overview.md` 中新增核心术语对照表，作为术语权威来源
3. 将评级映射表、一票否决表、金字塔权重模板等高频引用数据定义为唯一权威来源，其他文档改为引用
4. 对 `false-positive-negative-testing.md` 做12档适配升级并重新运行测试案例

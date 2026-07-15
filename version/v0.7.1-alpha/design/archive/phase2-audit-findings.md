# Phase 2 全面审计结果

> 审计日期: 2026-07-09 | 审计对象: D:\sandbox\loanagent\dev\reports\ 下35份HTML报告
> 审计标准: Type 1 单标的深度分析模板 | 内容8区域(A1-A8) + 风格5项(B1-B5)

---

## 一、报告分类

| 类别 | 数量 | 说明 |
|------|------|------|
| Type 1 单标的深度分析 | 24 | 核心审计对象，应遵循模板全要素 |
| Type 2 双标的前瞻对比 | 1 | pv-longi-vs-yidao-comparison |
| Type 3 黑天鹅回溯验证 | 1 | yongmei-retrospective |
| Type 4 多身份并行评估 | 1 | huachen-multi-stakeholder |
| Type 5 债券投资仪表盘 | 1 | pv-bond-dashboard |
| Type 6 马赛克完备性报告 | 1 | longi-mosaic-completeness |
| Type 7 行业方法论 | 1 | pv-industry-methodology |
| Type 8 债项LGD评估 | 1 | longi-l22cb-lgd |
| Type 9 外部支持专项评估 | 1 | hangzhou-ext-support |
| Type 10 ESG扫描 | 1 | longi-esg-scan |
| Type 11 压力测试 | 1 | longi-stress-test |
| Type 12 引擎验证统计 | 1 | engine-validation-stats |
| **合计** | **35** | |

> 注: 24份Type 1报告按全要素A1-A8/B1-B5审计；其余11份非Type 1报告标记类型并标注适用项。

---

## 二、审计结果汇总表

### 2.1 Type 1 报告 (24份) - 内容完整性 (A1-A8) + 风格合规 (B1-B5)

| # | 报告文件 | A1 Hero | A2 Strip | A3 金字塔 | A4 市场信号 | A5 交叉对撞 | A6 风险信号 | A7 信贷建议 | A8 完备性 | B1 CSS | B2 无内联style | B3 类名使用 | B4 语义色 | B5 无硬编码色 |
|---|---------|:-------:|:--------:|:---------:|:----------:|:----------:|:----------:|:----------:|:--------:|:------:|:-------------:|:---------:|:--------:|:-----------:|
| 1 | nev-byd-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | semiconductor-smic-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(208) | ✓ | ✓ | ✗(19色) |
| 3 | solar-longi-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(190) | ✓ | ✓ | ✗(18色) |
| 4 | datacenter-gds-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 5 | equipment-kede-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6 | lgv-hangzhou-credit-report | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7 | medicaldevice-mindray-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8 | biomedicine-beigene-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(6色) |
| 9 | equipment-tuopu-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(185) | ✓ | ✓ | ✗(16色) |
| 10 | medicaldevice-wandong-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(190) | ✓ | ✓ | ✗(17色) |
| 11 | datacenter-vnet-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(189) | ✓ | ✓ | ✗(17色) |
| 12 | solar-tongwei-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(189) | ✓ | ✓ | ✗(18色) |
| 13 | biomedicine-mabwell-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(185) | ✓ | ✓ | ✗(17色) |
| 14 | lgv-qiancheng-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(185) | ✓ | ✓ | ✗(17色) |
| 15 | nev-leapmotor-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(196) | ✓ | ✓ | ✗(17色) |
| 16 | semiconductor-ziguang-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(191) | ✓ | ✓ | ✗(17色) |
| 17 | solar-ja-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(192) | ✓ | ✓ | ✗(17色) |
| 18 | semiconductor-hhg-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(223) | ✓ | ✓ | ✗(21色) |
| 19 | equipment-haas-credit-report | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(184) | ✓ | ✓ | ✗(16色) |
| 20 | biomedicine-innovent-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(188) | ✓ | ✓ | ✗(16色) |
| 21 | datacenter-chinwey-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(7色) |
| 22 | medicaldevice-lepu-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(29) | ✓ | ✓ | ✗(16色) |
| 23 | nev-xpeng-credit-report | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗(20) | ✓ | ✓ | ✗(11色) |
| 24 | lgv-wuhan-credit-report | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗(189) | ✓ | ✓ | ✗(20色) |

### 2.2 非Type 1报告 (11份) - 适用项检查

| # | 报告文件 | 类型 | A1 Hero | A2 Strip | A3-8适用 | B1 CSS | B2 内联style | B3 类名 | B4 语义色 | B5 硬编码色 |
|---|---------|:----:|:-------:|:--------:|:--------:|:------:|:----------:|:------:|:--------:|:----------:|
| 25 | pv-industry-methodology | Type 7 | ✓ | ✓(10维) | N/A | ✓ | ✗(93) | ✓ | ✓ | ✗(3色) |
| 26 | longi-esg-scan | Type 10 | ✓ | ✓(3维) | N/A | ✓ | ✗(73) | ✓ | ✓ | ✗(2色) |
| 27 | longi-stress-test | Type 11 | ✓ | ✗ | N/A | ✓ | ✗(58) | ✓ | ✓ | ✗(2色) |
| 28 | hangzhou-ext-support | Type 9 | ✓ | ✓ | N/A | ✓ | ✗(79) | ✓ | ✓ | ✗(2色) |
| 29 | engine-validation-stats | Type 12 | ✓ | ✓(6列) | N/A | ✓ | ✗(78) | ✓ | ✓ | ✗(2色) |
| 30 | pv-bond-dashboard | Type 5 | ✓ | ✓ | N/A | ✓ | ✗(76) | ✓ | ✓ | ✗(3色) |
| 31 | longi-mosaic-completeness | Type 6 | ✓ | ✓ | N/A | ✓ | ✗(50) | ✓ | ✓ | ✗(2色) |
| 32 | longi-l22cb-lgd | Type 8 | ✓ | ✗ | N/A | ✓ | ✗(95) | ✓ | ✓ | ✗(2色) |
| 33 | yongmei-retrospective | Type 3 | ✓ | ✓ | N/A | ✓ | ✗(130) | ✓ | ✓ | ✗(3色) |
| 34 | huachen-multi-stakeholder | Type 4 | ✓ | ✓ | N/A | ✓ | ✗(117) | ✓ | ✓ | ✗(3色) |
| 35 | pv-longi-vs-yidao-comparison | Type 2 | ✓ | ✓(8列) | N/A | ✓ | ✗(83) | ✓ | ✓ | ✗(3色) |

---

## 三、缺陷清单 (按严重程度排列)

### 严重缺陷 (S级)

| ID | 报告 | 问题 | 说明 |
|----|------|------|------|
| S-01 | 18份报告 | **B5: 大量硬编码色值** | 使用 `#ef4444` `#22c55e` `#f59e0b` `#6366f1` 等原生色值替代CSS变量。虽多数色值恰好对应CSS变量值，但违背"无硬编码色"规范。B5阈值: 仅允许Hero渐变<style>块中使用hex |
| S-02 | 18份报告 | **B2: 大量使用内联 style** | 160-223处`style="..."`属性(见上表)。核心违规模式: 使用`style="border-left:4px solid #..."`替代`class="card-red/green/blue"`, 使用`style="color:#..."`替代`class="text-*"` |
| S-03 | lgv-hangzhou, lgv-wuhan | **A3: 无金字塔结构** | 使用城投双轨框架而非金字塔逐层扫描。虽双轨框架有其行业合理性，但与标准金字塔模板不一致 |
| S-04 | lgv-wuhan | **A6: 风险信号不足** | 无`紧急/高危`分级风险信号清单 |
| S-05 | medicaldevice-wandong, biomedicine-mabwell, lgv-qiancheng, nev-leapmotor, semiconductor-ziguang, equipment-haas | **A4: 市场定价信号不完整** | 缺少利差(`信貸利差`)和/或资金流向(`资金流向`)模块，不足4个完整信号卡片 |

### 中等缺陷 (M级)

| ID | 报告 | 问题 | 说明 |
|----|------|------|------|
| M-01 | lgv-hangzhou | **A6: 风险信号条数不足** | 未发现`紧急/高危`分级的风险信号清单 |
| M-02 | lgv-wuhan | **A4: 市场定价信号不完整** | 缺失波动率和资金流向模块 |
| M-03 | biomedicine-beigene | **B5: 6个硬编码色** | Hero梯度中使用了`#059669` `#2563eb` 等非CSS变量色值 |
| M-04 | datacenter-chinwey | **B5: 7个硬编码色** | 包含`#4f46e5` `#0ea5e9` 等 |
| M-05 | medicaldevice-lepu | **B2: 29处内联样式** | 少量但仍有违规，主要为独立样式覆盖 |
| M-06 | nev-xpeng | **B2: 20处内联样式** | 少量但仍有违规 |

### 轻微缺陷 (W级)

| ID | 报告 | 问题 | 说明 |
|----|------|------|------|
| W-01 | 11份非Type 1报告 | **B2: 50-130处内联样式** | 非Type 1报告未严格要求遵循模板，但内联样式数量仍偏高 |
| W-02 | equipment-kede | **A6: 风险信号条数少** | 仅1处风险相关标记，未满≥3条的标准 |
| W-03 | lgv-hangzhou | 4列Strip标签命名不标准 | 使用"综合等级/政府轨/平台轨/数据置信度"而非标准"综合评级/得分/展望/置信度" |

---

## 四、按严重度的报告分布

| 严重度 | 报告数量 | 报告名称 |
|--------|---------|---------|
| **严重 (S)** | 18份 | smic, solar-longi, equipment-tuopu, wandong, vnet, tongwei, mabwell, qiancheng, leapmotor, ziguang, ja, hhg, haas, innovent, lgv-wuhan, solar-ja, solar-tongwei, semiconductor-hhg |
| **中等 (M)** | 6份 | lgv-hangzhou, lgv-wuhan, biomedicine-beigene, chinwey, lepu, xpeng |
| **轻微 (W)** | 11份 | 所有非Type 1报告 |
| **合规优秀** | 4份 | **byd, mindray, gds, kede** — 0内联样式, 0硬编码色(除hero梯度), 全内容覆盖 |

---

## 五、关键发现总结

### 5.1 内容完整性 (A1-A8)

- **A1 Hero**: 24/24 Type 1报告全部达标 ✓
- **A2 Strip**: 24/24 Type 1报告全部有4列Strip ✓
- **A3 Pyramid**: 22/24达标 — lgv-hangzhou/lgv-wuhan使用双轨框架替代金字塔结构
- **A4 Market Signal**: 17/24达标 — 7份报告缺少利差或资金流向信号卡片
- **A5 Cross Collision**: 24/24全部有轨道A vs 轨道B对撞分析 ✓
- **A6 Risk Signals**: 21/24达标 — lgv-hangzhou/lgv-wuhan/equipment-kede风险信号不足
- **A7 Credit Suggestion**: 24/24全部提供信贷建议(额度/期限/担保/贷后) ✓
- **A8 Completeness**: 24/24全部提供完备性评估 ✓

### 5.2 风格合规 (B1-B5)

- **B1 CSS引用**: 35/35全部引用`template-base.css` ✓
- **B2 无内联style**: 仅4份达标(byd/mindray/gds/kede), 其余大量使用`style="..."`属性
- **B3 类名使用**: 35/35全部使用模板类名(card/section/strip/tag/signal) ✓
- **B4 语义色**: 35/35全部使用`text-red/green/amber/blue`等语义色类 ✓
- **B5 无硬编码色**: 仅4份达标(byd/mindray/gds/kede), 其余大量直接使用`#ef4444`等hex值

### 5.3 核心矛盾

1. **两套模板风格并存**: 存在两套实现路径——"纯CSS类"风格(BYD/Mindray/GDS/Kede)与"内联style+硬编码色"风格(其余20份)。后者虽视觉呈现相似，但完全不符合B2和B5规范。

2. **行业适配导致内容差异**: 城投债报告(lgv-hangzhou/lgv-wuhan)的双轨框架替代了标准金字塔，有其行业适配的合理性，但造成A3的不达标。

3. **非Type 1报告模板套用不一**: 11份非Type 1报告(ESG/压力测试/LGD/方法论等)各自使用自建布局，普遍有50-130处内联样式。

---

## 六、修复建议

### 优先级P0 (必须修复)
1. 将18份报告的`style="border-left:4px solid #ef4444/22c55e/6366f1/f59e0b"`替换为`class="card-red/green/blue/amber"`
2. 将`style="color:#ef4444/22c55e/f59e0b/#6366f1"`替换为`class="text-red/green/amber/blue"`
3. 删除`<style>`块中的硬编码色值, 改为引用CSS变量

### 优先级P1 (建议修复)
4. 补全7份报告缺失的市场信号卡片(利差/资金流向)
5. 城投双轨报告(lgv-hangzhou/lgv-wuhan)考虑增加金字塔映射说明
6. 补充equipment-kede/lgv-hangzhou/lgv-wuhan的风险信号至≥3条

### 优先级P2 (可选优化)
7. 非Type 1报告逐步迁移至模板基类, 减少内联样式
8. 统一所有报告的hero gradient规范, 确保仅hero可使用`<style>`中的硬编码gradient

---

*审计基于 D:\sandbox\loanagent\dev\reports\ 下35份HTML报告与 D:\sandbox\loanagent\dev\design\templates\template-base.css 的对比分析*

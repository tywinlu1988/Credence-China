# 能力验证证据存档

**性质**: 引擎能力验证产物（测试输出与证据存档）
**归属**: **不是项目组成部分** · 永不进入 `version/` 版本快照

---

## 这是什么

本目录收录固定收益信用分析引擎的**能力验证产物**——即引擎在各行业、各黑天鹅案例上的**测试输出与证据存档**。它们是引擎方法论的"实验记录"，用于回溯核查引擎的分析与预警能力，**而非项目交付物本身**。

**项目本体**（engine 方法论 + templates + 设计/数据规格 + product + skill）位于根级 `dev/` 目录。本目录与本体彻底分离：

- **如何验证**（验证方法论、黑天鹅回溯、双时点对比的方法）→ 见 `dev/engine/validation-methodology.md`，属于项目本体
- **验证出了什么**（72 份实测报告、假阳性/假阴性测试执行记录）→ 存档于本目录，**不属于项目本体**

## 三项硬约束

1. 本目录内容为**测试输出**，不是项目组成部分
2. **永不进入 `version/` 版本快照**——快照 = `dev/` 完整拷贝，验证产物天然排除
3. 引擎能力的真伪以本目录证据为凭，但证据的存在不构成项目本体的功能声明

---

## 目录索引

### `reports/` — 行业/案例验证报告（72 份，15 子目录；仅 2 份方法论参照公开）

> **GitHub 公开范围**：本目录为测试输出。主仓库仅公开 2 份**行业方法论参照**——`food-beverage/food-beverage-methodology.html`、`transportation/transportation-methodology.html`（被 `dev/engine/` 范式文档在"相关内容"中引用）；其余 70 份实测报告保留在维护者本地（测试输出，非交付物），不入 GitHub，亦不进入任何版本快照。

按"13 行业 + 系统智能层 + 验证专项"组织：

| 子目录 | 行业/类别 | 报告数 |
|---|---|---|
| `solar/` | 光伏/储能 | 11 |
| `semiconductor/` | 半导体/集成电路 | 7 |
| `lgv/` | 城投债 / LGFV | 6 |
| `food-beverage/` | 食品饮料 | 4 |
| `media-internet/` | 传媒/互联网 | 4 |
| `nev/` | 新能源汽车 | 4 |
| `retail/` | 商贸零售 | 4 |
| `textile-apparel/` | 纺织服装 | 4 |
| `transportation/` | 交通运输 | 4 |
| `biomedicine/` | 生物医药/创新药 | 3 |
| `datacenter/` | 数据中心/算力基建 | 3 |
| `equipment/` | 高端装备/工业母机 | 3 |
| `medicaldevice/` | 医疗器械 | 3 |
| `system-intelligence/` | 系统智能层（传染图谱·集中度·预警温度计） | 9 |
| `validation/` | 验证专项（多利益方·行业验证汇总·回溯） | 3 |

### `docs/` — 测试执行记录

- `false-positive-negative-testing.md` — 假阳性/假阴性测试方法与多案例实测执行记录

---

## 相关

- 项目本体：`dev/`（引擎架构总览见 `dev/engine/engine-overview.md`）
- 验证方法论：`dev/engine/validation-methodology.md`
- 版本快照规则：`version/`（本目录永不纳入）

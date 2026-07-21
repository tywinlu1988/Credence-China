# 路径 → 模板 → 分层 映射视图

**版本**: v0.9.1-release

> 本表是 `credit-report-builder` 的装配映射视图：给定 `path_id`，列出应选模板与主分层。模板清单的单一事实源为 `dev/engine/work-path-registry.md`（各路径 `templates` 字段）；分层语义的单一事实源为 `dev/engine/output-layered-framework.md` §二/§三/§五。本表不含任何阈值、分层时间预算或评级值——凡数值判断以所引引擎文档为准。本表如出现与该两份文档不一致之处，以其为准。

## 装配映射

| 路径 ID | 名称 | 深度 | 主分层 | 模板 |
|---|---|---|---|---|
| WP-M0-01 | 信贷审批单标的评级 | L2 | L2 深度报告 | template-type1 + template-type6 |
| WP-M0-02 | 审贷专项附加包（LGD+外部支持） | 专项 | 专项（模板定义） | template-type8 + template-type9 |
| WP-M1-01 | 债券投资仪表盘 | L2 | L2 深度报告 | template-type5 |
| WP-M1-02 | 双标的前瞻对比 | L2 | L2 深度报告 | template-type2 |
| WP-M2-01 | 承销可行性评估 | 专项 | 专项（模板定义） | template-type16 |
| WP-M3-01 | 交易盯市信号卡 | L0 | L0 信号卡 | L0-spec |
| WP-M4-01 | 组合集中度评估 | 专项 | 专项（模板定义） | template-type14 |
| WP-M4-02 | 跨行业传染分析 | 专项 | 专项（模板定义） | template-type13 |
| WP-M4-03 | 系统性风险读数 | 专项 | 专项（模板定义） | template-type15 |
| WP-M4-04 | 组合压力测试 | 专项 | 专项（模板定义） | template-type11 |
| WP-M5-01 | 企业融资顾问 | 专项 | 专项（模板定义） | template-type17 |
| WP-X-01 | 黑天鹅回溯验证 | 专项 | 专项（模板定义） | template-type3 |
| WP-X-02 | 多身份并行评估 | L2 | L2 深度报告 | template-type4 |
| WP-X-03 | 行业分析框架建设 | 专项 | 专项（模板定义） | template-type7 |
| WP-X-04 | ESG/治理风险扫描 | 专项 | 专项（模板定义） | template-type10 |
| WP-X-05 | 展望与持续监控 | 专项 | 专项（模板定义） | template-type18 |

## 分层指针（单一事实源）

- 三层输出总览与导航关系：`dev/engine/output-layered-framework.md` §二
- L0 信号卡（版面/元素/温度计卡片）：`dev/engine/output-layered-framework.md` §三
- L1 快照（四维雷达/关键异常/评级对比/排名）：`dev/engine/output-layered-framework.md` §四
- L2 深度报告（四屏结构/导航规则）：`dev/engine/output-layered-framework.md` §五
- 完备性灯号呈现：`dev/engine/output-layered-framework.md` §8.4

## 模板标记值（与 registry §schema 一致）

- `planned`：模板待开发（无文件），如实告知"待开发"，不伪造渲染产物。
- `L0-spec`：无独立模板文件，规范定义于所引引擎文档（L0 信号卡规范见 `dev/engine/output-layered-framework.md` §三）。

> 深度档 `L0/L1/L2` 决定主分层；`专项` 路径的交付物由所选模板定义，分层语义仍以上述引擎文档为准。

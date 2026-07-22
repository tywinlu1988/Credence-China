# 质检清单（QA Checklist）

**版本**: v0.9.6-release

> 本清单是 `credit-qa-verifier` 的复核依据：六项强制检查 + 常见路径质量门。每条**规则名必须能在所引引擎文档中 grep 到**（与注册表质量门同一溯源口径），不得虚构规则。规则正文与数值以所引引擎文档为单一事实源，本清单不复制任何阈值、SRI 档位、分层时间预算或评级值。

## 六项强制检查（mandatory_checks）

任一不通过即判 `fail`：

| 检查项 | 规则名（grep 溯源） | 规则源（引擎文档） |
|---|---|---|
| density_rule | 信号密度 | engine/mosaic-engine.md §4.3 |
| density_rule | 信息不足无法评估 | engine/mosaic-engine.md §4.3 |
| veto_ceiling | 一票否决 | engine/industry-framework.md §五 |
| veto_ceiling | 上限锁定为CCC | engine/industry-framework.md §五 |
| mode_b | Mode B | engine/mosaic-engine.md §六 |
| mode_b | 数据缺口 | engine/mosaic-engine.md §六 |
| single_source | 单一事实源 | engine/work-path-registry.md |
| template_fidelity | 模板一致性 | engine/pipeline-contract.md §五 |
| methodology_fidelity | 方法论一致性 | engine/pipeline-contract.md §五 |

## 常见路径质量门（gate_results）

逐门复核按路径单 `quality_gates` 执行；完整质量门清单以 `engine/work-path-registry.md` 各路径 `quality_gates` 字段为单一事实源。下列为 active 路径常用的质量门规则名及其溯源：

| 规则名（grep 溯源） | 规则源（引擎文档） |
|---|---|
| 交叉对撞 | engine/dual-track-methodology.md §四 |
| 五维集中度 | engine/concentration-framework.md §一 |
| 温度计 | engine/systemic-warning-framework.md §三 |
| 传染矩阵 | engine/contagion-matrix.md §二 |
| 四维 | engine/multi-stakeholder.md §二 |

## 判 fail 的情形（不限于）

- 缺完备性报告（完备性为每次分析的必备产物，规则源 `engine/mosaic-engine.md` §五）。
- 密度低于下限的维度出了数值评分，或加权密度不足时出了最终字母评级。
- 触发一票否决却未锁定评级上限。
- Mode B 幻觉：用户未显式提供数据源却出现外部数据值。
- 编造阈值/权重/评级映射；引擎未定义的量未如实标注。
- 三份产物 `path_id` 不一致或在注册表不可解析。
- 残留示例数据或未清理的占位符（对照 `tests/test_template_contract.py` 的 INSTANCE_NAMES 与数值残留检测口径）。
- 报告结构自行设计或与 registry 指定模板不对应（含"参考模板风格自制"、模板外自创章节）。
- 分析维度/评分体系/框架无法溯源至引擎文档章节，或以通用信用分析先验补位。

> 本清单如出现与所引引擎文档不一致之处，以引擎文档为准。

# GEMINI.md — Credence（v0.12.1-release）

固收信贷智能分析引擎：方法论优先（methodology-first），四段链 skill 驱动。

先读 `AGENTS.md`。skills 在 `.claude/skills/`（Gemini CLI 兼容读取该目录）。

| Skill | 一句话 |
|---|---|
| `credit-analysis-router` | 模糊/复合需求四问路由到工作路径 |
| `fixed-income-credit-analysis` | 按路径单或核心文档集执行分析 |
| `credit-report-builder` | 装配交付报告（选模板、映射 L0/L1/L2） |
| `credit-qa-verifier` | 四段链终态质检（质量门 + 强制检查） |

阈值、权重、评级映射只存放在 `engine/*.md`；绝不编造数值——引用 `engine/<doc>.md §节`，引擎未定义就输出 `引擎未定义`。详情见 `AGENTS.md`。

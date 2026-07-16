# Credence · 固收信贷智能分析引擎

> 方法论优先（methodology-first）的中国固定收益信用分析引擎——以 **Agent Skills**（`SKILL.md`）形式交付的**垂直领域方法论技能包**，可安装到 Claude Code / Codex / Cursor / Gemini / OpenCode 等 agent CLI 中直接使用。

**版本** `v0.8.0-release` · **许可** 源码可见 · 限商用（见 [LICENSE](LICENSE)） · **覆盖** 13 行业 · 系统智能层（传染 / 集中度 / SRI）已上线

---

## 这是什么

Credence 把"资深固收信用分析师的方法论"打包成 agent 能直接装载执行的形态。它**不是 agent 框架，也不是独立应用**，而是一个领域方法论技能包：

| 层 | 内容 | 位置 |
|---|---|---|
| **核心资产 = 领域方法论** | 十维评分 · 双轨对撞 · 12 档评级映射 · LGD · 外部支持 · 系统智能层（28 份文档） | `dev/engine/` |
| **交付形态 = Agent Skills 包** | 四段链技能：路由 → 分析 → 报告 → 质检 | `dev/.claude/skills/` |
| **运行方式 = 嵌入现有 agent CLI** | 模型与循环借宿主的，Credence 只供给领域专长 | — |
| **辅助件** | 报告模板（Type 1–15）+ 可执行编排器（接 SRI、五维集中度两个编码引擎） | `dev/templates/` · `src/` |

**核心原则**：传统财务分析在政策驱动型、技术壁垒型、资产租约型行业中系统性失效；最重的信用因子很少出现在资产负债表上；外部评级平均滞后真实信用恶化 17 个月以上。

## 快速开始

**关键前提**：skills 并非自包含——运行时从**包根**读取 `engine/` 与 `templates/`（单一事实源，绝不复制）。因此安装单元是整个包根；**把包根当项目打开**（Model A）即可，各工具零拷贝。

### 方式 A · npx（推荐）

```bash
npx github:tywinlu1988/fixedincome
```

把当前 release 包落成 `./credence/`，然后用你的 agent CLI 打开该目录即可。

### 方式 B · GitHub Release

从 [Releases](https://github.com/tywinlu1988/fixedincome/releases) 下载最新 `vX.Y.Z-release.zip`，解压后把包根当项目打开。

### 方式 C · 克隆源码

```bash
git clone https://github.com/tywinlu1988/fixedincome.git
```

可安装的发行包在 `version/v0.8.0-release/`（浏览/拷贝即用，包内 `INSTALL.md` 有分工具说明）；方法论源码在 `dev/`。

## 仓库地图

```
dev/          方法论与技能的开发源（engine/ 28 份 · .claude/skills/ 四段链 · templates/ 15 模板）
src/          可执行编排器 + 2 个编码引擎（pipeline.py · sri_calculator.py · concentration_scorer.py）
scripts/      build_dist.py（dev/ → 发行包组装器）· consistency_check.py（一致性校验）
tests/        回归测试（150 项）
version/      当前可安装发行包 version/v0.8.0-release/（历史快照见 git 标签）
validation/   能力验证证据（验证方法论 + 8 条端到端走查 + 2 份行业方法论参照）
docs/         版本管理策略 · Codex 深度适配
AGENTS.md     跨 CLI 通用入口（任何 agent CLI 从这里开始）
```

## 文档

- **项目总览与完整目录** → [`dev/README.md`](dev/README.md)
- **引擎架构总览** → [`dev/engine/engine-overview.md`](dev/engine/engine-overview.md)
- **跨 CLI 接入（含 Codex 深度适配）** → [`AGENTS.md`](AGENTS.md) · [`docs/adapters/codex.md`](docs/adapters/codex.md)
- **版本管理策略** → [`docs/VERSION-MANAGEMENT.md`](docs/VERSION-MANAGEMENT.md)

## 许可

本仓库为**源码可见（source-available）**项目：可查看、学习、用于非商业 / 内部评估；**任何商业使用须另行取得书面许可**。详见 [LICENSE](LICENSE)。

## 免责声明

本引擎输出为方法论演示与研究产物，**不构成投资建议**。

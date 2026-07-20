# Credence · 固收信贷智能分析引擎
# Credence · Fixed-Income Credit Analysis Engine

> **方法论优先的中国固定收益信用分析引擎**——以 **Agent Skills**（`SKILL.md`）形式交付的**垂直领域方法论技能包**，可安装到 Claude Code / Codex / Cursor / Gemini / OpenCode 中直接使用。
>
> **A methodology-first credit analysis engine for China's fixed-income market** — a vertical **domain-methodology skill pack** delivered as **Agent Skills** (`SKILL.md`), installable into Claude Code / Codex / Cursor / Gemini / OpenCode.

**版本 Version** `v0.9.0-release` · **许可 License** 源码可见 · 限商用 Source-available · Non-commercial（见 [LICENSE](LICENSE)） · **覆盖 Coverage** 13 行业 industries · 系统智能层 System-intelligence (contagion / concentration / SRI) · **CI** [![CI](https://github.com/tywinlu1988/Credence-China/actions/workflows/ci.yml/badge.svg)](https://github.com/tywinlu1988/Credence-China/actions/workflows/ci.yml)

[中文](#中文) · [English](#english)

---

## 中文

**13 行业 · 16 工作路径 · 5 编码引擎 · 30 引擎文档 · 18 报告模板**

### 能力亮点

- **四段链技能**：路由 → 分析 → 报告 → 质检，意图确认后才执行，不脑补。
- **5 条可复算编码引擎路径**（WP-M0-01 旗舰聚合 / WP-M4-01 集中度 / WP-M4-02 传染矩阵 / WP-M4-03 SRI / WP-X-05 展望监控）：评级、传染、SRI、展望等数值由 Python 确定性计算，非 LLM 即兴。
- **系统智能层**：13×13 传染图谱 · 五维集中度 · SRI 预警温度计。
- **双轨交叉验证**：基本面金字塔 × 市场定价信号，分歧即洞察。
- **马赛克公开数据引擎**：零内部/付费数据，碎片信号拼图 + 完备性报告。

### 这是什么

Credence 把"资深固收信用分析师的方法论"打包成 agent 能直接装载执行的形态。它**不是 agent 框架，也不是独立应用**，而是一个领域方法论技能包：

| 层 | 内容 | 位置 |
|---|---|---|
| **核心资产 = 领域方法论** | 十维评分 · 双轨对撞 · 12 档评级映射 · LGD · 外部支持 · 系统智能层（28 份文档） | `dev/engine/` |
| **交付形态 = Agent Skills 包** | 四段链技能：路由 → 分析 → 报告 → 质检 | `dev/.claude/skills/` |
| **运行方式 = 嵌入现有 agent CLI** | 模型与循环借宿主的，Credence 只供给领域专长 | — |
| **辅助件** | 报告模板（Type 1–15）+ 可执行编排器（接 SRI、五维集中度两个编码引擎） | `dev/templates/` · `src/` |

**核心原则**：传统财务分析在政策驱动型、技术壁垒型、资产租约型行业中系统性失效；最重的信用因子很少出现在资产负债表上；外部评级平均滞后真实信用恶化 17 个月以上。

### 快速开始

**关键前提**：skills 并非自包含——运行时从**包根**读取 `engine/` 与 `templates/`（单一事实源，绝不复制）。因此安装单元是整个包根；**把包根当项目打开**（Model A）即可，各工具零拷贝。

**方式 A · npx（推荐）**

```bash
npx github:tywinlu1988/Credence-China
```

把当前 release 包落成 `./credence/`，然后用你的 agent CLI 打开该目录即可。

**更新 / 钉版本**：再次运行同一命令即得最新版（先删除或改名旧 `./credence/`——安装器不做原地更新；克隆方式用 `git pull`）。钉住历史版本：`npx github:tywinlu1988/Credence-China#v0.8.0-release`（`#` 后接任意 git 标签）。

**方式 B · GitHub Release**

从 [Releases](https://github.com/tywinlu1988/Credence-China/releases) 下载最新 `vX.Y.Z-release.zip`，解压后把包根当项目打开。

**方式 C · 克隆源码**

```bash
git clone https://github.com/tywinlu1988/Credence-China.git
```

可安装的发行包在 `version/v0.9.0-release/`（浏览/拷贝即用，包内 `INSTALL.md` 有分工具说明）；方法论源码在 `dev/`。

### 快速上手

安装（三选一）后把包根当项目打开，直接说需求即可：

```
帮我看看这家公司            → 路由四问 + 意图确认卡 → 评级
这个组合有没有问题        → 集中度 + 传染 + SRI
现在系统性风险什么水平    → SRI 读数 + 温度计
给 X 一个评级展望并盯着   → 展望 + 观察名单 + 迁移矩阵
```

### 架构

```
用户需求 → [路由: 四问 + 意图确认] → 《工作路径单》
        → [分析: 引擎文档 + 5 编码引擎] → [报告: 17 模板] → [质检: 质量门]
引擎文档（dev/engine/）是唯一事实源；编码引擎（src/）运行时解析同一文档，不复制阈值。
```

### 路线图

- **v0.9.0（规划中）**：M2 承销可行性 + M5 融资顾问路径与模板（Type 16/17），全量路径收官。
- 版本历史与发布物见 [Releases](https://github.com/tywinlu1988/Credence-China/releases)。

### 仓库地图

```
dev/          方法论与技能的开发源（engine/ 28 份 · .claude/skills/ 四段链 · templates/ 15 模板）
src/          可执行编排器 + 2 个编码引擎（pipeline.py · sri_calculator.py · concentration_scorer.py）
scripts/      build_dist.py（dev/ → 发行包组装器）· consistency_check.py（一致性校验）
tests/        回归测试（150 项）
version/      当前可安装发行包 version/v0.9.0-release/（历史快照见 git 标签）
validation/   能力验证证据（验证方法论 + 8 条端到端走查 + 2 份行业方法论参照）
docs/         版本管理策略 · Codex 深度适配
AGENTS.md     跨 CLI 通用入口（任何 agent CLI 从这里开始）
```

### 文档

- **项目总览与完整目录** → [`dev/README.md`](dev/README.md)
- **引擎架构总览** → [`dev/engine/engine-overview.md`](dev/engine/engine-overview.md)
- **跨 CLI 接入（含 Codex 深度适配）** → [`AGENTS.md`](AGENTS.md) · [`docs/adapters/codex.md`](docs/adapters/codex.md)
- **版本管理策略** → [`docs/VERSION-MANAGEMENT.md`](docs/VERSION-MANAGEMENT.md)

### 许可与免责

本仓库为**源码可见（source-available）**项目：可查看、学习、用于非商业 / 内部评估；**任何商业使用须另行取得书面许可**，详见 [LICENSE](LICENSE)。本引擎输出为方法论演示与研究产物，**不构成投资建议**。

---

## English

### What is this

Credence packages the methodology of a seasoned China fixed-income credit analyst into a form an AI agent can load and execute directly. It is **not an agent framework and not a standalone app** — it is a domain-methodology skill pack:

| Layer | Contents | Location |
|---|---|---|
| **Core asset = domain methodology** | 10-dimension scoring · dual-track cross-validation · 12-notch rating map · LGD · external support · system-intelligence layer (28 docs) | `dev/engine/` |
| **Delivery = Agent Skills pack** | 4-stage skill chain: route → analyze → report → QA | `dev/.claude/skills/` |
| **Runtime = inside existing agent CLIs** | the model and loop come from the host; Credence supplies the domain expertise | — |
| **Extras** | report templates (Type 1–15) + executable orchestrator (2 coded engines: SRI, 5-dim concentration) | `dev/templates/` · `src/` |

**Core principle**: traditional financial analysis fails systematically in policy-driven, tech-barrier, and asset-lease industries; the heaviest credit factors rarely appear on the balance sheet; external ratings lag real credit deterioration by 17+ months on average.

**13 industries · 16 work paths · 5 coded engines · 30 engine docs · 18 report templates**

### Highlights

- **Four-stage skill chain**: route → analyze → report → QA, with a mandatory intent-confirmation gate before execution.
- **5 reproducible coded-engine paths** (WP-M0-01 composite rating / WP-M4-01 concentration / WP-M4-02 contagion / WP-M4-03 SRI / WP-X-05 outlook): deterministic Python numbers, not LLM improvisation.
- **System-intelligence layer**: 13×13 contagion matrix · 5-dim concentration · SRI thermometer.
- **Dual-track cross-validation**: fundamentals pyramid × market-pricing signals.
- **Mosaic public-data engine**: zero private/paid data; fragment signals → completeness report.

### Usage examples

Install (3 options below), open the package root as a project, then just ask:

```
帮我看看这家公司            → router + intent card → rating
这个组合有没有问题        → concentration + contagion + SRI
现在系统性风险什么水平    → SRI reading + thermometer
给 X 一个评级展望并盯着   → outlook + watchlist + migration
```

### Architecture

```
Request → [Router: 4 questions + intent confirmation] → Path Sheet
        → [Analysis: engine docs + 5 coded engines] → [Report: 17 templates] → [QA gates]
Engine docs (dev/engine/) are the single source of truth; coded engines (src/) parse them at runtime.
```

### Roadmap

- **v0.9.0 (planned)**: M2 underwriting + M5 financing-advisor paths & templates (Type 16/17).
- History & artifacts: [Releases](https://github.com/tywinlu1988/Credence-China/releases).

### Quickstart

**Key premise**: the skills are NOT self-contained — at runtime they read `engine/` and `templates/` from the **package root** (single source of truth, never copied). So the install unit is the whole package root; **open the package root as your project** (Model A) and everything resolves with zero copying.

**A · npx (recommended)**

```bash
npx github:tywinlu1988/Credence-China
```

Lays the current release package into `./credence/`; open that folder with your agent CLI.

**Updating / pinning**: re-run the same command for the latest version (delete or rename the old `./credence/` first — the installer never updates in place; with a clone, use `git pull`). To pin an older release: `npx github:tywinlu1988/Credence-China#v0.8.0-release` (any git tag after `#`).

**B · GitHub Release**

Download the latest `vX.Y.Z-release.zip` from [Releases](https://github.com/tywinlu1988/Credence-China/releases), unzip, and open the package root as a project.

**C · Clone the source**

```bash
git clone https://github.com/tywinlu1988/Credence-China.git
```

The installable package is at `version/v0.9.0-release/` (browse/copy and use; see `INSTALL.md` inside for per-tool setup); methodology source lives in `dev/`.

### Repository map

```
dev/          methodology & skill source (engine/ 28 docs · .claude/skills/ 4-stage chain · templates/ 15)
src/          executable orchestrator + 2 coded engines (pipeline.py · sri_calculator.py · concentration_scorer.py)
scripts/      build_dist.py (dev/ → release-package assembler) · consistency_check.py
tests/        regression tests (150)
version/      current installable package version/v0.9.0-release/ (history via git tags)
validation/   capability evidence (validation methodology + 8 end-to-end walkthroughs + 2 industry references)
docs/         versioning strategy · Codex deep-dive adapter
AGENTS.md     cross-CLI universal entry (start here from any agent CLI)
```

### Documentation

- **Project overview & full map** → [`dev/README.md`](dev/README.md)
- **Engine architecture** → [`dev/engine/engine-overview.md`](dev/engine/engine-overview.md)
- **Cross-CLI setup (incl. Codex deep-dive)** → [`AGENTS.md`](AGENTS.md) · [`docs/adapters/codex.md`](docs/adapters/codex.md)
- **Versioning strategy** → [`docs/VERSION-MANAGEMENT.md`](docs/VERSION-MANAGEMENT.md)

### License & disclaimer

This repository is **source-available**: you may view, learn from, and use it for non-commercial / internal evaluation; **any commercial use requires prior written permission** — see [LICENSE](LICENSE). The engine's output is a methodology demonstration / research artifact and is **not investment advice**.

# INSTALL — 安装 Credence（v0.9.5-release）

Credence 是一个自包含的 agent 包。**关键前提**：skills 并非自包含——它们在运行时从
**项目根**读取 `engine/` 方法论文档与 `templates/` 报告模板（单一事实源，绝不复制）。
因此安装单元是**整个包根**，不是单独的 skills 文件夹。

## Model A — 打开为项目（推荐，零配置）

把本包根目录 `credence/` 作为你的项目/工作区打开，直接用自然语言提问
（如"帮我看看这家公司""这个组合有没有问题"），`credit-analysis-router` 会接管四问路由。
所有引用（`engine/`、`templates/`、`.claude/skills/`）从包根自动解析，各工具零拷贝即用。

```
unzip credence-v0.9.5-release.zip        # 或 git clone <repo> credence
cd credence                   # 以包根为项目根
# Claude Code: claude   ·   Codex: codex   ·   其他: 打开该文件夹
```

## Model B — 整合进你已有的项目

把**整个运行时核**拷到你项目的根目录（不只是 skills 文件夹）：

```
.claude/skills/   →  <你的项目>/.claude/skills/
engine/           →  <你的项目>/engine/
templates/        →  <你的项目>/templates/
src/              →  <你的项目>/src/        (可选，仅当要用可执行编排器)
AGENTS.md / CLAUDE.md / GEMINI.md  →  并入你项目对应的 instructions file
```

## 按工具的全局安装目标（可选）

把 `.claude/skills/` 下的 4 个 skill 目录（连同 `engine/`、`templates/`）放到对应工具的
全局技能位置，可在任意项目中使用：

| 工具 | 全局技能目标 | 入口文件 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `CLAUDE.md` |
| Codex | `~/.codex/skills/`（技能为实验特性；主用 `AGENTS.md`） | `AGENTS.md` |
| Cursor | `~/.cursor/skills/` | `AGENTS.md` |
| Gemini CLI | `~/.gemini/skills/` | `GEMINI.md` |
| OpenCode | `~/.config/opencode/skills/` | `AGENTS.md` |

> 全局安装时 `engine/` 与 `templates/` 同样需对 skills 可达（见顶部前提）。最省事、
> 最可靠的仍是 Model A——把本包根当项目打开。

## Claude Code plugin / marketplace

`.claude-plugin/plugin.json` 是一个最小的 marketplace 清单，使本包可被作为 plugin
列出/安装。注意：因 `engine/` 单一事实源依赖，作为 plugin 安装后运行时仍需 `engine/`
对 agent 的工作目录可达——可靠路径仍是 Model A。

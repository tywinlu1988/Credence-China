# 版本管理策略

**对应引擎版本**: v0.9.2-release
**最后更新**: 2026-07-20

## 目录结构约定

- `dev/` —— 当前活跃开发工作区。所有正在迭代的方法论文档、报告、模板和 Skill 都放在这里。
- `version/<version>/` —— 该版本的只读归档快照。**GitHub 清理后：主仓库 git 仅跟踪当前一个 release 快照（现为 `version/v0.9.2-release/`）；历史快照已从 git 跟踪中移除，仍可从维护者本地磁盘与 git 提交历史找回（全部发布提交均在 master 提交图内，按 SHA 检出即可）。** 一旦快照创建，仅允许通过补丁分支修正明显错误，不允许继续功能迭代。
- `version/<version>.zip` —— 该版本归档的压缩包，**作为 GitHub Releases 附件对外分发**（不提交进仓库；`*.zip` 已 gitignore）。
- `validation/` —— 引擎能力验证产物（测试输出与证据存档），**不属于项目本体**，永不进入 `version/` 快照。

**快照边界**：自 **v0.8.0-release** 起，`version/<version>/` = **`scripts/build_dist.py` 产出的可安装 agent 包**（= `dist/credence/` 的内容）：skills 归位 `.claude/skills/`、`engine/` 平铺、`templates/`、`src/`、`adapters/`，加生成的 `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`INSTALL.md`/`README.md`/`.claude-plugin/plugin.json`。该包已清除死链接与根目录假设（剔除 `settings.local.json` 绝对路径、`engine/audits/`、`design/`、`product/`、`data/`、`validation/`，并模式化清除 16 处 audits/validation 溯源指针）。**例外**：`v0.8.0-alpha` 为旧的镜像三根布局（`dev/` + `AGENTS.md` + `src/`），系集成预发布、未做可安装化。`validation/` 验证产物永不入快照；`version/`（历史快照）、`scripts/`、`tests/`、`docs/` 及任何 `.git`/`__pycache__`/`*.pyc` 亦不入快照。

## 版本号体系

### 引擎版本

- 格式: `v<major>.<minor>.<patch>-<stage>`
- 适用范围: `dev/engine/` 下的所有核心方法论文档、Skill 包、模板和报告。
- 当前: `v0.9.2-release`
- 升级触发条件:
  - 新增功能模块或行业覆盖 → 递增 minor 版本
  - 方法论重大重构或评级体系变更 → 递增 major 版本
  - 一致性修复、术语统一、阈值对齐 → 递增 patch 版本

### 审查报告版本

- 格式: `v<major>.<minor>`（如 v1.0, v1.1）
- 适用范围: `dev/engine/*-audit.md`, `dev/engine/*-review-*.md`, `dev/engine/self-assessment-*.md`
- 必须在文件头标注: `**对应引擎版本**: vX.Y.Z-<stage>`

## 发布检查清单

在创建新的 `version/<version>/` 快照前，必须完成以下检查：

- [ ] `python scripts/promote.py vX.Y.Z-<stage>`（dry-run 预览）→ `--apply` 落盘，且打印的"规则未覆盖剩余"经人工核对全部为历史引用；两个版本历史表（engine-overview §六、dev/README.md）已人工补新行。
- [ ] 所有核心方法论文档的 `**版本**:` 头统一为当前引擎版本。
- [ ] Claude Skill 包 (`dev/.claude/skills/fixed-income-credit-analysis/`) 已同步并升级到当前引擎版本。
- [ ] Skill 包已随构建归位到 `version/<version>/.claude/skills/`（v0.8.0-release 起为包根 `.claude/skills/`，由 `scripts/build_dist.py` 生成）。
- [ ] `scripts/consistency_check.py` 运行通过（无断裂链接、版本号一致、SRI 示例在合法范围内）。
- [ ] `python scripts/build_dist.py` 构建 + 内置校验通过（零绝对路径、零 dev/ token、全链接可解析、4 skill 严格 frontmatter、28 份 CORE_DOCS 齐备）。
- [ ] 所有模板和报告的版本号与引擎版本对齐。
- [ ] `dev/README.md` 的版本历史和目录结构描述已更新。
- [ ] 压缩包 `version/<version>.zip` 已生成。

## 快照创建流程

1. 在 `dev/` 完成所有变更并通过回归门（`scripts/consistency_check.py` 与 `pytest` 全绿）。
2. 运行 `python scripts/build_dist.py`：把 `dev/` 源确定性组装为 `dist/credence/` 可安装包（复制 + 引用重写 + 溯源指针清除 + 入口/安装文档生成），并通过其内置校验（零绝对路径、零 dev/ token、全链接可解析）。
3. 把 `dist/credence/` 的内容复制为 `version/<version>/`（**v0.8.0-release 起**；`dist/` 本身是 gitignored 构建产物，提交的快照在 `version/`）。
4. 生成 `version/<version>.zip`（顶层为 `version/<version>/` 单根目录，跨平台），作为 **GitHub Releases 附件**上传分发（**不提交进仓库**；`*.zip` 已 gitignore）。
5. **git 跟踪约定**：主仓库仅跟踪**当前一个 release** 的 `version/<version>/` 目录。发新版时 `git rm -r` 旧 release 目录（**不带 `--cached`**——避免与 merge 叠加误删工作区文件的陷阱）、`git add` 新 release 目录，并把 `.gitignore` 里 `version/*` 的 `!version/<旧>/` 反例行改为 `!version/<新>/`。历史快照保留在本地磁盘与 git 提交历史。**git 标签约定（2026-07-17 起）**：标签与 Release **留痕保留、不再清理**——历史版本可按标签直接检出/下载，也支持 `npx github:tywinlu1988/Credence-China#<tag>` 钉版本安装；GitHub 的 Latest 标记始终指向最新 Release。主仓库 git 仍仅跟踪当前一个 release 快照目录。（此前约定为"远程仅保留当前 release 标签"；v0.8.0 及更早的历史标签已删，相应提交可从 master 历史按 SHA 找回。）
6. 更新 `dev/README.md` 与 `dev/engine/engine-overview.md` 的版本历史。

> **v0.8.0-alpha 例外**：该快照为旧的镜像三根布局——手动把 `dev/`、`src/` 整拷贝 + 根级 `AGENTS.md` 复制到 `version/v0.8.0-alpha/`，未经 `build_dist.py` 可安装化。自 v0.8.0-release 起统一走上述 build_dist 流程。

## 快照内部布局

自 **v0.8.0-release** 起，快照是一个**自包含的可安装 agent 包**（`scripts/build_dist.py` 产出的 `dist/credence/` 内容）——skills 归位到包根 `.claude/skills/`（Claude Code 原生发现 + Cursor/Gemini/OpenCode 兼容读），方法论文档平铺到 `engine/`，并生成各 agent CLI 的入口/安装文件：

```
version/<version>/
├── AGENTS.md / CLAUDE.md / GEMINI.md / INSTALL.md / README.md   ← 生成的跨 CLI 入口与安装说明
├── .claude-plugin/plugin.json        ← Claude Code marketplace 清单
├── .claude/skills/<4 skills>/        ← 四段链技能（intake/analysis/report/qa）
├── engine/          ← 28 份方法论文档（剔除 audits/，清除溯源指针）
├── templates/       ← Type 1–15 报告模板
├── src/             ← 可执行编排器 + 已编码引擎（pipeline.py path_sheet.py sri_calculator.py concentration_scorer.py …）
└── adapters/codex.md ← Codex 深度适配
```

> **历史快照差异**：≤ v0.7.1-release 的旧快照为 `dev/` 单根**扁平**拷贝（`version/<v>/` 顶层即 `dev/` 内容）；`v0.8.0-alpha` 为**镜像三根**布局（`dev/` + `src/` + `AGENTS.md`，未可安装化）；自 **v0.8.0-release** 起改为上述可安装包布局。

# 版本管理策略

**对应引擎版本**: v0.8.0-alpha
**最后更新**: 2026-07-16

## 目录结构约定

- `dev/` —— 当前活跃开发工作区。所有正在迭代的方法论文档、报告、模板和 Skill 都放在这里。
- `version/<version>/` —— 该版本的只读归档快照。一旦快照创建，仅允许通过补丁分支修正明显错误，不允许继续功能迭代。
- `version/<version>.zip` —— 该版本归档的压缩包，用于对外分发。
- `validation/` —— 引擎能力验证产物（测试输出与证据存档），**不属于项目本体**，永不进入 `version/` 快照。

**快照边界**：自 **v0.8.0** 起，`version/<version>/` = **`dev/` + `AGENTS.md` + `src/`** 三个根（此前为 `dev/` 单根完整拷贝）。`validation/` 验证产物天然排除在外；`version/`（历史快照）、`scripts/`、`tests/`、`docs/` 及任何 `.git`/`__pycache__`/`*.pyc` 亦不入快照。

## 版本号体系

### 引擎版本

- 格式: `v<major>.<minor>.<patch>-<stage>`
- 适用范围: `dev/engine/` 下的所有核心方法论文档、Skill 包、模板和报告。
- 当前: `v0.8.0-alpha`
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

- [ ] 所有核心方法论文档的 `**版本**:` 头统一为当前引擎版本。
- [ ] Claude Skill 包 (`dev/.claude/skills/fixed-income-credit-analysis/`) 已同步并升级到当前引擎版本。
- [ ] Skill 包已随 `dev/` 完整复制到 `version/<version>/dev/.claude/skills/`（v0.8.0 起为 `dev/` 子目录）。
- [ ] `scripts/consistency_check.py` 运行通过（无断裂链接、版本号一致、SRI 示例在合法范围内）。
- [ ] 所有模板和报告的版本号与引擎版本对齐。
- [ ] `dev/README.md` 的版本历史和目录结构描述已更新。
- [ ] 压缩包 `version/<version>.zip` 已生成。

## 快照创建流程

1. 在 `dev/` 完成所有变更并通过一致性检查。
2. 自 v0.8.0 起，快照含三个根：把 `dev/` 完整复制到 `version/<version>/dev/`，把 `src/` 完整复制到 `version/<version>/src/`，把根级 `AGENTS.md` 复制到 `version/<version>/AGENTS.md`。
3. 在 `version/<version>/` 中删除 `.git/`、`__pycache__/`、`*.pyc`（如果误复制）。
4. 用 `shutil.make_archive` 生成 `version/<version>.zip`（跨平台）。
5. 更新 `dev/README.md` 的版本历史。

## 快照内部布局

自 **v0.8.0** 起，快照采用**镜像（mirrored）三根布局**：因纳入 `dev/`、`src/`、`AGENTS.md` 三个根，各自保留原名作为子目录/文件，自我描述、互不混淆（不再像旧快照那样把 `dev/` 扁平化到顶层）：

```
version/<version>/
├── dev/            ← 开发工作区完整拷贝（engine/ templates/ design/ data/ product/ .claude/skills/ README.md …）
├── src/            ← 可执行编排器 + 已编码引擎（pipeline.py path_sheet.py sri_calculator.py concentration_scorer.py …）
└── AGENTS.md       ← 跨 CLI 通用入口（仓库根级）
```

> **历史快照差异**：v0.8.0 之前的旧快照（≤ v0.7.1-release）为 `dev/` 单根**扁平**拷贝——`version/<v>/` 顶层即 `dev/` 内容（如 `README.md`、`engine/`、`templates/`、`.claude/`）。自 v0.8.0 起改为上述三根镜像布局。

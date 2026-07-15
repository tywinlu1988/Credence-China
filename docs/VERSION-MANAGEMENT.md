# 版本管理策略

**对应引擎版本**: v0.7.1-release
**最后更新**: 2026-07-15

## 目录结构约定

- `dev/` —— 当前活跃开发工作区。所有正在迭代的方法论文档、报告、模板和 Skill 都放在这里。
- `version/<version>/` —— 该版本的只读归档快照。一旦快照创建，仅允许通过补丁分支修正明显错误，不允许继续功能迭代。
- `version/<version>.zip` —— 该版本归档的压缩包，用于对外分发。
- `validation/` —— 引擎能力验证产物（测试输出与证据存档），**不属于项目本体**，永不进入 `version/` 快照。快照 = `dev/` 完整拷贝，验证产物天然排除在外。

## 版本号体系

### 引擎版本

- 格式: `v<major>.<minor>.<patch>-<stage>`
- 适用范围: `dev/engine/` 下的所有核心方法论文档、Skill 包、模板和报告。
- 当前: `v0.7.1-release`
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
- [ ] Skill 包已复制到 `version/<version>/.claude/skills/fixed-income-credit-analysis/`。
- [ ] `scripts/consistency_check.py` 运行通过（无断裂链接、版本号一致、SRI 示例在合法范围内）。
- [ ] 所有模板和报告的版本号与引擎版本对齐。
- [ ] `dev/README.md` 的版本历史和目录结构描述已更新。
- [ ] 压缩包 `version/<version>.zip` 已生成。

## 快照创建流程

1. 在 `dev/` 完成所有变更并通过一致性检查。
2. 复制 `dev/` 的全部内容到 `version/<version>/`。
3. 在 `version/<version>/` 中删除 `.git/`（如果误复制）。
4. 生成 `version/<version>.zip`。
5. 更新 `dev/README.md` 的版本历史。

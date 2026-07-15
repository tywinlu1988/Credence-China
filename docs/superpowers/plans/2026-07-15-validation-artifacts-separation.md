# 验证产物与项目本体分离清理计划

**日期**: 2026-07-15
**分支**: `separate-validation-artifacts`（从 master 切出，完成后 --no-ff 合并）
**背景**: 用户纠正——72 份报告及各类验证项目是**引擎能力验证的测试输出**，不是项目组成部分。此前被错误纳入 dev/ 本体、README 成果表和版本快照。

**用户三项裁决**：
1. 72 份验证报告 → 移入根级 `validation/`（保留可查，永不入快照）
2. 只重建 v0.7.1 快照（剔除报告）；v0.7.0 及更早快照作历史保留
3. README/SKILL.md 中的验证结果表格与案例清单 → **完全移除**（非降级引用）

**修正后的本体边界**：
- 项目本体 = engine 方法论 + templates + design/data 规格 + product + skill + scripts/src/tests
- 验证证据 = 根级 `validation/`（测试输出存档）
- 保留判断：`engine/validation-methodology.md` 是"如何验证"的方法论 → 留 engine/；`engine/false-positive-negative-testing.md` 是"5案例实测结果" → 移 validation/docs/；`engine/audits/` 是文档质量审查史 → 不动

---

## Task 1: 迁移验证产物

**Files:**
- Move: `dev/reports/`（72份，15子目录）→ `validation/reports/`
- Move: `dev/engine/false-positive-negative-testing.md` → `validation/docs/`
- Create: `validation/README.md`
- Modify: `dev/engine/paradigm-brand-channel.md`、`paradigm-network-traffic.md`（报告链接）、`dev/engine/engine-overview.md`（fp/np 文档链接 + 验证状态内容检查）

- [ ] **Step 1**: `git mv dev/reports validation/reports`（保持 15 子目录结构）；`mkdir -p validation/docs && git mv dev/engine/false-positive-negative-testing.md validation/docs/`
- [ ] **Step 2**: 创建 `validation/README.md`，明确声明：
  - 本目录为引擎**能力验证产物**（测试输出/证据存档），**不是项目组成部分**
  - 永不进入 `version/` 版本快照；验证方法论见 `dev/engine/validation-methodology.md`
  - 目录索引：reports/（72份，15子目录：13行业+system-intelligence+validation）、docs/（测试执行记录）
- [ ] **Step 3**: CSS 链接重写：移动后报告位于 `validation/reports/<sub>/`，`../../templates/template-base.css` → `../../../dev/templates/template-base.css`（71份）；验证 `grep -rn "\.\./\.\./templates" validation/ | wc -l` = 0
- [ ] **Step 4**: 更新 engine 文档链接：
  - `paradigm-brand-channel.md:436` → `../../validation/reports/food-beverage/food-beverage-methodology.html`
  - `paradigm-network-traffic.md:428` → `../../validation/reports/transportation/transportation-methodology.html`
  - `engine-overview.md` 中 false-positive-negative-testing.md 引用 → `../validation/docs/false-positive-negative-testing.md`（按实际相对深度）；并检查其中验证状态/成果罗列内容，结果类表述移除（纯导航保留）
- [ ] **Step 5**: 验证 `python scripts/consistency_check.py` + `python -m pytest tests/ -q` 全绿
- [ ] **Step 6**: Commit `refactor(validation): separate validation artifacts from project body to root validation/`

## Task 2: 文档净化（README + SKILL.md + 测试适配）

- [ ] **Step 1**: `dev/README.md` 完全移除：
  - "方法论验证（13/13 行业完成）"整表
  - "系统智能层"表中引用验证报告的"核心文档"列的复盘/情景报告表述（保留方法论模块行，删报告份数描述）
  - "报告与模板"表 → 仅保留模板行（15种，templates/）
  - "黑天鹅回溯验证（3/3 完成）"整表、"假阳性/假阴性测试（完成）"整节
  - 快速导航中"13行业完整验证结果 reports/（71份报告）"行及指向具体报告的行
  - engine 计数 26 → 25（fp/np 已移出），目录树相应更新
  - 加一行中性事实说明：能力验证证据存档于根级 `../validation/`（非项目组成部分）
- [ ] **Step 2**: SKILL.md 完全移除 `## Black-Swan Retrospective Validation` 与 `## Validated Industries & Cases` 两节（含 14 行业表格）；版本历史表保留（changelog 非验证表格）
- [ ] **Step 3**: `tests/test_engine_coherence.py` 中 skill 验证声明测试适配（表格已删，测试改为断言这两节不存在，防回归）
- [ ] **Step 4**: 验证三件套（pytest / checker / TOC 抽查）
- [ ] **Step 5**: Commit `docs(readme,skill): remove validation result tables and case lists from project docs`

## Task 3: 制度固化 + v0.7.1 快照重建

- [ ] **Step 1**: `docs/VERSION-MANAGEMENT.md` 增补规则："根级 `validation/` 为验证产物（测试输出），不属于项目本体，**永不进入 `version/` 快照**；快照 = `dev/` 完整拷贝，验证产物天然排除"
- [ ] **Step 2**: 重建快照：
  ```bash
  rm -rf version/v0.7.1-alpha version/v0.7.1-alpha.zip
  cp -r dev version/v0.7.1-alpha
  rm -rf version/v0.7.1-alpha/.git
  rm -f version/v0.7.1-alpha/.claude/settings.local.json
  powershell Compress-Archive
  ```
  验证：快照内**无 reports/ 目录**、templates/=16、engine=25+audits/15、README 无验证表格；`unzip -t` 通过
- [ ] **Step 3**: README 版本历史 v0.7.1-alpha 行附注："快照于 2026-07-15 重建：剔除验证报告（验证产物不属于项目本体）"
- [ ] **Step 4**: 全量验证 + Commit `release: rebuild v0.7.1-alpha snapshot excluding validation artifacts`
- [ ] **Step 5**: 合并 master（--no-ff）后，本地重锚 tag：`git tag -f v0.7.1-alpha`（tag 未推送，重锚安全）——向用户披露

---

## 执行方式

subagent-driven：Task 1→2→3 顺序派发 implementer + reviewer，ledger 记账于 `.superpowers/sdd/progress.md`。

**注意**：`dev/reports/` 整体移出 dev 后，`dev/README.md` 目录树、engine-overview 导航、checker 的链接检查（check_links 覆盖 engine md 中的 html 链接）都会受影响，必须同 Task 内原子完成。

#!/usr/bin/env python3
"""Credence 可安装 agent 包的确定性组装器（版本戳派生自 engine-overview.md 头，见 _version()）。

把 `dev/` 工作区（源）组装为 `dist/credence/`（产物）——一个自包含、可移植、
可按行业惯例安装到 Claude Code / Codex / Cursor / Gemini / OpenCode 的 agent 包。
`dev/` 布局保持不变（checker 与测试继续验证它）；本脚本只**复制+重写+清除**，
产出即 `version/<v>-release/` 与 zip 的内容。这是标准的 source-vs-artifact 模型。

## 布局契约（dist 测试 test_dist_package.py 与本脚本共同遵守的唯一参照）

dist/credence/
├── AGENTS.md / CLAUDE.md / GEMINI.md / INSTALL.md / README.md   (生成)
├── .claude-plugin/plugin.json                                   (生成)
├── .claude/skills/<4 skills>/{SKILL.md,references/}            (dev/.claude/skills 复制+重写)
├── engine/          (dev/engine 剔除 audits/, 重写+清除溯源指针)
├── templates/       (dev/templates 全量)
├── src/             (剔除 __pycache__/*.pyc, 注释重写)
└── adapters/codex.md (自 docs/adapters 移入+重写)

## 引用重写规则（有序，最长前缀优先；对每个复制的文本文件应用）
1. `dev/.claude/skills/` → `.claude/skills/`
2. `dev/engine/`         → `engine/`
3. `dev/templates/`      → `templates/`
4. `../../src/`          → `../src/`        (engine-overview.md 的深度位移链接)
注：`multi-stakeholder.md` 的 `../engine/`、`../templates/` 在两种布局下都解析，不动。

## 溯源指针清除（模式化，非行号；每处记日志）
- 行内片段剥除：`（…audits/…）` / `(…audits/…)` 括号片段（保留句子）。
- 整行删除：剥除后仍含 `audits/` 的纯指针行（表行/来源注/要点）。
- 整行删除：含 `validation/` 路径 token 的行（validation/ 已剔除出包）。

## 剔除（绝不允许进入 dist）
`settings.local.json`、`__pycache__`、`*.pyc`、`engine/audits/`、`design/`、
`product/`、`data/`、`validation/`、`.git/`、`version/`、`tests/`、`scripts/`、
`docs/`（除 adapters/codex.md）、`dev/README.md`（生成新包 README 替代）。

## 校验（--check 或构建后自动执行；任一失败即响亮退出）
(i) 零 `[A-Za-z]:[\\/]` 绝对路径；(ii) 零残留 `dev/` 路径 token；(iii) 每个相对
链接在 dist 内可解析；(iv) 4 个 SKILL.md 且 frontmatter 恰为 name+description；
(v) 28 份 CORE_DOCS 全部在 engine/ 下；(vi) src 能在 dist 布局定位 engine/templates；
(vii) 无任何被剔除的产物。
(viii) 文本文件无 CRLF（LF 强制，见根 .gitattributes）。
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "dev"
DIST = ROOT / "dist" / "credence"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from consistency_check import CORE_DOCS  # noqa: E402  单一事实源，不复制清单

# 有序引用重写（最长前缀优先）。skills 规则不带尾斜杠以同时覆盖
# `dev/.claude/skills` 与 `dev/.claude/skills/...` 两种形态。
REWRITE_RULES = [
    ("dev/.claude/skills", ".claude/skills"),
    ("dev/engine/", "engine/"),
    ("dev/templates/", "templates/"),
    ("../../src/", "../src/"),
]

TEXT_EXTS = {".md", ".py", ".html", ".css", ".yaml", ".yml", ".txt", ".json"}

SKILL_NAMES = [
    "credit-analysis-router",
    "fixed-income-credit-analysis",
    "credit-report-builder",
    "credit-qa-verifier",
]

ABS_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")  # 盘符前不得为字母（排除 https:// 等 scheme）
DEV_TOKEN_RE = re.compile(r"(?<![\w/.-])dev[/\\]")
# 行内 audits 括号片段（全角/半角括号），剥除但保留句子。
AUDIT_FRAGMENT_RE = re.compile(r"（[^（）]*audits/[^（）]*）|\([^()]*audits/[^()]*\)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# 复制 + 重写 + 清除
# ---------------------------------------------------------------------------

def _apply_rewrites(text: str) -> str:
    for old, new in REWRITE_RULES:
        text = text.replace(old, new)
    return text


def _scrub(text: str, rel: str, log: list) -> str:
    """溯源指针清除：先剥行内 audits 片段，再删残留 audits//validation/ 指针行。"""
    text, n_frag = AUDIT_FRAGMENT_RE.subn("", text)
    for _ in range(n_frag):
        log.append(f"fragment-strip (audits paren) in {rel}")
    kept = []
    for line in text.split("\n"):
        if "audits/" in line or "validation/" in line:
            log.append(f"drop pointer line in {rel}: {line.strip()[:70]}")
            continue
        kept.append(line)
    return "\n".join(kept)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _copy_and_transform(src: Path, dst: Path, log: list, scrub: bool) -> None:
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        if "__pycache__" in f.parts or f.suffix == ".pyc" or f.name == "settings.local.json":
            log.append(f"excluded: {f.relative_to(src)}")
            continue
        rel = f.relative_to(src)
        out = dst / rel
        if f.suffix in TEXT_EXTS:
            text = f.read_text(encoding="utf-8")
            text = _apply_rewrites(text)
            if scrub:
                text = _scrub(text, str(rel), log)
            _write_text(out, text)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, out)


# ---------------------------------------------------------------------------
# 生成的入口 / 安装文件（版本戳派生自 engine-overview.md 头，不硬编码）
# ---------------------------------------------------------------------------

def _version() -> str:
    text = (DEV / "engine" / "engine-overview.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*版本\*\*\s*[:：]\s*(\S+)", text)
    return m.group(1) if m else "v0.9.5-release"


def _gen_agents_md(v: str) -> str:
    return f"""# AGENTS.md — Credence 跨 CLI 通用入口

**项目**：Credence（固收信贷智能分析引擎）
**引擎版本**：{v}
**一句话**：方法论优先（methodology-first）的信用分析引擎；可移植单元是 `SKILL.md`。

> 任何 agent CLI 都从这里开始：先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。
> 安装与按工具接入详见 `INSTALL.md`。

## 这个包是什么

面向中国固定收益市场的信用分析引擎，分四层（four-layer）：

1. **马赛克引擎（Mosaic）** — 把碎片化公开数据拼成连贯信号；数据缺口本身即风险信号。
2. **双轨引擎（Dual-Track）** — 行业多层金字塔（基本面）与市场定价信号并行，再交叉对撞。
3. **多利益相关者（Multi-Stakeholder）** — M0 审贷 / M1 投资 / M2 承销 / M3 交易 / M4 风控 / M5 融资多视角。
4. **系统智能层（System-Intelligence, SRI）** — 跨行业传染、五维集中度、系统性风险指数（SRI）。

**阈值、权重、评级映射只存放在 `engine/*.md`。** 本文件与任何 skill 都不复制这些数值；凡涉及数值判断，一律引用引擎文档 + 章节。

## 如何在你的 agent CLI 中使用

本包是自包含的可安装 agent 包，skills 实体在 `.claude/skills/`。**最简单的方式（Model A）**：把本包根目录作为你的项目打开即可，全部引用自动解析。

| agent CLI | 如何接入 |
|---|---|
| **Claude Code** | 自动发现 `.claude/skills/`（把本包根当项目打开）；`CLAUDE.md` 指向本文件。惯例分发渠道为 plugin/marketplace（见 `.claude-plugin/plugin.json`）。 |
| **Codex** | 原生读本 `AGENTS.md`；随后手动读当前任务的 `SKILL.md` 正文。深度适配见 `adapters/codex.md`。 |
| **Cursor** | 读本 `AGENTS.md`，并兼容读取 `.claude/skills/`。 |
| **Gemini** | 读 `GEMINI.md`，并兼容读取 `.claude/skills/`。 |
| **OpenCode** | 读本 `AGENTS.md`，并兼容读取 `.claude/skills/`。 |

统一姿势：**先读你的 instructions file，再读当前任务对应的那份 `SKILL.md`。** 把本包整合进你已有的项目（Model B）或做全局安装的目标路径，见 `INSTALL.md`。

## Skill 索引

| Skill | 何时使用（Use when…） | 路径 |
|---|---|---|
| `credit-analysis-router` | 需求模糊或复合（"帮我看看这家公司""该做哪种分析""该从哪儿入手"），需先四问路由到工作路径 | `.claude/skills/credit-analysis-router/SKILL.md` |
| `fixed-income-credit-analysis` | 已点名的具体方法论任务或引擎路径，按路径单或核心文档集执行分析 | `.claude/skills/fixed-income-credit-analysis/SKILL.md` |
| `credit-report-builder` | 把完成的信用分析装配为交付报告（选模板 Type 1–15、映射 L0/L1/L2 层、装配仪表盘）；需上游分析产物，自身不做分析 | `.claude/skills/credit-report-builder/SKILL.md` |
| `credit-qa-verifier` | 交付前复核报告/分析（质量门、密度规则、一票否决上限、Mode B 护栏、单源合规）；四段链终态质检 | `.claude/skills/credit-qa-verifier/SKILL.md` |

## 四段管线

引擎把一次信用分析拆成四段链式契约，`path_id` 是贯穿各段的 join key：

| 阶段 | 职责 | 承载 skill |
|---|---|---|
| ① intake | 四问路由，产出《工作路径单》 | `credit-analysis-router` |
| ② analysis | 按路径单 `engine_reading_order` 执行分析 | `fixed-income-credit-analysis` |
| ③ report | 把完成的分析装配为交付报告 | `credit-report-builder` |
| ④ qa | 交付前质量门复核 | `credit-qa-verifier` |

四段产物（工作路径单 / 分析产物 / 交付单 / 质检裁决）的字段形状与链式边的单一事实源为 `engine/pipeline-contract.md`。

**可执行编排器**：`src/pipeline.py` 以代码驱动四段链，从 `pipeline-contract.md` 读阶段定义，仅对已接线路径调用编码引擎——**WP-M4-03 → SRI（`src/sri_calculator.py`）、WP-M4-01 → 五维集中度（`src/concentration_scorer.py`）**；其余路径仍由 LLM 按引擎文档编排。

## 单一事实源规则

**绝不复制阈值、权重、SRI 档位、评级映射或分层时间预算。** 任何数值判断都引用 `engine/<doc>.md §节`；引擎文档未定义就输出 `引擎未定义`，不得编造数值。

## 路由基线（工作路径注册表）

`engine/work-path-registry.md` 是路由单一事实源：**16 条工作路径（8 条 active / 6 条 partial / 2 条 planned）**。router 据此把模糊需求路由到具体工作路径；推荐到 planned 路径时须如实告知"待开发"并给出可替代的 active 路径。

## 平台中立说明

本文件与各 skill 统一称"你的 instructions file"——每个 agent CLI 的项目级指令文件名各不相同，本包不假定任何特定产品文件名。引用字面路径 `.claude/skills` 是允许的：那是一个路径，不是一条行为指令。

## 开发者回归门（需完整源码仓库）

本安装包是**运行时产物**，不含测试与一致性校验脚本。若要运行回归门（`pytest` + `consistency_check.py`）或修改方法论本身，请克隆完整源码仓库。
"""


def _gen_claude_md() -> str:
    return """# CLAUDE.md — Credence

先读 `AGENTS.md`。skills 在 `.claude/skills/`。

阈值、权重、评级映射只存放在 `engine/*.md`；绝不编造数值——引用 `engine/<doc>.md §节`，引擎未定义就输出 `引擎未定义`。
"""


def _gen_gemini_md() -> str:
    return """# GEMINI.md — Credence

先读 `AGENTS.md`。skills 在 `.claude/skills/`（Gemini CLI 兼容读取该目录）。

阈值、权重、评级映射只存放在 `engine/*.md`；绝不编造数值——引用 `engine/<doc>.md §节`，引擎未定义就输出 `引擎未定义`。
"""


def _gen_install_md(v: str) -> str:
    return f"""# INSTALL — 安装 Credence（{v}）

Credence 是一个自包含的 agent 包。**关键前提**：skills 并非自包含——它们在运行时从
**项目根**读取 `engine/` 方法论文档与 `templates/` 报告模板（单一事实源，绝不复制）。
因此安装单元是**整个包根**，不是单独的 skills 文件夹。

## Model A — 打开为项目（推荐，零配置）

把本包根目录 `credence/` 作为你的项目/工作区打开，直接用自然语言提问
（如"帮我看看这家公司""这个组合有没有问题"），`credit-analysis-router` 会接管四问路由。
所有引用（`engine/`、`templates/`、`.claude/skills/`）从包根自动解析，各工具零拷贝即用。

```
unzip credence-{v}.zip        # 或 git clone <repo> credence
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
"""


def _gen_readme_md(v: str) -> str:
    return f"""# Credence — 固收信贷智能分析引擎（{v}）

方法论优先的中国固定收益信用分析引擎：行业多层金字塔 + 双轨交叉验证 + 马赛克公开数据引擎 +
多利益相关者视角 + 系统智能层（传染/集中度/SRI）。以 **Agent Skills**（`SKILL.md`）形式分发，
可在 Claude Code / Codex / Cursor / Gemini / OpenCode 中安装使用。

## 快速开始
见 **`INSTALL.md`**（推荐 Model A：把本包根当项目打开，零配置）。入口为 **`AGENTS.md`**。

## 包内容
- `.claude/skills/` — 四段链技能（intake 路由 → analysis 分析 → report 报告 → qa 质检）
- `engine/` — 28 份方法论文档（阈值/权重/评级映射的单一事实源）
- `templates/` — Type 1–15 报告模板
- `src/` — 可执行编排器与 2 个编码引擎（SRI、五维集中度）
- `adapters/` — 按工具的深度适配说明
"""


def _gen_plugin_json(v: str) -> str:
    import json
    manifest = {
        "name": "credence",
        "version": v.lstrip("v"),
        "description": "固收信贷智能分析引擎（Credence）：行业多层金字塔 + 双轨交叉验证 + "
        "马赛克引擎 + 系统智能层。四段链技能：intake 路由 / analysis 分析 / report 报告 / qa 质检。",
        "skills": ".claude/skills/",
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def _gen_adapter_codex(log: list) -> str:
    src = ROOT / "docs" / "adapters" / "codex.md"
    text = src.read_text(encoding="utf-8")
    text = _apply_rewrites(text)
    # dist 无 tests/scripts：把"运行两道校验器"改为 Model-A 用法说明。
    text = re.sub(
        r"## 4\. 运行两道校验器.*",
        "## 4. 说明\n\n本适配面向**安装包**使用者。安装包为运行时产物，不含测试与一致性校验脚本；"
        "若要运行回归门（`pytest` + `consistency_check.py`）或修改方法论，请克隆完整源码仓库。\n",
        text,
        flags=re.DOTALL,
    )
    return text


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def _check_links(errors: list, base: Path) -> None:
    for f in sorted(base.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if (
                (f.parent / target).exists()
                or (base / target).exists()
                or (base / "engine" / target).exists()
            ):
                continue
            errors.append(f"BROKEN_LINK: {f.relative_to(base)} -> {target}")


def validate(out_dir=None) -> list:
    base = Path(out_dir) if out_dir is not None else DIST
    errors = []
    if not base.is_dir():
        return [f"dist missing: {base}"]

    for f in sorted(base.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(base)
        # (vii) 剔除物不得出现
        if "__pycache__" in f.parts or f.suffix == ".pyc" or f.name == "settings.local.json":
            errors.append(f"EXCLUDED_PRESENT: {rel}")
        if "audits" in f.parts or f.parts[0] in ("design", "product", "data", "validation"):
            errors.append(f"EXCLUDED_DIR_PRESENT: {rel}")
        data = f.read_bytes()
        if b"\0" not in data and b"\r\n" in data:
            errors.append(f"CRLF: {rel}")
        if f.suffix in TEXT_EXTS:
            text = f.read_text(encoding="utf-8")
            for m in ABS_PATH_RE.finditer(text):
                errors.append(f"ABS_PATH: {rel}: ...{text[max(0,m.start()-15):m.start()+25]!r}...")
            if DEV_TOKEN_RE.search(text):
                errors.append(f"DEV_TOKEN: {rel}")

    # (iv) 4 skill + 严格 frontmatter
    for name in SKILL_NAMES:
        sf = base / ".claude" / "skills" / name / "SKILL.md"
        if not sf.exists():
            errors.append(f"MISSING_SKILL: {name}")
            continue
        fm = sf.read_text(encoding="utf-8").split("---")[1]
        keys = re.findall(r"^([a-z-]+):", fm, re.MULTILINE)
        if keys != ["name", "description"]:
            errors.append(f"FRONTMATTER: {name} keys={keys}, want ['name','description']")

    # (v) 28 CORE_DOCS 在 engine/ 下
    for doc in CORE_DOCS:
        if not (base / "engine" / doc).exists():
            errors.append(f"MISSING_CORE_DOC: engine/{doc}")

    # (vi) src 定位 engine/templates（dist 平铺布局）
    if not (base / "engine").is_dir() or not (base / "templates").is_dir():
        errors.append("LAYOUT: engine/ or templates/ missing at package root")

    # (iii) 链接
    _check_links(errors, base)
    return errors


# ---------------------------------------------------------------------------
# 构建
# ---------------------------------------------------------------------------

def build(out_dir=None) -> list:
    out = Path(out_dir) if out_dir is not None else DIST
    log = []
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    _copy_and_transform(DEV / ".claude" / "skills", out / ".claude" / "skills", log, scrub=True)
    # engine：剔除 audits/
    engine_src = DEV / "engine"
    for f in sorted(engine_src.rglob("*")):
        if f.is_dir() or "audits" in f.parts:
            continue
        rel = f.relative_to(engine_src)
        if f.suffix in TEXT_EXTS:
            text = _scrub(_apply_rewrites(f.read_text(encoding="utf-8")), str(rel), log)
            _write_text(out / "engine" / rel, text)
        else:
            dst = out / "engine" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst)
    _copy_and_transform(DEV / "templates", out / "templates", log, scrub=True)
    _copy_and_transform(ROOT / "src", out / "src", log, scrub=False)

    v = _version()
    _write_text(out / "AGENTS.md", _gen_agents_md(v))
    _write_text(out / "CLAUDE.md", _gen_claude_md())
    _write_text(out / "GEMINI.md", _gen_gemini_md())
    _write_text(out / "INSTALL.md", _gen_install_md(v))
    _write_text(out / "README.md", _gen_readme_md(v))
    _write_text(out / ".claude-plugin" / "plugin.json", _gen_plugin_json(v))
    _write_text(out / "adapters" / "codex.md", _gen_adapter_codex(log))

    return log


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble the Credence installable agent package.")
    ap.add_argument("--check", action="store_true", help="validate an existing dist/ only")
    ap.add_argument("--verbose", action="store_true", help="print the transform log")
    args = ap.parse_args()

    if not args.check:
        log = build()
        print(f"built {DIST} ({sum(1 for _ in DIST.rglob('*') if _.is_file())} files)")
        if args.verbose:
            for line in log:
                print("  ", line)

    errors = validate()
    if errors:
        print(f"dist validation FAILED ({len(errors)}):")
        for e in errors[:60]:
            print("  ", e)
        return 1
    print("dist validation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

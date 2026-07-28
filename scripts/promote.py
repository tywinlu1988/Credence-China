#!/usr/bin/env python3
"""Credence 版本晋升脚本（建议4：版本声明单源化）。

输入新版本号，按**显式规则表**改写全部版本声明点（28 份 CORE_DOCS 头、4 份
SKILL.md、references 头、README/AGENTS/dev README、pyproject/package.json、
EXPECTED_VERSION、build_dist fallback、.gitignore 反例行、VERSION-MANAGEMENT 的
"现为"行）。只匹配声明形态——版本历史表、"自 vX 起"叙述、"v0.8.0 skill 架构"
时代描述、`**范式版本**` 均不在规则内，天然免疫。

默认 dry-run（逐条打印 文件:行号 旧行→新行 与规则未覆盖的剩余出现处），
--apply 才落盘。落盘前要求工作区无已跟踪改动（?? 未跟踪放行）。
"""

import argparse
import re
import subprocess
import sys
from collections import namedtuple
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(Path(__file__).resolve().parent))
from consistency_check import CORE_DOCS  # noqa: E402  单一事实源，不复制清单

SKILL_NAMES = [
    "credit-analysis-router",
    "fixed-income-credit-analysis",
    "credit-report-builder",
    "credit-qa-verifier",
]

VERSION_RE = re.compile(r"^v(\d+\.\d+\.\d+)-[a-z0-9-]+$")
EXPECTED_RE = re.compile(r'^EXPECTED_VERSION\s*=\s*"([^"]+)"', re.MULTILINE)

Change = namedtuple("Change", ["rule_id", "path", "line_no", "old_line", "new_line"])


def derive_semver(version: str):
    """v0.8.1-release -> 0.8.1；不合法返回 None。"""
    m = VERSION_RE.match(version)
    return m.group(1) if m else None


def detect_old_version(root: Path):
    text = (root / "scripts" / "consistency_check.py").read_text(encoding="utf-8")
    m = EXPECTED_RE.search(text)
    return m.group(1) if m else None


def _rules(root: Path, old: str, new: str, semver: str, old_semver: str):
    """规则表：(rule_id, [相对路径], 编译后正则, 替换串)。只匹配声明形态。"""
    O = re.escape(old)
    OS = re.escape(old_semver)
    refs = sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.glob("dev/.claude/skills/*/references/*.md")
    )
    templates = sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.glob("dev/templates/*.html")
    )
    return [
        ("engine-headers", [f"dev/engine/{d}" for d in CORE_DOCS],
         re.compile(r"(\*\*版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("engine-crossrefs", [f"dev/engine/{d}" for d in CORE_DOCS],
         re.compile(r"([（(])" + O + r"([）)])"), r"\g<1>" + new + r"\g<2>"),
        ("engine-current", [f"dev/engine/{d}" for d in CORE_DOCS],
         re.compile(r"(当前 )" + O), r"\g<1>" + new),
        ("overview-table", ["dev/engine/engine-overview.md"],
         re.compile(r"(\|\s*[\w.-]+\.md\s*\|\s*)" + O + r"(?=\s*\|)"), r"\g<1>" + new),
        ("overview-sysver", ["dev/engine/engine-overview.md"],
         re.compile(r"(\*\*引擎版本\*\*\s*\|[^|\n]*\|\s*)" + O + r"(?=\s*\|)"), r"\g<1>" + new),
        ("skill-version", [f"dev/.claude/skills/{s}/SKILL.md" for s in SKILL_NAMES],
         re.compile(r"(\*\*对应引擎版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("skill-title", ["dev/.claude/skills/fixed-income-credit-analysis/SKILL.md"],
         re.compile(r"(# Fixed Income Credit Analysis Engine\s*)" + O), r"\g<1>" + new),
        ("references-headers", refs,
         re.compile(r"(\*\*版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("dev-readme-header", ["dev/README.md"],
         re.compile(r"(\*\*版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("agents-version", ["AGENTS.md"],
         re.compile(r"(\*\*引擎版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("readme-badge", ["README.md"],
         re.compile(r"`" + O + r"`"), f"`{new}`"),
        ("readme-paths", ["README.md"],
         re.compile(r"version/" + O + r"/"), f"version/{new}/"),
        ("pyproject", ["pyproject.toml"],
         re.compile(r'^(version\s*=\s*")' + OS + r'"', re.MULTILINE), r"\g<1>" + semver + '"'),
        ("package-json", ["package.json"],
         re.compile(r'("version"\s*:\s*")' + OS + r'"'), r"\g<1>" + semver + '"'),
        ("expected-version", ["scripts/consistency_check.py"],
         re.compile(r'(EXPECTED_VERSION\s*=\s*")' + O + r'"'), r"\g<1>" + new + '"'),
        ("build-dist-fallback", ["scripts/build_dist.py"],
         re.compile(r'(return m\.group\(1\) if m else ")' + O + r'"'), r"\g<1>" + new + '"'),
        ("gitignore-paths", [".gitignore"],
         re.compile(r"version/" + O + r"/"), f"version/{new}/"),
        ("templates-stamps", templates,
         re.compile(O), new),
        ("adapters-codex", ["docs/adapters/codex.md"],
         re.compile(r"(\*\*引擎版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("version-mgmt-header", ["docs/VERSION-MANAGEMENT.md"],
         re.compile(r"(\*\*对应引擎版本\*\*[:：]\s*)" + O), r"\g<1>" + new),
        ("version-mgmt-path", ["docs/VERSION-MANAGEMENT.md"],
         re.compile(r"`version/" + O + r"/`"), f"`version/{new}/`"),
        ("version-mgmt-tag", ["docs/VERSION-MANAGEMENT.md"],
         re.compile(r"`" + O + r"`"), f"`{new}`"),
    ]


def sanitize_note(note: str) -> str:
    """--note 消毒：换行/回车/dev-/（当前）/竖线 五类非法内容拒绝。"""
    for bad, why in (("\n", "换行"), ("\r", "回车"), ("dev/", "dev/ token"), ("（当前）", "（当前）标记"), ("|", "竖线")):
        if bad in note:
            raise ValueError(f"--note 含非法内容（{why}）: {note!r}")
    return note


def _read_lines(path: Path) -> list:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _write_lines(path: Path, lines: list) -> None:
    path.write_text("".join(lines), encoding="utf-8", newline="\n")


def _section_last_table_line(lines: list, header_re) -> tuple:
    """header 命中行之后、下一个 ^#{1,3} 标题或 EOF 之前，最后一个 | 开头行的索引。"""
    start = next((i for i, l in enumerate(lines) if header_re.search(l)), None)
    if start is None:
        return None, None
    last = None
    for i in range(start + 1, len(lines)):
        if re.match(r"^#{1,3} ", lines[i]):
            break
        if lines[i].lstrip().startswith("|"):
            last = i
    return start, last


def _append_dev_readme_history(root: Path, new: str, today: str, note: str, tests, apply: bool, hints=None) -> list:
    path = root / "dev" / "README.md"
    if not path.is_file():
        return []
    lines = _read_lines(path)
    start, last = _section_last_table_line(lines, re.compile(r"^##\s+版本历史"))
    if last is None:
        if hints is not None:
            hints.append("dev/README.md 版本历史节未找到表格行，跳过历史行追加")
        return []
    marker = f"**{new}**"
    if any(marker in lines[i] for i in range(start + 1, last + 1)):
        if hints is not None:
            hints.append(f"dev/README.md 版本历史表已含 {new} 行，跳过（防重复）")
        return []
    row = f"| **{new}** | **{today}** | **{note}。{tests} 项测试通过。** |\n"
    anchor = lines[last]
    lines.insert(last + 1, row)
    if apply:
        _write_lines(path, lines)
    return [Change("dev-readme-history", "dev/README.md", last + 2, anchor.rstrip("\n"), row.rstrip("\n"))]


def _append_overview_history(root: Path, new: str, today: str, note: str, tests, framework_changed: bool, apply: bool, hints=None) -> list:
    path = root / "dev" / "engine" / "engine-overview.md"
    if not path.is_file():
        return []
    lines = _read_lines(path)
    start, last = _section_last_table_line(lines, re.compile(r"^##\s+六[、.]\s*版本历史"))
    if last is None:
        if hints is not None:
            hints.append("dev/engine/engine-overview.md §六 版本历史节未找到表格行，跳过历史行追加")
        return []
    marker = f"**{new.removeprefix('v')}**"
    if any(marker in lines[i] for i in range(start + 1, last + 1)):
        if hints is not None:
            hints.append(f"dev/engine/engine-overview.md §六 版本历史表已含 {new} 行，跳过（防重复）")
        return []
    suffix = "" if framework_changed else "（本框架与阈值无变更）"
    row = f"| **{new.removeprefix('v')}** | **{today}** | **{note}{suffix}。{tests} 项测试通过** |\n"
    anchor = lines[last]
    lines.insert(last + 1, row)
    if apply:
        _write_lines(path, lines)
    return [Change("overview-history", "dev/engine/engine-overview.md", last + 2, anchor.rstrip("\n"), row.rstrip("\n"))]


def _append_systemic_history(root: Path, old: str, new: str, note: str, framework_changed: bool, apply: bool, hints=None) -> list:
    path = root / "dev" / "engine" / "systemic-warning-framework.md"
    if not path.is_file():
        return []
    lines = _read_lines(path)
    start, _ = _section_last_table_line(lines, re.compile(r"^###\s+11\.3"))
    if start is None:
        if hints is not None:
            hints.append("dev/engine/systemic-warning-framework.md 未找到 §11.3 节，跳过历史行追加")
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^#{1,3} ", lines[i]):
            end = i
            break
    if any(f"{new}（当前）" in lines[i] for i in range(start + 1, end)):
        if hints is not None:
            hints.append(f"dev/engine/systemic-warning-framework.md §11.3 已含 {new}（当前）行，跳过（防重复）")
        return []
    cur_re = re.compile(r"\|\s*" + re.escape(old) + r"（当前）\s*\|")
    idx = None
    for i in range(start + 1, end):
        if cur_re.search(lines[i]):
            idx = i
            break
    if idx is None:
        if hints is not None:
            hints.append("dev/engine/systemic-warning-framework.md §11.3 未找到（当前）标记行，跳过")
        return []
    old_line = lines[idx]
    migrated = old_line.replace(f"{old}（当前）", old, 1)
    suffix = "" if framework_changed else "（本框架与阈值无变更）"
    row = f"| {new}（当前） | {note}{suffix} |\n"
    lines[idx] = migrated
    lines.insert(idx + 1, row)
    if apply:
        _write_lines(path, lines)
    rel = "dev/engine/systemic-warning-framework.md"
    return [
        Change("systemic-history", rel, idx + 1, old_line.rstrip("\n"), migrated.rstrip("\n")),
        Change("systemic-history", rel, idx + 2, "", row.rstrip("\n")),
    ]


def _flip_roadmap(root: Path, new: str, apply: bool) -> tuple:
    """README 双语路线图：（规划中）/(planned) → 删除线 + （已发布）/(released)。无匹配返回提示。"""
    path = root / "README.md"
    if not path.is_file():
        return [], None
    semver = derive_semver(new)
    lines = _read_lines(path)
    zh_old, zh_new = f"**v{semver}（规划中）**", f"~~**v{semver}**~~（已发布）"
    en_old, en_new = f"**v{semver} (planned)**", f"~~**v{semver}**~~ (released)"
    changes = []
    for i, line in enumerate(lines):
        nl = line.replace(zh_old, zh_new).replace(en_old, en_new)
        if nl != line:
            changes.append(Change("roadmap-flip", "README.md", i + 1, line.rstrip("\n"), nl.rstrip("\n")))
            lines[i] = nl
    if changes and apply:
        _write_lines(path, lines)
    hint = None if changes else f"README 路线图无 v{semver} 的（规划中）/(planned) 行；如为计划外版本（热修等）可忽略"
    return changes, hint


def apply_rules(root: Path, old: str, new: str, apply: bool, note=None, tests=None, framework_changed=False, hints=None) -> list:
    """按规则表改写声明点；apply=False 只报告不落盘。返回 Change 列表。"""
    semver = derive_semver(new)
    old_semver = derive_semver(old)
    if semver is None or old_semver is None:
        raise ValueError(f"版本号形式不合法: old={old!r} new={new!r}")
    if apply and (note is None or tests is None or tests < 1):
        raise ValueError("--apply 必须提供 note 与 tests（tests 需为正整数）")
    if note is not None:
        sanitize_note(note)  # 内置消毒：直接调用方不可绕过（main 亦前置检查以早反馈）
    changes = []
    for rule_id, files, pattern, repl in _rules(root, old, new, semver, old_semver):
        for rel in files:
            path = root / rel
            if not path.is_file():
                continue  # 假树/部分树：缺失文件跳过（真树完整性由 check_versions 保证）
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            touched = False
            for i, line in enumerate(lines):
                new_line = pattern.sub(repl, line)
                if new_line != line:
                    changes.append(
                        Change(rule_id, rel, i + 1, line.rstrip("\n"), new_line.rstrip("\n"))
                    )
                    lines[i] = new_line
                    touched = True
            if touched and apply:
                path.write_text("".join(lines), encoding="utf-8", newline="\n")
    today = date.today().isoformat()
    note_text = note if note is not None else "〈note〉"
    tests_text = tests if tests is not None else "〈N〉"
    changes.extend(_append_dev_readme_history(root, new, today, note_text, tests_text, apply, hints=hints))
    changes.extend(_append_overview_history(root, new, today, note_text, tests_text, framework_changed, apply, hints=hints))
    changes.extend(_append_systemic_history(root, old, new, note_text, framework_changed, apply, hints=hints))
    roadmap_changes, hint = _flip_roadmap(root, new, apply)
    changes.extend(roadmap_changes)
    if hint and hints is not None:
        hints.append(hint)
    return changes


def _git_grep(root: Path, old: str) -> set:
    out = subprocess.run(
        ["git", "grep", "-n", old, "--", ".", ":!version"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    hits = set()
    for line in out.splitlines():
        path, line_no, _content = line.split(":", 2)
        hits.add((path, line_no))
    return hits


def _working_tree_clean(root: Path) -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    return all(line.startswith("??") for line in out.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description="Credence 版本晋升（dry-run 默认）")
    parser.add_argument("new_version")
    parser.add_argument("--old", default=None, help="旧版本（默认从 consistency_check 检测）")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--note", default=None, help="版本历史行描述（末尾不加句号）")
    parser.add_argument("--tests", type=int, default=None, help="测试通过数 N")
    parser.add_argument("--framework-changed", action="store_true",
                        help="本版改动了 systemic/overview 框架本体，抑制（本框架与阈值无变更）后缀")
    args = parser.parse_args()

    if derive_semver(args.new_version) is None:
        print(f"新版本号形式不合法: {args.new_version!r}（需 vX.Y.Z-<stage>）")
        return 1
    old = args.old or detect_old_version(ROOT)
    if old is None:
        print("无法从 consistency_check.py 检测旧版本，请用 --old 指定")
        return 1
    if args.apply and not _working_tree_clean(ROOT):
        print("工作区有已跟踪改动，--apply 拒绝执行（先提交或stash）")
        return 1
    if args.note is not None:
        try:
            sanitize_note(args.note)
        except ValueError as e:
            print(e)
            return 1
    if args.apply and (args.note is None or args.tests is None or args.tests < 1):
        print("--apply 必须提供 --note 与 --tests（--tests 需为正整数）")
        return 1

    hints = []
    changes = apply_rules(ROOT, old, args.new_version, apply=args.apply, note=args.note, tests=args.tests, framework_changed=args.framework_changed, hints=hints)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {old} -> {args.new_version}: {len(changes)} 处声明改写")
    for c in changes:
        print(f"  [{c.rule_id}] {c.path}:{c.line_no}")
        print(f"    - {c.old_line.strip()[:100]}")
        print(f"    + {c.new_line.strip()[:100]}")

    changed_keys = {(c.path, str(c.line_no)) for c in changes}
    leftovers = sorted(_git_grep(ROOT, old) - changed_keys)
    print(f"\n规则未覆盖的旧版本出现处（{len(leftovers)}，应全部为历史引用，请人工核对）:")
    for path, line_no in leftovers:
        print(f"  {path}:{line_no}")
    for h in hints:
        print(f"提示: {h}")
    if not args.apply:
        print("\n（dry-run，未落盘；确认后加 --apply）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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


def apply_rules(root: Path, old: str, new: str, apply: bool) -> list:
    """按规则表改写声明点；apply=False 只报告不落盘。返回 Change 列表。"""
    semver = derive_semver(new)
    old_semver = derive_semver(old)
    if semver is None or old_semver is None:
        raise ValueError(f"版本号形式不合法: old={old!r} new={new!r}")
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

    changes = apply_rules(ROOT, old, args.new_version, apply=args.apply)
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
    if not args.apply:
        print("\n（dry-run，未落盘；确认后加 --apply）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

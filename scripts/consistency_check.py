#!/usr/bin/env python3
"""Regression checker for the fixed-income credit analysis engine."""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = ROOT / "dev" / "engine"
TEMPLATES_DIR = ROOT / "dev" / "design" / "templates"
SKILL_FILE = ROOT / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "SKILL.md"

EXPECTED_VERSION = "v0.7.0-alpha"

CORE_DOCS = [
    "engine-overview.md",
    "dual-track-methodology.md",
    "industry-framework.md",
    "qualitative-analysis.md",
    "quantitative-analysis.md",
    "mosaic-engine.md",
    "output-layered-framework.md",
    "contagion-theory.md",
    "contagion-matrix.md",
    "concentration-framework.md",
    "systemic-warning-framework.md",
]


def collect_errors(only_links: bool = False):
    errors = []

    # 1. Core docs must declare EXPECTED_VERSION
    for doc in CORE_DOCS:
        path = ENGINE_DIR / doc
        if not path.exists():
            errors.append(f"MISSING: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if f"**版本**: {EXPECTED_VERSION}" not in text and f"**版本** {EXPECTED_VERSION}" not in text:
            errors.append(f"VERSION: {doc} does not declare {EXPECTED_VERSION}")

    # 2. Skill must declare EXPECTED_VERSION
    if not SKILL_FILE.exists():
        errors.append(f"MISSING: {SKILL_FILE.relative_to(ROOT)}")
    else:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        if EXPECTED_VERSION not in skill_text:
            errors.append(f"VERSION: SKILL.md does not contain {EXPECTED_VERSION}")

    # 3. All internal .md links must resolve
    for path in ENGINE_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[.*?\]\(([^)]+\.md)(?:#[^)]*)?\)", text):
            link = match.group(1)
            target = ENGINE_DIR / link
            if not target.exists():
                errors.append(f"BROKEN_LINK: {path.relative_to(ROOT)} -> {link}")

    if only_links:
        return errors

    # 4. No percentage-scale SRI examples in engine or templates
    sri_pct_pattern = re.compile(r"SRI\s*[:：]\s*\d{2}\s*/\s*100", re.IGNORECASE)
    for path in list(ENGINE_DIR.rglob("*.md")) + list(TEMPLATES_DIR.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if sri_pct_pattern.search(text):
            errors.append(f"SRI_PCT: {path.relative_to(ROOT)} contains percentage-scale SRI")

    # 5. No old 6-notch rating artifacts
    old_notch_patterns = [r"AA/A", r"BBB/BB", r"4\.0-5\.9", r"2\.0-3\.9"]
    for doc in ["false-positive-negative-testing.md", "final-review-2026-07-08.md"]:
        path = ENGINE_DIR / doc
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in old_notch_patterns:
            if re.search(pattern, text):
                errors.append(f"OLD_NOTCH: {doc} contains '{pattern}'")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-links", action="store_true")
    parser.add_argument("--only-toc")
    args = parser.parse_args()

    if args.only_toc:
        # Lightweight TOC/body order check for a single file
        path = Path(args.only_toc)
        text = path.read_text(encoding="utf-8")
        toc_entries = re.findall(r"^\s*\d+\.\s+\[(.+?)\]\(#", text, re.MULTILINE)
        body_entries = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
        if toc_entries != body_entries[: len(toc_entries)]:
            print("TOC mismatch")
            sys.exit(1)
        print("TOC OK")
        return

    errors = collect_errors(only_links=args.only_links)
    if errors:
        print(f"Consistency check FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Consistency check PASSED")


if __name__ == "__main__":
    main()

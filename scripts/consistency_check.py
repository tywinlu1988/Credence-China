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
    "validation-methodology.md",
    "qualitative-analysis.md",
    "quantitative-analysis.md",
    "mosaic-engine.md",
    "output-layered-framework.md",
    "contagion-theory.md",
    "contagion-matrix.md",
    "concentration-framework.md",
    "systemic-warning-framework.md",
    "financial-bond-framework.md",
    "holding-company-framework.md",
    "non-credit-risk-overlay.md",
    "external-support-framework.md",
    "esg-framework.md",
    "governance-fraud-risk.md",
    "false-positive-negative-testing.md",
    "final-review-2026-07-08.md",
    "outlook-monitoring-framework.md",
    "lgd-recovery-framework.md",
    "lgv-framework.md",
]

SRI_PCT_PATTERN = re.compile(r"SRI\s*[:：]\s*\d{2}\s*/\s*100", re.IGNORECASE)
OLD_NOTCH_PATTERNS = [re.compile(p) for p in (
    r"(?<![A-Z+-])AA/A(?![A-Z+-])",  # old 6-notch combined notation, not "AA+/AA/AA-"
    r"(?<![A-Z+-])BBB/BB(?![A-Z+-])",  # old 6-notch combined notation, not "BBB+/BBB/BBB-"
    r"4\.0-5\.9",
    r"2\.0-3\.9",
)]


def check_versions() -> list[str]:
    errors = []
    for doc in CORE_DOCS:
        path = ENGINE_DIR / doc
        if not path.exists():
            errors.append(f"MISSING: {path.relative_to(ENGINE_DIR)}")
            continue
        text = path.read_text(encoding="utf-8")
        if (f"**版本**: {EXPECTED_VERSION}" not in text
                and f"**版本** {EXPECTED_VERSION}" not in text
                and f"**对应引擎版本**: {EXPECTED_VERSION}" not in text
                and f"**对应引擎版本** {EXPECTED_VERSION}" not in text):
            errors.append(f"VERSION: {doc} does not declare {EXPECTED_VERSION}")

    if not SKILL_FILE.exists():
        errors.append(f"MISSING: {SKILL_FILE}")
    else:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        if EXPECTED_VERSION not in skill_text:
            errors.append(f"VERSION: SKILL.md does not contain {EXPECTED_VERSION}")
    return errors


def check_links() -> list[str]:
    errors = []
    for path in ENGINE_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[.*?\]\(([^)]+\.md)(?:#[^)]*)?\)", text):
            link = match.group(1)
            target = ENGINE_DIR / link
            if not target.exists():
                errors.append(f"BROKEN_LINK: {path.relative_to(ENGINE_DIR)} -> {link}")
    return errors


def check_sri_scale() -> list[str]:
    errors = []
    for path in list(ENGINE_DIR.rglob("*.md")) + list(TEMPLATES_DIR.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if SRI_PCT_PATTERN.search(text):
            rel = path.relative_to(ENGINE_DIR) if path.is_relative_to(ENGINE_DIR) else path.relative_to(TEMPLATES_DIR)
            errors.append(f"SRI_PCT: {rel} contains percentage-scale SRI")
    return errors


def check_rating_map() -> list[str]:
    errors = []
    for path in ENGINE_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for pattern in OLD_NOTCH_PATTERNS:
            if pattern.search(text):
                errors.append(f"OLD_NOTCH: {path.relative_to(ENGINE_DIR)} contains '{pattern.pattern}'")
    return errors


def check_audit_versions() -> list[str]:
    errors = []
    pattern = re.compile(r"\*\*对应引擎版本\*\*\s*:\s*" + re.escape(EXPECTED_VERSION) + r"\b")
    for path in ENGINE_DIR.rglob("*.md"):
        name = path.name
        if not (name.endswith("-audit.md") or re.match(r".*-review-.*\.md$", name) or name.startswith("self-assessment-")):
            continue
        text = path.read_text(encoding="utf-8")
        if not pattern.search(text):
            errors.append(f"AUDIT_VERSION: {path.relative_to(ENGINE_DIR)} does not declare 对应引擎版本: {EXPECTED_VERSION}")
    return errors


def collect_errors(only_links: bool = False) -> list[str]:
    errors = check_links()
    if only_links:
        return errors
    errors.extend(check_versions())
    errors.extend(check_sri_scale())
    errors.extend(check_rating_map())
    errors.extend(check_audit_versions())
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
        body_entries = [
            re.sub(r"^[一二三四五六七八九十百千万]+[、.\\s]+", "", h)
            for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
            if h != "目录"
        ]
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

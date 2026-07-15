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
SKILL_REFERENCES_DIR = ROOT / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "references"

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

CANONICAL_RATING_INTERVALS = [
    (9.5, 10.0, "AAA"),
    (9.0, 9.4, "AA+"),
    (8.5, 8.9, "AA"),
    (8.0, 8.4, "AA-"),
    (7.5, 7.9, "A+"),
    (7.0, 7.4, "A"),
    (6.5, 6.9, "A-"),
    (6.0, 6.4, "BBB+"),
    (5.5, 5.9, "BBB"),
    (5.0, 5.4, "BBB-"),
    (4.5, 4.9, "BB+"),
    (4.0, 4.4, "BB"),
    (3.5, 3.9, "BB-"),
    (3.0, 3.4, "B+"),
    (2.5, 2.9, "B"),
    (2.0, 2.4, "B-"),
    (1.0, 1.9, "CCC"),
    (0.0, 0.9, "D"),
]
RATING_INTERVAL_RE = re.compile(
    r"\|\s*(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*\|\s*([A-D]{1,3}[+-]?)\s*\|"
)
HISTORICAL_NAME_PATTERNS = [re.compile(p) for p in (
    r".*-audit.*\.md$",
    r".*-review-.*\.md$",
    r"^self-assessment-",
)]

YELLOW_05_PATTERNS = [
    re.compile(r"yellow\s*=\s*0\.5", re.IGNORECASE),
    re.compile(r"关注.*0\.5\s*分?"),
    re.compile(r"🟡.*0\.5\s*分?"),
]
YELLOW_0_PATTERNS = [
    re.compile(r"yellow\s*=\s*0\b(?!\.\d)", re.IGNORECASE),
    re.compile(r"关注.*\b0\s*分"),
    re.compile(r"🟡.*\b0\s*分"),
]

ORANGE_05_PATTERNS = [
    re.compile(r"orange\s*=\s*0\.5", re.IGNORECASE),
    re.compile(r"橙色.*0\.5\s*分?"),
    re.compile(r"🟠.*0\.5\s*分?"),
]
ORANGE_10_PATTERNS = [
    re.compile(r"orange\s*=\s*1\.0", re.IGNORECASE),
    re.compile(r"橙色.*1\.0\s*分?"),
    re.compile(r"🟠.*1\.0\s*分?"),
]

RED_10_PATTERNS = [
    re.compile(r"red\s*=\s*1\.0", re.IGNORECASE),
    re.compile(r"红色.*1\.0\s*分?"),
    re.compile(r"🔴.*1\.0\s*分?"),
]
RED_15_PATTERNS = [
    re.compile(r"red\s*=\s*1\.5", re.IGNORECASE),
    re.compile(r"红色.*1\.5\s*分?"),
    re.compile(r"🔴.*1\.5\s*分?"),
]

REFERENCE_TO_ENGINE_MAP = {
    "industry-pyramids.md": "industry-framework.md",
    "mosaic-engine-architecture.md": "mosaic-engine.md",
    "validation-cases.md": "validation-methodology.md",
}
VERSION_HEADER_RE = re.compile(r"\*\*(?:版本|对应引擎版本)\*\*\s*[:：]?\s*([^\s|]+)")


def _extract_version_header(text: str) -> str | None:
    m = VERSION_HEADER_RE.search(text)
    return m.group(1) if m else None


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


def check_rating_map_consistency() -> list[str]:
    """Flag any score-range -> rating table that deviates from the canonical 12-notch map."""
    errors = []
    canonical_set = {(low, high, label) for low, high, label in CANONICAL_RATING_INTERVALS}
    for path in ENGINE_DIR.rglob("*.md"):
        if path.name == "dual-track-methodology.md":
            continue
        if any(p.match(path.name) for p in HISTORICAL_NAME_PATTERNS):
            continue
        text = path.read_text(encoding="utf-8")
        for match in RATING_INTERVAL_RE.finditer(text):
            low = float(match.group(1))
            high = float(match.group(2))
            label = match.group(3)
            if (low, high, label) not in canonical_set:
                errors.append(
                    f"RATING_MAP: {path.relative_to(ENGINE_DIR)} has non-canonical "
                    f"interval/label ({low:g}-{high:g} -> {label})"
                )
    return errors


def check_sri_track_b_consistency() -> list[str]:
    """Flag contradictory textual descriptions of Track-B penalties across yellow/orange/red."""
    path = ENGINE_DIR / "systemic-warning-framework.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    contradictions = []
    if any(p.search(text) for p in YELLOW_05_PATTERNS) and any(p.search(text) for p in YELLOW_0_PATTERNS):
        contradictions.append("yellow penalty as both 0.5 and 0")
    if any(p.search(text) for p in ORANGE_05_PATTERNS) and any(p.search(text) for p in ORANGE_10_PATTERNS):
        contradictions.append("orange penalty as both 0.5 and 1.0")
    if any(p.search(text) for p in RED_10_PATTERNS) and any(p.search(text) for p in RED_15_PATTERNS):
        contradictions.append("red penalty as both 1.0 and 1.5")
    if contradictions:
        return [
            f"SRI_TRACK_B: {path.relative_to(ENGINE_DIR)} describes " + " and ".join(contradictions)
        ]
    return []


def check_skill_references() -> list[str]:
    """Compare Skill reference files with their engine counterparts by version header."""
    errors = []
    if not SKILL_REFERENCES_DIR.exists():
        return errors
    for ref_path in SKILL_REFERENCES_DIR.glob("*.md"):
        engine_name = REFERENCE_TO_ENGINE_MAP.get(ref_path.name, ref_path.name)
        engine_path = ENGINE_DIR / engine_name
        if not engine_path.exists():
            errors.append(f"SKILL_REF_MISSING: {ref_path.name} has no engine counterpart ({engine_name})")
            continue
        ref_text = ref_path.read_text(encoding="utf-8")
        engine_text = engine_path.read_text(encoding="utf-8")
        ref_ver = _extract_version_header(ref_text)
        engine_ver = _extract_version_header(engine_text)
        if ref_ver is None and engine_ver is None:
            continue
        if ref_ver is None:
            errors.append(
                f"SKILL_REF_VERSION: {ref_path.name} missing version header "
                f"(engine {engine_name} is {engine_ver})"
            )
        elif engine_ver is None:
            errors.append(
                f"SKILL_REF_VERSION: {ref_path.name} version {ref_ver} "
                f"but engine {engine_name} missing version header"
            )
        elif ref_ver != engine_ver:
            errors.append(
                f"SKILL_REF_STALE: {ref_path.name} version {ref_ver} "
                f"!= engine {engine_name} version {engine_ver}"
            )
    return errors


def _parse_contagion_industries(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    start = text.find("### 1.2 范式映射表")
    if start == -1:
        return []
    end = text.find("### 1.3", start)
    section = text[start:end] if end != -1 else text[start:]
    industries = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) < 4:
            continue
        first = cells[0]
        if first.isdigit():
            industries.append(cells[1])
    return industries


def _industry_covered(industry: str, text: str) -> bool:
    if industry in text:
        return True
    # Allow heading matches using the first slash-separated segment, e.g. "高端装备/工业母机" -> "高端装备"
    parts = re.split(r"[/(（]", industry)
    for part in parts:
        part = part.strip().strip(")）")
        if not part:
            continue
        if re.search(rf"^#+\s+.*{re.escape(part)}", text, re.MULTILINE):
            return True
    return False


def check_paradigm_coverage() -> list[str]:
    """Ensure every industry in contagion-matrix §1.2 appears in industry-framework.md."""
    contagion_path = ENGINE_DIR / "contagion-matrix.md"
    industry_path = ENGINE_DIR / "industry-framework.md"
    if not contagion_path.exists() or not industry_path.exists():
        return []
    industries = _parse_contagion_industries(contagion_path)
    text = industry_path.read_text(encoding="utf-8")
    errors = []
    for industry in industries:
        if not _industry_covered(industry, text):
            errors.append(
                f"PARADIGM_COVERAGE: {industry} listed in contagion-matrix.md "
                f"is missing from industry-framework.md"
            )
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


def collect_warnings() -> list[str]:
    """Structural coherence checks that are reported as warnings until fixes land."""
    warnings = []
    warnings.extend(check_rating_map_consistency())
    warnings.extend(check_sri_track_b_consistency())
    warnings.extend(check_skill_references())
    warnings.extend(check_paradigm_coverage())
    return warnings


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
    if not args.only_links:
        warnings = collect_warnings()
        if warnings:
            print(f"Consistency warnings ({len(warnings)} issue(s)):")
            for w in warnings:
                print(f"  - {w}")
    if errors:
        print(f"Consistency check FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Consistency check PASSED")


if __name__ == "__main__":
    main()

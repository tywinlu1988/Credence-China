"""Regression tests for cross-document coherence of the v0.7.0-alpha engine."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = ROOT / "dev" / "engine"
SKILL_FILE = ROOT / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "SKILL.md"

# Authoritative 12-notch rating map from dual-track-methodology.md §六.
# Each tuple is (low_score, high_score, rating_label).
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


def _read_engine_doc(name: str) -> str:
    return (ENGINE_DIR / name).read_text(encoding="utf-8")


def _parse_rating_table(text: str, start_marker: str, end_marker: str | None = None) -> list[tuple[float, float, str]]:
    """Extract score-range -> rating rows from a Markdown table section."""
    start = text.find(start_marker)
    if start == -1:
        return []
    section = text[start:]
    if end_marker:
        end = section.find(end_marker, len(start_marker))
        if end != -1:
            section = section[:end]

    intervals = []
    for match in RATING_INTERVAL_RE.finditer(section):
        low = float(match.group(1))
        high = float(match.group(2))
        label = match.group(3)
        intervals.append((low, high, label))
    return intervals


def test_rating_map_consistency_in_systemic_warning_framework():
    """The SRI input table must use the same canonical 12-notch map as the rest of the engine."""
    text = _read_engine_doc("systemic-warning-framework.md")
    intervals = _parse_rating_table(
        text,
        start_marker="**信号A：轨道A行业评分**",
        end_marker="**信号B：轨道B市场信号**",
    )
    assert intervals, "No rating intervals parsed from systemic-warning-framework.md"
    assert intervals == CANONICAL_RATING_INTERVALS, (
        f"Rating intervals in systemic-warning-framework.md do not match the canonical map.\n"
        f"Expected: {CANONICAL_RATING_INTERVALS}\n"
        f"Found: {intervals}"
    )


def test_issuer_survival_veto_ceiling_is_ccc():
    """Every document defining one-shot veto must cap the issuer rating at CCC."""
    docs = ["dual-track-methodology.md", "industry-framework.md", "governance-fraud-risk.md"]
    for doc in docs:
        text = _read_engine_doc(doc)
        assert "一票否决" in text, f"{doc} no longer mentions one-shot veto (一票否决)"
        assert "上限锁定为CCC" in text, (
            f"{doc} does not state the CCC ceiling for veto (上限锁定为CCC)"
        )


def test_thermometer_thresholds_consistent():
    """The SRI thermometer thresholds must be stable across engine and skill docs."""
    engine_text = _read_engine_doc("systemic-warning-framework.md")
    skill_text = SKILL_FILE.read_text(encoding="utf-8")

    # Engine §3.1 explicit band boundaries.
    assert "SRI < 0.5" in engine_text
    assert "0.5 ≤ SRI < 1.0" in engine_text
    assert "1.0 ≤ SRI < 1.8" in engine_text
    assert "SRI ≥ 1.8" in engine_text

    # Skill summary uses the same numeric cutoffs.
    assert "<0.5" in skill_text
    assert "0.5–1.0" in skill_text
    assert "1.0–1.8" in skill_text
    assert "≥1.8" in skill_text


def test_thermometer_full_band_definitions_present():
    """Explicit band boundaries must exist in the engine thermometer definition."""
    text = _read_engine_doc("systemic-warning-framework.md")
    assert "SRI < 0.5" in text
    assert "0.5 ≤ SRI < 1.0" in text
    assert "1.0 ≤ SRI < 1.8" in text
    assert "SRI ≥ 1.8" in text


def test_skill_validation_table_matches_engine():
    """The skill validation table must not overstate which cases are complete."""
    skill = SKILL_FILE.read_text(encoding="utf-8")
    # Solar/PV forward validation is complete, but retrospective validation is
    # intentionally not claimed in the engine validation methodology.
    assert "Solar/PV | 完成 | 完成" not in skill, (
        "Skill overstates Solar/PV retrospective validation as complete"
    )

"""Integration tests for the v0.8.0 release (T11.1-T11.5).

These tests assert the *integration* of the v0.7.6-v0.7.9 staircase into a coherent
release, not any single component:

- T11.1: every one of the 8 active work paths yields a valid 4-stage plan (S1..S4,
  non-empty names/skills) via the thin orchestrator.
- T11.2: the 2 wired paths (WP-M4-01 concentration, WP-M4-03 SRI) execute code at the
  analysis stage; the other 6 active paths produce a complete LLM-orchestrated plan.
- T11.3: the end-to-end walkthrough record exists and literally names all 8 path ids.
- T11.4: version promotion is consistent (EXPECTED_VERSION == v0.8.0-alpha and every
  CORE_DOCS doc + skill declares it), mirroring consistency_check.check_versions.
- T11.5: the v0.8.0 snapshot exists with the mirrored dev/ + src/ + AGENTS.md layout.

Single-source rule: the tests assert structure/versions only. They never restate engine
thresholds/weights -- the only numbers here are the *fixture inputs* and the *real engine
outputs* returned by the wired coded engines (mirrors tests/test_pipeline.py fixtures).
"""

import importlib.util
from pathlib import Path

import pytest

from src.concentration_scorer import ConcentrationMetrics
from src.path_sheet import load_registry_paths
from src.pipeline import (
    EXECUTABLE_ENGINES,
    load_contract,
    load_stage_plan,
    run_executable_stages,
)
from src.sri_calculator import IndustryInput, Outlook, TrackBLevel

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "dev" / "engine" / "pipeline-contract.md"
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"
ENGINE_DIR = ROOT / "dev" / "engine"
SKILLS_DIR = ROOT / "dev" / ".claude" / "skills"
WALKTHROUGH = ROOT / "validation" / "docs" / "v0.8.0-end-to-end-walkthroughs.md"
SNAPSHOT = ROOT / "version" / "v0.8.0-alpha"
SNAPSHOT_ZIP = ROOT / "version" / "v0.8.0-alpha.zip"
CONSISTENCY_CHECK = ROOT / "scripts" / "consistency_check.py"

ACTIVE_PATHS = [
    "WP-M0-01", "WP-M1-01", "WP-M4-01", "WP-M4-02",
    "WP-M4-03", "WP-X-01", "WP-X-02", "WP-X-03",
]
WIRED_PATHS = ["WP-M4-01", "WP-M4-03"]
UNWIRED_ACTIVE = [p for p in ACTIVE_PATHS if p not in WIRED_PATHS]

FOUR_SKILLS = (
    "credit-analysis-router",
    "fixed-income-credit-analysis",
    "credit-report-builder",
    "credit-qa-verifier",
)


# --------------------------------------------------------------------------
# fixtures / helpers
# --------------------------------------------------------------------------

def _load_consistency_check():
    """importlib-load scripts/consistency_check.py (it is not a package module)."""
    spec = importlib.util.spec_from_file_location("consistency_check", CONSISTENCY_CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cc():
    return _load_consistency_check()


@pytest.fixture(scope="module")
def contract():
    return load_contract(CONTRACT)


@pytest.fixture(scope="module")
def registry_paths():
    return load_registry_paths(REGISTRY)


def _sheet_for(path_id, registry_paths, **overrides):
    """A valid path sheet for an active path, built from the registry's real entry.

    role/object/depth come from the registry; engine_sequence maps to the sheet's
    engine_reading_order; quality_gates are copied verbatim. mode defaults to A
    (public data). This mirrors the construction approach in tests/test_pipeline.py.
    """
    entry = registry_paths[path_id]
    sheet = {
        "role": str(entry["role"]),
        "object": str(entry["trigger"]["object"]),
        "depth": str(entry["depth"]),
        "mode": "A",
        "path_id": path_id,
        "engine_reading_order": list(entry["engine_sequence"]),
        "quality_gates": list(entry["quality_gates"]),
        "notes": "",
    }
    sheet.update(overrides)
    return sheet


def _sri_inputs():
    """The known 2026Q2 SRI fixture (mirrors tests/test_pipeline.py)."""
    industries = [
        IndustryInput("LGV", 5.25, TrackBLevel.YELLOW, Outlook.STABLE),
        IndustryInput("PV", 5.0, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("NEV", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("Retail", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
    ] + [
        IndustryInput(f"other_{i}", 7.0, TrackBLevel.GREEN, Outlook.STABLE)
        for i in range(9)
    ]
    weights = [0.25, 0.0233, 0.0222, 0.04]
    residual = 1.0 - sum(weights)
    weights += [residual / 9] * 9
    return {"industries": industries, "weights": weights}


def _concentration_inputs():
    """An all-green ConcentrationMetrics fixture (mirrors tests/test_pipeline.py)."""
    return {
        "metrics": ConcentrationMetrics(
            hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
            single_province_share=0.10, weak_region_share=0.02,
            aaa_share=0.20, pseudo_high_rating_share=0.01,
            maturity_12m_share=0.20, single_month_peak=0.05,
            top_channel_share=0.30,
        )
    }


def _wired_inputs(path_id):
    return _sri_inputs() if path_id == "WP-M4-03" else _concentration_inputs()


# --------------------------------------------------------------------------
# T11.1 — all 8 active paths produce a valid 4-stage plan (S1..S4)
# --------------------------------------------------------------------------

def test_t11_1_all_active_paths_yield_valid_four_stage_plan(contract, registry_paths):
    # every active path id the walkthrough covers must actually be registered active
    for pid in ACTIVE_PATHS:
        assert pid in registry_paths, f"{pid} not registered"
        assert str(registry_paths[pid].get("status")) == "active", f"{pid} not active"

    # the contract drives S1->S2->S3->S4 in order (load_stage_plan re-validates this)
    assert [cs["id"] for cs in contract["stages"]] == ["S1", "S2", "S3", "S4"]

    for pid in ACTIVE_PATHS:
        plan = load_stage_plan(_sheet_for(pid, registry_paths), registry_paths, contract)
        assert len(plan) == 4, f"{pid}: expected 4 stages"
        for idx, stage in enumerate(plan):
            cs = contract["stages"][idx]
            assert cs["id"] == f"S{idx + 1}"
            # stage name/skill come from the contract and are non-empty
            assert stage.name == cs["name"] and stage.name.strip()
            assert stage.skill == cs["skill"] and stage.skill.strip()
            assert stage.path_id == pid


# --------------------------------------------------------------------------
# T11.2 — 2 wired paths execute code; the other 6 are LLM-orchestrated
# --------------------------------------------------------------------------

def test_t11_2_wired_execute_code_others_llm_orchestrated(contract, registry_paths):
    assert set(WIRED_PATHS) == set(EXECUTABLE_ENGINES), "wired set drifted from EXECUTABLE_ENGINES"

    # wired: analysis stage runs the coded engine (mode="code") with real outputs
    for pid in WIRED_PATHS:
        plan = load_stage_plan(_sheet_for(pid, registry_paths), registry_paths, contract)
        assert plan[1].executable is True, f"{pid}: analysis must be executable"
        manifest = run_executable_stages(plan, _wired_inputs(pid))
        assert manifest["path_id"] == pid
        analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
        assert analysis["mode"] == "code", f"{pid}: analysis must run as code"
        assert analysis["outputs"], f"{pid}: analysis must return real outputs"
        if pid == "WP-M4-03":
            assert set(analysis["outputs"]) == {"sri", "thermometer"}
        else:  # WP-M4-01
            assert set(analysis["outputs"]) == {"score", "adjustment", "levels", "bb_cap_triggered"}

    # unwired: complete plan, analysis not executable, every stage llm-orchestrated
    assert len(UNWIRED_ACTIVE) == 6
    for pid in UNWIRED_ACTIVE:
        assert pid not in EXECUTABLE_ENGINES
        plan = load_stage_plan(_sheet_for(pid, registry_paths), registry_paths, contract)
        assert len(plan) == 4, f"{pid}: unwired path still yields a complete 4-stage plan"
        assert plan[1].executable is False, f"{pid}: analysis must NOT be executable"
        manifest = run_executable_stages(plan, {})
        assert all(s["mode"] == "llm-orchestrated" for s in manifest["stages"]), pid
        analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
        assert analysis["outputs"] is None


# --------------------------------------------------------------------------
# T11.3 — walkthrough record exists and literally names all 8 path ids
# --------------------------------------------------------------------------

def test_t11_3_walkthrough_covers_all_eight_paths():
    assert WALKTHROUGH.exists(), f"walkthrough missing: {WALKTHROUGH}"
    text = WALKTHROUGH.read_text(encoding="utf-8")
    for pid in ACTIVE_PATHS:
        assert pid in text, f"walkthrough does not name {pid}"


# --------------------------------------------------------------------------
# T11.4 — version promotion consistency (mirrors check_versions)
# --------------------------------------------------------------------------

def test_t11_4_version_promotion_consistent(cc):
    assert cc.EXPECTED_VERSION == "v0.8.0-alpha"
    # check_versions must report no errors: all CORE_DOCS + the executor skill declare it
    assert cc.check_versions() == [], "check_versions reported errors after promotion"
    # every CORE_DOCS doc header declares the promoted version (mirror check_versions logic)
    for doc in cc.CORE_DOCS:
        text = (ENGINE_DIR / doc).read_text(encoding="utf-8")
        assert (
            f"**版本**: {cc.EXPECTED_VERSION}" in text
            or f"**版本** {cc.EXPECTED_VERSION}" in text
            or f"**对应引擎版本**: {cc.EXPECTED_VERSION}" in text
            or f"**对应引擎版本** {cc.EXPECTED_VERSION}" in text
        ), f"{doc} does not declare {cc.EXPECTED_VERSION}"
    # all four stage skills reference the promoted version
    for skill in FOUR_SKILLS:
        skill_text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
        assert cc.EXPECTED_VERSION in skill_text, f"{skill} SKILL.md not on {cc.EXPECTED_VERSION}"


# --------------------------------------------------------------------------
# T11.5 — snapshot integrity: mirrored dev/ + src/ + AGENTS.md
# --------------------------------------------------------------------------

def test_t11_5_snapshot_integrity():
    assert SNAPSHOT.is_dir(), f"snapshot missing: {SNAPSHOT}"
    assert (SNAPSHOT / "dev").is_dir(), "snapshot missing dev/"
    assert (SNAPSHOT / "src").is_dir(), "snapshot missing src/"
    assert (SNAPSHOT / "AGENTS.md").is_file(), "snapshot missing AGENTS.md"
    # the snapshot carries the coded engines and the promoted entry version
    assert (SNAPSHOT / "src" / "pipeline.py").is_file()
    assert "v0.8.0-alpha" in (SNAPSHOT / "AGENTS.md").read_text(encoding="utf-8")
    # no excluded artifacts leaked into the snapshot
    leaked = [
        p for p in SNAPSHOT.rglob("*")
        if (p.is_dir() and p.name in (".git", "__pycache__"))
        or (p.is_file() and p.suffix == ".pyc")
    ]
    assert not leaked, f"excluded artifacts in snapshot: {leaked}"
    # distribution zip generated alongside the dir
    assert SNAPSHOT_ZIP.is_file(), f"snapshot zip missing: {SNAPSHOT_ZIP}"

"""Integration tests for the v0.8 release line (T11.1-T11.5).

These tests assert the *integration* of the v0.7.6-v0.7.9 staircase into a coherent
release, not any single component:

- T11.1: every one of the 11 active work paths yields a valid 4-stage plan (S1..S4,
  non-empty names/skills) via the thin orchestrator.
- T11.2: the 5 wired paths (WP-M0-01 composite, WP-M4-01 concentration, WP-M4-02
  contagion, WP-M4-03 SRI, WP-X-05 outlook) execute code at the analysis stage; the
  other 6 active paths produce a complete LLM-orchestrated plan.
- T11.3: the end-to-end walkthrough record exists and literally names all active path ids.
- T11.4: version promotion is consistent (EXPECTED_VERSION well-formed and aligned with
  pyproject/package.json; every CORE_DOCS doc + skill declares it), mirroring
  consistency_check.check_versions / check_version_alignment.
- T11.5: the current snapshot (the single version/*-release dir, named == EXPECTED_VERSION)
  exists as the installable agent package (skills @ .claude/skills, flattened engine/,
  generated entry/install docs) with no dead links.

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
def _current_snapshot_dir() -> Path:
    """version/ 下唯一**被 git 跟踪**的 *-release 目录即当前快照（install.js 语义，
    但按 git ls-files 过滤——维护者本地磁盘上残留的历史快照目录不参与）。"""
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "version/"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    dirs = {line.split("/")[1] for line in out.splitlines() if line.count("/") >= 2}
    releases = sorted(d for d in dirs if d.endswith("-release"))
    assert len(releases) == 1, (
        f"version/ 被跟踪的 *-release 目录应唯一，实际: {releases}"
    )
    return ROOT / "version" / releases[0]


SNAPSHOT = _current_snapshot_dir()
CONSISTENCY_CHECK = ROOT / "scripts" / "consistency_check.py"
BUILD_DIST = ROOT / "scripts" / "build_dist.py"

ACTIVE_PATHS = [
    "WP-M0-01", "WP-M1-01", "WP-M2-01", "WP-M4-01", "WP-M4-02",
    "WP-M4-03", "WP-M5-01", "WP-X-01", "WP-X-02", "WP-X-03", "WP-X-05",
]
WIRED_PATHS = ["WP-M0-01", "WP-M4-01", "WP-M4-02", "WP-M4-03", "WP-X-05"]
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


def _load_build_dist():
    """importlib-load scripts/build_dist.py (it is not a package module)."""
    spec = importlib.util.spec_from_file_location("build_dist", BUILD_DIST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bd():
    return _load_build_dist()


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


def _contagion_inputs():
    return {
        "holdings": {"光伏/储能": 0.4, "半导体/集成电路": 0.35, "食品饮料": 0.25},
        "escalation_factors": ["市场恐慌"],
    }


def _outlook_inputs():
    return {
        "signals": [
            {"layer": "L1", "direction": "negative", "signal": "行业准入收紧"},
            {"layer": "外部支持", "direction": "negative", "signal": "支持方评级下调"},
            {"layer": "L4", "direction": "positive", "signal": "经营现金流转正"},
        ],
        "rating": "AA",
        "paradigm": "政策驱动型",
        "watchlist_triggers": [{"side": "negative", "event": "被监管立案调查"}],
    }


def _composite_inputs():
    return {
        "d_scores": {"D1": 4, "D2": 4, "D3": 5, "D4": 4, "D5": 3,
                     "D6": 3, "D7": 2, "D8": 2, "D9": 3, "D10": 3},
        "layer_scores": {"L1": 8, "L2": 7, "L3": 6, "L4": 7},
        "industry": "光伏/储能",
    }


def _wired_inputs(path_id):
    return {
        "WP-M0-01": _composite_inputs,
        "WP-M4-01": _concentration_inputs,
        "WP-M4-02": _contagion_inputs,
        "WP-M4-03": _sri_inputs,
        "WP-X-05": _outlook_inputs,
    }[path_id]()


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
# T11.2 — 3 wired paths execute code; the other 5 are LLM-orchestrated
# --------------------------------------------------------------------------

EXPECTED_OUTPUT_KEYS = {
    "WP-M0-01": {"paradigm", "composite", "rating", "veto_capped", "conflict", "out_of_scope"},
    "WP-M4-03": {"sri", "thermometer"},
    "WP-M4-01": {"score", "adjustment", "levels", "bb_cap_triggered"},
    "WP-M4-02": {"exposure", "links", "factors_applied"},
    "WP-X-05": {"outlook", "confidence", "net_score", "watchlist", "migration"},
}


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
        assert set(analysis["outputs"]) == EXPECTED_OUTPUT_KEYS[pid]

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
# T11.3 — walkthrough record exists and literally names all active path ids
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
    # 版本无关：形式合法 + 三处对齐（pyproject/package.json），镜像 P2 硬校验
    assert cc.VERSION_RELEASE_RE.match(cc.EXPECTED_VERSION), cc.EXPECTED_VERSION
    assert cc.check_version_alignment() == []
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
# T11.5 — snapshot integrity: installable agent package (no dead links)
# --------------------------------------------------------------------------

def test_t11_5_snapshot_integrity(cc, bd, tmp_path):
    assert SNAPSHOT.is_dir(), f"snapshot missing: {SNAPSHOT}"
    assert SNAPSHOT.name == cc.EXPECTED_VERSION, (
        f"快照目录 {SNAPSHOT.name} 与 EXPECTED_VERSION {cc.EXPECTED_VERSION} 不一致——"
        "快照未随晋升更新"
    )

    # generated entry/install docs (single universal package, per-tool entries)
    for entry in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "INSTALL.md", "README.md"):
        assert (SNAPSHOT / entry).is_file(), f"snapshot missing entry {entry}"
    assert (SNAPSHOT / ".claude-plugin" / "plugin.json").is_file(), "missing plugin.json"
    assert (SNAPSHOT / "adapters" / "codex.md").is_file(), "missing adapters/codex.md"

    # skills归位 .claude/skills/（Claude Code 原生 + Cursor/Gemini/OpenCode 兼容读）
    for skill in FOUR_SKILLS:
        assert (SNAPSHOT / ".claude" / "skills" / skill / "SKILL.md").is_file(), skill

    # engine 平铺：28 份 CORE_DOCS + 报告模板 + 可执行编排器
    for doc in cc.CORE_DOCS:
        assert (SNAPSHOT / "engine" / doc).is_file(), f"snapshot missing engine/{doc}"
    assert (SNAPSHOT / "templates").is_dir(), "snapshot missing templates/"
    assert (SNAPSHOT / "src" / "pipeline.py").is_file(), "snapshot missing src/pipeline.py"

    # the snapshot carries the promoted entry version
    assert cc.EXPECTED_VERSION in (SNAPSHOT / "AGENTS.md").read_text(encoding="utf-8")

    # no excluded artifacts leaked (settings.local.json / audits / design / product /
    # data / validation / dev 源 / 字节码缓存)
    leaked = [
        p for p in SNAPSHOT.rglob("*")
        if (p.is_dir() and p.name in (
            ".git", "__pycache__", "audits", "design", "product", "data", "validation"))
        or (p.is_file() and (p.suffix == ".pyc" or p.name == "settings.local.json"))
    ]
    assert not leaked, f"excluded artifacts in snapshot: {leaked}"

    # 无死链接：无绝对路径、无残留 dev/ 路径 token（用户核心诉求——别的用户根目录不一致）
    dead = []
    for f in SNAPSHOT.rglob("*"):
        if f.is_file() and f.suffix in bd.TEXT_EXTS:
            text = f.read_text(encoding="utf-8")
            if bd.ABS_PATH_RE.search(text):
                dead.append(f"{f.relative_to(SNAPSHOT)}: absolute path")
            if bd.DEV_TOKEN_RE.search(text):
                dead.append(f"{f.relative_to(SNAPSHOT)}: dev/ token")
    assert not dead, f"dead links in snapshot: {dead[:20]}"

    # distribution packaging: the snapshot dir can be zipped into the release artifact
    # (top-level <v>-release/). The zip itself is NOT committed (*.zip is gitignored)
    # — it is built on demand and attached to GitHub Releases, so we build it into a
    # tmp dir here to verify the packaging path works on any clean clone.
    import zipfile
    tmp_zip = tmp_path / "release.zip"
    files = sorted(p for p in SNAPSHOT.rglob("*") if p.is_file())
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, f"{SNAPSHOT.name}/{p.relative_to(SNAPSHOT).as_posix()}")
    with zipfile.ZipFile(tmp_zip) as z:
        names = z.namelist()
    assert names and all(n.startswith(f"{SNAPSHOT.name}/") for n in names)
    assert sum(n.endswith("SKILL.md") for n in names) == len(FOUR_SKILLS)

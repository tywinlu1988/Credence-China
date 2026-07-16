"""Integrity tests for the dimension registry (v0.7.9).

The registry (dev/engine/dimension-registry.md) objectifies the analysis
dimensions -- 6 paradigms (A-F) + the LGFV special category, and the 6
stakeholder roles (M0-M5) -- as addressable yaml entries. It is a POINTER
layer: definitions/weights/thresholds stay single-sourced in the referenced
engine docs. These tests (T10.1-T10.5) validate the registry's structure,
pointer traceability, paradigm->industry consistency with contagion-matrix
section 1.2, the no-copied-thresholds rule, and CORE_DOCS coverage. They do
not exercise any engine logic.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "dev" / "engine" / "dimension-registry.md"
CONTAGION = ROOT / "dev" / "engine" / "contagion-matrix.md"
WORK_PATH_REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"
CHECKER = ROOT / "scripts" / "consistency_check.py"

YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)

# definition pointer of the form: 关键字 (dev/engine/<doc>.md §节)
# The keyword (before " (") must be grep-able in the referenced doc (T10.2).
DEF_RE = re.compile(r"^(?P<kw>.+?)\s*\((?P<doc>dev/engine/\S+?\.md)\s*§(?P<sec>[^)]+)\)\s*$")

DIMENSION_REQUIRED_FIELDS = [
    "id",
    "name",
    "letter",
    "definition",
    "standalone_doc",
    "industries",
    "used_by_paths",
]
ROLE_REQUIRED_FIELDS = ["id", "name", "definition", "used_by_paths"]

EXPECTED_DIMENSION_IDS = {
    "paradigm-A",
    "paradigm-B",
    "paradigm-C",
    "paradigm-D",
    "paradigm-E",
    "paradigm-F",
    "lgfv",
}
EXPECTED_LETTERS = {"A", "B", "C", "D", "E", "F", "特殊"}
EXPECTED_ROLE_IDS = {"role-M0", "role-M1", "role-M2", "role-M3", "role-M4", "role-M5"}
EXPECTED_ROLE_NAMES = {"审贷", "投资", "承销", "交易", "风控", "融资"}

# No-copied-thresholds guard (T10.4): whitelist version tokens (v0.7.1-release)
# and section refs (§x.y); path ids and dates carry no decimal point.
DECIMAL_RE = re.compile(r"\d+\.\d+")
DECIMAL_WHITELIST_PREV = ("v", "V", "§")


def _load_block(key: str) -> list[dict]:
    """Return the list under the top-level ``key`` of the registry's yaml block."""
    text = REGISTRY.read_text(encoding="utf-8")
    for block in YAML_BLOCK_RE.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and key in data:
            return data[key]
    return []


def _import_checker():
    import importlib.util

    spec = importlib.util.spec_from_file_location("consistency_check", CHECKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["consistency_check"] = module
    spec.loader.exec_module(module)
    return module


def _parse_contagion_paradigm_map(path: Path) -> dict[str, str]:
    """Adapted from consistency_check._parse_contagion_industries: extract each
    industry's MAIN paradigm letter from contagion-matrix section 1.2.

    The main paradigm is the first ``范式X`` token in the 主要范式 column, or
    ``特殊`` for the LGFV government-credit category. Returns {industry: letter}.
    """
    text = path.read_text(encoding="utf-8")
    start = text.find("### 1.2 范式映射表")
    if start == -1:
        return {}
    end = text.find("### 1.3", start)
    section = text[start:end] if end != -1 else text[start:]
    mapping: dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) < 3:
            continue
        if not cells[0].isdigit():
            continue
        industry = cells[1]
        main_cell = cells[2]
        m = re.search(r"范式\s*([A-F])", main_cell)
        if m:
            letter = m.group(1)
        elif "特殊" in main_cell:
            letter = "特殊"
        else:
            continue
        mapping[industry] = letter
    return mapping


def test_t10_1_declares_all_dimensions_and_roles():
    """T10.1: registry parses and declares all 6 paradigms + LGFV + all 6 roles."""
    dims = _load_block("dimensions")
    roles = _load_block("roles")
    assert dims, "dimensions yaml block not found or empty"
    assert roles, "roles yaml block not found or empty"

    assert {d["id"] for d in dims} == EXPECTED_DIMENSION_IDS
    assert {d["letter"] for d in dims} == EXPECTED_LETTERS
    assert {r["id"] for r in roles} == EXPECTED_ROLE_IDS
    assert {r["name"] for r in roles} == EXPECTED_ROLE_NAMES

    for d in dims:
        for field in DIMENSION_REQUIRED_FIELDS:
            assert field in d and d[field] is not None, f"{d.get('id')}: missing field {field!r}"
    for r in roles:
        for field in ROLE_REQUIRED_FIELDS:
            assert field in r and r[field] is not None, f"{r.get('id')}: missing field {field!r}"


def test_t10_2_definition_pointers_resolve_and_traceable():
    """T10.2: every dimension/role definition doc-pointer resolves (doc exists)
    and its keyword is grep-able in that doc (T2.7-style traceability)."""
    for entry in _load_block("dimensions") + _load_block("roles"):
        definition = entry["definition"]
        m = DEF_RE.match(str(definition))
        assert m, f"{entry['id']}: definition {definition!r} not in 'keyword (doc §sec)' form"
        doc = ROOT / m.group("doc")
        assert doc.exists(), f"{entry['id']}: definition doc missing: {m.group('doc')}"
        keyword = m.group("kw").strip()
        corpus = doc.read_text(encoding="utf-8")
        assert keyword in corpus, (
            f"{entry['id']}: definition keyword {keyword!r} not grep-able in {m.group('doc')}"
        )

    # Standalone (non-embedded) paradigm docs must also resolve -- guards the
    # orphan-wiring of paradigm-E/F and the LGFV framework pointer.
    for d in _load_block("dimensions"):
        standalone = str(d["standalone_doc"])
        if standalone.startswith("dev/"):
            assert (ROOT / standalone).exists(), f"{d['id']}: standalone_doc missing: {standalone}"


def test_t10_3_industry_mapping_consistent_with_contagion_matrix():
    """T10.3: the registry's paradigm->industry mapping matches contagion-matrix
    section 1.2 范式映射表 (main paradigm per industry), in both directions."""
    cmap = _parse_contagion_paradigm_map(CONTAGION)
    assert cmap, "contagion-matrix section 1.2 paradigm map parse yielded nothing"

    dims = _load_block("dimensions")
    by_letter = {d["letter"]: d for d in dims}

    # contagion -> registry: each industry lands under its main-paradigm dimension.
    for industry, letter in cmap.items():
        dim = by_letter.get(letter)
        assert dim is not None, f"no dimension for letter {letter!r} (industry {industry})"
        assert industry in dim["industries"], (
            f"{industry} (范式{letter}) not listed in {dim['id']}.industries"
        )

    # registry -> contagion: every registered industry is its dimension's main paradigm.
    for d in dims:
        for industry in d["industries"]:
            assert cmap.get(industry) == d["letter"], (
                f"{industry} registered under {d['id']} but contagion-matrix assigns "
                f"main paradigm {cmap.get(industry)!r}"
            )


def test_t10_4_no_copied_numeric_thresholds():
    """T10.4: dimension-registry.md copies no numeric thresholds (pointer layer)."""
    text = REGISTRY.read_text(encoding="utf-8")
    for m in DECIMAL_RE.finditer(text):
        prev = text[m.start() - 1] if m.start() > 0 else ""
        assert prev in DECIMAL_WHITELIST_PREV, (
            f"numeric-threshold-like decimal {m.group()!r} at offset {m.start()}. "
            "Whitelist: version tokens (v0.7.1-release) and section refs (§x.y)."
        )


def test_t10_5_core_docs_membership():
    """T10.5: the 2 paradigm docs + dimension-registry are in CORE_DOCS, so
    check_versions covers them (version-check gap closed)."""
    cc = _import_checker()
    for doc in (
        "paradigm-brand-channel.md",
        "paradigm-network-traffic.md",
        "dimension-registry.md",
    ):
        assert doc in cc.CORE_DOCS, f"{doc} not in CORE_DOCS"


def _load_work_paths() -> list[dict]:
    """Parse the work-path registry's ```yaml blocks (dicts carrying an ``id``)."""
    text = WORK_PATH_REGISTRY.read_text(encoding="utf-8")
    paths = []
    for block in YAML_BLOCK_RE.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            paths.append(data)
    return paths


def test_t10_6_used_by_paths_matches_work_path_registry():
    """T10.6: ``used_by_paths`` is recomputed from work-path-registry.md and must
    match -- the registry's most routing-relevant field, guarded against drift.

    Aggregation rules (mirroring dimension-registry §三):
    - roles: path ids whose ``role`` equals the role letter (M0-M5).
    - paradigms: path ids whose ``paradigm_selection`` begins with "六范式"
      (the collective 六范式+LGFV mapping reference), shared uniformly across all
      7 dimensions because the source is collective rather than per-paradigm.
    """
    paths = _load_work_paths()
    assert paths, "work-path registry parse yielded nothing"

    for role in _load_block("roles"):
        letter = role["id"].split("-", 1)[1]  # role-M0 -> M0
        expected = sorted(p["id"] for p in paths if str(p.get("role")) == letter)
        assert expected, f"{role['id']}: no work paths with role {letter}"
        assert sorted(role["used_by_paths"]) == expected, (
            f"{role['id']}.used_by_paths {sorted(role['used_by_paths'])} != {expected}"
        )

    paradigm_path_ids = sorted(
        p["id"]
        for p in paths
        if str(p.get("paradigm_selection", "")).startswith("六范式")
    )
    assert paradigm_path_ids, "no work paths with a 六范式 paradigm_selection"
    for dim in _load_block("dimensions"):
        assert sorted(dim["used_by_paths"]) == paradigm_path_ids, (
            f"{dim['id']}.used_by_paths {sorted(dim['used_by_paths'])} != "
            f"{paradigm_path_ids}"
        )

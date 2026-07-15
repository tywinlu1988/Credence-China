"""Integrity tests for the work-path registry (v0.7.2).

The registry (dev/engine/work-path-registry.md) is the routing baseline for the
v0.8.0 skill architecture. Each of the 16 work paths is registered as a fenced
```yaml block. These tests (T2.1-T2.7) validate the registry's own structure and
internal consistency only -- they do not exercise any engine logic.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"

# Fields every registered path must declare (T2.1).
REQUIRED_FIELDS = [
    "id",
    "name",
    "status",
    "role",
    "depth",
    "engine_sequence",
    "templates",
    "quality_gates",
]

VALID_STATUS = {"active", "partial", "planned"}
ALL_ROLES = ["M0", "M1", "M2", "M3", "M4", "M5"]
ID_RE = re.compile(r"^WP-(M[0-5]|X)-\d{2}$")

# Non-file markers allowed in `templates` (must match registry §schema).
TEMPLATE_MARKERS = ("planned", "L0-spec")

YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def _load_paths() -> list[dict]:
    """Parse every fenced ```yaml block; keep those that look like a path record."""
    text = REGISTRY.read_text(encoding="utf-8")
    paths = []
    for block in YAML_BLOCK_RE.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            paths.append(data)
    return paths


PATHS = _load_paths()
PATHS_BY_ID = {p["id"]: p for p in PATHS}


def _is_template_marker(entry: object) -> bool:
    """A templates entry is either a real file path or an allowed marker value."""
    s = str(entry).strip()
    return any(s == m or s.startswith(m + ":") or s.startswith(m + " ") for m in TEMPLATE_MARKERS)


def _gate_rule_name(gate: object) -> str:
    """Extract the rule name from a quality-gate string of the form '规则名 (文档 §节)'."""
    s = str(gate)
    idx = s.find(" (")
    return s[:idx].strip() if idx != -1 else s.strip()


def test_registry_has_exactly_16_paths():
    """Guard against dropped/duplicated yaml blocks during edits."""
    assert len(PATHS) == 16, f"expected 16 registered paths, found {len(PATHS)}"


def test_t2_1_required_fields_present():
    """T2.1: every path declares all schema required fields."""
    for p in PATHS:
        for field in REQUIRED_FIELDS:
            assert field in p, f"{p.get('id')}: missing required field '{field}'"
            assert p[field] is not None, f"{p['id']}: field '{field}' is None"


def test_t2_2_engine_sequence_docs_exist():
    """T2.2: every engine_sequence reference resolves to a real file on disk.

    planned paths may carry an empty engine_sequence (or explicit 'planned'
    markers), which are skipped.
    """
    for p in PATHS:
        seq = p["engine_sequence"] or []
        assert isinstance(seq, list), f"{p['id']}: engine_sequence must be a list"
        for doc in seq:
            if str(doc).strip().lower() == "planned":
                continue
            assert (ROOT / str(doc)).exists(), f"{p['id']}: engine doc missing: {doc}"


def test_t2_3_templates_exist_or_allowed_marker():
    """T2.3: every templates reference is a real file or an allowed marker.

    Allowed non-file markers (defined in registry §schema): 'planned' and
    'L0-spec: <doc> §节'. No dangling template paths are permitted.
    """
    for p in PATHS:
        tmpls = p["templates"] or []
        assert tmpls, f"{p['id']}: templates must not be empty (use 'planned' marker)"
        for t in tmpls:
            if _is_template_marker(t):
                continue
            assert (ROOT / str(t)).exists(), f"{p['id']}: template missing: {t}"


def test_t2_4_status_semantics_self_consistent():
    """T2.4: status is a valid enum; an active path must not reference planned templates."""
    for p in PATHS:
        assert p["status"] in VALID_STATUS, f"{p['id']}: invalid status {p['status']!r}"
        if p["status"] == "active":
            planned = [t for t in p["templates"] if str(t).strip() == "planned"]
            assert not planned, f"{p['id']}: active path must not have planned templates"


def test_t2_5_all_customer_roles_covered():
    """T2.5: each customer role M0-M5 has at least one path (planned allowed)."""
    roles = {p["role"] for p in PATHS}
    for role in ALL_ROLES:
        assert role in roles, f"role {role} has no registered path"


def test_t2_6_id_unique_and_wellformed():
    """T2.6: path ids are unique, match WP-{role}-{seq}, and align with the role field."""
    ids = [p["id"] for p in PATHS]
    assert len(ids) == len(set(ids)), f"duplicate path ids: {ids}"
    for p in PATHS:
        pid = p["id"]
        assert ID_RE.match(pid), f"{pid}: does not match {ID_RE.pattern}"
        prefix = pid.split("-")[1]
        if prefix.startswith("M"):
            assert p["role"] == prefix, f"{pid}: role field {p['role']!r} != id prefix {prefix!r}"
        else:  # X paths are meta/specialist, not a single customer role
            assert p["role"] == "meta", f"{pid}: X path role must be 'meta', got {p['role']!r}"


def test_t2_7_active_quality_gates_traceable():
    """T2.7: each active path's quality-gate rule name is grep-able in its engine docs.

    The rule name (text before the ' (' separator) must appear verbatim in at
    least one of the path's engine_sequence documents -- proving the gate is not
    fabricated. planned paths are exempt (no engine to trace against).
    """
    for p in PATHS:
        if p["status"] != "active":
            continue
        corpus = "".join(
            (ROOT / str(doc)).read_text(encoding="utf-8") for doc in p["engine_sequence"]
        )
        gates = p["quality_gates"] or []
        assert gates, f"{p['id']}: active path must declare at least one quality gate"
        for gate in gates:
            rule = _gate_rule_name(gate)
            assert rule, f"{p['id']}: could not extract rule name from gate {gate!r}"
            assert rule in corpus, (
                f"{p['id']}: quality-gate rule {rule!r} not found in engine_sequence docs"
            )

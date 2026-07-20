"""Unit tests for the work-path sheet schema + validator (v0.7.5 — 管线化基础).

src/path_sheet.py is the machine-readable single source for the 《工作路径单》 emitted
by the credit-analysis-router skill. These tests (T5.1-T5.4) cover the validator's
correctness, the planned-path 待开发 notice, the cross-reference consistency of the
registry's chaining-rules section, and the validator's wiring into consistency_check.

T5.1/T5.2 use small synthetic registry dicts and tmp fixtures, not the real registry.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

from src.path_sheet import (
    Depth,
    Mode,
    Object,
    PathSheet,
    PathStatus,
    Role,
    is_planned,
    is_template_marker,
    load_registry_paths,
    sheet_notice,
    validate_path_sheet,
)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"
CHECKER = ROOT / "scripts" / "consistency_check.py"


# --------------------------------------------------------------------------
# helpers / fixtures
# --------------------------------------------------------------------------

def _valid_sheet() -> dict:
    """A fully valid sheet pointing at the active path WP-M0-01."""
    return {
        "role": "M0",
        "object": "single-issuer",
        "depth": "L2",
        "mode": "A",
        "path_id": "WP-M0-01",
        "engine_reading_order": ["dev/engine/industry-framework.md"],
        "quality_gates": ["信号密度 (dev/engine/mosaic-engine.md §4.3)"],
        "notes": "",
    }


def _active_registry(template: str = "dev/templates/template-type1.html") -> dict:
    return {
        "WP-M0-01": {
            "id": "WP-M0-01",
            "name": "信贷审批单标的评级",
            "status": "active",
            "templates": [template],
        }
    }


def _planned_registry() -> dict:
    return {
        "WP-M2-01": {
            "id": "WP-M2-01",
            "name": "承销可行性评估",
            "status": "planned",
            "templates": ["planned"],
        }
    }


def _make_template(root: Path, rel: str = "dev/templates/template-type1.html") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<html></html>", encoding="utf-8")
    return path


def _import_checker():
    spec = importlib.util.spec_from_file_location("consistency_check", CHECKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["consistency_check"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# T5.1 — validator correctness
# --------------------------------------------------------------------------

def test_t5_1_valid_sheet_passes(tmp_path):
    """A fully valid sheet yields an empty error list."""
    _make_template(tmp_path)
    errors = validate_path_sheet(_valid_sheet(), _active_registry(), root=tmp_path)
    assert errors == []


def test_t5_1_missing_required_field_reported(tmp_path):
    """A sheet missing a required field reports that field by name."""
    _make_template(tmp_path)
    for field in ("role", "object", "depth", "mode", "path_id", "engine_reading_order"):
        sheet = _valid_sheet()
        del sheet[field]
        errors = validate_path_sheet(sheet, _active_registry(), root=tmp_path)
        assert any(field in e for e in errors), f"missing field {field!r} not reported: {errors}"


def test_t5_1_empty_scalar_field_reported(tmp_path):
    """A present-but-empty scalar required field is reported as empty."""
    _make_template(tmp_path)
    sheet = _valid_sheet()
    sheet["role"] = "   "
    errors = validate_path_sheet(sheet, _active_registry(), root=tmp_path)
    assert any("role" in e and "empty" in e for e in errors)


def test_t5_1_illegal_enum_values_reported(tmp_path):
    """An illegal enum value reports the field name and the offending value."""
    _make_template(tmp_path)
    cases = [
        ("role", "M9"),
        ("object", "single-issue"),  # near-miss typo
        ("depth", "L9"),
        ("mode", "C"),
    ]
    for field, bad in cases:
        sheet = _valid_sheet()
        sheet[field] = bad
        errors = validate_path_sheet(sheet, _active_registry(), root=tmp_path)
        assert any(field in e and bad in e for e in errors), (
            f"illegal {field}={bad!r} not reported with field+value: {errors}"
        )


def test_t5_1_unknown_path_id_reported(tmp_path):
    """An unknown path_id reports the invalid id."""
    _make_template(tmp_path)
    sheet = _valid_sheet()
    sheet["path_id"] = "WP-M9-99"
    errors = validate_path_sheet(sheet, _active_registry(), root=tmp_path)
    assert any("WP-M9-99" in e for e in errors)


def test_t5_1_active_path_template_must_exist(tmp_path):
    """An active path whose template is missing on disk is flagged; markers are skipped."""
    # template file NOT created -> dangling
    errors = validate_path_sheet(_valid_sheet(), _active_registry(), root=tmp_path)
    assert any("template" in e for e in errors)

    # marker templates are skipped even for active paths
    registry = _active_registry(template="L0-spec: dev/engine/output-layered-framework.md §3")
    assert validate_path_sheet(_valid_sheet(), registry, root=tmp_path) == []


def test_t5_1_non_planned_path_empty_list_rejected(tmp_path):
    """An active/partial path with an empty engine_reading_order/quality_gates is rejected.

    Empty executable sequences are only allowed for planned (待开发) paths; a
    non-planned path must carry a non-empty engine sequence and quality gates.
    """
    _make_template(tmp_path)
    for field in ("engine_reading_order", "quality_gates"):
        sheet = _valid_sheet()
        sheet[field] = []
        errors = validate_path_sheet(sheet, _active_registry(), root=tmp_path)
        assert any(field in e and "empty" in e for e in errors), (
            f"empty {field!r} on active path not rejected: {errors}"
        )


def test_t5_1_enum_meta_and_special_values_accepted(tmp_path):
    """The meta role/object and 专项 depth are legal enum values."""
    registry = {
        "WP-X-01": {"id": "WP-X-01", "status": "partial", "templates": ["planned"]}
    }
    sheet = _valid_sheet()
    sheet.update({"role": "meta", "object": "meta", "depth": "专项", "path_id": "WP-X-01"})
    assert validate_path_sheet(sheet, registry, root=tmp_path) == []


# --------------------------------------------------------------------------
# T5.2 — planned path yields 待开发 notice, not a template-invocation instruction
# --------------------------------------------------------------------------

def test_t5_2_planned_path_passes_validation_but_flagged(tmp_path):
    """A sheet pointing at a planned path passes validation yet is detectably planned."""
    registry = _planned_registry()
    sheet = _valid_sheet()
    sheet.update(
        {
            "role": "M2",
            "object": "single-issuer",
            "depth": "专项",
            "path_id": "WP-M2-01",
            "engine_reading_order": [],
            "quality_gates": [],
        }
    )
    # validation does NOT fail solely because the path is planned
    assert validate_path_sheet(sheet, registry, root=tmp_path) == []
    # ... but the planned-detection helper flags it
    assert is_planned("WP-M2-01", registry) is True
    assert is_planned("WP-M0-01", _active_registry()) is False


def test_t5_2_planned_notice_is_not_an_invocation(tmp_path):
    """The planned notice is a 待开发 notice, not a template-invocation instruction."""
    registry = _planned_registry()
    sheet = _valid_sheet()
    sheet.update({"path_id": "WP-M2-01", "engine_reading_order": [], "quality_gates": []})
    notice = sheet_notice(sheet, registry)
    assert notice is not None
    assert "待开发" in notice
    assert "WP-M2-01" in notice

    # active / unknown paths produce no notice
    assert sheet_notice(_valid_sheet(), _active_registry()) is None
    unknown = _valid_sheet()
    unknown["path_id"] = "WP-M9-99"
    assert sheet_notice(unknown, _active_registry()) is None


# --------------------------------------------------------------------------
# T5.3 — chaining-rules section cross-reference consistency
# --------------------------------------------------------------------------

def _chaining_section(text: str) -> str:
    m = re.search(r"^## .*链式规则[^\n]*\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def test_t5_3_chaining_rules_cross_reference_consistent():
    """The chaining-rules section references the tier/SRI source docs and uses the same
    tier labels, without restating any numeric threshold that belongs to a source doc."""
    text = REGISTRY.read_text(encoding="utf-8")
    section = _chaining_section(text)
    assert section, "registry is missing a 链式规则 (chaining-rules) section"

    # references the single-source docs by document name
    assert "output-layered-framework" in section
    assert "systemic-warning-framework" in section

    # uses the same L0/L1/L2 tier labels defined in output-layered-framework
    for tier in ("L0", "L1", "L2"):
        assert tier in section

    # does NOT restate source-doc numeric thresholds: tier time budgets (§2.1),
    # signal-priority gates (§6.3), and SRI thermometer bands (§3.1) live in the
    # source docs and must not be re-defined here.
    for forbidden in ("5秒", "30秒", "分钟", ">30", ">15", "0.5", "1.0", "1.8"):
        assert forbidden not in section, (
            f"chaining-rules section restates source-doc threshold {forbidden!r}"
        )


# --------------------------------------------------------------------------
# T5.4 — validator wired into consistency_check.collect_errors
# --------------------------------------------------------------------------

def test_t5_4_validator_wired_into_consistency_check(monkeypatch):
    """consistency_check defines check_path_sheets() and collect_errors() invokes it."""
    cc = _import_checker()
    assert hasattr(cc, "check_path_sheets"), "consistency_check must define check_path_sheets()"

    # the check passes on the current repo state
    assert cc.check_path_sheets() == []

    # and collect_errors() actually calls it
    calls = []
    monkeypatch.setattr(cc, "check_path_sheets", lambda: calls.append(1) or [])
    cc.collect_errors()
    assert calls, "collect_errors() must call check_path_sheets()"


# --------------------------------------------------------------------------
# supporting: registry parsing + dataclass interop
# --------------------------------------------------------------------------

def test_load_registry_paths_parses_real_registry():
    """load_registry_paths is the single-source parser shared by validator and tests."""
    paths = load_registry_paths(REGISTRY)
    assert len(paths) == 16
    assert paths["WP-M2-01"]["status"] == PathStatus.ACTIVE.value
    assert paths["WP-M0-02"]["status"] == PathStatus.PARTIAL.value


def test_path_sheet_dataclass_roundtrip():
    sheet = _valid_sheet()
    obj = PathSheet.from_dict(sheet)
    assert obj.to_dict() == sheet
    # validate accepts a PathSheet instance as well as a plain dict
    assert validate_path_sheet(obj, _active_registry(), root=ROOT) == []


def test_is_template_marker():
    assert is_template_marker("planned")
    assert is_template_marker("L0-spec: dev/engine/output-layered-framework.md §3")
    assert not is_template_marker("dev/templates/template-type1.html")


def test_enum_values_match_router_contract():
    assert {r.value for r in Role} == {"M0", "M1", "M2", "M3", "M4", "M5", "meta"}
    assert {o.value for o in Object} == {"single-issuer", "portfolio", "industry", "market", "meta"}
    assert {d.value for d in Depth} == {"L0", "L1", "L2", "专项"}
    assert {m.value for m in Mode} == {"A", "B"}

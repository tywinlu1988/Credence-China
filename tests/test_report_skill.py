"""Integrity tests for the credit-report-builder skill (v0.7.7).

The report skill (dev/.claude/skills/credit-report-builder/SKILL.md) is stage S3 of
the four-stage chain: it turns an upstream 《分析产物》 into a deliverable report by
selecting the work path's registered templates and mapping findings onto the
L0/L1/L2 output tiers, then emits a 《交付单》. These tests (T7.1-T7.5) validate the
skill's structure and its fidelity to the single-source principle (it must not copy
engine thresholds/tier budgets) -- they do not exercise any engine logic.
"""

import re
from pathlib import Path

import yaml

from src.path_sheet import is_template_marker, load_registry_paths

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "dev" / ".claude" / "skills" / "credit-report-builder"
SKILL_MD = SKILL_DIR / "SKILL.md"
REPORT_MAPPING = SKILL_DIR / "references" / "report-mapping.md"
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"
CONTRACT = ROOT / "dev" / "engine" / "pipeline-contract.md"
TEMPLATES_DIR = ROOT / "dev" / "templates"
SKILLS_DIR = ROOT / "dev" / ".claude" / "skills"

SKILL_TEXT = SKILL_MD.read_text(encoding="utf-8")
MAPPING_TEXT = REPORT_MAPPING.read_text(encoding="utf-8")

YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
TEMPLATE_RE = re.compile(r"template-type\d+")

# --- no-copied-thresholds guard (same pattern as test_router_skill T3.2) ---------
# Allow only version tokens (v0.7.1-release, preceded by v/V) and section refs
# (§x.y, preceded by §). Path ids, Type N labels, and ISO dates carry no decimal.
DECIMAL_RE = re.compile(r"\d+\.\d+")
DECIMAL_WHITELIST_PREV = ("v", "V", "§")

FOUR_SKILLS = (
    "credit-analysis-router",
    "fixed-income-credit-analysis",
    "credit-report-builder",
    "credit-qa-verifier",
)


def _assert_no_thresholds(text: str, label: str) -> None:
    for m in DECIMAL_RE.finditer(text):
        prev = text[m.start() - 1] if m.start() > 0 else ""
        assert prev in DECIMAL_WHITELIST_PREV, (
            f"{label}: numeric-threshold-like decimal {m.group()!r} at offset {m.start()}. "
            "Whitelist: version tokens (v0.7.1-release) and section refs (§x.y)."
        )


def _section(text: str, heading: str) -> str:
    """Return the body of a '## <heading>' section up to the next '## ' heading."""
    m = re.search(rf"## {re.escape(heading)}[^\n]*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return m.group(1) if m else ""


def _mapping_rows() -> list[list[str]]:
    """Parse the 装配映射 table into data rows (list of cell lists)."""
    section = _section(MAPPING_TEXT, "装配映射")
    lines = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 3, "装配映射 table must have a header, separator, and data rows"
    return [
        [c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[2:]
    ]


def _registry_template_tokens(path_id: str, registry_paths: dict) -> set[str]:
    """Normalize a registry path's templates to file stems + marker keywords."""
    tokens = set()
    for entry in registry_paths[path_id].get("templates") or []:
        s = str(entry)
        if is_template_marker(s):
            tokens.add("L0-spec" if s.startswith("L0-spec") else "planned")
        else:
            tokens.add(Path(s).stem)
    return tokens


def test_t7_1_frontmatter_structure_and_guardrail():
    """T7.1: frontmatter valid, SKILL <=200 lines, 'does not perform analysis' present."""
    fm_match = re.match(r"---\n(.*?)\n---\n", SKILL_TEXT, re.DOTALL)
    assert fm_match, "frontmatter block not found"
    fm = yaml.safe_load(fm_match.group(1))
    assert isinstance(fm, dict), "frontmatter must be a mapping"
    assert fm.get("name") == "credit-report-builder"
    assert fm.get("description"), "frontmatter description missing"
    assert len(fm["description"]) < 500, "description must be <500 chars"

    n_lines = len(SKILL_TEXT.splitlines())
    assert n_lines <= 200, f"SKILL.md has {n_lines} lines (>200)"

    # the assembly-layer guardrail must be explicit (report does not analyze)
    assert "does not perform analysis" in SKILL_TEXT
    assert "不做分析" in SKILL_TEXT


def test_t7_2_references_templates_and_tier_doc_no_thresholds():
    """T7.2: references the registry templates field + the tier doc; no thresholds."""
    assert "work-path-registry" in SKILL_TEXT, "must reference the registry (templates source)"
    assert "templates" in SKILL_TEXT, "must reference the registry templates field"
    assert "output-layered-framework" in SKILL_TEXT, "must reference the tier doc"
    assert "output-layered-framework" in MAPPING_TEXT, "mapping must reference the tier doc"
    _assert_no_thresholds(SKILL_TEXT, "SKILL.md")
    _assert_no_thresholds(MAPPING_TEXT, "references/report-mapping.md")


def test_t7_3_named_templates_exist_or_marker():
    """T7.3: every named template Type exists on disk or is a registered marker."""
    combined = SKILL_TEXT + "\n" + MAPPING_TEXT
    named = set(TEMPLATE_RE.findall(combined))
    assert named, "report skill must name at least one template Type"
    for stem in named:
        assert (TEMPLATES_DIR / f"{stem}.html").exists(), (
            f"{stem} named but missing under dev/templates/"
        )
    # markers referenced are recognized registry markers (planned / L0-spec)
    for marker in set(re.findall(r"planned|L0-spec", combined)):
        assert is_template_marker(marker), f"{marker!r} is not a registered template marker"


def test_t7_4_path_template_mapping_subset_of_registry():
    """T7.4: the skill's path→template mapping is a subset of the registry (no drift)."""
    registry_paths = load_registry_paths(REGISTRY)
    rows = _mapping_rows()
    assert len(rows) == 16, f"expected 16 mapping rows, found {len(rows)}"
    for cells in rows:
        pid, tmpl_cell = cells[0], cells[4]
        assert pid in registry_paths, f"mapping references unknown path {pid}"
        listed = set(TEMPLATE_RE.findall(tmpl_cell))
        for marker in ("planned", "L0-spec"):
            if marker in tmpl_cell:
                listed.add(marker)
        allowed = _registry_template_tokens(pid, registry_paths)
        assert listed <= allowed, (
            f"{pid}: mapping templates {sorted(listed)} drift from registry {sorted(allowed)}"
        )


def test_t7_5_contract_declares_four_stages_and_skill_dirs():
    """T7.5: pipeline-contract declares all 4 stages; each of the 4 skill dirs present."""
    contract = CONTRACT.read_text(encoding="utf-8")
    for artifact in ("工作路径单", "分析产物", "交付单", "质检裁决"):
        assert artifact in contract, f"contract missing stage artifact {artifact!r}"
    for skill in FOUR_SKILLS:
        assert skill in contract, f"contract does not reference skill {skill!r}"
        assert (SKILLS_DIR / skill / "SKILL.md").exists(), (
            f"skill dir {skill}/SKILL.md missing on disk"
        )

"""Integrity tests for the credit-analysis-router skill (v0.7.3).

The router skill (dev/.claude/skills/credit-analysis-router/SKILL.md) performs
progressive requirement elicitation (four questions) and emits a structured
work-path sheet that routes to the work-path registry. These tests (T3.1-T3.6)
validate the router's structure and its fidelity to the single-source principle
(it must not copy engine thresholds) -- they do not exercise any engine logic.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "dev" / ".claude" / "skills" / "credit-analysis-router"
SKILL_MD = SKILL_DIR / "SKILL.md"
WORK_PATHS_MD = SKILL_DIR / "references" / "work-paths.md"
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"

SKILL_TEXT = SKILL_MD.read_text(encoding="utf-8")
WORK_PATHS_TEXT = WORK_PATHS_MD.read_text(encoding="utf-8")
REGISTRY_TEXT = REGISTRY.read_text(encoding="utf-8")

PATH_ID_RE = re.compile(r"WP-(?:M[0-5]|X)-\d{2}")
YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)

# Marker used in the Routing Table for the vague-requirement scenario, which
# routes to the four-question protocol rather than a concrete path id.
FOUR_QUESTION_MARKER = "四问协议"

# Fields the emitted work-path sheet must always declare (T3.4).
REQUIRED_SHEET_FIELDS = [
    "role",
    "object",
    "depth",
    "mode",
    "path_id",
    "engine_reading_order",
    "quality_gates",
]


def _registry_path_ids() -> set[str]:
    """Collect every registered path id from the registry's fenced yaml blocks."""
    ids = set()
    for block in YAML_BLOCK_RE.findall(REGISTRY_TEXT):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            ids.add(str(data["id"]).strip())
    return ids


REGISTRY_IDS = _registry_path_ids()


def _section(text: str, heading: str) -> str:
    """Return the body of a '## <heading>' section up to the next '## ' heading."""
    m = re.search(rf"## {re.escape(heading)}[^\n]*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return m.group(1) if m else ""


def _routing_table() -> tuple[list[str], list[list[str]]]:
    """Parse the Routing Table markdown table into (header_cells, data_rows)."""
    section = _section(SKILL_TEXT, "Routing Table")
    lines = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 3, "Routing Table must have a header, separator, and data rows"
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    rows = [
        [c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[2:]
    ]
    return header, rows


def _path_sheet_template() -> dict:
    """Return the first (template) yaml block inside the Path Sheet Output section."""
    section = _section(SKILL_TEXT, "Path Sheet Output")
    blocks = YAML_BLOCK_RE.findall(section)
    assert blocks, "no yaml block found in the Path Sheet Output section"
    data = yaml.safe_load(blocks[0])
    assert isinstance(data, dict), "path-sheet template yaml must be a mapping"
    return data


def test_registry_parsed():
    """Sanity guard: the registry parse yielded the expected path set."""
    assert len(REGISTRY_IDS) == 16, f"expected 16 registry ids, found {len(REGISTRY_IDS)}"


def test_t3_1_routing_table_coverage():
    """T3.1: Routing Table has >=10 scenario rows; each recommended path id exists.

    The vague-requirement row routes to the four-question protocol (marked
    '四问协议') instead of a path id -- that row is allowed and must be present.
    """
    header, rows = _routing_table()
    rec_idx = header.index("推荐路径")
    assert len(rows) >= 10, f"expected >=10 scenario rows, found {len(rows)}"
    saw_four_question = False
    for cells in rows:
        rec = cells[rec_idx]
        if FOUR_QUESTION_MARKER in rec:
            saw_four_question = True
            continue
        ids = PATH_ID_RE.findall(rec)
        assert ids, f"routing row recommends neither a path id nor the marker: {cells}"
        for pid in ids:
            assert pid in REGISTRY_IDS, f"recommended path {pid} not in registry"
    assert saw_four_question, "no vague-requirement row routing to the four-question protocol"


# --- T3.2: no copied engine thresholds ---------------------------------------
#
# The router must not reproduce any engine threshold/weight/rating number. We
# scan for decimal-number patterns (\d+\.\d+) and allow only a small whitelist:
#   - version tokens such as 'v0.7.1-release'  (decimal preceded by 'v'/'V')
#   - section references such as '§4.3'         (decimal preceded by '§')
# Path ids (WP-M0-01) and ISO dates (2026-07-15) contain no decimal point, so
# they never match the pattern and need no whitelist entry. Any other decimal
# is treated as a leaked threshold and fails the test.
DECIMAL_RE = re.compile(r"\d+\.\d+")
DECIMAL_WHITELIST_PREV = ("v", "V", "§")


def _assert_no_thresholds(text: str, label: str) -> None:
    for m in DECIMAL_RE.finditer(text):
        prev = text[m.start() - 1] if m.start() > 0 else ""
        assert prev in DECIMAL_WHITELIST_PREV, (
            f"{label}: numeric-threshold-like decimal {m.group()!r} at offset {m.start()}. "
            "Whitelist: version tokens (v0.7.1-release) and section refs (§x.y); "
            "path ids and dates carry no decimal point."
        )


def test_t3_2_no_copied_engine_thresholds():
    """T3.2: neither SKILL.md nor references/work-paths.md copies engine thresholds."""
    _assert_no_thresholds(SKILL_TEXT, "SKILL.md")
    _assert_no_thresholds(WORK_PATHS_TEXT, "references/work-paths.md")


def test_t3_3_all_referenced_path_ids_exist():
    """T3.3: every WP- path id mentioned anywhere in the router exists in the registry."""
    for label, text in (("SKILL.md", SKILL_TEXT), ("work-paths.md", WORK_PATHS_TEXT)):
        for pid in sorted(set(PATH_ID_RE.findall(text))):
            assert pid in REGISTRY_IDS, f"{label} references unknown path id {pid}"


def test_t3_4_path_sheet_schema():
    """T3.4: the path-sheet yaml template declares all required fields."""
    sheet = _path_sheet_template()
    for field in REQUIRED_SHEET_FIELDS:
        assert field in sheet, f"path-sheet template missing required field {field!r}"


def test_t3_5_mode_b_guardrail_present():
    """T3.5: the Mode B anti-hallucination guardrail is stated in the protocol."""
    assert "未显式提供" in SKILL_TEXT, "Mode B guardrail keyword '未显式提供' missing"
    assert "数据缺口" in SKILL_TEXT, "Mode B guardrail keyword '数据缺口' missing"


def test_t3_6_skill_structure():
    """T3.6: frontmatter complete, SKILL.md <=200 lines, references version in sync."""
    # frontmatter
    fm_match = re.match(r"---\n(.*?)\n---\n", SKILL_TEXT, re.DOTALL)
    assert fm_match, "frontmatter block not found"
    fm = yaml.safe_load(fm_match.group(1))
    assert isinstance(fm, dict), "frontmatter must be a mapping"
    assert fm.get("name") == "credit-analysis-router"
    assert fm.get("description"), "frontmatter description missing"

    # line budget
    n_lines = len(SKILL_TEXT.splitlines())
    assert n_lines <= 200, f"SKILL.md has {n_lines} lines (>200)"

    # references/work-paths.md version header matches the registry version header
    ver_re = re.compile(r"\*\*版本\*\*\s*[:：]?\s*([^\s|]+)")

    def _ver(text: str) -> str | None:
        m = ver_re.search(text)
        return m.group(1) if m else None

    ref_ver, reg_ver = _ver(WORK_PATHS_TEXT), _ver(REGISTRY_TEXT)
    assert ref_ver is not None, "references/work-paths.md missing 版本 header"
    assert reg_ver is not None, "registry missing 版本 header"
    assert ref_ver == reg_ver, f"work-paths.md version {ref_ver} != registry {reg_ver}"

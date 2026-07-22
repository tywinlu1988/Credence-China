"""Integrity tests for the credit-qa-verifier skill (v0.7.7).

The qa skill (dev/.claude/skills/credit-qa-verifier/SKILL.md) is stage S4 (terminal)
of the four-stage chain: it verifies a Delivery Note plus its upstream Analysis
Artifact and Path Sheet against the path's quality gates and four mandatory checks,
then emits a terminal 《质检裁决》. These tests (T8.1-T8.5) validate the skill's
structure, the grep-ability of its gate rule-names in the engine docs (T2.7-style
traceability), and its fidelity to the single-source principle -- they do not
exercise any engine logic.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "dev" / ".claude" / "skills" / "credit-qa-verifier"
SKILL_MD = SKILL_DIR / "SKILL.md"
QA_CHECKLIST = SKILL_DIR / "references" / "qa-checklist.md"
AGENTS_MD = ROOT / "AGENTS.md"

SKILL_TEXT = SKILL_MD.read_text(encoding="utf-8")
CHECKLIST_TEXT = QA_CHECKLIST.read_text(encoding="utf-8")

YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
DOC_PATH_RE = re.compile(r"dev/engine/[\w.-]+\.md")

# --- no-copied-thresholds guard (same pattern as test_router_skill T3.2) ---------
DECIMAL_RE = re.compile(r"\d+\.\d+")
DECIMAL_WHITELIST_PREV = ("v", "V", "§")

NEW_SKILLS = ("credit-report-builder", "credit-qa-verifier")


def _assert_no_thresholds(text: str, label: str) -> None:
    for m in DECIMAL_RE.finditer(text):
        prev = text[m.start() - 1] if m.start() > 0 else ""
        assert prev in DECIMAL_WHITELIST_PREV, (
            f"{label}: numeric-threshold-like decimal {m.group()!r} at offset {m.start()}. "
            "Whitelist: version tokens (v0.7.1-release) and section refs (§x.y)."
        )


def _checklist_gate_rows() -> list[tuple[str, str]]:
    """Parse (rule_name, doc_path) pairs from the checklist's gate tables.

    In every gate row the rule name is the cell immediately before the engine-doc
    cell (the one carrying a 'dev/engine/*.md' path). Header/separator rows carry
    no doc path and are skipped.
    """
    rows = []
    for ln in CHECKLIST_TEXT.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        doc_idx = next((i for i, c in enumerate(cells) if DOC_PATH_RE.search(c)), None)
        if doc_idx is None or doc_idx == 0:
            continue
        rule = cells[doc_idx - 1]
        if "规则名" in rule or "规则源" in rule:
            continue
        doc = DOC_PATH_RE.search(cells[doc_idx]).group(0)
        rows.append((rule, doc))
    return rows


def _concrete_qa_verdict() -> dict:
    """Return the concrete QA Verdict example (the yaml block with a non-empty path_id)."""
    for block in YAML_BLOCK_RE.findall(SKILL_TEXT):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and str(data.get("path_id") or "").strip():
            return data
    raise AssertionError("no concrete QA Verdict yaml block found in SKILL.md")


def test_t8_1_frontmatter_structure_and_guardrails():
    """T8.1: frontmatter valid, SKILL <=200 lines, never-relax/density/Mode-B keywords."""
    fm_match = re.match(r"---\n(.*?)\n---\n", SKILL_TEXT, re.DOTALL)
    assert fm_match, "frontmatter block not found"
    fm = yaml.safe_load(fm_match.group(1))
    assert isinstance(fm, dict), "frontmatter must be a mapping"
    assert fm.get("name") == "credit-qa-verifier"
    assert fm.get("description"), "frontmatter description missing"
    assert len(fm["description"]) < 500, "description must be <500 chars"

    n_lines = len(SKILL_TEXT.splitlines())
    assert n_lines <= 200, f"SKILL.md has {n_lines} lines (>200)"

    assert "never relaxes a gate" in SKILL_TEXT, "'never relaxes a gate' guardrail missing"
    assert "从不放宽门禁" in SKILL_TEXT, "'从不放宽门禁' guardrail missing"
    assert "信号密度" in SKILL_TEXT, "density keyword '信号密度' missing"
    assert "Mode B" in SKILL_TEXT, "Mode B keyword missing"


def test_t8_2_gate_rule_names_grep_in_engine_docs():
    """T8.2: every qa gate rule-name is grep-able in its named engine doc (T2.7-style)."""
    rows = _checklist_gate_rows()
    assert rows, "no gate rows parsed from references/qa-checklist.md"
    for rule, doc in rows:
        path = ROOT / doc
        assert path.exists(), f"rule source doc {doc} not found on disk"
        text = path.read_text(encoding="utf-8")
        assert rule in text, (
            f"qa gate rule {rule!r} not grep-able in {doc} (fabricated rule?)"
        )


def test_t8_3_qa_verdict_required_fields():
    """T8.3: the concrete QA Verdict yaml declares verdict/gate_results/mandatory_checks."""
    v = _concrete_qa_verdict()
    for field in ("path_id", "verdict", "gate_results", "mandatory_checks", "remediation"):
        assert field in v, f"QA Verdict missing required field {field!r}"
    assert v["verdict"] in ("pass", "pass-with-findings", "fail"), (
        f"illegal verdict {v['verdict']!r}"
    )
    mc = v["mandatory_checks"]
    for check in ("density_rule", "veto_ceiling", "mode_b", "single_source",
                  "template_fidelity", "methodology_fidelity"):
        assert check in mc, f"mandatory_checks missing {check!r}"
    for g in v["gate_results"]:
        for sub in ("gate", "status", "evidence"):
            assert sub in g, f"gate_results entry missing {sub!r}: {g}"


def test_t8_4_no_thresholds():
    """T8.4: neither SKILL.md nor references/qa-checklist.md copies engine thresholds."""
    _assert_no_thresholds(SKILL_TEXT, "SKILL.md")
    _assert_no_thresholds(CHECKLIST_TEXT, "references/qa-checklist.md")


def test_t8_5_new_skills_referenced_in_agents_md():
    """T8.5: both new skills are referenced in AGENTS.md (sync with check_agents_entry)."""
    agents = AGENTS_MD.read_text(encoding="utf-8")
    for name in NEW_SKILLS:
        assert f"skills/{name}/SKILL.md" in agents, (
            f"AGENTS.md does not reference skills/{name}/SKILL.md"
        )

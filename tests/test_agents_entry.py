"""Integrity tests for the cross-CLI universal entry (v0.7.6).

v0.7.6 adds a repo-root AGENTS.md that any agent CLI can read to discover and
use the Credence skills, plus a Codex deep-adapter (docs/adapters/codex.md).
These tests (T6.1-T6.5) guard the single-source rule (no copied thresholds),
platform neutrality (no CLAUDE.md write instruction; >=2 non-Claude CLIs named),
and that every skill referenced in AGENTS.md resolves on disk with valid
frontmatter. They validate structure and fidelity only -- no engine logic.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = ROOT / "AGENTS.md"
CODEX_ADAPTER = ROOT / "docs" / "adapters" / "codex.md"
SKILLS_DIR = ROOT / "dev" / ".claude" / "skills"

AGENTS_TEXT = AGENTS_MD.read_text(encoding="utf-8") if AGENTS_MD.exists() else ""

# Reuse the T3.2 no-numeric-threshold guard: any decimal number (\d+\.\d+) is a
# leaked threshold unless whitelisted -- version tokens (v0.7.1-release, decimal
# preceded by 'v'/'V') and section refs (§x.y, decimal preceded by '§'). Path ids
# and ISO dates carry no decimal point, so they never match and need no entry.
DECIMAL_RE = re.compile(r"\d+\.\d+")
DECIMAL_WHITELIST_PREV = ("v", "V", "§")

# A skill path referenced inside AGENTS.md, e.g. dev/.claude/skills/<name>/SKILL.md
SKILL_PATH_RE = re.compile(r"dev/\.claude/skills/([A-Za-z0-9_-]+)/SKILL\.md")

# Non-Claude agent CLIs the universal entry must name so discovery is portable.
NON_CLAUDE_CLIS = ("codex", "cursor", "gemini", "opencode")

FRONTMATTER_RE = re.compile(r"---\n(.*?)\n---\n", re.DOTALL)


def _assert_no_thresholds(text: str, label: str) -> None:
    for m in DECIMAL_RE.finditer(text):
        prev = text[m.start() - 1] if m.start() > 0 else ""
        assert prev in DECIMAL_WHITELIST_PREV, (
            f"{label}: numeric-threshold-like decimal {m.group()!r} at offset {m.start()}. "
            "Whitelist: version tokens (v0.7.1-release) and section refs (§x.y); "
            "path ids and dates carry no decimal point."
        )


def _referenced_skill_names() -> list[str]:
    """Skill names whose SKILL.md path is referenced in AGENTS.md."""
    return sorted(set(SKILL_PATH_RE.findall(AGENTS_TEXT)))


def test_t6_1_agents_md_exists_and_skill_paths_resolve():
    """T6.1: root AGENTS.md exists; every referenced dev/.claude/skills/*/SKILL.md exists."""
    assert AGENTS_MD.exists(), "root AGENTS.md is missing"
    names = _referenced_skill_names()
    assert names, "AGENTS.md references no dev/.claude/skills/*/SKILL.md path"
    for name in names:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.exists(), f"AGENTS.md references missing skill file {path}"


def test_t6_2_platform_neutral_no_claude_md_write_and_names_non_claude_clis():
    """T6.2: AGENTS.md must not instruct writing a CLAUDE.md, and names >=2 non-Claude CLIs."""
    assert AGENTS_MD.exists(), "root AGENTS.md is missing"
    lowered = AGENTS_TEXT.lower()
    # Platform-neutral: the entry must not tell the reader to write/create a
    # CLAUDE.md. The literal path dev/.claude/skills is allowed -- it contains
    # '.claude/' but never the substring 'claude.md', so this check is safe.
    assert "claude.md" not in lowered, (
        "AGENTS.md must stay platform-neutral: refer to 'your instructions file', "
        "never instruct writing a CLAUDE.md"
    )
    named = [c for c in NON_CLAUDE_CLIS if c in lowered]
    assert len(named) >= 2, f"AGENTS.md names {len(named)} non-Claude CLIs (<2): {named}"


def test_t6_3_referenced_skills_have_valid_frontmatter():
    """T6.3: every skill referenced in AGENTS.md has frontmatter with name + description."""
    names = _referenced_skill_names()
    assert names, "AGENTS.md references no skill (nothing to validate)"
    for name in names:
        text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        assert m, f"{name}: frontmatter block not found"
        fm = yaml.safe_load(m.group(1))
        assert isinstance(fm, dict), f"{name}: frontmatter must be a mapping"
        assert fm.get("name") == name, f"{name}: frontmatter name {fm.get('name')!r} != dir name"
        assert fm.get("description"), f"{name}: frontmatter description missing"


def test_t6_4_agents_md_has_no_copied_thresholds():
    """T6.4: AGENTS.md must not copy engine thresholds (DECIMAL_RE guard)."""
    assert AGENTS_MD.exists(), "root AGENTS.md is missing"
    _assert_no_thresholds(AGENTS_TEXT, "AGENTS.md")


def test_t6_5_codex_adapter_references_registry_and_four_questions_no_thresholds():
    """T6.5: docs/adapters/codex.md exists, references registry + 4-question protocol, no thresholds."""
    assert CODEX_ADAPTER.exists(), "docs/adapters/codex.md is missing"
    text = CODEX_ADAPTER.read_text(encoding="utf-8")
    assert "work-path-registry" in text, "codex adapter must reference the work-path registry"
    assert ("四问" in text) or ("four-question" in text.lower()) or ("Q1" in text), (
        "codex adapter must reference the router's four-question protocol"
    )
    _assert_no_thresholds(text, "docs/adapters/codex.md")

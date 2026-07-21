#!/usr/bin/env python3
"""Regression checker for the fixed-income credit analysis engine."""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 仓库根，供 src.* 可导入
from src.rating_map import CANONICAL_RATING_INTERVALS  # noqa: E402  18 档单源（src/，随发行包分发）

ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = ROOT / "dev" / "engine"
TEMPLATES_DIR = ROOT / "dev" / "templates"
SKILL_FILE = ROOT / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "SKILL.md"
SKILL_TEMPLATES_DIR = ROOT / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "templates"
ROUTER_SKILL_FILE = ROOT / "dev" / ".claude" / "skills" / "credit-analysis-router" / "SKILL.md"
SKILLS_DIR = ROOT / "dev" / ".claude" / "skills"
AGENTS_MD = ROOT / "AGENTS.md"

# Make `src` importable when this script is run directly (python scripts/consistency_check.py),
# where sys.path[0] is the scripts/ dir rather than the repo root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.path_sheet import load_registry_paths, validate_path_sheet  # noqa: E402

EXPECTED_VERSION = "v0.9.4-release"
VERSION_RELEASE_RE = re.compile(r"^v(\d+\.\d+\.\d+)-release$")

CORE_DOCS = [
    "engine-overview.md",
    "dual-track-methodology.md",
    "industry-framework.md",
    "validation-methodology.md",
    "qualitative-analysis.md",
    "quantitative-analysis.md",
    "mosaic-engine.md",
    "output-layered-framework.md",
    "contagion-theory.md",
    "contagion-matrix.md",
    "concentration-framework.md",
    "systemic-warning-framework.md",
    "financial-bond-framework.md",
    "holding-company-framework.md",
    "non-credit-risk-overlay.md",
    "external-support-framework.md",
    "esg-framework.md",
    "governance-fraud-risk.md",
    "outlook-monitoring-framework.md",
    "lgd-recovery-framework.md",
    "lgfv-framework.md",
    "multi-stakeholder.md",
    "financial-deep-dive.md",
    "paradigm-brand-channel.md",
    "paradigm-network-traffic.md",
    "work-path-registry.md",
    "dimension-registry.md",
    "m2-underwriting-framework.md",
    "m5-financing-advisor-framework.md",
    "pipeline-contract.md",
]

SRI_PCT_PATTERN = re.compile(r"SRI\s*[:：]\s*\d{2}\s*/\s*100", re.IGNORECASE)
OLD_NOTCH_PATTERNS = [re.compile(p) for p in (
    r"(?<![A-Z+-])AA/A(?![A-Z+-])",  # old 6-notch combined notation, not "AA+/AA/AA-"
    r"(?<![A-Z+-])BBB/BB(?![A-Z+-])",  # old 6-notch combined notation, not "BBB+/BBB/BBB-"
    r"4\.0-5\.9",
    r"2\.0-3\.9",
)]

RATING_INTERVAL_RE = re.compile(
    r"\|\s*(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*\|\s*([A-D]{1,3}[+-]?)\s*\|"
)
HISTORICAL_NAME_PATTERNS = [re.compile(p) for p in (
    r".*-audit.*\.md$",
    r".*-review-.*\.md$",
    r"^self-assessment-",
)]

YELLOW_05_PATTERNS = [
    re.compile(r"yellow\s*=\s*0\.5", re.IGNORECASE),
    re.compile(r"关注.*0\.5\s*分?"),
    re.compile(r"🟡.*0\.5\s*分?"),
]
YELLOW_0_PATTERNS = [
    re.compile(r"yellow\s*=\s*0\b(?!\.\d)", re.IGNORECASE),
    re.compile(r"关注.*\b0\s*分"),
    re.compile(r"🟡.*\b0\s*分"),
]

ORANGE_05_PATTERNS = [
    re.compile(r"orange\s*=\s*0\.5", re.IGNORECASE),
    re.compile(r"橙色.*0\.5\s*分?"),
    re.compile(r"🟠.*0\.5\s*分?"),
]
ORANGE_10_PATTERNS = [
    re.compile(r"orange\s*=\s*1\.0", re.IGNORECASE),
    re.compile(r"橙色.*1\.0\s*分?"),
    re.compile(r"🟠.*1\.0\s*分?"),
]

RED_10_PATTERNS = [
    re.compile(r"red\s*=\s*1\.0", re.IGNORECASE),
    re.compile(r"红色.*1\.0\s*分?"),
    re.compile(r"🔴.*1\.0\s*分?"),
]
RED_15_PATTERNS = [
    re.compile(r"red\s*=\s*1\.5", re.IGNORECASE),
    re.compile(r"红色.*1\.5\s*分?"),
    re.compile(r"🔴.*1\.5\s*分?"),
]

REFERENCE_TO_ENGINE_MAP = {
    "industry-pyramids.md": "industry-framework.md",
    "mosaic-engine-architecture.md": "mosaic-engine.md",
    "validation-cases.md": "validation-methodology.md",
    "industry-scoring.md": "industry-framework.md",
    "system-intelligence.md": "systemic-warning-framework.md",
    "stakeholder-paths.md": "multi-stakeholder.md",
    "work-paths.md": "work-path-registry.md",
    "report-mapping.md": "output-layered-framework.md",
    "qa-checklist.md": "output-layered-framework.md",
}
VERSION_HEADER_RE = re.compile(r"\*\*(?:版本|对应引擎版本)\*\*\s*[:：]?\s*([^\s|]+)")
YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
PATH_SHEET_SECTION_RE = re.compile(r"## Path Sheet Output[^\n]*\n(.*?)(?=\n## |\Z)", re.DOTALL)


def _extract_version_header(text: str) -> str | None:
    m = VERSION_HEADER_RE.search(text)
    return m.group(1) if m else None


def check_versions() -> list[str]:
    errors = []
    for doc in CORE_DOCS:
        path = ENGINE_DIR / doc
        if not path.exists():
            errors.append(f"MISSING: {path.relative_to(ENGINE_DIR)}")
            continue
        text = path.read_text(encoding="utf-8")
        if (f"**版本**: {EXPECTED_VERSION}" not in text
                and f"**版本** {EXPECTED_VERSION}" not in text
                and f"**对应引擎版本**: {EXPECTED_VERSION}" not in text
                and f"**对应引擎版本** {EXPECTED_VERSION}" not in text):
            errors.append(f"VERSION: {doc} does not declare {EXPECTED_VERSION}")

    if not SKILL_FILE.exists():
        errors.append(f"MISSING: {SKILL_FILE}")
    else:
        skill_text = SKILL_FILE.read_text(encoding="utf-8")
        if EXPECTED_VERSION not in skill_text:
            errors.append(f"VERSION: SKILL.md does not contain {EXPECTED_VERSION}")
    return errors


def check_version_alignment() -> list[str]:
    """pyproject.toml / package.json 的 version 必须与 EXPECTED_VERSION 派生值一致。"""
    m = VERSION_RELEASE_RE.match(EXPECTED_VERSION)
    if not m:
        return [
            f"VERSION_ALIGN: EXPECTED_VERSION {EXPECTED_VERSION!r} 不是 vX.Y.Z-release 形式"
        ]
    want = m.group(1)
    errors = []
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    pm = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if pm is None or pm.group(1) != want:
        got = pm.group(1) if pm else None
        errors.append(
            f"VERSION_ALIGN: pyproject.toml version={got!r}，应为 {want!r}"
            f"（派生自 EXPECTED_VERSION={EXPECTED_VERSION}）"
        )
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    if pkg.get("version") != want:
        errors.append(
            f"VERSION_ALIGN: package.json version={pkg.get('version')!r}，应为 {want!r}"
            f"（派生自 EXPECTED_VERSION={EXPECTED_VERSION}）"
        )
    return errors


def check_links() -> list[str]:
    errors = []
    for path in ENGINE_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[.*?\]\(([^)]+\.md)(?:#[^)]*)?\)", text):
            link = match.group(1)
            # Resolve relative to the referencing file's own directory first
            # (standard markdown semantics, so same-dir links inside audits/
            # resolve), then fall back to the engine root for the bare sibling
            # links authored when every doc lived flat under dev/engine/.
            target = path.parent / link
            if not target.exists():
                target = ENGINE_DIR / link
            if not target.exists():
                errors.append(f"BROKEN_LINK: {path.relative_to(ENGINE_DIR)} -> {link}")
    return errors


def check_sri_scale() -> list[str]:
    errors = []
    for path in list(ENGINE_DIR.rglob("*.md")) + list(TEMPLATES_DIR.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if SRI_PCT_PATTERN.search(text):
            rel = path.relative_to(ENGINE_DIR) if path.is_relative_to(ENGINE_DIR) else path.relative_to(TEMPLATES_DIR)
            errors.append(f"SRI_PCT: {rel} contains percentage-scale SRI")
    return errors


def check_rating_map() -> list[str]:
    errors = []
    for path in ENGINE_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for pattern in OLD_NOTCH_PATTERNS:
            if pattern.search(text):
                errors.append(f"OLD_NOTCH: {path.relative_to(ENGINE_DIR)} contains '{pattern.pattern}'")
    return errors


def check_audit_versions() -> list[str]:
    errors = []
    pattern = re.compile(r"\*\*对应引擎版本\*\*\s*:\s*" + re.escape(EXPECTED_VERSION) + r"\b")
    for path in ENGINE_DIR.rglob("*.md"):
        # audits/ holds frozen historical reports. Their 对应引擎版本 records the
        # engine era under review (e.g. v0.7.0-alpha/v0.5.4-alpha) on an independent
        # report-version scheme (v1.0/v1.1), so it must not track EXPECTED_VERSION.
        # The audit-version requirement applies only to current (non-archived) docs.
        if "audits" in path.relative_to(ENGINE_DIR).parts:
            continue
        name = path.name
        if not (name.endswith("-audit.md") or re.match(r".*-review-.*\.md$", name) or name.startswith("self-assessment-")):
            continue
        text = path.read_text(encoding="utf-8")
        if not pattern.search(text):
            errors.append(f"AUDIT_VERSION: {path.relative_to(ENGINE_DIR)} does not declare 对应引擎版本: {EXPECTED_VERSION}")
    return errors


def check_rating_map_consistency() -> list[str]:
    """Flag any score-range -> rating table that deviates from the canonical 12-notch map."""
    errors = []
    canonical_set = {(low, high, label) for low, high, label in CANONICAL_RATING_INTERVALS}
    for path in ENGINE_DIR.rglob("*.md"):
        if path.name == "dual-track-methodology.md":
            continue
        if any(p.match(path.name) for p in HISTORICAL_NAME_PATTERNS):
            continue
        text = path.read_text(encoding="utf-8")
        for match in RATING_INTERVAL_RE.finditer(text):
            low = float(match.group(1))
            high = float(match.group(2))
            label = match.group(3)
            if (low, high, label) not in canonical_set:
                errors.append(
                    f"RATING_MAP: {path.relative_to(ENGINE_DIR)} has non-canonical "
                    f"interval/label ({low:g}-{high:g} -> {label})"
                )
    return errors


TEMPLATE_MARKER_RE = re.compile(r"^L0-spec:\s*(\S+)\s+§\S+$")
QG_REF_RE = re.compile(r"\((dev/[^)]+\.md)\s+§([^\s)]+)\)")
MIGRATION_RATINGS = [
    "AAA", "AA+", "AA", "AA-", "A+", "A / A-",
    "BBB+", "BBB / BBB-", "BB", "B", "CCC", "D",
]


def check_registry_templates() -> list[str]:
    """registry 每条路径的 templates 字段：文件存在或合法标记（planned / L0-spec: <doc> §节）。"""
    registry_file = ENGINE_DIR / "work-path-registry.md"
    if not registry_file.exists():
        return []
    errors = []
    for pid, entry in load_registry_paths(registry_file).items():
        for tpl in entry.get("templates") or []:
            if tpl == "planned":
                continue
            m = TEMPLATE_MARKER_RE.match(tpl)
            if m:
                if not (ROOT / m.group(1)).is_file():
                    errors.append(f"REGISTRY_TEMPLATE: {pid} L0-spec 文档缺失 {m.group(1)}")
                continue
            if not (ROOT / tpl).is_file():
                errors.append(f"REGISTRY_TEMPLATE: {pid} 模板文件缺失 {tpl}")
    return errors


def check_registry_quality_gates() -> list[str]:
    """quality_gates 的 '规则名 (文档路径 §节)' 引用：文档存在 + §节可定位。"""
    registry_file = ENGINE_DIR / "work-path-registry.md"
    if not registry_file.exists():
        return []
    errors = []
    for pid, entry in load_registry_paths(registry_file).items():
        for gate in entry.get("quality_gates") or []:
            for doc_rel, sec in QG_REF_RE.findall(gate):
                doc = ROOT / doc_rel
                if not doc.is_file():
                    errors.append(f"REGISTRY_GATE: {pid} 质量门文档缺失 {doc_rel}")
                    continue
                text = doc.read_text(encoding="utf-8")
                if not re.search(r"^#+\s*" + re.escape(sec) + r"[、.\s]", text, re.MULTILINE):
                    errors.append(f"REGISTRY_GATE: {pid} 质量门节号不可定位 {doc_rel} §{sec}")
    return errors


def check_migration_matrix_structure() -> list[str]:
    """outlook-monitoring §5.1 迁移矩阵：12 个评级行齐全且每行 4 概率列非空。"""
    path = ENGINE_DIR / "outlook-monitoring-framework.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    sec = re.search(r"### 5\.1 .*?(?=\n### |\Z)", text, re.DOTALL)
    if not sec:
        return ["MIGRATION_MATRIX: §5.1 段落缺失"]
    body = sec.group(0)
    errors = []
    for rating in MIGRATION_RATINGS:
        row = re.search(
            r"^\|\s*\*\*" + re.escape(rating) + r"\*\*\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|",
            body, re.MULTILINE,
        )
        if not row:
            errors.append(f"MIGRATION_MATRIX: 缺评级行 {rating}")
        elif any(not cell.strip() or cell.strip() == "-" for cell in row.groups()):
            errors.append(f"MIGRATION_MATRIX: {rating} 行存在空概率列")
    return errors


def check_sri_track_b_consistency() -> list[str]:
    """Flag contradictory textual descriptions of Track-B penalties across yellow/orange/red."""
    path = ENGINE_DIR / "systemic-warning-framework.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    contradictions = []
    if any(p.search(text) for p in YELLOW_05_PATTERNS) and any(p.search(text) for p in YELLOW_0_PATTERNS):
        contradictions.append("yellow penalty as both 0.5 and 0")
    if any(p.search(text) for p in ORANGE_05_PATTERNS) and any(p.search(text) for p in ORANGE_10_PATTERNS):
        contradictions.append("orange penalty as both 0.5 and 1.0")
    if any(p.search(text) for p in RED_10_PATTERNS) and any(p.search(text) for p in RED_15_PATTERNS):
        contradictions.append("red penalty as both 1.0 and 1.5")
    if contradictions:
        return [
            f"SRI_TRACK_B: {path.relative_to(ENGINE_DIR)} describes " + " and ".join(contradictions)
        ]
    return []


def _skill_reference_files() -> list[Path]:
    """Every ``references/*.md`` across all on-disk skills (discovery by convention).

    Generalized in v0.7.7 from a single hardcoded skill dir to every skill under
    ``dev/.claude/skills/``, so new stage skills (credit-report-builder,
    credit-qa-verifier) get the same version-header-vs-engine check with no
    per-skill checker edits.
    """
    if not SKILLS_DIR.exists():
        return []
    return sorted(SKILLS_DIR.glob("*/references/*.md"))


def check_skill_references() -> list[str]:
    """Compare every skill's reference files with their engine counterparts by version header."""
    errors = []
    for ref_path in _skill_reference_files():
        engine_name = REFERENCE_TO_ENGINE_MAP.get(ref_path.name, ref_path.name)
        engine_path = ENGINE_DIR / engine_name
        if not engine_path.exists():
            errors.append(f"SKILL_REF_MISSING: {ref_path.name} has no engine counterpart ({engine_name})")
            continue
        ref_text = ref_path.read_text(encoding="utf-8")
        engine_text = engine_path.read_text(encoding="utf-8")
        ref_ver = _extract_version_header(ref_text)
        engine_ver = _extract_version_header(engine_text)
        if ref_ver is None and engine_ver is None:
            continue
        if ref_ver is None:
            errors.append(
                f"SKILL_REF_VERSION: {ref_path.name} missing version header "
                f"(engine {engine_name} is {engine_ver})"
            )
        elif engine_ver is None:
            errors.append(
                f"SKILL_REF_VERSION: {ref_path.name} version {ref_ver} "
                f"but engine {engine_name} missing version header"
            )
        elif ref_ver != engine_ver:
            errors.append(
                f"SKILL_REF_STALE: {ref_path.name} version {ref_ver} "
                f"!= engine {engine_name} version {engine_ver}"
            )
    return errors


def check_skill_template_drift() -> list[str]:
    """Templates are single-sourced under dev/templates/; the skill must not keep copies."""
    if SKILL_TEMPLATES_DIR.exists():
        return [
            "SKILL_TEMPLATE_DRIFT: skill must not keep its own templates/ copies; "
            "dev/templates/ is the single source"
        ]
    return []


def check_path_sheets() -> list[str]:
    """Validate the router's concrete work-path sheet(s) against the registry (v0.7.5).

    The router emits a 《工作路径单》 whose path_id must resolve to a registered work
    path and whose active-path templates must exist on disk. We parse the registry and
    validate every concrete example sheet in the router's Path Sheet Output section
    (the blank template, whose path_id is empty, is skipped). A real violation — an
    illegal enum, an unknown path_id, or a dangling active-path template — surfaces
    here as a PATH_SHEET error.
    """
    registry_path = ENGINE_DIR / "work-path-registry.md"
    if not ROUTER_SKILL_FILE.exists() or not registry_path.exists():
        return []
    registry_paths = load_registry_paths(registry_path)
    text = ROUTER_SKILL_FILE.read_text(encoding="utf-8")
    match = PATH_SHEET_SECTION_RE.search(text)
    if not match:
        return []
    errors = []
    for block in YAML_BLOCK_RE.findall(match.group(1)):
        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            continue
        if not str(data.get("path_id") or "").strip():
            continue  # the blank path-sheet template, not a concrete sheet
        for err in validate_path_sheet(data, registry_paths):
            errors.append(f"PATH_SHEET: {err}")
    return errors


def _skill_markdown_files() -> list[Path]:
    """Each on-disk skill's SKILL.md plus its references/*.md (for the join-key scan)."""
    if not SKILLS_DIR.exists():
        return []
    files: list[Path] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            files.append(skill_md)
        refs = skill_dir / "references"
        if refs.exists():
            files.extend(sorted(refs.glob("*.md")))
    return files


def check_artifact_path_ids() -> list[str]:
    """Join-key referential integrity for the four-stage chain artifacts (v0.7.7).

    Every yaml block in any skill's SKILL.md or references/*.md that carries a
    non-empty ``path_id`` must resolve to a registered work path. This covers the
    concrete Delivery Note / QA Verdict examples emitted by the report and qa
    skills (and the router's own concrete path-sheet examples). Blank schema
    templates (empty ``path_id``) are skipped.

    We assert ONLY that the ``path_id`` resolves -- we do NOT run full path-sheet
    field validation here, because chain artifacts (Delivery Note, QA Verdict)
    legitimately omit the role/object/depth fields a real path sheet requires;
    running validate_path_sheet on them would false-positive. Full path-sheet
    validation stays in check_path_sheets (router Path Sheet Output section only).
    """
    registry_path = ENGINE_DIR / "work-path-registry.md"
    if not SKILLS_DIR.exists() or not registry_path.exists():
        return []
    registry_paths = load_registry_paths(registry_path)
    errors = []
    for md in _skill_markdown_files():
        text = md.read_text(encoding="utf-8")
        for block in YAML_BLOCK_RE.findall(text):
            data = yaml.safe_load(block)
            if not isinstance(data, dict):
                continue
            pid = str(data.get("path_id") or "").strip()
            if not pid:
                continue  # blank schema template, not a concrete artifact
            if pid not in registry_paths:
                errors.append(
                    f"ARTIFACT_PATH_ID: {md.relative_to(SKILLS_DIR)} references "
                    f"unknown path_id {pid!r}"
                )
    return errors


def check_agents_entry() -> list[str]:
    """Orphan-skill guard for the cross-CLI universal entry (v0.7.6).

    The repo-root AGENTS.md is the universal entry any agent CLI reads to discover
    the skills. It must exist, and every skill present on disk under
    dev/.claude/skills/ must be referenced in it -- otherwise that skill would be
    undiscoverable to the CLIs that do not auto-discover dev/.claude/skills (an
    orphan). This keeps AGENTS.md in sync with the on-disk skill set.
    """
    if not AGENTS_MD.exists():
        return ["AGENTS_ENTRY: root AGENTS.md is missing"]
    if not SKILLS_DIR.exists():
        return []
    text = AGENTS_MD.read_text(encoding="utf-8")
    errors = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        # Anchor to the discovery-index path reference, not a bare substring --
        # otherwise a passing mention of the skill name elsewhere (e.g. the
        # 4-stage pipeline table) would mask its absence from the Skill Index.
        if f"skills/{skill_dir.name}/SKILL.md" not in text:
            errors.append(
                f"AGENTS_ENTRY: on-disk skill '{skill_dir.name}' is not referenced in AGENTS.md"
            )
    return errors


def _parse_contagion_industries(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    start = text.find("### 1.2 范式映射表")
    if start == -1:
        return []
    end = text.find("### 1.3", start)
    section = text[start:end] if end != -1 else text[start:]
    industries = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) < 4:
            continue
        first = cells[0]
        if first.isdigit():
            industries.append(cells[1])
    return industries


def _industry_covered(industry: str, text: str) -> bool:
    if industry in text:
        return True
    # Allow heading matches using the first slash-separated segment, e.g. "高端装备/工业母机" -> "高端装备"
    parts = re.split(r"[/(（]", industry)
    for part in parts:
        part = part.strip().strip(")）")
        if not part:
            continue
        if re.search(rf"^#+\s+.*{re.escape(part)}", text, re.MULTILINE):
            return True
    return False


def check_paradigm_coverage() -> list[str]:
    """Ensure every industry in contagion-matrix §1.2 appears in industry-framework.md."""
    contagion_path = ENGINE_DIR / "contagion-matrix.md"
    industry_path = ENGINE_DIR / "industry-framework.md"
    if not contagion_path.exists() or not industry_path.exists():
        return []
    industries = _parse_contagion_industries(contagion_path)
    text = industry_path.read_text(encoding="utf-8")
    errors = []
    for industry in industries:
        if not _industry_covered(industry, text):
            errors.append(
                f"PARADIGM_COVERAGE: {industry} listed in contagion-matrix.md "
                f"is missing from industry-framework.md"
            )
    return errors


def collect_errors(only_links: bool = False) -> list[str]:
    errors = check_links()
    if only_links:
        return errors
    errors.extend(check_versions())
    errors.extend(check_sri_scale())
    errors.extend(check_rating_map())
    errors.extend(check_audit_versions())
    errors.extend(check_skill_template_drift())
    errors.extend(check_path_sheets())
    errors.extend(check_artifact_path_ids())
    errors.extend(check_agents_entry())
    errors.extend(check_version_alignment())
    errors.extend(check_registry_templates())
    errors.extend(check_registry_quality_gates())
    errors.extend(check_migration_matrix_structure())
    return errors


def collect_warnings() -> list[str]:
    """Structural coherence checks that are reported as warnings until fixes land."""
    warnings = []
    warnings.extend(check_rating_map_consistency())
    warnings.extend(check_sri_track_b_consistency())
    warnings.extend(check_skill_references())
    warnings.extend(check_paradigm_coverage())
    return warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-links", action="store_true")
    parser.add_argument("--only-toc")
    args = parser.parse_args()

    if args.only_toc:
        # Lightweight TOC/body order check for a single file
        path = Path(args.only_toc)
        text = path.read_text(encoding="utf-8")
        toc_entries = re.findall(r"^\s*\d+\.\s+\[(.+?)\]\(#", text, re.MULTILINE)
        body_entries = [
            re.sub(r"^[一二三四五六七八九十百千万]+[、.\\s]+", "", h)
            for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
            if h != "目录"
        ]
        if toc_entries != body_entries[: len(toc_entries)]:
            print("TOC mismatch")
            sys.exit(1)
        print("TOC OK")
        return

    errors = collect_errors(only_links=args.only_links)
    if not args.only_links:
        warnings = collect_warnings()
        if warnings:
            print(f"Consistency warnings ({len(warnings)} issue(s)):")
            for w in warnings:
                print(f"  - {w}")
    if errors:
        print(f"Consistency check FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Consistency check PASSED")


if __name__ == "__main__":
    main()

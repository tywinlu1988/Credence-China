import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "consistency_check.py"
ENGINE_DIR = ROOT / "dev" / "engine"


def _import_checker():
    import importlib.util

    spec = importlib.util.spec_from_file_location("consistency_check", CHECKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["consistency_check"] = module
    spec.loader.exec_module(module)
    return module


def run_checker(*args):
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        capture_output=True,
        text=True,
    )


def test_checker_runs():
    result = run_checker()
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    assert result.returncode == 0, "Consistency checker reported issues"
    assert "PASSED" in result.stdout


def test_only_links_skips_content_checks(tmp_path, monkeypatch):
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "systemic-warning-framework.md").write_text(
        "**版本**: v0.7.0-alpha\n\nSRI: 38/100\n", encoding="utf-8"
    )

    cc = _import_checker()
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(cc, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(cc, "SKILL_FILE", tmp_path / "SKILL.md")

    full = cc.collect_errors(only_links=False)
    assert any("SRI_PCT" in e for e in full)

    links_only = cc.collect_errors(only_links=True)
    assert not any("SRI_PCT" in e for e in links_only)
    assert not links_only


def test_sri_pct_pattern_detects_percentage_scale():
    cc = _import_checker()
    assert cc.SRI_PCT_PATTERN.search("SRI: 38/100")
    assert cc.SRI_PCT_PATTERN.search("SRI 38/100") is None


def test_old_notch_patterns_detect_artifacts():
    cc = _import_checker()
    sample = "旧 6 档体系（AAA/AA/A/BBB/BB/B/CCC/D）"
    assert any(p.search(sample) for p in cc.OLD_NOTCH_PATTERNS)


def test_check_rating_map_consistency_flags_deviation(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "dual-track-methodology.md").write_text(
        "## 六、评级映射\n| 评分范围 | 新评级 |\n|---|---|\n| 9.5 - 10.0 | AAA |\n",
        encoding="utf-8",
    )
    (fake_engine / "systemic-warning-framework.md").write_text(
        "## 二、信号聚合\n| 评分区间 | 对应评级 |\n|---|---|\n| 9.0 - 10.0 | AAA |\n",
        encoding="utf-8",
    )
    (fake_engine / "consistency-audit-v0.5.2.md").write_text(
        "| 9.0 - 10.0 | AAA |\n", encoding="utf-8"
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    errors = cc.check_rating_map_consistency()
    assert any("systemic-warning-framework.md" in e and "9-10" in e for e in errors)
    assert not any("dual-track-methodology.md" in e for e in errors)
    assert not any("consistency-audit" in e for e in errors)


def test_check_sri_track_b_consistency_flags_contradiction(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "systemic-warning-framework.md").write_text(
        "trackB_penalty:\n  yellow = 0.5 for watch\n  yellow = 0 for calm\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    errors = cc.check_sri_track_b_consistency()
    assert errors
    assert all("yellow penalty" in e for e in errors)


def test_check_sri_track_b_consistency_allows_single_rule(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "systemic-warning-framework.md").write_text(
        "trackB_penalty:\n  yellow = 0 for calm\n", encoding="utf-8"
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    assert cc.check_sri_track_b_consistency() == []


def test_check_sri_track_b_consistency_flags_orange_contradiction(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "systemic-warning-framework.md").write_text(
        "trackB_penalty:\n  orange = 0.5 for elevated\n  orange = 1.0 for warning\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    errors = cc.check_sri_track_b_consistency()
    assert errors
    assert any("orange penalty" in e for e in errors)


def test_check_sri_track_b_consistency_flags_red_contradiction(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "systemic-warning-framework.md").write_text(
        "trackB_penalty:\n  red = 1.0 for severe\n  red = 1.5 for critical\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    errors = cc.check_sri_track_b_consistency()
    assert errors
    assert any("red penalty" in e for e in errors)


def test_check_skill_references_flags_stale_version(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "industry-framework.md").write_text(
        "**版本**: v0.7.0-alpha\n", encoding="utf-8"
    )
    fake_refs = tmp_path / "references"
    fake_refs.mkdir()
    (fake_refs / "industry-pyramids.md").write_text(
        "**版本**: v0.6.9-alpha\n", encoding="utf-8"
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(cc, "SKILL_REFERENCES_DIR", fake_refs)
    errors = cc.check_skill_references()
    assert any("industry-pyramids.md" in e and "v0.6.9-alpha" in e for e in errors)


def test_check_skill_references_flags_missing_version(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "mosaic-engine.md").write_text(
        "**版本**: v0.7.0-alpha\n", encoding="utf-8"
    )
    fake_refs = tmp_path / "references"
    fake_refs.mkdir()
    (fake_refs / "mosaic-engine-architecture.md").write_text(
        "# Mosaic engine\n", encoding="utf-8"
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(cc, "SKILL_REFERENCES_DIR", fake_refs)
    errors = cc.check_skill_references()
    assert any("mosaic-engine-architecture.md" in e and "missing version header" in e for e in errors)


def test_check_paradigm_coverage_flags_missing_industry(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "contagion-matrix.md").write_text(
        "### 1.2 范式映射表\n"
        "| 序号 | 行业 | 范式归属 | 范式核心特征 | 金融属性 |\n"
        "|---|---|---|---|---|\n"
        "| 1 | 光伏/储能 | 范式A | ... | 中等 |\n"
        "| 2 | 城投债(LGV) | 特殊 | ... | 极高 |\n"
        "### 1.3 范式内聚类\n",
        encoding="utf-8",
    )
    (fake_engine / "industry-framework.md").write_text(
        "## 四、七行业金字塔规格\n### 4.1 光伏/储能\n| D1 | ... |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    errors = cc.check_paradigm_coverage()
    assert any("城投债(LGV)" in e for e in errors)
    assert not any("光伏/储能" in e for e in errors)


def test_check_paradigm_coverage_accepts_judgmental_note(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "contagion-matrix.md").write_text(
        "### 1.2 范式映射表\n"
        "| 序号 | 行业 | 范式归属 | 典型主体 | 金融属性 | 传染烈度 |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | 食品饮料 | 品牌+渠道型 | B+/B/CCC | 低 | 高 |\n"
        "### 1.3\n",
        encoding="utf-8",
    )
    (fake_engine / "industry-framework.md").write_text(
        "## 范式边界说明\n食品饮料： judgmental assignment （品牌+渠道型范式）\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    assert cc.check_paradigm_coverage() == []


def test_check_rating_map_consistency_accepts_legitimate_12_notch(tmp_path, monkeypatch):
    cc = _import_checker()
    fake_engine = tmp_path / "engine"
    fake_engine.mkdir()
    (fake_engine / "some-framework.md").write_text(
        "## 评级档次\n"
        "投资级包括 AA+/AA/AA- 和 BBB+/BBB/BBB- 等共12档。\n"
        "| 评分范围 | 新评级 |\n"
        "|---|---|\n"
        "| 9.5 - 10.0 | AAA |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cc, "ENGINE_DIR", fake_engine)
    assert cc.check_rating_map_consistency() == []

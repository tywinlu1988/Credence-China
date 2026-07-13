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

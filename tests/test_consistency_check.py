import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "consistency_check.py"


def test_checker_runs():
    result = subprocess.run([sys.executable, str(CHECKER)], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    assert result.returncode == 0, "Consistency checker reported issues"
    assert "PASSED" in result.stdout


def test_only_links_runs_and_does_not_flag_sri_pct():
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--only-links"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "Link-only check failed"
    assert "PASSED" in result.stdout


def test_sri_pct_pattern_detects_percentage_scale():
    import re

    sri_pct_pattern = re.compile(r"SRI\s*[:：]\s*\d{2}\s*/\s*100", re.IGNORECASE)
    assert sri_pct_pattern.search("SRI: 38/100")
    assert sri_pct_pattern.search("SRI 38/100") is None


def test_old_notch_patterns_detect_artifacts():
    import re

    old_notch_patterns = [r"AA/A", r"BBB/BB", r"4\.0-5\.9", r"2\.0-3\.9"]
    sample = "旧 6 档体系（AAA/AA/A/BBB/BB/B/CCC/D）"
    assert any(re.search(p, sample) for p in old_notch_patterns)

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "consistency_check.py"


def test_checker_runs():
    result = subprocess.run([sys.executable, str(CHECKER)], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    assert result.returncode == 0, "Consistency checker reported issues"
    assert "PASSED" in result.stdout

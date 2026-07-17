"""P0 换行符门禁：被跟踪文本文件在工作区必须为 LF。

`.gitattributes`（`* text=auto eol=lf`）是强制机制，本测试是绊线——任何因非标准
机器配置混入检出/提交的 CRLF 都会在此失败，而不是悄悄进入发布 zip。
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def test_gitattributes_enforces_lf():
    content = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "text=auto" in content and "eol=lf" in content


def test_tracked_files_have_no_crlf():
    offenders = []
    for rel in _tracked_files():
        data = (ROOT / rel).read_bytes()
        if b"\0" in data:  # 二进制启发式（与 git 相同）：跳过；二进制经 .gitattributes 标 binary
            continue
        if b"\r\n" in data:
            offenders.append(rel)
    assert offenders == [], f"CRLF in tracked files: {offenders[:10]}"

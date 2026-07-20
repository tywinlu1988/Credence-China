"""模板契约门禁（v0.9.0）：戳记/base.css/footer 合规 + 无未标注实例名（防幻觉铁律）。

允许保留的仅"方法论案例库"语境：实例名出现的行或其最近标题行含 案例/回测/历史/示例/违约 标记。
"""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "dev" / "templates"
TEMPLATE_FILES = sorted(TEMPLATES_DIR.glob("template-type*.html"))

INSTANCE_NAMES = ["隆基", "一道", "永煤", "华晨", "紫光", "苏宁", "杭州城投"]
CASE_CONTEXT_RE = re.compile(r"案例|回测|历史|示例|违约")
HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.DOTALL)


def test_templates_present():
    """模板数量下限（Type 1-15 + 18 + 新增 16/17，随路径扩展只增不减）。"""
    assert len(TEMPLATE_FILES) >= 16


def test_stamps_and_base_css():
    for f in TEMPLATE_FILES:
        text = f.read_text(encoding="utf-8")
        assert "<!-- @template:" in text, f"{f.name} 缺 @template 戳记"
        assert "<!-- @engine-version:" in text, f"{f.name} 缺 @engine-version 戳记"
        assert "template-base.css" in text, f"{f.name} 未引用 template-base.css"


def test_footer_contract():
    for f in TEMPLATE_FILES:
        text = f.read_text(encoding="utf-8")
        assert "报告编号" in text and "生成于" in text, f"{f.name} footer 缺编号/日期行"
        assert "不构成投资建议" in text, f"{f.name} footer 缺免责声明行"


def _violations(f: Path) -> list[str]:
    lines = f.read_text(encoding="utf-8").splitlines()
    bad = []
    last_heading = ""
    for i, ln in enumerate(lines, 1):
        m = HEADING_RE.search(ln)
        if m:
            last_heading = m.group(1)
        for name in INSTANCE_NAMES:
            if name in ln and not (CASE_CONTEXT_RE.search(ln) or CASE_CONTEXT_RE.search(last_heading)):
                bad.append(f"{f.name}:{i} 未标注实例名 {name}")
    return bad


def test_no_unmarked_instance_data():
    violations = []
    for f in TEMPLATE_FILES:
        violations.extend(_violations(f))
    assert violations == [], "\n".join(violations[:20])

"""模板契约门禁（v0.9.0）：戳记/base.css/footer 合规 + 无未标注实例名（防幻觉铁律）。

允许保留的仅"方法论案例库"语境：实例名出现的行或其最近标题行含 案例/回测/历史/示例/违约 标记。
"""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "dev" / "templates"
TEMPLATE_FILES = sorted(TEMPLATES_DIR.glob("template-type*.html"))

INSTANCE_NAMES = [
    # 短名
    "隆基", "一道", "永煤", "华晨", "紫光", "苏宁", "杭州城投",
    # 全名与已知案例关联实体
    "一道新能", "杭州市城市建设投资集团",
    "通威", "晶科", "天合", "晶澳", "晶能",
    # 品牌与代码
    "Hi-MO", "601012",
]
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


# 数值残留检测（防"改名留数"）：含数值数据且非占位符、非方法论语境的行即违规。
# 豁免必须带行号与理由（方法论语义行，如 SRI 刻度、强度值、评级区间）。
NUMERIC_DATA_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|亿|万|notch|bp|倍)")
STOCK_CODE_RE = re.compile(r"(?<![\d.:#])\d{6}(?![\d.:%])")
METHODOLOGY_CONTEXT_RE = re.compile(
    r"案例|回测|历史|示例|违约|阈值|档位|温度计|评级映射|权重|强度|刻度"
)
STYLE_BLOCK_RE = re.compile(r"<style>.*?</style>", re.DOTALL)

# 豁免表：{文件名: {行号: 理由}}——逐条审计后登记，禁止泛化豁免。
EXEMPT: dict[str, dict[int, str]] = {
    "template-type8.html": {
        44: "LGD1 等级定义区间（方法论，与 lgd-recovery-framework §2.1 一致）",
        45: "LGD2 等级定义区间（同上）",
        46: "LGD3 等级定义区间（同上）",
        47: "LGD4 等级定义区间（同上）",
        48: "LGD5 等级定义区间（同上）",
    },
    "template-type14.html": {},
    "template-type15.html": {
        740: "温度计标尺 UI（结构性刻度组件）",
        741: "温度计标尺 UI（同上）",
    },
}

# 模式豁免：{文件名: [(正则, 理由)]}——结构性组件（非主体数据）的模式化豁免。
EXEMPT_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "template-type14.html": [
        (r"threshold-(label|marker)", "集中度标尺 UI（结构性刻度组件）"),
        (r"(敞口|行业)[+-]\d+%", "敏感性测试情景参数（结构性常量，非主体数据）"),
    ],
}


def _numeric_violations(f: Path) -> list[str]:
    text = f.read_text(encoding="utf-8")
    # CSS 不计，但以等量换行替换保持行号不变（EXEMPT 行号与违规报告均按真实文件行号）
    text = STYLE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    bad = []
    last_heading = ""
    patterns = EXEMPT_PATTERNS.get(f.name, [])
    for i, ln in enumerate(text.splitlines(), 1):
        if f.name in EXEMPT and i in EXEMPT[f.name]:
            continue
        if any(re.search(p, ln) for p, _ in patterns):
            continue
        m = HEADING_RE.search(ln)
        if m:
            last_heading = m.group(1)
        if METHODOLOGY_CONTEXT_RE.search(ln) or METHODOLOGY_CONTEXT_RE.search(last_heading):
            continue
        stripped = re.sub(r"\{[^}]*\}", "", ln)  # 剥除占位符后扫描残余（防"行内有占位符即放行"漏检）
        if NUMERIC_DATA_RE.search(stripped) or STOCK_CODE_RE.search(stripped):
            bad.append(f"{f.name}:{i} 数值残留 {stripped.strip()[:60]}")
    return bad


def test_no_numeric_residue():
    violations = []
    for f in TEMPLATE_FILES:
        violations.extend(_numeric_violations(f))
    assert violations == [], "\n".join(violations[:30])

"""WP-M4-02 contagion_engine 测试。

单一事实源纪律：漂移门的期望值全部从文档运行时解析（§2.3.1 系数表、§5.5/5.6
top3、§3.1 链路清单、§3.3 计数），测试不复制任何矩阵数值；计算层测试用手工
fixture 小矩阵。
"""

import re
from pathlib import Path

import pytest

from src.contagion_engine import (
    ContagionCell,
    ContagionMatrix,
    apply_escalation,
    contagion_coefficients,
    col_sums,
    high_intensity_links,
    load_matrix,
    portfolio_exposure,
    row_sums,
    sri_weights,
    super_spreaders,
    vulnerable_industries,
)
from src.path_sheet import engine_dir

MATRIX_MD = engine_dir() / "contagion-matrix.md"
SYSTEMIC_MD = engine_dir() / "systemic-warning-framework.md"

# systemic §2.3.1 表的别名形态 → §2.4 规范名（两处文档的行业名写法不一致）
_NAME_ALIASES = {"城投债(LGFV)": "城投债 / LGFV"}


def _canonical(name: str) -> str:
    return _NAME_ALIASES.get(name, name)


@pytest.fixture(scope="module")
def matrix():
    return load_matrix(MATRIX_MD)


def _doc_text(path=MATRIX_MD):
    return path.read_text(encoding="utf-8")


# ---------------- 解析层（真实文档） ----------------

def test_load_matrix_structure(matrix):
    assert len(matrix.industries) == 13
    cells = list(matrix.itercells())
    assert len(cells) == 13 * 12
    assert all(1 <= c.intensity <= 5 for c in cells)
    for ind in matrix.industries:
        assert matrix.intensity(ind, ind) == 0  # 对角线
    assert "城投债 / LGFV" in matrix.industries


def test_load_matrix_unknown_pair_raises(matrix):
    with pytest.raises(ValueError, match="未知行业对"):
        matrix.cell("不存在行业", "光伏/储能")


# ---------------- 漂移门（值全部来自文档本身） ----------------

def _systemic_coefficient_table():
    """解析 systemic §2.3.1：{行业: 行合计总分}。"""
    text = _doc_text(SYSTEMIC_MD)
    sec = re.search(r"#### 2\.3\.1.*?(?=####|\Z)", text, re.DOTALL).group(0)
    out = {}
    for m in re.finditer(r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|", sec, re.MULTILINE):
        out[_canonical(m.group(1).strip())] = int(m.group(2))
    return out


def test_row_sums_match_systemic_table(matrix):
    assert row_sums(matrix) == _systemic_coefficient_table()


def _section_top3(header_regex):
    text = _doc_text()
    sec = re.search(header_regex + r".*?(?=###|\Z)", text, re.DOTALL).group(0)
    return [
        m.group(1).strip()
        for m in re.finditer(r"^\|\s*\*\*\d+\*\*\s*\|\s*\*\*(.+?)\*\*\s*\|", sec, re.MULTILINE)
    ]


def test_super_spreaders_match_doc(matrix):
    doc_top3 = _section_top3(r"### 5\.5")
    assert [name for name, _ in super_spreaders(matrix)] == doc_top3


def test_vulnerable_industries_match_doc(matrix):
    doc_top3 = _section_top3(r"### 5\.6")
    assert [name for name, _ in vulnerable_industries(matrix)] == doc_top3


def _doc_high_intensity_pairs():
    """解析 §3.1 代码块中的链路清单 → {frozenset({a, b}): 是否双向}。"""
    text = _doc_text()
    sec = re.search(r"### 3\.1.*?```\n(.*?)```", text, re.DOTALL).group(1)
    pairs = {}
    for ln in sec.splitlines():
        m = re.match(r"\s*(.+?)\s*(↔|→)\s*(.+?)\s*\(", ln)
        if m:
            a, arrow, b = m.group(1).strip(), m.group(2), m.group(3).strip()
            pairs[frozenset((a, b))] = arrow == "↔"
    return pairs


def test_high_intensity_links_match_doc(matrix):
    links = high_intensity_links(matrix, threshold=4)
    computed = {}
    for c in links:
        key = frozenset((c.source, c.target))
        computed.setdefault(key, []).append(c)
    doc_pairs = _doc_high_intensity_pairs()
    assert set(computed) == set(doc_pairs)
    for key, cells in computed.items():
        assert (len(cells) == 2) == doc_pairs[key], f"方向性与文档不符: {sorted(key)}"


def test_low_intensity_count_matches_doc(matrix):
    n = sum(1 for c in matrix.itercells() if c.intensity <= 2)
    m = re.search(r"强度≤2的行业对共(\d+)对", _doc_text())
    assert n == int(m.group(1))


# ---------------- 派生计算（真实矩阵 + fixture） ----------------

def test_contagion_coefficients_normalized(matrix):
    coefs = contagion_coefficients(matrix)
    assert len(coefs) == 13
    mean = sum(coefs.values()) / len(coefs)
    assert abs(mean - 1.0) < 1e-9  # 系数均值恒为 1（行合计/均值）
    # 与 systemic §2.3.1 的系数列一致（容差：文档保留 3 位小数）
    text = _doc_text(SYSTEMIC_MD)
    for m in re.finditer(
        r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*\d+\s*\|\s*\d+\s*/\s*[\d.]+\s*=\s*([\d.]+)\s*\|",
        text, re.MULTILINE,
    ):
        assert abs(coefs[_canonical(m.group(1).strip())] - float(m.group(2))) < 5e-4


def test_sri_weights():
    coefs = {"A": 1.2, "B": 0.8}
    w = sri_weights({"A": 0.5, "B": 0.5}, coefs)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["A"] > w["B"]  # 系数大者权重上浮
    with pytest.raises(ValueError):
        sri_weights({"A": 0.5}, coefs)  # 键不一致


# ---------------- 组合分析（fixture 小矩阵） ----------------

def _mini():
    inds = ["甲", "乙", "丙"]
    cells = {}
    vals = {("甲", "乙"): 4, ("乙", "甲"): 2, ("甲", "丙"): 1,
            ("丙", "甲"): 5, ("乙", "丙"): 3, ("丙", "乙"): 2}
    for (s, t), n in vals.items():
        cells[(s, t)] = ContagionCell(s, t, n, types=("C",), confidence="M", bidirectional=n >= 4)
    return ContagionMatrix(inds, cells)


def test_portfolio_exposure_math():
    m = _mini()
    exp = portfolio_exposure(m, {"甲": 0.5, "乙": 0.3, "丙": 0.2})
    by_ind = {e["industry"]: e for e in exp}
    # 甲被传染暴露 = 乙→甲(2)×0.3 + 丙→甲(5)×0.2 = 1.6
    assert abs(by_ind["甲"]["inbound"] - 1.6) < 1e-9
    # 甲对外传染力 = 甲→乙(4)×0.3 + 甲→丙(1)×0.2 = 1.4
    assert abs(by_ind["甲"]["outbound"] - 1.4) < 1e-9
    assert exp[0]["inbound"] >= exp[-1]["inbound"]  # 降序
    with pytest.raises(ValueError):
        portfolio_exposure(m, {})


def test_high_intensity_links_threshold():
    m = _mini()
    links = high_intensity_links(m, threshold=4)
    assert {(c.source, c.target) for c in links} == {("甲", "乙"), ("丙", "甲")}
    assert links[0].intensity >= links[-1].intensity
    subset = high_intensity_links(m, industries=["甲", "乙"], threshold=1)
    assert {(c.source, c.target) for c in subset} == {("甲", "乙"), ("乙", "甲")}


# ---------------- 压力跳升（§6.2） ----------------

def test_apply_escalation_explicit_and_generic(matrix):
    stressed = apply_escalation(matrix, ["市场恐慌"])
    # 显式对（文档 §6.2 规则1）：半导体→光伏 4→5
    assert stressed.intensity("半导体/集成电路", "光伏/储能") == 5
    # 通用规则：含 S 标记 +1（新能源汽车→光伏，C+S 标记、非显式对：3→4）
    assert stressed.intensity("新能源汽车", "光伏/储能") == 4
    # 不含 S/L 且非显式的对不变（高端装备→光伏，C 标记，保持 3）
    assert stressed.intensity("高端装备/工业母机", "光伏/储能") == 3
    # 原矩阵不可变
    assert matrix.intensity("半导体/集成电路", "光伏/储能") == 4


def test_apply_escalation_year_end_lgfv_and_cap(matrix):
    stressed = apply_escalation(matrix, ["年末效应"])
    assert stressed.intensity("城投债 / LGFV", "交通运输") == 5  # 4+1 封顶 5
    assert stressed.intensity("城投债 / LGFV", "食品饮料") == 2  # 1+1
    assert stressed.intensity("光伏/储能", "食品饮料") == 1      # 非城投对 +0
    with pytest.raises(ValueError, match="未知升级因子"):
        apply_escalation(matrix, ["不存在因子"])


def test_apply_escalation_stacks(matrix):
    stressed = apply_escalation(matrix, ["市场恐慌", "监管真空"])
    assert stressed.intensity("城投债 / LGFV", "交通运输") == 5


def test_escalation_rules_covered_in_doc():
    """编码的每条显式跳升对必须能在 §6.2 文本检索到（防静默漂移）。"""
    from src.contagion_engine import _EXPLICIT_JUMPS

    text = _doc_text()
    sec = re.search(r"### 6\.2.*?(?=### 6\.3|\Z)", text, re.DOTALL).group(0)
    for factor, jumps in _EXPLICIT_JUMPS.items():
        assert factor in sec, f"§6.2 缺少因子段落: {factor}"
        for (_s, _t, base, stressed, label) in jumps:
            assert label in sec, f"§6.2 缺少跳升对: {factor}/{label}"
            row = next(ln for ln in sec.splitlines() if label in ln)
            assert f"| {base} |" in row and f"| {stressed} |" in row, row

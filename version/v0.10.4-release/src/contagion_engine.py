"""WP-M4-02 → contagion-matrix.md 的可执行实现（传染矩阵 + 组合暴露 + 压力跳升）。

单一事实源：矩阵数据（§2.1 强度热图 + §2.4 全标记表）从引擎文档运行时解析，不复制；
派生语义见 contagion-matrix.md §5.5/§5.6（超级传染者=行合计 top3、脆弱行业=列合计
top3）与 systemic-warning-framework.md §2.3（传染力系数=行合计/13 行业均值、
行业权重=存量权重×系数并归一化）。§6.2 压力跳升规则编码为代码逻辑（sri_calculator
先例），每条显式跳升对带文档覆盖测试（tests/test_contagion_engine.py）。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir

INTENSITY_MIN, INTENSITY_MAX = 1, 5
CONTAGION_TYPES = frozenset("CRLS")  # 信用链/区域共振/流动性挤兑/信心崩塌（§2.2）
N_INDUSTRIES = 13

ESCALATION_FACTORS = ("市场恐慌", "监管真空", "高杠杆", "信息不对称", "年末效应")

# §6.2 显式跳升表：(source, target, 正常强度, 压力强度, 文档原文对名)。
# 仅编码正常强度与文档表格一致的方向（如 数据中心↔传媒 仅 数据→传媒 基值 3）。
_EXPLICIT_JUMPS = {
    "市场恐慌": [
        ("半导体/集成电路", "光伏/储能", 4, 5, "半导体→光伏"),
        ("半导体/集成电路", "新能源汽车", 3, 4, "半导体→新能源车"),
        ("城投债 / LGFV", "交通运输", 4, 5, "城投债→交通运输"),
        ("生物医药/创新药", "医疗器械", 4, 5, "生物医药↔医疗器械"),
        ("医疗器械", "生物医药/创新药", 4, 5, "生物医药↔医疗器械"),
        ("商贸零售", "传媒/互联网", 3, 4, "商贸零售↔传媒互联网"),
        ("传媒/互联网", "商贸零售", 3, 4, "商贸零售↔传媒互联网"),
        ("食品饮料", "纺织服装", 2, 3, "食品饮料↔纺织服装"),
        ("纺织服装", "食品饮料", 2, 3, "食品饮料↔纺织服装"),
    ],
    "监管真空": [
        ("城投债 / LGFV", "交通运输", 4, 5, "城投债→交通运输"),
        ("城投债 / LGFV", "光伏/储能", 3, 4, "城投债→光伏"),
        ("城投债 / LGFV", "数据中心/算力基建", 3, 4, "城投债→数据中心"),
        ("城投债 / LGFV", "新能源汽车", 2, 3, "城投债→新能源车"),
        ("城投债 / LGFV", "半导体/集成电路", 2, 3, "城投债→半导体"),
        ("城投债 / LGFV", "高端装备/工业母机", 2, 3, "城投债→高端装备"),
        ("城投债 / LGFV", "生物医药/创新药", 2, 3, "城投债→生物医药"),
    ],
    "高杠杆": [
        ("城投债 / LGFV", "交通运输", 4, 5, "城投债→交通运输"),
        ("数据中心/算力基建", "传媒/互联网", 3, 4, "数据中心↔传媒互联网"),
        ("商贸零售", "传媒/互联网", 3, 4, "商贸零售↔传媒互联网"),
        ("传媒/互联网", "商贸零售", 3, 4, "商贸零售↔传媒互联网"),
        ("半导体/集成电路", "光伏/储能", 4, 5, "半导体↔光伏"),
        ("光伏/储能", "半导体/集成电路", 4, 5, "半导体↔光伏"),
        ("数据中心/算力基建", "城投债 / LGFV", 3, 4, "数据中心→城投债"),
    ],
    "信息不对称": [
        ("城投债 / LGFV", "交通运输", 4, 5, "城投债→交通运输"),
    ],
    "年末效应": [],
}

# §6.2 通用标记规则：因子 → 受影响传染类型集合（命中 +1，封顶 5）。
# 市场恐慌=含 S/L；信息不对称=含 C/R（规则1/规则4 原文）；其余因子无通用规则
# （规则2 特别说明"+0~+1" 与规则5 "全部 +0~+1" 为模糊区间，留 LLM 判断，编码为 +0）。
_GENERIC_TYPE_BUMP = {"市场恐慌": frozenset("SL"), "信息不对称": frozenset("CR")}


@dataclass(frozen=True)
class ContagionCell:
    source: str
    target: str
    intensity: int
    types: tuple = ()
    confidence: str = "-"
    bidirectional: bool = False


class ContagionMatrix:
    """13 行业有向传染矩阵（解析自 contagion-matrix.md，不可变）。"""

    def __init__(self, industries, cells):
        self.industries = list(industries)
        self._cells = dict(cells)

    def cell(self, source, target) -> ContagionCell:
        try:
            return self._cells[(source, target)]
        except KeyError:
            raise ValueError(
                f"未知行业对: {source!r} → {target!r}（已知 {len(self.industries)} 个行业）"
            ) from None

    def intensity(self, source, target) -> int:
        if source == target:
            return 0
        return self.cell(source, target).intensity

    def itercells(self):
        return iter(self._cells.values())

    def with_intensities(self, overrides) -> "ContagionMatrix":
        cells = dict(self._cells)
        for (s, t), n in overrides.items():
            c = self.cell(s, t)
            cells[(s, t)] = ContagionCell(s, t, n, c.types, c.confidence, c.bidirectional)
        return ContagionMatrix(self.industries, cells)


# ---------------------------------------------------------------------------
# 解析层（§2.1 热图 + §2.4 全标记；文档=单一事实源）
# ---------------------------------------------------------------------------

def _parse_heatmap(text: str):
    """§2.1 代码块 → 13×13 强度网格 {(i,j): int}（0 基索引）。"""
    sec = re.search(r"### 2\.1 .*?(?=### 2\.2 )", text, re.DOTALL)
    if not sec:
        raise ValueError("§2.1 传热图段落缺失")
    block = re.search(r"```\n(.*?)```", sec.group(0), re.DOTALL)
    if not block:
        raise ValueError("§2.1 代码块缺失")
    lines = [ln for ln in block.group(1).splitlines() if "│" in ln]
    if len(lines) != N_INDUSTRIES + 1:
        raise ValueError(f"§2.1 热图应有 {N_INDUSTRIES + 1} 行含 │ 的行，实际 {len(lines)}")
    abbrevs = lines[0].split("│", 1)[1].split()
    if len(abbrevs) != N_INDUSTRIES:
        raise ValueError(f"§2.1 列头应有 {N_INDUSTRIES} 个行业缩写，实际 {len(abbrevs)}")
    grid = {}
    for i, ln in enumerate(lines[1:]):
        _name, _, rest = ln.partition("│")
        cells = rest.split()
        if len(cells) != N_INDUSTRIES:
            raise ValueError(f"§2.1 第 {i + 1} 行应有 {N_INDUSTRIES} 格，实际 {len(cells)}")
        for j, v in enumerate(cells):
            if i == j:
                if v != "-":
                    raise ValueError(f"§2.1 对角线 ({i},{j}) 应为 '-'，实际 {v!r}")
            else:
                n = int(v)
                if not INTENSITY_MIN <= n <= INTENSITY_MAX:
                    raise ValueError(f"§2.1 强度越界 ({i},{j}): {n}")
                grid[(i, j)] = n
    return grid


def _parse_full_matrix(text: str):
    """§2.4 行块 → (13 个规范名, {(i,j): (types, confidence, bidirectional, intensity)})。"""
    blocks = list(re.finditer(
        r"#### 行(\d+)：(.+?)\s*→\s*各行业\s*\n(.*?)(?=\n#### |\n## |\Z)", text, re.DOTALL
    ))
    if len(blocks) != N_INDUSTRIES:
        raise ValueError(f"§2.4 应有 {N_INDUSTRIES} 个行块，实际 {len(blocks)}")
    full_names, marks = [], {}
    for bm in blocks:
        i = int(bm.group(1))
        if i != len(full_names) + 1:
            raise ValueError(f"§2.4 行块序号不连续: 行{i}")
        name = bm.group(2).strip()
        full_names.append(name)
        seen_j = set()
        for row in re.finditer(
            r"^\|\s*(\d+)→(\d+)\s+[^|]*?\|\s*([CRLS+\-]+)\s*\|\s*(\d+)\s*\|"
            r"\s*([HML-])\s*\|\s*(↔|→|-)\s*\|",
            bm.group(3), re.MULTILINE,
        ):
            bi, bj = int(row.group(1)), int(row.group(2))
            if bi != i:
                raise ValueError(f"§2.4 行{i}块出现 {bi}→{bj}")
            types = tuple(ch for ch in row.group(3) if ch in CONTAGION_TYPES)
            marks[(bi, bj)] = (types, row.group(5), row.group(6) == "↔", int(row.group(4)))
            seen_j.add(bj)
        if seen_j != set(range(1, N_INDUSTRIES + 1)) - {i}:
            raise ValueError(f"§2.4 行{i}块受体覆盖不全: {sorted(seen_j)}")
    return full_names, marks


def load_matrix(matrix_md_path=None) -> ContagionMatrix:
    """从 contagion-matrix.md 解析 13×13 传染矩阵（§2.1 与 §2.4 交叉校验）。"""
    path = Path(matrix_md_path) if matrix_md_path else engine_dir() / "contagion-matrix.md"
    text = path.read_text(encoding="utf-8")
    grid = _parse_heatmap(text)
    full_names, marks = _parse_full_matrix(text)
    cells = {}
    for (i, j), n in grid.items():
        types, conf, bidir, mn = marks[(i + 1, j + 1)]  # §2.4 标签为 1 基
        if mn != n:
            raise ValueError(f"§2.1 与 §2.4 强度不一致 ({i}→{j}): {n} vs {mn}")
        s, t = full_names[i], full_names[j]
        cells[(s, t)] = ContagionCell(s, t, n, types, conf, bidir)
    return ContagionMatrix(full_names, cells)


# ---------------------------------------------------------------------------
# 派生计算（§5.5/§5.6 + systemic §2.3）
# ---------------------------------------------------------------------------

def row_sums(matrix) -> dict:
    """行合计 = 对外传染力（§5.5 超级传染者得分）。"""
    return {s: sum(matrix.intensity(s, t) for t in matrix.industries if t != s)
            for s in matrix.industries}


def col_sums(matrix) -> dict:
    """列合计 = 被传染风险（§5.6 脆弱行业得分）。"""
    return {t: sum(matrix.intensity(s, t) for s in matrix.industries if s != t)
            for t in matrix.industries}


def _top(scores: dict, n: int) -> list:
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def super_spreaders(matrix, top=3) -> list:
    return _top(row_sums(matrix), top)


def vulnerable_industries(matrix, top=3) -> list:
    return _top(col_sums(matrix), top)


def contagion_coefficients(matrix) -> dict:
    """传染力系数 = 行合计 / 13 行业行合计均值（systemic §2.3）。"""
    sums = row_sums(matrix)
    mean = sum(sums.values()) / len(sums)
    return {k: v / mean for k, v in sums.items()}


def sri_weights(debt_shares: dict, coefficients: dict) -> dict:
    """行业权重 = 存量权重 × 传染力系数，归一化（systemic §2.3）。"""
    if set(debt_shares) != set(coefficients):
        raise ValueError("debt_shares 与 coefficients 的行业集合不一致")
    if any(v < 0 for v in debt_shares.values()):
        raise ValueError("debt_shares 不允许负值")
    raw = {k: debt_shares[k] * coefficients[k] for k in debt_shares}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("加权总和必须为正")
    return {k: v / total for k, v in raw.items()}


# ---------------------------------------------------------------------------
# 组合分析（WP-M4-02 输出）
# ---------------------------------------------------------------------------

def portfolio_exposure(matrix, holdings: dict) -> list:
    """每只持仓的被传染暴露与对外传染力（其他持仓行业强度 × 其权重），按暴露降序。"""
    if not holdings:
        raise ValueError("holdings 不能为空")
    for ind, w in holdings.items():
        if ind not in matrix.industries:
            raise ValueError(f"未知行业: {ind!r}")
        if w < 0:
            raise ValueError(f"权重不允许负值: {ind}={w}")
    out = []
    for h in holdings:
        inbound = sum(matrix.intensity(s, h) * w
                      for s, w in holdings.items() if s != h)
        outbound = sum(matrix.intensity(h, t) * w
                       for t, w in holdings.items() if t != h)
        out.append({"industry": h, "inbound": inbound, "outbound": outbound})
    out.sort(key=lambda e: (-e["inbound"], e["industry"]))
    return out


def high_intensity_links(matrix, industries=None, threshold=4) -> list:
    """（组合内）强度 ≥ threshold 的有向传染边，按强度降序（§3.1 图谱数据形态）。"""
    inds = list(industries) if industries is not None else matrix.industries
    links = [
        matrix.cell(s, t)
        for s in inds for t in inds
        if s != t and matrix.intensity(s, t) >= threshold
    ]
    links.sort(key=lambda c: (-c.intensity, c.source, c.target))
    return links


# ---------------------------------------------------------------------------
# 压力跳升（§6.2）
# ---------------------------------------------------------------------------

def apply_escalation(matrix, factors) -> ContagionMatrix:
    """给定触发因子集，返回压力矩阵（显式对跳升 + 标记通用 +1，封顶 5；原矩阵不变）。"""
    unknown = sorted(set(factors) - set(ESCALATION_FACTORS))
    if unknown:
        raise ValueError(f"未知升级因子: {unknown}，可选: {list(ESCALATION_FACTORS)}")
    boosts = {}
    for f in factors:
        for (s, t, base, stressed, _label) in _EXPLICIT_JUMPS.get(f, []):
            cur = matrix.intensity(s, t)
            if cur != base:
                raise ValueError(
                    f"§6.2 跳升基准漂移: {f} {s}→{t} 文档正常强度={base}，矩阵实际={cur}"
                )
            key = (s, t)
            boosts[key] = max(boosts.get(key, cur), stressed)
        types = _GENERIC_TYPE_BUMP.get(f)
        if types:
            for c in matrix.itercells():
                if set(c.types) & types:
                    key = (c.source, c.target)
                    cur = boosts.get(key, c.intensity)
                    boosts[key] = min(cur + 1, INTENSITY_MAX)
        if f == "年末效应":  # 规则5：城投债相关所有对 +1（"全部 +0~+1" 模糊区间留 LLM）
            for c in matrix.itercells():
                if "城投债" in c.source or "城投债" in c.target:
                    key = (c.source, c.target)
                    cur = boosts.get(key, c.intensity)
                    boosts[key] = min(cur + 1, INTENSITY_MAX)
    return matrix.with_intensities(boosts)

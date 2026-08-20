"""WP-M4-04 → 组合压力测试引擎（T1 解析层 + 基础类型）。

单一事实源：financial-deep-dive.md E.1 三场景参数表（:216-220）与七行业
Severe 校准锚表（:231-239）、E.5 安全边际四档表（:294-299）、E.8 分行业
偏离因子表（:352-363）、E.10.2 标准情景模板（:508-513），以及
concentration-framework.md §9.2 阈值跳升表（:777-783）均运行时解析，解析
失败即 raise（不裸复制数值副本）。

已裁决设计决策（SDD 2026-08-20-wp-m4-04-stress-engine，注释处标注）：
- D1 Severe 参数裁决（resolve_severe_params）：E.1 校准锚表命中行业 → 锚值
  （不再乘 E.8 因子）；锚表未命中 → 默认 Severe 参数 × E.8 偏离因子；E.8
  也无该行业（或该行业因子标注「不适用」，如 Biotech）→ 纯默认 Severe 参数。

区间语义（文档档位文本直译）：E.5 阈值 ">X" / "<X" 为开区间端点，"X-Y" 为
闭区间；统一表示为 (lo, hi, lo_open, hi_open)，None = 该侧无界。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir

_DEEP_DIVE_DOC = "financial-deep-dive.md"
_CONCENTRATION_DOC = "concentration-framework.md"

# E.1 七行业校准锚表当前 7 行；E.8 偏离因子表当前 10 行；E.10.2 标准情景
# 模板当前 4 行。下界校验防"行首加粗丢失 → 正则静默丢行"（解析失败即 raise
# 纪律要求丢失可观测，而非容忍稀疏结果）。
_ANCHOR_MIN_ROWS = 7
_DEVIATION_MIN_ROWS = 10
_MV_SCENARIO_MIN_ROWS = 4

# E.5 安全边际表恒为四档（🟢/🟡/🟠/🔴）；§9.2 阈值跳升表当前五情景。
_SAFETY_BAND_COUNT = 4
_JUMP_MIN_ROWS = 5


@dataclass(frozen=True)
class StressTables:
    """五张可解析表的运行时解析结果。

    scenario_params:   E.1 三场景参数 → {"Base"/"Bear"/"Severe":
                       {"revenue_change": %|None, "margin_change_pp": pp|None,
                        "funding_cost_change_bp": bp|None}}（Base 行「基准」
                       解析为 None）。
    severe_anchors:    E.1 七行业校准锚 → {行业: {"revenue_change": %,
                       "margin_change_pp": pp}}（均为负值）。
    deviation_factors: E.8 偏离因子 → {行业: {"bear_revenue", "severe_revenue",
                       "bear_margin", "severe_margin"}}（倍率；「不适用」→ None）。
    safety_bands:      E.5 四档 → [{"emoji", "name", "interest_coverage",
                       "fcf_interest", "cash_runway_months"}]，三指标阈值均为
                       (lo, hi, lo_open, hi_open)（None = 该侧无界）。
    threshold_jumps:   §9.2 五情景 → {情景名: {"dimensions": 受影响维度,
                       "rule": 跳升规则原文}}（文本结构，数值未抽取）。
    mv_scenarios:      E.10.2 四档情景 → [{"name", "risk_free_bp", "spread_bp",
                       "rating", "liquidity", "probability_pct"}]。
    """

    scenario_params: dict
    severe_anchors: dict
    deviation_factors: dict
    safety_bands: list
    threshold_jumps: dict
    mv_scenarios: list


@dataclass(frozen=True)
class IssuerFinancials:
    """发行人基准财务输入（供 T2 场景传导计算消费）。

    revenue/period_expenses/da/capex/interest_expense/cash/unused_credit/
    inventory 为金额（同币种同单位）；gross_margin/tax_rate 为小数比率
    （0.20 = 20%）；dso_days/dio_days 为天数。
    """

    revenue: float
    gross_margin: float
    period_expenses: float
    tax_rate: float
    da: float
    capex: float
    interest_expense: float
    cash: float
    unused_credit: float
    inventory: float
    dso_days: float
    dio_days: float


def _read(path, default_name: str) -> str:
    p = Path(path) if path else engine_dir() / default_name
    return p.read_text(encoding="utf-8")


def _section(text: str, num: str) -> str:
    """按节号切片（E 节为 ``### ``、E.x.y 子节为 ``#### ``，故锁 ``#{2,4}``）。

    行首锁防正文提及误锚；``(?!\\d)`` 节号边界防 ``E.1`` 误锚 ``E.10`` 之类的
    前缀误锚（锚点须为独立小节标题行）。切片终于下一个同级或更高级标题。
    """
    sec = re.search(
        rf"^#{{2,4}}\s{re.escape(num)}(?!\d)\s.*?(?=\n#{{2,4}}\s|\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if not sec:
        raise ValueError(f"§{num} 段落缺失")
    return sec.group(0)


# ---------------- E.1 三场景参数 + 七行业校准锚 ----------------

_PARAM_ROW_RE = re.compile(
    r"^\|\s*(收入变动|毛利率变动|融资成本变动)\s*\|"
    r"\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

_PARAM_UNITS = {"收入变动": "%", "毛利率变动": "个百分点", "融资成本变动": "bp"}


def _parse_param_cell(cell: str, unit: str, row: str) -> float | None:
    """E.1 参数单元格 → 数值；"基准" → None；尾部全角括注（校准说明锚点）剥离。"""
    cell = re.sub(r"（[^（）]*）", "", cell).strip()
    if cell == "基准":
        return None
    m = re.fullmatch(rf"([+-]?\d+(?:\.\d+)?){re.escape(unit)}", cell)
    if not m:
        raise ValueError(f"E.1「{row}」参数单元格无法解析: {cell!r}")
    return float(m.group(1))


def _parse_scenario_params(text: str) -> dict:
    """E.1 参数表 → {"Base"/"Bear"/"Severe": {revenue_change, margin_change_pp,
    funding_cost_change_bp}}（Base 行「基准」→ None）。"""
    sec = _section(text, "E.1")
    rows = {}
    for m in _PARAM_ROW_RE.finditer(sec):
        row, base, bear, severe = m.groups()
        unit = _PARAM_UNITS[row]
        rows[row] = (
            _parse_param_cell(base, unit, row),
            _parse_param_cell(bear, unit, row),
            _parse_param_cell(severe, unit, row),
        )
    if set(rows) != set(_PARAM_UNITS):
        raise ValueError(
            f"E.1 参数表应有 {sorted(_PARAM_UNITS)} 三行，实际 {sorted(rows)}"
        )
    keys = ("revenue_change", "margin_change_pp", "funding_cost_change_bp")
    params = {"Base": {}, "Bear": {}, "Severe": {}}
    for row, key in zip(("收入变动", "毛利率变动", "融资成本变动"), keys):
        for scenario, value in zip(("Base", "Bear", "Severe"), rows[row]):
            params[scenario][key] = value
    return params


def _parse_severe_anchors(text: str) -> dict:
    """E.1 校准锚表 → {行业: {"revenue_change": %, "margin_change_pp": pp}}。"""
    sec = _section(text, "E.1")
    anchors = {}
    for m in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|[^|]*\|"
        r"\s*([+-]?\d+(?:\.\d+)?)%\s*\|\s*([+-]?\d+(?:\.\d+)?)pp\s*\|",
        sec, re.MULTILINE,
    ):
        anchors[m.group(1).strip()] = {
            "revenue_change": float(m.group(2)),
            "margin_change_pp": float(m.group(3)),
        }
    if len(anchors) < _ANCHOR_MIN_ROWS:
        raise ValueError(
            f"E.1 校准锚表至少应有 {_ANCHOR_MIN_ROWS} 行，实际 {len(anchors)}"
            "（疑似加粗标记丢失致静默丢行）"
        )
    return anchors


# ---------------- E.8 分行业偏离因子 ----------------

def _parse_factor_cell(cell: str, industry: str) -> float | None:
    """E.8 因子单元格 "1.2x" → 1.2；"不适用" → None（Biotech 无稳定收入）。"""
    cell = cell.strip()
    if cell == "不适用":
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)x", cell)
    if not m:
        raise ValueError(f"E.8「{industry}」偏离因子单元格无法解析: {cell!r}")
    return float(m.group(1))


def _parse_deviation_factors(text: str) -> dict:
    """E.8 → {行业: {bear_revenue, severe_revenue, bear_margin, severe_margin}}。"""
    sec = _section(text, "E.8")
    factors = {}
    for m in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
        r"\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        sec, re.MULTILINE,
    ):
        industry = m.group(1).strip()
        cells = m.group(2, 3, 4, 5)
        factors[industry] = dict(zip(
            ("bear_revenue", "severe_revenue", "bear_margin", "severe_margin"),
            (_parse_factor_cell(c, industry) for c in cells),
        ))
    if len(factors) < _DEVIATION_MIN_ROWS:
        raise ValueError(
            f"E.8 偏离因子表至少应有 {_DEVIATION_MIN_ROWS} 行，实际 {len(factors)}"
            "（疑似加粗标记丢失致静默丢行）"
        )
    return factors


# ---------------- E.5 安全边际四档 ----------------

def _parse_band_cell(cell: str, label: str) -> tuple:
    """E.5 阈值单元格 → (lo, hi, lo_open, hi_open)（None = 该侧无界）。

    ">3.0x" → (3.0, None, True, False)；"1.5-3.0x" → (1.5, 3.0, False, False)；
    "<1.0x" → (None, 1.0, False, True)；"个月" 后缀同口径（">18个月"）。
    """
    cell = cell.strip()
    m = re.fullmatch(r">(\d+(?:\.\d+)?)(?:x|个月)?", cell)
    if m:
        return (float(m.group(1)), None, True, False)
    m = re.fullmatch(r"<(\d+(?:\.\d+)?)(?:x|个月)?", cell)
    if m:
        return (None, float(m.group(1)), False, True)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?:x|个月)?", cell)
    if m:
        return (float(m.group(1)), float(m.group(2)), False, False)
    raise ValueError(f"E.5 安全边际阈值单元格无法解析（{label}）: {cell!r}")


def _parse_safety_bands(text: str) -> list:
    """E.5 → [{"emoji", "name", "interest_coverage", "fcf_interest",
    "cash_runway_months"}]（恒四档，档数不符即 raise）。"""
    sec = _section(text, "E.5")
    bands = []
    for m in re.finditer(
        r"^\|\s*(🟢|🟡|🟠|🔴)\s*([^|]+?)\s*\|"
        r"\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        sec, re.MULTILINE,
    ):
        emoji, name = m.group(1), m.group(2).strip()
        bands.append({
            "emoji": emoji,
            "name": name,
            "interest_coverage": _parse_band_cell(m.group(3), f"{emoji}{name} 利息覆盖"),
            "fcf_interest": _parse_band_cell(m.group(4), f"{emoji}{name} FCF/利息"),
            "cash_runway_months": _parse_band_cell(m.group(5), f"{emoji}{name} 现金跑道"),
        })
    if len(bands) != _SAFETY_BAND_COUNT:
        raise ValueError(
            f"E.5 安全边际表应有 {_SAFETY_BAND_COUNT} 档，实际 {len(bands)}"
        )
    return bands


# ---------------- §9.2 阈值跳升表（concentration-framework.md） ----------------

def _parse_threshold_jumps(text: str) -> dict:
    """§9.2 → {情景名: {"dimensions": 受影响维度, "rule": 跳升规则原文}}。

    规则单元格保留原文（文本结构；数值如 3%/10%/20% 未抽取，留 T2 消费时
    再行结构化）。"""
    sec = _section(text, "9.2")
    jumps = {}
    for m in re.finditer(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
        sec, re.MULTILINE,
    ):
        name, dimensions, rule = (g.strip() for g in m.groups())
        if name == "压力场景" or set(name) <= set("-: "):  # 表头行 / 分隔行
            continue
        jumps[name] = {"dimensions": dimensions, "rule": rule}
    if len(jumps) < _JUMP_MIN_ROWS:
        raise ValueError(
            f"§9.2 阈值跳升表至少应有 {_JUMP_MIN_ROWS} 行，实际 {len(jumps)}"
        )
    return jumps


# ---------------- E.10.2 标准情景模板 ----------------

def _parse_mv_scenarios(text: str) -> list:
    """E.10.2 → [{"name", "risk_free_bp", "spread_bp", "rating", "liquidity",
    "probability_pct"}]（概率单元格 "历史概率约20%" 取数值部分）。"""
    sec = _section(text, "E.10.2")
    scenarios = []
    for m in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|\s*\+(\d+)bp\s*\|\s*\+(\d+)bp\s*\|"
        r"\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*历史概率约(\d+(?:\.\d+)?)%\s*\|",
        sec, re.MULTILINE,
    ):
        scenarios.append({
            "name": m.group(1).strip(),
            "risk_free_bp": float(m.group(2)),
            "spread_bp": float(m.group(3)),
            "rating": m.group(4).strip(),
            "liquidity": m.group(5).strip(),
            "probability_pct": float(m.group(6)),
        })
    if len(scenarios) < _MV_SCENARIO_MIN_ROWS:
        raise ValueError(
            f"E.10.2 标准情景模板至少应有 {_MV_SCENARIO_MIN_ROWS} 行，"
            f"实际 {len(scenarios)}（疑似加粗标记丢失致静默丢行）"
        )
    return scenarios


# ---------------- 顶层装载 ----------------

def load_stress_tables(deep_dive_path=None, concentration_path=None) -> StressTables:
    """运行时解析 E.1（参数+校准锚）/E.8/E.5/E.10.2（financial-deep-dive.md）
    与 §9.2（concentration-framework.md）五张表；任何一张解析失败即 raise。"""
    dd = _read(deep_dive_path, _DEEP_DIVE_DOC)
    conc = _read(concentration_path, _CONCENTRATION_DOC)
    return StressTables(
        scenario_params=_parse_scenario_params(dd),
        severe_anchors=_parse_severe_anchors(dd),
        deviation_factors=_parse_deviation_factors(dd),
        safety_bands=_parse_safety_bands(dd),
        threshold_jumps=_parse_threshold_jumps(conc),
        mv_scenarios=_parse_mv_scenarios(dd),
    )


# ---------------- D1：Severe 参数裁决 ----------------

def resolve_severe_params(industry: str, tables: StressTables) -> dict:
    """D1 裁决：行业 Severe 场景参数解析。

    分支一：E.1 七行业校准锚表命中 → 锚值（行业历史最大回撤，不再乘 E.8
    因子）；分支二：锚表未命中但 E.8 有数值因子 → 默认 Severe 参数 × E.8
    偏离因子；分支三：E.8 也无该行业，或该行业因子标注「不适用」（Biotech
    无稳定收入，文档指引改用现金跑道压力测试）→ 纯默认 Severe 参数。
    融资成本三分支均沿用 E.1 默认 +200bp（E.1/E.8 均无融资成本行业校准）。
    """
    default = tables.scenario_params["Severe"]
    funding = default["funding_cost_change_bp"]
    base = {
        "revenue_change": default["revenue_change"],
        "margin_change_pp": default["margin_change_pp"],
        "funding_cost_change_bp": funding,
    }
    anchor = tables.severe_anchors.get(industry)
    if anchor is not None:
        return {
            **base,
            "revenue_change": anchor["revenue_change"],
            "margin_change_pp": anchor["margin_change_pp"],
            "source": "E.1锚",
            "note": (
                f"D1：E.1 校准锚表命中「{industry}」，采用行业历史最大回撤锚值"
                f"（收入 {anchor['revenue_change']:.4g}%、毛利率 "
                f"{anchor['margin_change_pp']:.4g}pp）；融资成本无行业校准，"
                f"沿用默认 +{funding:.4g}bp"
            ),
        }
    factors = tables.deviation_factors.get(industry)
    if (
        factors is not None
        and factors["severe_revenue"] is not None
        and factors["severe_margin"] is not None
    ):
        return {
            **base,
            "revenue_change": default["revenue_change"] * factors["severe_revenue"],
            "margin_change_pp": default["margin_change_pp"] * factors["severe_margin"],
            "source": "E.8因子",
            "note": (
                f"D1：E.1 锚表未覆盖「{industry}」，默认 Severe × E.8 偏离因子"
                f"（收入 ×{factors['severe_revenue']:.4g}、毛利率 "
                f"×{factors['severe_margin']:.4g}）；融资成本无行业偏离因子，"
                f"沿用默认 +{funding:.4g}bp"
            ),
        }
    if factors is not None:
        note = (
            f"D1：E.8 对「{industry}」偏离因子标注「不适用」（Biotech 无稳定收入，"
            "文档指引改用现金跑道压力测试），取纯默认 Severe 参数"
        )
    else:
        note = f"D1：E.1 锚表与 E.8 因子表均未覆盖「{industry}」，取纯默认 Severe 参数"
    return {**base, "source": "默认", "note": note}

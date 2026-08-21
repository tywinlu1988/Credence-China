"""WP-M4-04 → 组合压力测试引擎（T1 解析层 + T2 §E 三场景矩阵计算 +
T3 §九 压力传导 + E.10 债券市值维度）。

单一事实源：financial-deep-dive.md E.1 三场景参数表（:216-220）与七行业
Severe 校准锚表（:231-239）、E.5 安全边际四档表（:294-299）、E.8 分行业
偏离因子表（:352-363）、E.10.2 标准情景模板（:508-513），以及
concentration-framework.md §9.2 阈值跳升表（:777-783）均运行时解析，解析
失败即 raise（不裸复制数值副本）。E.3 线性链/E.6 临界值/E.7 二阶效应的公式
与规则、§9.2 五情景的操作化映射为硬编码 + parity 锚点（惯例；§9.2 映射另加
运行时锚点校验——规则文本不含锚点片段即 raise），注释处标注节出处。

已裁决设计决策（SDD 2026-08-20-wp-m4-04-stress-engine，注释处标注）：
- D1 Severe 参数裁决（resolve_severe_params）：E.1 校准锚表命中行业 → 锚值
  （不再乘 E.8 因子）；锚表未命中 → 默认 Severe 参数 × E.8 偏离因子；E.8
  也无该行业（或该行业因子标注「不适用」，如 Biotech）→ 纯默认 Severe 参数。
- D2 现金跑道操作化（文档未定义公式）：fcf < 0 → 现金 / (-fcf/12)；
  否则 999（"无限"哨兵）；unused_credit 单独报告不并入。
- D3 E.7 融资成本二阶上浮：文档区间 50-100bp 取保守端 +50bp 并注记。
- 融资成本口径（主会话 Fix R1 裁决，E.9 语义为准）：融资成本变动为利率
  加点（bp），利息支出放大系数 = 1 + 加点/基准融资利率（E.9 :412，6亿 ×
  (1+200bp/4%) = 9亿）；E.3:271 字面式 ×(1+加点) 与 E.1 参数表 bp 利率
  单位不自洽（简化笔误）。IssuerFinancials.base_funding_rate 缺失时回退
  E.3 字面口径（低估冲击）并于输出注记留 LLM 判断。
- D5 行业名归一（normalize_industry）：canonical 13 行业名/别名 → E.1/E.8
  表键（E.1 锚表「新能源汽车—OEM」与 E.8 因子表「新能源车—OEM」为同一
  行业两种拼写，T1 审查发现），归一后再走 D1 三级链。

区间语义（文档档位文本直译）：E.5 阈值 ">X" / "<X" 为开区间端点，"X-Y" 为
闭区间；统一表示为 (lo, hi, lo_open, hi_open)，None = 该侧无界。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.concentration_scorer import (
    DEFAULT_WEIGHTS,
    ConcentrationMetrics,
    _risk_level,
    channel_score,
    concentration_risk_score,
    industry_score,
    maturity_score,
    rating_score,
    region_score,
)
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
    （0.20 = 20%）；dso_days/dio_days 为天数。base_funding_rate 为基准融资
    利率（小数比率，0.04 = 4%；可选）——提供时利息放大按 E.9 加点口径，
    缺失时回退 E.3 字面口径并注记（主会话 Fix R1 裁决）。
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
    base_funding_rate: float | None = None


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


# ---------------- D5：行业名归一 ----------------

# canonical 13 行业口径：contagion-matrix.md 行1-13（:123-346）。
# parity 锚点（T1 审查发现，D5 裁决）：E.1 校准锚表键「新能源汽车—OEM」
# （financial-deep-dive.md :238）与 E.8 因子表键「新能源车—OEM」（:361）为
# 同一行业的两种拼写，未归一时同一行业会走 D1 不同分支产出不同参数。
_INDUSTRY_KEY_MAP = {
    "新能源汽车": "新能源汽车—OEM",      # canonical 行6 → E.1 锚键（OEM 整车口径）
    "新能源车—OEM": "新能源汽车—OEM",    # E.8 拼法 → E.1 拼法（同一行业）
    "新能源汽车—供应链": "新能源车—供应链",  # E.8 键（:362，与 OEM 不同行，Fix R2 补）
    "高端装备/工业母机": "高端装备/机床",  # canonical 行3 → E.1/E.8 键（:235/:357）
    "数据中心/算力基建": "数据中心",      # canonical 行7 → E.1/E.8 键（:239/:363）
}

# 半导体/生物医药必须带子类型（E.8 仅登记子类型键）；裸名按文档口径处理并注记。
_SEMICONDUCTOR_BARE = {"半导体/集成电路", "半导体", "集成电路"}  # canonical 行2
_BIO_BARE = {"生物医药/创新药", "生物医药", "创新药"}            # canonical 行4


def normalize_industry(industry: str) -> tuple:
    """D5 行业名归一 → (表键, 注记|None)。

    半导体裸名：E.1 锚表有裸键「半导体/IC」可用则用之（锚表缺裸键时该键
    不命中任何表，自然落入 D1 后续分支）；生物医药裸名：E.1/E.8 均无裸键，
    原样下传走 D1 默认分支。两种裸名均附子类型注记（LLM 应提供
    Foundry/Fabless、Pharma/Biotech 子类型键）。
    """
    if industry in _SEMICONDUCTOR_BARE:
        return "半导体/IC", (
            f"D5：「{industry}」为裸名，未带子类型（半导体—Foundry/半导体—Fabless），"
            "按文档口径取 E.1 锚表裸键「半导体/IC」"
        )
    if industry in _BIO_BARE:
        return industry, (
            f"D5：「{industry}」为裸名，未带子类型（生物医药—Pharma/生物医药—Biotech），"
            "E.1/E.8 均无裸键，走 D1 默认分支"
        )
    key = _INDUSTRY_KEY_MAP.get(industry)
    if key is not None and key != industry:
        return key, f"D5：「{industry}」归一至表键「{key}」"
    return industry, None


# ---------------- D1：Severe 参数裁决 ----------------

def resolve_severe_params(industry: str, tables: StressTables) -> dict:
    """D1 裁决：行业 Severe 场景参数解析（先经 D5 归一求表键）。

    分支一：E.1 七行业校准锚表命中 → 锚值（行业历史最大回撤，不再乘 E.8
    因子）；分支二：锚表未命中但 E.8 有数值因子 → 默认 Severe 参数 × E.8
    偏离因子；分支三：E.8 也无该行业，或该行业因子标注「不适用」（Biotech
    无稳定收入，文档指引改用现金跑道压力测试）→ 纯默认 Severe 参数。
    融资成本三分支均沿用 E.1 默认 +200bp（E.1/E.8 均无融资成本行业校准）。
    """
    industry, norm_note = normalize_industry(industry)
    default = tables.scenario_params["Severe"]
    funding = default["funding_cost_change_bp"]
    base = {
        "revenue_change": default["revenue_change"],
        "margin_change_pp": default["margin_change_pp"],
        "funding_cost_change_bp": funding,
    }
    anchor = tables.severe_anchors.get(industry)
    if anchor is not None:
        result = {
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
    else:
        factors = tables.deviation_factors.get(industry)
        if (
            factors is not None
            and factors["severe_revenue"] is not None
            and factors["severe_margin"] is not None
        ):
            result = {
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
        else:
            if factors is not None:
                note = (
                    f"D1：E.8 对「{industry}」偏离因子标注「不适用」（Biotech 无稳定收入，"
                    "文档指引改用现金跑道压力测试），取纯默认 Severe 参数"
                )
            else:
                note = f"D1：E.1 锚表与 E.8 因子表均未覆盖「{industry}」，取纯默认 Severe 参数"
            result = {**base, "source": "默认", "note": note}
    if norm_note:
        result["note"] = f"{norm_note}；{result['note']}"
    return result


# ================= T2：§E 三场景矩阵计算 =================

# E.7 二阶效应规则参数（financial-deep-dive.md :340-346，硬编码+parity 锚点）：
_SO_WRITEDOWN_REVENUE_DROP = -20.0   # 存货跌价触发：收入降幅>20%（严格大于）
_SO_WRITEDOWN_MARGIN_PP = -10.0      # 且毛利率压缩>10pp（严格大于）
_SO_WRITEDOWN_RATE = 0.10            # 存货跌价率假设 10%
_SO_FREEZE_REVENUE_DROP = -25.0      # 营运资金冻结触发：收入降幅>25%（严格大于）
_SO_DSO_EXTRA_DAYS = 20.0            # DSO 被动延长 20 天（客户付款延迟）
_SO_DIO_EXTRA_DAYS = 30.0            # DIO 滞销延长 30 天
_SO_FUNDING_EXTRA_BP = 50.0          # D3：融资成本二阶 50-100bp 取保守端 +50bp
_SO_CAPEX_CUT_RATE = 0.50            # Capex 削减 50%（非必要 Capex）
_SO_CAPEX_RUNWAY_FLOOR = 12.0        # 触发条件：FCF<0 且现金跑道<12 个月

# D2 现金跑道操作化（文档未定义公式）：fcf<0 → 现金/(-fcf/12)；否则 999 哨兵。
_RUNWAY_POSITIVE_FCF = 999.0

# E.5 补充判定（:301）警告文本：Severe 任一指标🔴 → 标记于综合评级输出，不降级。
TAIL_RISK_WARNING = (
    "尾部风险警告：Severe 场景下任一指标落入🔴区间，该主体在极端冲击下必然违约"
    "（E.5 补充判定——标记于综合评级输出，但不自动降级，Severe 不是基准判断）"
)

# E.5 档序（🟢<🟡<🟠<🔴），综合档取最差。
_BAND_SEVERITY = {"🟢": 0, "🟡": 1, "🟠": 2, "🔴": 3}

_SAFETY_METRICS = ("interest_coverage", "fcf_interest", "cash_runway_months")


@dataclass(frozen=True)
class SecondOrderEffect:
    """E.7 二阶效应单条记录（:340-346）。

    target 语义（run_scenario 应用口径）：
    - "profit"：从净利润与 CFO 扣减 amount（存货跌价，额外减少净利润）；
    - "cfo"：从 CFO 扣减 amount（营运资金冻结额外占用）；
    - "interest"：利息支出增加 amount（融资成本二阶，D3 +50bp）；
    - "capex"：Capex 削减 amount（FCF 相应回升）；
    - "note"：纯文本注记（资产减值-净资产侵蚀，无金额，amount 恒 0）。
    未触发时 amount = 0；detail 记录触发条件与计算过程（留痕可复算）。
    """

    name: str
    triggered: bool
    target: str
    amount: float
    detail: str


@dataclass(frozen=True)
class ScenarioResult:
    """E.3 传导链结果（severe=True 时为 E.7 二阶修正后终值）。

    金额单位与 IssuerFinancials 一致；interest_coverage/fcf_interest 为倍数；
    cash_runway_months 为月数（D2：fcf≥0 → 999 哨兵）。capex 为场景值
    （Capex 削减触发后 = 基准 × 50%）。second_order_effects 非 Severe 为空。
    note 为口径注记（如基准融资利率缺失的 E.3 字面口径回退，Fix R1）。
    """

    scenario: str
    industry: str
    revenue: float
    gross_profit: float
    ebitda: float
    net_profit: float
    cfo: float
    capex: float
    fcf: float
    interest: float
    interest_coverage: float
    fcf_interest: float
    cash_runway_months: float
    second_order_effects: tuple = ()
    note: str = ""


def _ratio(num: float, den: float) -> float:
    """零息保护：利息为 0 时覆盖倍数按分子符号外推（无付息义务）。"""
    if den == 0:
        return float("inf") if num >= 0 else float("-inf")
    return num / den


def _param(params: dict, key: str) -> float:
    """E.1 Base 行「基准」解析为 None → 零冲击。"""
    value = params[key]
    return value if value is not None else 0.0


def _stress_interest(fin: IssuerFinancials, funding_bp: float) -> tuple:
    """变动后利息支出（E.9 语义为准，主会话 Fix R1 裁决）。

    E.9 实演练口径：融资成本变动为利率加点（bp），放大系数 =
    1 + 加点/基准融资利率（:412，6亿 × (1+200bp/4%) = 9亿）；E.3:271 字面式
    ×(1+加点) 与 E.1 参数表 bp 利率单位不自洽（简化笔误）。
    base_funding_rate 缺失时回退 E.3 字面口径（低估冲击）→ 注记留 LLM 判断。
    返回 (变动后利息, 注记|None)。
    """
    if fin.base_funding_rate:
        return (
            fin.interest_expense * (1 + funding_bp / 10000 / fin.base_funding_rate),
            None,
        )
    return fin.interest_expense * (1 + funding_bp / 10000), (
        "基准融资利率缺失，按 E.3 字面口径 ×(1+加点) 计算变动后利息"
        "（低估冲击，留 LLM 判断）"
    )


def run_scenario(
    fin: IssuerFinancials,
    params: dict,
    industry: str,
    tables: StressTables,
    severe: bool = False,
    scenario: str = "",
) -> ScenarioResult:
    """E.3 线性传导链（:264-273）；severe=True 时叠加 E.7 二阶修正（D3）。

    params 为 E.1 场景参数 dict（revenue_change %、margin_change_pp pp、
    funding_cost_change_bp bp；可含 resolve_severe_params 的 source/note，
    计算时忽略）。利息口径（Fix R1，E.9 语义为准）：base_funding_rate 提供时
    放大系数 = 1 + 加点/基准融资利率；缺失时回退 E.3:271 字面式 ×(1+加点)
    并于 note 注记（低估冲击，留 LLM 判断）。
    EBITDA = 变动后毛利 - 期间费用 + D&A（:272 与 E.9.3 口径一致）。
    tables 保留在签名内（T3 消费；本函数数值链不依赖表值）。
    """
    rev_chg = _param(params, "revenue_change")
    margin_pp = _param(params, "margin_change_pp")
    funding_bp = _param(params, "funding_cost_change_bp")
    revenue = fin.revenue * (1 + rev_chg / 100)
    gross = revenue * (fin.gross_margin + margin_pp / 100)
    ebitda = gross - fin.period_expenses + fin.da
    net = (gross - fin.period_expenses) * (1 - fin.tax_rate)  # E.3 简化口径
    cfo = net + fin.da
    capex = fin.capex
    fcf = cfo - capex
    interest, rate_note = _stress_interest(fin, funding_bp)
    effects = ()
    if severe:
        base = ScenarioResult(
            scenario="Severe(线性基链)",
            industry=industry,
            revenue=revenue,
            gross_profit=gross,
            ebitda=ebitda,
            net_profit=net,
            cfo=cfo,
            capex=capex,
            fcf=fcf,
            interest=interest,
            interest_coverage=_ratio(ebitda, interest),
            fcf_interest=_ratio(fcf, interest),
            cash_runway_months=(
                fin.cash / (-fcf / 12) if fcf < 0 else _RUNWAY_POSITIVE_FCF
            ),
        )
        effects = tuple(second_order(fin, params, base))
        for e in effects:
            if not e.triggered:
                continue
            if e.target == "profit":
                net -= e.amount
                cfo -= e.amount
            elif e.target == "cfo":
                cfo -= e.amount
            elif e.target == "interest":
                interest += e.amount
            elif e.target == "capex":
                capex -= e.amount
        fcf = cfo - capex
    runway = fin.cash / (-fcf / 12) if fcf < 0 else _RUNWAY_POSITIVE_FCF
    return ScenarioResult(
        scenario=scenario or ("Severe" if severe else ""),
        industry=industry,
        revenue=revenue,
        gross_profit=gross,
        ebitda=ebitda,
        net_profit=net,
        cfo=cfo,
        capex=capex,
        fcf=fcf,
        interest=interest,
        interest_coverage=_ratio(ebitda, interest),
        fcf_interest=_ratio(fcf, interest),
        cash_runway_months=runway,
        second_order_effects=effects,
        note=rate_note or "",
    )


def second_order(
    fin: IssuerFinancials, params: dict, base_result: ScenarioResult
) -> list:
    """E.7 二阶效应五规则（:340-346，仅 Severe 启用）。

    base_result 为线性基链结果。规则按文档表序求值：存货跌价 → 营运资金
    冻结 → 融资成本二阶（D3 保守端 +50bp，Severe 恒触发——评级下调 1-2 档
    假设）→ Capex 削减（对 1-3 修正后的中间 FCF/跑道判定）→ 资产减值注记
    （引擎无历史盈亏输入，按场景净利<0 触发提示性注记，「持续亏损>2 年」
    需 LLM 结合历史数据确认）。
    """
    rev_chg = _param(params, "revenue_change")
    margin_pp = _param(params, "margin_change_pp")
    effects = []

    # 规则一：存货跌价——收入降幅>20% 且毛利率压缩>10pp → 存货×10%（:342）
    trig = rev_chg < _SO_WRITEDOWN_REVENUE_DROP and margin_pp < _SO_WRITEDOWN_MARGIN_PP
    amount = fin.inventory * _SO_WRITEDOWN_RATE if trig else 0.0
    effects.append(SecondOrderEffect(
        "存货跌价", trig, "profit", amount,
        f"触发条件：收入降幅>20% 且毛利率压缩>10pp（实际 {rev_chg:.4g}% / "
        f"{margin_pp:.4g}pp）→ {'触发，' if trig else '未触发；'}"
        + (f"存货 {fin.inventory:.4g} × 10% = {amount:.4g}，额外减少净利润" if trig else ""),
    ))

    # 规则二：营运资金冻结——收入降幅>25% → DSO+20 天/DIO+30 天（:343）
    trig = rev_chg < _SO_FREEZE_REVENUE_DROP
    cost = base_result.revenue - base_result.gross_profit  # 变动后成本
    amount = (
        base_result.revenue / 365 * _SO_DSO_EXTRA_DAYS + cost / 365 * _SO_DIO_EXTRA_DAYS
        if trig else 0.0
    )
    effects.append(SecondOrderEffect(
        "营运资金冻结", trig, "cfo", amount,
        f"触发条件：收入降幅>25%（实际 {rev_chg:.4g}%）→ {'触发，' if trig else '未触发；'}"
        + (f"额外占用 = 变动后收入 {base_result.revenue:.4g}/365×20 + "
           f"变动后成本 {cost:.4g}/365×30 = {amount:.4g}" if trig else ""),
    ))

    # 规则三：融资成本二阶上升（D3：50-100bp 取保守端 +50bp；Severe 恒触发，:344）
    extra_bp_interest, _ = _stress_interest(fin, _SO_FUNDING_EXTRA_BP)
    amount = extra_bp_interest - fin.interest_expense
    effects.append(SecondOrderEffect(
        "融资成本二阶", True, "interest", amount,
        f"Severe 场景假设评级下调 1-2 档，融资成本在一阶基础上再上浮 50bp"
        f"（D3：文档区间 50-100bp 取保守端）；额外利息 = {amount:.4g}"
        f"（口径同一阶：{'加点/基准融资利率' if fin.base_funding_rate else 'E.3 字面 ×(1+加点)，基准利率缺失'}）",
    ))

    # 中间状态（应用规则 1-3 后），供规则四/五判定
    net_mid = base_result.net_profit - effects[0].amount
    cfo_mid = base_result.cfo - effects[0].amount - effects[1].amount
    fcf_mid = cfo_mid - fin.capex
    runway_mid = fin.cash / (-fcf_mid / 12) if fcf_mid < 0 else _RUNWAY_POSITIVE_FCF

    # 规则四：Capex 削减——FCF<0 且现金跑道<12 个月 → 削减 50%（:345）
    trig = fcf_mid < 0 and runway_mid < _SO_CAPEX_RUNWAY_FLOOR
    amount = fin.capex * _SO_CAPEX_CUT_RATE if trig else 0.0
    effects.append(SecondOrderEffect(
        "Capex削减", trig, "capex", amount,
        f"触发条件：FCF<0 且现金跑道<12 个月（中间 FCF {fcf_mid:.4g}、跑道 "
        f"{runway_mid:.4g} 月）→ {'触发，' if trig else '未触发；'}"
        + (f"削减非必要 Capex 50%：{fin.capex:.4g} × 50% = {amount:.4g}" if trig else ""),
    ))

    # 规则五：资产减值-净资产侵蚀注记——持续亏损>2 年（:346，文本注记无金额）
    trig = net_mid < 0
    effects.append(SecondOrderEffect(
        "资产减值注记", trig, "note", 0.0,
        f"触发条件：持续亏损>2 年（引擎无历史盈亏输入，按场景净利 {net_mid:.4g}"
        f"{'<0 触发提示性注记' if trig else '≥0 未触发'}；持续年限需结合历史数据"
        "确认）→ 净资产缩水→资产负债率上升→触发补充抵押要求或交叉违约条款风险",
    ))
    return effects


# ---------------- E.5 安全边际判定 ----------------

def _band_for(value: float, bands: list, metric: str) -> dict:
    """E.5 阈值匹配：(lo, hi, lo_open, hi_open)，None = 该侧无界。

    区间语义直译文档：">X"/"<X" 开区间（端点不归属本档），"X-Y" 闭区间
    （端点归属本档）——故恰 3.0x 落 🟡 而非 🟢，恰 1.0x 落 🟠 而非 🔴。
    """
    for band in bands:
        lo, hi, lo_open, hi_open = band[metric]
        if lo is not None and (value < lo or (lo_open and value == lo)):
            continue
        if hi is not None and (value > hi or (hi_open and value == hi)):
            continue
        return band
    raise ValueError(f"E.5 四档未覆盖指标值 {value}（{metric}）")


def safety_verdict(bear_result: ScenarioResult, tables: StressTables) -> dict:
    """E.5 三指标四档判定（:294-299）+ 综合档（取最差）。

    阈值运行时解析自 tables.safety_bands（不硬编码副本）。
    """
    matched = []
    verdict = {}
    for metric in _SAFETY_METRICS:
        value = getattr(bear_result, metric)
        band = _band_for(value, tables.safety_bands, metric)
        matched.append(band)
        verdict[metric] = {
            "value": value,
            "emoji": band["emoji"],
            "name": band["name"],
        }
    worst = max(matched, key=lambda b: _BAND_SEVERITY[b["emoji"]])
    verdict["overall"] = {"emoji": worst["emoji"], "name": worst["name"]}
    return verdict


def tail_risk_flag(severe_result: ScenarioResult, tables: StressTables) -> bool:
    """E.5 补充判定（:301）：Severe 任一指标落入🔴区间 → True。

    True 时调用方应输出 TAIL_RISK_WARNING 文本（标记于综合评级输出，
    不自动降级——Severe 场景不是基准判断）。
    """
    return any(
        _band_for(getattr(severe_result, m), tables.safety_bands, m)["emoji"] == "🔴"
        for m in _SAFETY_METRICS
    )


# ---------------- E.6 逆向压力测试 ----------------

def reverse_stress(fin: IssuerFinancials, params: dict) -> dict:
    """E.6 三临界值（:303-334）：解 变动后EBITDA/变动后利息 = 1.0x。

    其他参数取 Bear 档（params 传入 Bear 参数行）。EBITDA 口径与 E.3/E.9
    一致（变动后毛利 - 期间费用 + D&A）——E.6 正文内联公式（变动后收入 =
    利息/毛利率、临界毛利率 = 利息/收入 + 费用率）未扣 D&A，与其自身 E.3
    EBITDA 定义不一致，引擎采用 E.3 口径（注记留痕）。

    临界融资成本升幅 x = 变动后EBITDA/基准利息 - 1（利息 × (1+x) = EBITDA
    的代数解）。bp 换算随利息口径分支（Fix R2）：提供基准融资利率时输出
    加点口径 x × base_funding_rate × 10000（E.9 语义——加点/基准利率 =
    相对放大 x）；缺失时 x × 10000（与 E.3 字面回退口径一致）。
    Bear 档毛利率 ≤0 或变动后收入 ≤0 时对应临界值无意义 → None + 注记。
    """
    funding_bp = _param(params, "funding_cost_change_bp")
    interest_b, rate_note = _stress_interest(fin, funding_bp)
    margin_b = fin.gross_margin + _param(params, "margin_change_pp") / 100
    revenue_b = fin.revenue * (1 + _param(params, "revenue_change") / 100)
    notes = []

    if margin_b > 0:
        revenue_crit = (interest_b + fin.period_expenses - fin.da) / margin_b
        drop_pct = (fin.revenue - revenue_crit) / fin.revenue * 100
    else:
        drop_pct = None
        notes.append(f"Bear 档毛利率 {margin_b:.4g}≤0，收入端无解（增收不增 EBITDA）")
    if revenue_b > 0:
        margin_crit = (interest_b + fin.period_expenses - fin.da) / revenue_b
        compression_pp = (fin.gross_margin - margin_crit) * 100
    else:
        compression_pp = None
        notes.append(f"Bear 档变动后收入 {revenue_b:.4g}≤0，毛利率临界值无意义")
    ebitda_b = revenue_b * margin_b - fin.period_expenses + fin.da
    rise = ebitda_b / fin.interest_expense - 1
    # Fix R2：bp 换算随利息口径分支——E.9 加点口径下达成相对放大 rise 所需
    # 加点 = rise × 基准融资利率；字面回退口径下 = rise × 10000。
    if fin.base_funding_rate:
        rise_bp = rise * fin.base_funding_rate * 10000
        bp_note = (
            f"临界加点 {rise_bp:.4g}bp = x × 基准融资利率 {fin.base_funding_rate:.4g}"
            " × 10000（E.9 加点口径）"
        )
    else:
        rise_bp = rise * 10000
        bp_note = "临界升幅 bp = x × 10000（E.3 字面回退口径）"
    return {
        "critical_revenue_drop_pct": drop_pct,
        "critical_margin_compression_pp": compression_pp,
        "critical_funding_cost_rise": rise,
        "critical_funding_cost_rise_bp": rise_bp,
        "note": (
            "E.6 逆向压力测试：解 变动后EBITDA/变动后利息=1.0x，其他参数取 Bear 档"
            f"（变动后利息 {interest_b:.4g}、Bear 收入 {revenue_b:.4g}、Bear 毛利率 "
            f"{margin_b:.4g}、Bear EBITDA {ebitda_b:.4g}）；EBITDA 口径同 E.3/E.9"
            "（毛利-期间费用+D&A），非 E.6 正文未扣 D&A 的简化内联公式"
            f"；{bp_note}"
            + ("；" + rate_note if rate_note else "")
            + ("；" + "；".join(notes) if notes else "")
        ),
    }


# ================= T3：§九 压力传导（concentration-framework.md §9） =================

_DIM_SCORERS = {
    "industry": industry_score,
    "region": region_score,
    "rating": rating_score,
    "maturity": maturity_score,
    "channel": channel_score,
}

_LEVEL_SEVERITY = {"green": 0, "yellow": 1, "orange": 2, "red": 3}

# §9.2 五情景操作化映射（:777-783；硬编码 + 运行时 parity 锚点——anchor 片段
# 须出现在运行时解析的规则原文中，文档规则文本变更即 raise 失锚，防陈旧硬编码
# 静默生效）：
# - 市场恐慌：「每个维度的阈值上移一个等级」——操作化为档位上移一级（不重算
#   阈值，🔴封顶；综合分按次档代表分即档位下界重算，见 _shift_score_up）。
# - 城投展期潮/评级泡沫破裂/市场窗口冻结：按表格给出的新阈值经
#   concentration_scorer 阈值注入扩展重算对应维度。
# - 传染链路激活：「MAX1阈值从20%收紧至15%」——§2.2.4 MAX1 正常档上限 25%、
#   超级传染者例外下调至 20%（:152）、§2.3 调整表 ≤20%（:158-172），故
#   「MAX1阈值」= 关注档下界（占比上限），操作化为 25%→15%（40%/60% 档界文档
#   未提及，保持不变）；「集群A总敞口上限设为25%」无对应组合指标，无法机械
#   映射，注记留 LLM 判断并以规则原文透传。
_JUMP_OPS = {
    "市场恐慌(VIX>30)": {
        "anchor": "上移一个等级",
        "mode": "shift",
        "overrides": {},
        "note": "§9.2：每个维度的阈值上移一个等级——操作化为档位上移一级"
                "（不重算阈值，🔴封顶；综合分按次档代表分重算）",
    },
    "区域性城投展期潮": {
        "anchor": "收紧至5%/15%/25%",
        "mode": "override",
        "overrides": {"region": {"weak_region_share": (0.05, 0.15, 0.25)}},
        "note": "§9.2：弱区域占比阈值 10%/20%/35% → 5%/15%/25%（D₂区域重算）",
    },
    "评级泡沫破裂": {
        "anchor": "收紧至3%/10%/20%",
        "mode": "override",
        "overrides": {"rating": {"pseudo_high_rating_share": (0.03, 0.10, 0.20)}},
        "note": "§9.2：伪高评级阈值 5%/15%/30% → 3%/10%/20%（D₃评级重算）",
    },
    "市场窗口冻结": {
        "anchor": "收紧至20%/40%/60%",
        "mode": "override",
        "overrides": {
            "maturity": {"maturity_12m_share": (0.20, 0.40, 0.60)},
            "channel": {"top_channel_share": (0.50, 0.50, 0.90)},
        },
        "note": "§9.2：12个月内到期阈值 30%/50%/70% → 20%/40%/60%（D₄期限重算）；"
                "「债券渠道>50%即触发警示」→ D₅渠道警示下界收紧至 50%（关注档退化为"
                "空；引擎档位边界为 >= 闭区间，与文档其他阈值口径一致）",
    },
    "传染矩阵高传染链路激活": {
        "anchor": "收紧至15%",
        "mode": "override",
        "overrides": {"industry": {"max1": (0.15, 0.40, 0.60)}},
        "note": "§9.2：超级传染者行业 MAX1 阈值（§2.2.4 例外下调至 20% 的占比上限）"
                "收紧至 15% → max1 关注档下界 25%→15%（40%/60% 档界文档未提及，保持"
                "不变）；「集群A总敞口上限设为25%」无对应组合指标，无法机械映射，"
                "留 LLM 判断",
    },
}


def _shift_score_up(score: int) -> int:
    """市场恐慌操作化：档位上移一级 → 次档代表分（次档下界）；🔴封顶不变。

    绿(1-3)→4（黄下界）、黄(4-5)→6（橙下界）、橙(6-7)→8（红下界）、红(8-10)
    →保持原分（clamp）。
    """
    if score >= 8:
        return score
    if score >= 6:
        return 8
    if score >= 4:
        return 6
    return 4


def concentration_stress(
    metrics: ConcentrationMetrics, scenario: str, tables: StressTables
) -> dict:
    """§9.1 五维压力传导：§9.2 跳升映射 → 重算五维档位与综合分 → 跳档诊断
    + 三重集中标记。

    scenario 须为 §9.2 阈值跳升表登记的情景名（运行时解析自
    tables.threshold_jumps）；操作化映射（_JUMP_OPS）以 anchor 片段对规则原文
    做运行时 parity 校验，文档规则文本变更即 raise。输出：
    {scenario, normal_levels, stressed_levels, jumps: [{dim, from, to}],
     composite_normal, composite_stressed, triple_concentration, notes}；
    三重集中 = 压力后 ≥3 维度 🟠/🔴（orange/red）。jumps 仅记录恶化跳档
    （档位文字为 concentration_scorer 口径 green/yellow/orange/red）。
    """
    if scenario not in tables.threshold_jumps:
        raise ValueError(
            f"§9.2 阈值跳升表未登记压力场景: {scenario!r}"
            f"（已登记：{sorted(tables.threshold_jumps)}）"
        )
    rule_text = tables.threshold_jumps[scenario]["rule"]
    op = _JUMP_OPS.get(scenario)
    if op is None:
        raise ValueError(f"§9.2 情景「{scenario}」无操作化映射（_JUMP_OPS 未覆盖）")
    if op["anchor"] not in rule_text:
        raise ValueError(
            f"§9.2「{scenario}」规则原文不含锚点片段 {op['anchor']!r}，"
            "操作化映射失锚（文档规则文本已变更，需重新裁决映射）"
        )

    normal_scores = {dim: fn(metrics) for dim, fn in _DIM_SCORERS.items()}
    normal_levels = {dim: _risk_level(s) for dim, s in normal_scores.items()}
    composite_normal = concentration_risk_score(metrics)

    if op["mode"] == "shift":
        stressed_scores = {
            dim: _shift_score_up(s) for dim, s in normal_scores.items()
        }
        composite_stressed = sum(
            s * w for s, w in zip(stressed_scores.values(), DEFAULT_WEIGHTS)
        )
    else:
        stressed_scores = {
            dim: fn(metrics, op["overrides"].get(dim))
            for dim, fn in _DIM_SCORERS.items()
        }
        composite_stressed = concentration_risk_score(
            metrics, thresholds_override=op["overrides"]
        )
    stressed_levels = {dim: _risk_level(s) for dim, s in stressed_scores.items()}

    jumps = [
        {"dim": dim, "from": normal_levels[dim], "to": stressed_levels[dim]}
        for dim in _DIM_SCORERS
        if _LEVEL_SEVERITY[stressed_levels[dim]] > _LEVEL_SEVERITY[normal_levels[dim]]
    ]
    triple = (
        sum(1 for lvl in stressed_levels.values() if lvl in ("orange", "red")) >= 3
    )
    return {
        "scenario": scenario,
        "normal_levels": normal_levels,
        "stressed_levels": stressed_levels,
        "jumps": jumps,
        "composite_normal": composite_normal,
        "composite_stressed": composite_stressed,
        "triple_concentration": triple,
        "notes": [op["note"], f"§9.2 规则原文透传：{rule_text}"],
    }


# ================= T3：E.10 债券市值维度（bond_mv_stress） =================

# D4 裁决（E.10.2 :506 原文）：加权总影响输出时固定附注。
D4_INDEPENDENCE_NOTE = "独立假设可能低估总影响，误差约10-20%"


def bond_mv_stress(
    years: float,
    ytm: float,
    tables: StressTables,
    custom_shocks: dict | None = None,
) -> dict:
    """E.10 债券市值压力：D_approx = 待偿年数/(1+YTM)；ΔP ≈ -D × ΔYTM
    （:481-485，简化版——固定利率、无含权、非零息）。

    四档标准情景（E.10.2 :510-515，运行时解析自 tables.mv_scenarios）的
    ΔYTM = 无风险利率 + 信用利差合计，逐档 ΔP 与概率加权；加权总影响
    Σ(ΔP_i × S_i)（E.10.2 情景加权法，概率为各情景独立历史概率，非归一）
    附 D4 独立假设注记。custom_shocks：{名称: ΔYTM(bp) 数值}（纯信息，
    不并入加权）或 {名称: {"delta_ytm_bp": bp, "probability_pct": 概率%}}
    （并入加权）。输出：{d_approx, scenarios: [{name, delta_ytm, delta_p,
    probability, weighted, rating, liquidity}], custom_scenarios: [...],
    weighted_total, note}；金额口径为小数比率（-0.029 = -2.9%）。
    """
    if years <= 0:
        raise ValueError(f"待偿年数须为正: {years!r}")
    if ytm <= -1:
        raise ValueError(f"YTM 须大于 -100%: {ytm!r}")
    d_approx = years / (1 + ytm)

    def _scenario(name, delta_ytm, probability, rating=None, liquidity=None):
        delta_p = -d_approx * delta_ytm
        weighted = delta_p * probability if probability is not None else None
        entry = {
            "name": name,
            "delta_ytm": delta_ytm,
            "delta_p": delta_p,
            "probability": probability,
            "weighted": weighted,
        }
        if rating is not None:
            entry["rating"] = rating
            entry["liquidity"] = liquidity
        return entry

    scenarios = []
    weighted_total = 0.0
    for s in tables.mv_scenarios:
        probability = s["probability_pct"] / 100
        entry = _scenario(
            s["name"],
            (s["risk_free_bp"] + s["spread_bp"]) / 10000,
            probability,
            rating=s["rating"],
            liquidity=s["liquidity"],
        )
        weighted_total += entry["weighted"]
        scenarios.append(entry)

    custom = []
    for name, shock in (custom_shocks or {}).items():
        if isinstance(shock, dict):
            if "delta_ytm_bp" not in shock:
                raise ValueError(f"自定义冲击「{name}」缺 delta_ytm_bp: {shock!r}")
            bp = shock["delta_ytm_bp"]
            prob_pct = shock.get("probability_pct")
        else:
            bp = shock
            prob_pct = None
        probability = prob_pct / 100 if prob_pct is not None else None
        entry = _scenario(name, bp / 10000, probability)
        if entry["weighted"] is not None:
            weighted_total += entry["weighted"]
        custom.append(entry)

    note = (
        f"E.10 近似久期 D_approx = 待偿年数/(1+YTM) = {years:.4g}/(1+{ytm:.4g}) "
        f"= {d_approx:.4f}；ΔP ≈ -D×ΔYTM 为线性近似，不含凸性修正（利率变化越"
        "大误差越大），含权债不适用（E.10.1 局限标注）；概率加权总影响 "
        f"{weighted_total:.4%}——{D4_INDEPENDENCE_NOTE}（D4，E.10.2 原文）"
    )
    if custom:
        note += "；含自定义冲击（无概率的纯信息冲击不并入加权）"
    return {
        "d_approx": d_approx,
        "scenarios": scenarios,
        "custom_scenarios": custom,
        "weighted_total": weighted_total,
        "note": note,
    }

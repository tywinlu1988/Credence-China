"""WP-M0-02 → lgd-recovery-framework.md 的 LGD 引擎（T1 解析层 + T2 五路 Δ 分量 + T3 顶层合成）。

单一事实源：§2.1 LGD 五级定义表、§5.1 中国信用债品种优先级表、§7.2 担保类型
表、§8.2 行业 Δ 表、§11.4 统计不确定区间表均运行时解析，解析失败即 raise（不
裸复制数值副本）。硬编码项（SENIORITY_BASE / DELTA_RANGES / pd_lgd_bounds /
§6.1.3 股权质押树 / §6.1.4 房地产系数 / §9.4 情景表 / §10.2 逃废债块 / §10.3
区域列表）以文档文本为锚点，由 tests/test_lgd_scorer.py 的 parity 测试回读文档
校验防漂移。

区间取值纪律（全引擎统一）：文档模糊区间取**保守端 = 绝对值最小端**（最小干预
原则），并在 note 注明"留 LLM 判断"；覆盖外输入返回 0 + 低置信注记。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir
from src.rating_map import CANONICAL_RATING_INTERVALS  # 18 档单源，不复制

_DOC_NAME = "lgd-recovery-framework.md"

# §3.2 公式块 "Base_LGD 基准值（仅考虑优先级）" 四档（parity 锚定：
# tests/test_lgd_scorer.py 回读 "无担保优先级债券：Base_LGD = 60%" 等文本锚点）。
SENIORITY_BASE = {"有担保优先": 45.0, "无担保优先": 60.0, "次级": 75.0, "劣后": 90.0}

# §3.2 公式块 "调整项（Δ）" 五因子范围（单位 pp；parity 锚定 "-25pp 至 +10pp" 等）。
DELTA_RANGES = {
    "collateral": (-25.0, 10.0),
    "guarantee": (-15.0, 5.0),
    "industry": (-5.0, 10.0),
    "recovery_path": (-5.0, 10.0),
    "legal": (-5.0, 10.0),
}

# §2.2 PD 评级 → LGD 可达区间约束（硬编码 + parity；档位前缀按 18 档单源归桶）。
#   AAA-AA → 上限 LGD4；A-BBB → 无约束；BB-B → 下限 LGD2；CCC-D → 下限 LGD3。
#   前缀归桶依据：如 "B-" 经 startswith("B") 落 BB-B 桶——§2.2 表 "BB - B" 行覆盖 B-。
_PD_LGD_BUCKETS = (
    (("AAA", "AA"), (None, "LGD4")),
    (("A", "BBB"), (None, None)),
    (("BB", "B"), ("LGD2", None)),
    (("CCC", "D"), ("LGD3", None)),
)

_KNOWN_RATINGS = {r for _, _, r in CANONICAL_RATING_INTERVALS}

# §5.1 品种先验表当前 11 行；下界校验防"行首加粗丢失 → 正则静默丢行"
# （解析失败即 raise 纪律要求丢失可观测，而非容忍稀疏结果）。
_BOND_PRIOR_MIN_ROWS = 8

# §7.2 担保类型表 / §8.2 行业 Δ 表当前各 8 行（同为加粗行首，同纪律设下界）。
_GUARANTEE_MIN_ROWS = 8
_INDUSTRY_MIN_ROWS = 8


@dataclass(frozen=True)
class LgdTables:
    """lgd-recovery-framework.md 五张可解析表的运行时解析结果。

    levels:           §2.1 五级表 → ((name, loss_low, loss_high, rec_low, rec_high), ...)
                      5 行，单位 %；开区间端点（<20% / >80%）以 0/100 闭合。
    bond_priors:      §5.1 品种先验 → {品种: (LGD 下限, LGD 上限)}（单档区间两端相同）。
    ci_ranges:        §11.4 CI 表 → {LGD 等级: (中国调整后回收率低, 高)}（单位 %）。
    guarantee_deltas: §7.2 担保类型 → {担保类型: (Δ 首端, Δ 次端)}（单位 pp；
                      单值区间两端相同；区间原样保留，保守端由 delta_guarantee 取）。
    industry_deltas:  §8.2 行业 Δ → {行业: (Δ 首端, Δ 次端)}（单位 pp，同上限）。
    """

    levels: tuple
    bond_priors: dict
    ci_ranges: dict
    guarantee_deltas: dict
    industry_deltas: dict


def clamp(v: float, lo: float, hi: float) -> float:
    """把 v 截断到 [lo, hi]。"""
    return max(lo, min(hi, v))


def pd_lgd_bounds(rating: str) -> tuple:
    """§2.2：PD 评级 → (LGD 下限, LGD 上限)（None = 该侧无约束）。"""
    r = rating.strip().upper()
    if r not in _KNOWN_RATINGS:
        raise ValueError(f"未知评级 {rating!r}（不在 18 档单源内）")
    for prefixes, bounds in _PD_LGD_BUCKETS:
        if any(r.startswith(p) for p in prefixes):
            return bounds
    raise ValueError(f"评级 {rating!r} 未落入 §2.2 任何约束桶")  # 防御：单源扩档时暴露


def _read(path) -> str:
    p = Path(path) if path else engine_dir() / _DOC_NAME
    return p.read_text(encoding="utf-8")


def _section(text: str, num: str) -> str:
    """按节号切片。``^### `` 行首锁防正文提及误锚；``(?!\\d)`` 节号边界防
    ``### 2.10`` 之类的前缀误锚（锚点须为独立小节标题行）。"""
    sec = re.search(
        rf"^### {re.escape(num)}(?!\d)\s.*?(?=\n### |\n## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if not sec:
        raise ValueError(f"§{num} 段落缺失")
    return sec.group(0)


def _parse_levels(text: str) -> tuple:
    """§2.1 → ((name, loss_low, loss_high, rec_low, rec_high), ...)（5 行，%）。"""
    sec = _section(text, "2.1")
    rows = []
    for m in re.finditer(
        r"^\|\s*(LGD\d)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", sec, re.MULTILINE
    ):
        name, loss, rec = m.group(1), m.group(2), m.group(3)
        rows.append((name, *_parse_pct_range(loss), *_parse_pct_range(rec)))
    names = [r[0] for r in rows]
    if names != [f"LGD{i}" for i in range(1, 6)]:
        raise ValueError(f"§2.1 应有 LGD1-LGD5 顺序 5 行，实际 {names}")
    return tuple(rows)


def _parse_pct_range(cell: str) -> tuple:
    """"20% - 40%" → (20.0, 40.0)；"<20%" → (0.0, 20.0)；">80%" → (80.0, 100.0)。"""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)%\s*-\s*(\d+(?:\.\d+)?)%", cell)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.fullmatch(r"<(\d+(?:\.\d+)?)%", cell)
    if m:
        return 0.0, float(m.group(1))
    m = re.fullmatch(r">(\d+(?:\.\d+)?)%", cell)
    if m:
        return float(m.group(1)), 100.0
    raise ValueError(f"§2.1 百分比区间单元格无法解析: {cell!r}")


def _parse_bond_priors(text: str) -> dict:
    """§5.1 → {品种: (LGD 下限, LGD 上限)}（单档区间如 "LGD5" 两端相同）。"""
    sec = _section(text, "5.1")
    priors = {}
    for m in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|[^|]*\|\s*(LGD\d)(?:\s*-\s*(LGD\d))?\s*\|",
        sec, re.MULTILINE,
    ):
        lo, hi = m.group(2), m.group(3) or m.group(2)
        priors[m.group(1).strip()] = (lo, hi)
    if len(priors) < _BOND_PRIOR_MIN_ROWS:
        raise ValueError(
            f"§5.1 品种先验表至少应有 {_BOND_PRIOR_MIN_ROWS} 行，实际 {len(priors)}"
            "（疑似加粗标记丢失致静默丢行）"
        )
    return priors


def _parse_ci_ranges(text: str) -> dict:
    """§11.4 → {LGD 等级: (中国调整后回收率低, 高)}（第 4 列 "65% - 98%（…）"）。"""
    sec = _section(text, "11.4")
    ranges = {}
    for m in re.finditer(
        r"^\|\s*(LGD\d)\s*\|\s*\d+%\s*\|\s*\d+%\s*-\s*\d+%\s*\|"
        r"\s*(\d+(?:\.\d+)?)%\s*-\s*(\d+(?:\.\d+)?)%",
        sec, re.MULTILINE,
    ):
        ranges[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    if sorted(ranges) != [f"LGD{i}" for i in range(1, 6)]:
        raise ValueError(f"§11.4 应有 LGD1-LGD5 共 5 行，实际 {sorted(ranges)}")
    return ranges


def _parse_delta_pp(text: str, pattern: str, section: str, min_rows: int) -> dict:
    """加粗行首 + "Xpp [to Ypp]" Δ 单元格的通用解析 → {键: (首端, 次端)}（pp）。

    区间原样保留（不取端点），行数低于 min_rows 即 raise（同 §5.1 下界纪律）。
    """
    rows = {}
    for m in re.finditer(pattern, text, re.MULTILINE):
        first = float(m.group(2))
        second = float(m.group(3)) if m.group(3) is not None else first
        rows[m.group(1).strip()] = (first, second)
    if len(rows) < min_rows:
        raise ValueError(
            f"{section} 至少应有 {min_rows} 行，实际 {len(rows)}"
            "（疑似加粗标记丢失致静默丢行）"
        )
    return rows


def _parse_guarantee_deltas(text: str) -> dict:
    """§7.2 → {担保类型: (Δ 首端, Δ 次端)}；单元格形如 "Δ=-10pp to -15pp"。"""
    sec = _section(text, "7.2")
    return _parse_delta_pp(
        sec,
        r"^\|\s*\*\*(.+?)\*\*\s*\|[^|]*\|\s*Δ=\s*([+-]?\d+(?:\.\d+)?)pp"
        r"(?:\s*to\s*([+-]?\d+(?:\.\d+)?)pp)?\s*\|",
        "§7.2 担保类型表",
        _GUARANTEE_MIN_ROWS,
    )


def _parse_industry_deltas(text: str) -> dict:
    """§8.2 → {行业: (Δ 首端, Δ 次端)}；单元格形如 "+5pp to +10pp"。"""
    sec = _section(text, "8.2")
    return _parse_delta_pp(
        sec,
        r"^\|\s*\*\*(.+?)\*\*\s*\|\s*([+-]?\d+(?:\.\d+)?)pp"
        r"(?:\s*to\s*([+-]?\d+(?:\.\d+)?)pp)?\s*\|",
        "§8.2 行业 Δ 表",
        _INDUSTRY_MIN_ROWS,
    )


def load_lgd_tables(path=None) -> LgdTables:
    """运行时解析 §2.1/§5.1/§7.2/§8.2/§11.4 五张表；任何一张解析失败即 raise。"""
    text = _read(path)
    return LgdTables(
        levels=_parse_levels(text),
        bond_priors=_parse_bond_priors(text),
        ci_ranges=_parse_ci_ranges(text),
        guarantee_deltas=_parse_guarantee_deltas(text),
        industry_deltas=_parse_industry_deltas(text),
    )


# ================= T2：五路 Δ 分量 =================


@dataclass(frozen=True)
class DeltaItem:
    """单路 Δ 分量结果。value 单位 pp（负值 = 降低 LGD）。"""

    name: str
    value: float
    confidence: str  # 高（规则精确）/ 中（区间取保守端）/ 低（覆盖外或缺输入）
    note: str = ""


@dataclass(frozen=True)
class CollateralInput:
    """Δ_Collateral 输入。kind 分派：

    cash_or_treasury / equity_pledge / real_estate / receivables / equipment / none。
    比率类字段均为百分数（45.0 表示 45%）。
    """

    kind: str
    # equity_pledge（§6.1.3）
    pledge_ratio: float = None            # 质押率 = 质押贷款金额 / 质押股权市值
    volatility_30d: float = None          # 30 日年化波动率
    turnover_rate: float = None           # 日均换手率
    maintenance_ratio: float = None       # 维持担保比例 = 质押股权市值 / 贷款余额
    concentration: float = None           # 质押股数 / 总股本
    pledgor_is_controlling: bool = False  # 质押方为控股股东
    pledgor_in_legal_dispute: bool = False
    # real_estate（§6.1.4）
    ltv: float = None                     # 抵押率
    city_tier: str = None                 # 一线 / 二线 / 三线及以下
    # receivables / equipment（§6.1.5/§6.1.6，LLM 落档值）
    manual_delta: float = None


@dataclass(frozen=True)
class GuaranteeInput:
    """Δ_Guarantee 输入。guarantee_type 为 §7.2 八类键或 "无"；

    relation ∈ {无关联, 母担子, 子担母, 互保, 实控人担保}（§7.3）。
    """

    guarantee_type: str
    relation: str = "无关联"
    executability_confirmed: bool = False  # 实控人担保：可识别且可执行的独立核心资产已确认


@dataclass(frozen=True)
class EvasionFlags:
    """§10.2 逃废债四触发（可叠加）。"""

    local_soe_in_prior_evidence_province: bool = False  # 地方国企且所在省份此前有逃废债案例
    major_asset_disposal_6m: bool = False               # 违约前 6 个月内大额资产处置/分红
    controller_detained_or_absconded: bool = False      # 实控人被采取强制措施或境外失联
    systemic_related_party_transfer: bool = False       # 系统性关联交易和资产转移嫌疑


def _conservative_end(rng: tuple) -> float:
    """文档模糊区间取保守端 = 绝对值最小端（最小干预原则）。"""
    lo, hi = rng
    return lo if abs(lo) <= abs(hi) else hi


# ---------------- Δ_Collateral ----------------

_COLLATERAL_KINDS = (
    "cash_or_treasury",
    "equity_pledge",
    "real_estate",
    "receivables",
    "equipment",
    "none",
)

# §6.1.4 法拍折扣系数（硬编码；parity 锚 "其中法拍折扣系数：一线0.75, 二线0.65,
# 三线及以下0.55"，见 tests/test_lgd_scorer.py::test_real_estate_parity）。
_REAL_ESTATE_COEFF = {"一线": 0.75, "二线": 0.65, "三线及以下": 0.55}
_REAL_ESTATE_TIER_ALIAS = {"三线": "三线及以下", "三线以下": "三线及以下"}


def _delta_equity_pledge(c: CollateralInput) -> DeltaItem:
    """§6.1.3 股权质押决策树（硬编码 + parity 锚 :272-280 代码块，按序首条命中）。"""
    p, v, t = c.pledge_ratio, c.volatility_30d, c.turnover_rate
    m, k = c.maintenance_ratio, c.concentration
    if p is not None and v is not None and t is not None and p < 50 and v < 30 and t > 1:
        val, branch = -20.0, "质押率<50% 且波动率<30% 且换手率>1%"
    elif p is not None and v is not None and 50 <= p <= 60 and v < 40:
        val, branch = -15.0, "质押率50-60% 且波动率<40%"
    elif p is not None and v is not None and 60 < p <= 70 and v < 50:
        val, branch = -10.0, "质押率60-70% 且波动率<50%"
    elif p is not None and m is not None and 70 < p <= 80 and m > 150:
        val, branch = -5.0, "质押率70-80% 且维持担保比例>150%"
    elif (p is not None and p > 80) or (m is not None and m < 130):
        val, branch = 0.0, "质押率>80% 或维持担保比例<130%"
    elif (k is not None and k > 50) or (c.pledgor_is_controlling and c.pledgor_in_legal_dispute):
        val, branch = 5.0, "集中度>50% 或质押方为控股股东且法律纠纷中"
    else:
        return DeltaItem(
            "Δ_Collateral", 0.0, "低",
            "§6.1.3 决策树未命中任何分支（输入缺失或落在树未覆盖分支），取 0 留 LLM 判断",
        )
    lo, hi = DELTA_RANGES["collateral"]
    return DeltaItem(
        "Δ_Collateral", clamp(val, lo, hi), "中",
        f"§6.1.3 股权质押树命中「{branch}」（文档注明为经验基准而非回归结果）",
    )


def _delta_real_estate(c: CollateralInput) -> DeltaItem:
    """§6.1.4 公式 LTV%×系数−60% + D2 映射（pp = round(计算值×2/3, 5 的倍数））。

    D2 为已批准设计裁决，三算例吻合：-21→-15 / -16→-10 / -10.5→-5。
    """
    if c.ltv is None:
        return DeltaItem(
            "Δ_Collateral", 0.0, "低",
            "§6.1.4 缺抵押率 LTV 输入，取 0 留 LLM 判断",
        )
    tier = _REAL_ESTATE_TIER_ALIAS.get(c.city_tier, c.city_tier)
    tier_note = ""
    if tier not in _REAL_ESTATE_COEFF:
        coeff = _REAL_ESTATE_COEFF["三线及以下"]
        tier_note = f"未知城市能级 {c.city_tier!r}，按三线及以下保守系数 0.55 处理；"
    else:
        coeff = _REAL_ESTATE_COEFF[tier]
    raw = c.ltv * coeff - 60.0
    pp = float(round(raw * 2.0 / 3.0 / 5.0) * 5)
    lo, hi = DELTA_RANGES["collateral"]
    return DeltaItem(
        "Δ_Collateral", clamp(pp, lo, hi), "中",
        f"§6.1.4 {tier_note}公式 {c.ltv}%×{coeff}-60%={raw:.4g}%，"
        f"D2 映射 ×2/3 取 5pp 档 → {pp:.4g}pp",
    )


def _delta_manual_collateral(c: CollateralInput, lo: float, hi: float, label: str) -> DeltaItem:
    """§6.1.5/§6.1.6：取 LLM 落档值 manual_delta 并 clamp 到文档区间。"""
    if c.manual_delta is None:
        return DeltaItem(
            "Δ_Collateral", 0.0, "低",
            f"{label} 缺 LLM 落档值（manual_delta），取 0 留 LLM 判断",
        )
    val = clamp(c.manual_delta, lo, hi)
    clamp_note = "" if val == c.manual_delta else f"（原值 {c.manual_delta} 已 clamp 至 [{lo},{hi}]）"
    return DeltaItem(
        "Δ_Collateral", val, "中",
        f"{label} 采用 LLM 落档值{clamp_note}",
    )


def delta_collateral(c: CollateralInput) -> DeltaItem:
    """Δ_Collateral：按 kind 分派五类抵押物规则。"""
    if c.kind == "none":
        return DeltaItem("Δ_Collateral", 0.0, "高", "无抵押")
    if c.kind == "cash_or_treasury":
        # §6.1.1-6.1.2 "Δ_Collateral = -20pp to -25pp" 取保守端（绝对值最小端 -20）
        return DeltaItem(
            "Δ_Collateral", -20.0, "中",
            "§6.1.1-6.1.2 现金/国债质押区间 -20~-25pp 取保守端 -20，具体落点留 LLM 判断",
        )
    if c.kind == "equity_pledge":
        return _delta_equity_pledge(c)
    if c.kind == "real_estate":
        return _delta_real_estate(c)
    if c.kind == "receivables":
        return _delta_manual_collateral(c, -5.0, 5.0, "§6.1.5 应收账款质押")
    if c.kind == "equipment":
        return _delta_manual_collateral(c, -5.0, 10.0, "§6.1.6 机器设备抵押")
    raise ValueError(
        f"未知抵押物 kind {c.kind!r}（允许值：{_COLLATERAL_KINDS}）"
    )


# ---------------- Δ_Guarantee ----------------

def delta_guarantee(g: GuaranteeInput, tables: LgdTables = None) -> DeltaItem:
    """Δ_Guarantee：§7.2 表运行时解析 + §7.3 关联规则。"""
    if g.guarantee_type in ("无", "none", ""):
        return DeltaItem("Δ_Guarantee", 0.0, "高", "无担保")
    tables = tables if tables is not None else load_lgd_tables()
    rng = tables.guarantee_deltas.get(g.guarantee_type)
    if rng is None:
        return DeltaItem(
            "Δ_Guarantee", 0.0, "低",
            f"§7.2 未覆盖担保类型 {g.guarantee_type!r}，取 0 留 LLM 判断",
        )
    base = _conservative_end(rng)
    if rng[0] != rng[1]:
        note = (f"§7.2「{g.guarantee_type}」区间 {rng[0]:.4g}~{rng[1]:.4g}pp "
                f"取保守端 {base:.4g}pp，具体落点留 LLM 判断")
    else:
        note = f"§7.2「{g.guarantee_type}」Δ={base:.4g}pp（区间取保守端原则，留 LLM 判断）"
    val = base
    # §7.3 关联担保特殊风险（方向性指引，文档注明高度主观）
    if g.relation == "母担子":
        val = base / 2.0
        note += "；§7.3 母担子关联担保，LGD 调整减半"
    elif g.relation == "子担母":
        val = 0.0
        note += "；§7.3 子担母合并口径下增信虚置，LGD 调整不适用"
    elif g.relation == "互保":
        val = base / 2.0
        note += "；§7.3 兄弟公司互保，LGD 调整减半"
    elif g.relation == "实控人担保":
        if g.executability_confirmed:
            note += "；§7.3 实控人担保已确认可执行独立核心资产，保留调整"
        else:
            val = 0.0
            note += "；§7.3 实控人担保未确认可执行独立核心资产，取 0"
    lo, hi = DELTA_RANGES["guarantee"]
    return DeltaItem("Δ_Guarantee", clamp(val, lo, hi), "中", note)


# ---------------- Δ_Industry ----------------

def delta_industry(industry_key: str, tables: LgdTables = None) -> DeltaItem:
    """Δ_Industry：§8.2 表运行时解析（八行业；区间取保守端）。"""
    tables = tables if tables is not None else load_lgd_tables()
    rng = tables.industry_deltas.get(industry_key)
    if rng is None:
        return DeltaItem(
            "Δ_Industry", 0.0, "低",
            f"§8.2 未覆盖行业 {industry_key!r}，取 0 留 LLM 判断",
        )
    val = _conservative_end(rng)
    if rng[0] != rng[1]:
        note = (f"§8.2「{industry_key}」区间 {rng[0]:.4g}~{rng[1]:.4g}pp "
                f"取保守端 {val:.4g}pp，具体落点留 LLM 判断（框架设定值非实证回归）")
    else:
        note = f"§8.2「{industry_key}」Δ={val:.4g}pp（框架设定值非实证回归，留 LLM 判断）"
    lo, hi = DELTA_RANGES["industry"]
    return DeltaItem("Δ_Industry", clamp(val, lo, hi), "中", note)


# ---------------- Δ_RecoveryPath ----------------

# §9.4 四情景枚举（硬编码 + parity 锚，见 test_recovery_path_parity）。
# "清算" 区间 +5~+10 取保守端 +5。
_RECOVERY_PATH_DELTA = {
    "重整-资产尚可": -5.0,
    "重整-空心化": 0.0,
    "清算": 5.0,
    "庭外-谈判强": 5.0,
}


def delta_recovery_path(scenario: str) -> DeltaItem:
    """Δ_RecoveryPath：§9.4 四情景枚举。"""
    if scenario in _RECOVERY_PATH_DELTA:
        val = _RECOVERY_PATH_DELTA[scenario]
        lo, hi = DELTA_RANGES["recovery_path"]
        return DeltaItem(
            "Δ_RecoveryPath", clamp(val, lo, hi), "中",
            f"§9.4 情景「{scenario}」（区间取值均取保守端，留 LLM 判断）",
        )
    return DeltaItem(
        "Δ_RecoveryPath", 0.0, "低",
        f"§9.4 未覆盖情景 {scenario!r}，取 0 留 LLM 判断",
    )


# ---------------- Δ_Legal（§10.3 区域 + §10.2 逃废债） ----------------

# §10.3 Δ_Legal 区域列表（硬编码 + parity 锚，见 test_legal_region_parity）。
# 注意：§10.3 表中"河南/河北/山西"同行的山西未列入 Δ 名单 → 归"其他"取 0 并注记。
_LEGAL_REGION_MINUS5 = ("北京", "上海", "广东", "江苏", "浙江")
_LEGAL_REGION_PLUS5 = ("辽宁", "吉林", "黑龙江", "河南", "河北")
# "西部省份（甘肃/青海/新疆等）"收窄为五省区（主会话裁决：司法效率较低、破产
# 实践稀少口径；避免把破产法庭实践较活跃的四川/陕西/重庆等拖入 +5pp——重庆在
# §10.3 散文表中列"中等"）；区间 +5~+10 取保守端 +5。
_LEGAL_REGION_WEST = ("甘肃", "青海", "新疆", "宁夏", "西藏")
# 西部边界省份归"其他"取 0，note 注明留 LLM 判断（同上裁决）。
_LEGAL_REGION_WEST_BOUNDARY = ("陕西", "四川", "重庆", "云南", "贵州", "广西", "内蒙古")

# §10.2 逃废债 if 块（硬编码 + parity 锚 :522-529，见 test_evasion_block_parity；
# 四触发可叠加）。
_EVASION_DELTAS = (
    ("local_soe_in_prior_evidence_province", 5.0, "地方国企且所在省份此前有逃废债案例"),
    ("major_asset_disposal_6m", 5.0, "违约前6个月内仍有大额资产处置/分红"),
    ("controller_detained_or_absconded", 10.0, "实际控制人已被采取强制措施或境外失联"),
    ("systemic_related_party_transfer", 10.0, "存在系统性关联交易和资产转移嫌疑"),
)

_PROVINCE_SUFFIXES = ("维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "省", "市")


def _normalize_province(province: str) -> str:
    """"辽宁省"/"上海市"/"内蒙古自治区" → "辽宁"/"上海"/"内蒙古"。"""
    p = province.strip()
    for suf in _PROVINCE_SUFFIXES:
        if p.endswith(suf):
            p = p[: -len(suf)]
            break
    return {"内蒙": "内蒙古"}.get(p, p)


def _legal_region(province: str) -> tuple:
    """§10.3 区域映射 → (Δ, 注记)。"""
    p = _normalize_province(province)
    if p in _LEGAL_REGION_MINUS5:
        return -5.0, f"§10.3 区域 {p}（司法效率较高档）-5pp"
    if p in _LEGAL_REGION_PLUS5:
        return 5.0, f"§10.3 区域 {p}（推进缓慢/担保执行不确定档）+5pp"
    if p in _LEGAL_REGION_WEST:
        return 5.0, f"§10.3 西部省份 {p} 区间 +5~+10pp 取保守端 +5，留 LLM 判断"
    if p in _LEGAL_REGION_WEST_BOUNDARY:
        return 0.0, f"§10.3 西部边界省份 {p} 归「其他」档取 0（西部名单收窄裁决），留 LLM 判断"
    if p == "山西":
        return 0.0, "山西在 §10.3 Δ 列表中未列名（表中「河南/河北/山西」行的 Δ 仅列河南/河北），取 0 留 LLM 判断"
    return 0.0, f"§10.3 区域 {p} 归「其他」档取 0"


def delta_legal(province: str, evasion: EvasionFlags) -> DeltaItem:
    """Δ_Legal：§10.3 区域映射 + §10.2 逃废债加成（可叠加，clamp 到 legal 区间）。"""
    region_val, region_note = _legal_region(province)
    evasion_val = 0.0
    triggers = []
    for field_name, delta, label in _EVASION_DELTAS:
        if getattr(evasion, field_name):
            evasion_val += delta
            triggers.append(f"{label} +{delta:.4g}pp")
    raw = region_val + evasion_val
    lo, hi = DELTA_RANGES["legal"]
    val = clamp(raw, lo, hi)
    note = region_note
    if triggers:
        note += "；§10.2 逃废债触发：" + "、".join(triggers)
        note += "（定性判断指标组合，仅作风险提示）"
    if val != raw:
        note += f"；合计 {raw:.4g}pp 已 clamp 至 legal 区间 [{lo:.4g},{hi:.4g}]"
    # 终审 M-1 口径：文档明列的「其他：0pp」档属文档内档位 → "中"置信（非数据
    # 缺口）；"低"置信仅留给带"留 LLM 判断"注记的分支（山西 / 西部边界七省区）。
    llm_defer = region_val == 0.0 and "留 LLM 判断" in region_note
    confidence = "低" if (llm_defer and not triggers) else "中"
    return DeltaItem("Δ_Legal", val, confidence, note)


# ================= T3：compute_lgd 顶层合成 =================


@dataclass(frozen=True)
class LgdResult:
    """compute_lgd 输出（对应 §13.1 单一债券 LGD 评估输出模板）。

    lgd_pct:        合成损失率 %（Base + ΣΔ 后 clamp [0,100]；D6 加法式）。
                    §2.2 PD 约束只钳制等级、不回改本值——合成原值保留可见。
    lgd_level:      五级等级（§2.1 运行时 levels 左闭右开映射 + §2.2 PD 约束钳制后）。
    recovery_range: 该等级预期回收率区间 (低, 高) %（§2.1 levels）。
    breakdown:      (Base_LGD, 五路 Δ[, PD约束钳制]) DeltaItem 审计链。
    ci_range:       §11.4 中国调整后回收率范围 (低, 高) %。
    prior_check:    {"expected_range": (LGD低, LGD高)|None,
                     "within_prior": bool|None}（§5.1 品种先验交叉；
                     品种未覆盖时两端均 None）。
    data_gaps:      真未覆盖缺口清单（"name: note"，note 含「未覆盖」的 Δ 分量，
                    对应 §13.1「数据缺口与不确定性」；低置信但属文档内档位/
                    留 LLM 判断分支的分量不入列）。
    out_of_scope:   框架覆盖外输入清单（note 标「未覆盖」的 Δ 分量 +
                    §5.1 未收录债券品种）。
    """

    lgd_pct: float
    lgd_level: str
    recovery_range: tuple
    breakdown: tuple
    ci_range: tuple
    prior_check: dict
    data_gaps: tuple
    out_of_scope: tuple


def _level_num(level: str) -> int:
    """"LGD3" → 3。"""
    return int(level[-1])


def _level_for_pct(pct: float, levels: tuple) -> str:
    """§2.1 损失率区间映射，左闭右开（40% → LGD3）；右端 100% 闭合落 LGD5。"""
    for name, loss_low, loss_high, _, _ in levels:
        if loss_low <= pct < loss_high:
            return name
    return levels[-1][0]


def compute_lgd(
    seniority: str,
    collateral: CollateralInput,
    guarantee: GuaranteeInput,
    industry_key: str,
    recovery_scenario: str,
    province: str,
    evasion: EvasionFlags,
    pd_rating: str,
    bond_type: str,
    tables: LgdTables = None,
) -> LgdResult:
    """顶层合成：Base + ΣΔ（D6 加法式）→ clamp [0,100] → 五级映射
    → §2.2 PD 约束钳制等级 → §11.4 CI / §5.1 先验交叉 / 缺口清单装配。"""
    tables = tables if tables is not None else load_lgd_tables()
    if seniority not in SENIORITY_BASE:
        raise ValueError(
            f"未知优先级 {seniority!r}（允许值：{tuple(SENIORITY_BASE)}）"
        )
    base = SENIORITY_BASE[seniority]
    items = [
        DeltaItem(
            "Base_LGD", base, "高",
            f"§3.2「{seniority}」基准（基于全球基准，未经中国市场历史数据校准）",
        ),
        delta_collateral(collateral),
        delta_guarantee(guarantee, tables),
        delta_industry(industry_key, tables),
        delta_recovery_path(recovery_scenario),
        delta_legal(province, evasion),
    ]
    pct = clamp(base + sum(i.value for i in items[1:]), 0.0, 100.0)
    level = _level_for_pct(pct, tables.levels)
    # §2.2 PD 约束：只钳制等级，不回改 lgd_pct（合成原值保留可见，钳制留痕）
    lo_b, hi_b = pd_lgd_bounds(pd_rating)
    n = _level_num(level)
    clamped = int(clamp(
        n,
        _level_num(lo_b) if lo_b else 1,
        _level_num(hi_b) if hi_b else 5,
    ))
    if clamped != n:
        side, bound = ("下限", lo_b) if clamped > n else ("上限", hi_b)
        new_level = f"LGD{clamped}"
        items.append(DeltaItem(
            "PD约束钳制", 0.0, "高",
            f"§2.2 PD 评级 {pd_rating.strip().upper()} {side} {bound}："
            f"合成等级 {level} 已钳制至 {new_level}"
            f"（lgd_pct 保留合成原值 {pct:.4g}%）",
        ))
        level = new_level
    row = next(r for r in tables.levels if r[0] == level)
    # §5.1 品种先验交叉
    prior = tables.bond_priors.get(bond_type)
    if prior is None:
        prior_check = {"expected_range": None, "within_prior": None}
    else:
        prior_check = {
            "expected_range": prior,
            "within_prior": _level_num(prior[0]) <= _level_num(level) <= _level_num(prior[1]),
        }
    # 缺口 / 覆盖外清单（PD约束钳制项置信度恒为高、note 无「未覆盖」，天然不入列）
    # data_gaps 收窄口径：仅收 note 含「未覆盖」的真缺口；低置信但属文档内档位
    # 或留 LLM 判断分支（如缺 LTV 输入、山西/西部边界省份）不再入列。
    data_gaps = []
    out_of_scope = []
    for it in items[1:]:
        entry = f"{it.name}: {it.note}"
        if "未覆盖" in it.note:
            data_gaps.append(entry)
            if it.confidence == "低":
                out_of_scope.append(entry)
    if prior is None:
        out_of_scope.append(
            f"§5.1 品种先验表未覆盖债券品种 {bond_type!r}，先验交叉不可用"
        )
    return LgdResult(
        lgd_pct=pct,
        lgd_level=level,
        recovery_range=(row[3], row[4]),
        breakdown=tuple(items),
        ci_range=tables.ci_ranges[level],
        prior_check=prior_check,
        data_gaps=tuple(data_gaps),
        out_of_scope=tuple(out_of_scope),
    )

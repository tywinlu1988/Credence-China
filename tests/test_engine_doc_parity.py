"""双源对账桥 — coded scorers ↔ normative engine docs parity (v0.7.8).

The engine docs are the NORMATIVE source; ``src/sri_calculator.py`` and
``src/concentration_scorer.py`` are their EXECUTABLE implementations. These tests assert
the two stay consistent: for each documented value/concept, (a) the doc text actually
states it (grep-able anchor), AND (b) the code behaves accordingly. Anchors target the
specific tokens the docs use (Chinese numerals/ranges included), not brittle full-prose
parsing, so a legitimate doc rephrase that keeps the value still passes while a real
threshold drift fails.
"""

import re
from pathlib import Path

from src.concentration_scorer import (
    ConcentrationMetrics,
    concentration_risk_score,
    rating_adjustment,
)
from src.external_support_scorer import (
    SupportInput,
    compute_support,
    load_support_tables,
)
from src.lgd_scorer import (
    CollateralInput,
    EvasionFlags,
    GuaranteeInput,
    compute_lgd,
    delta_guarantee,
    load_lgd_tables,
)
from src.sri_calculator import (
    IndustryInput,
    Outlook,
    TrackBLevel,
    industry_risk_score,
    thermometer_level,
)

ROOT = Path(__file__).resolve().parent.parent
SRI_DOC = (ROOT / "dev" / "engine" / "systemic-warning-framework.md").read_text(
    encoding="utf-8"
)
CONC_DOC = (ROOT / "dev" / "engine" / "concentration-framework.md").read_text(
    encoding="utf-8"
)
LGD_DOC = (ROOT / "dev" / "engine" / "lgd-recovery-framework.md").read_text(
    encoding="utf-8"
)
SUPPORT_DOC = (ROOT / "dev" / "engine" / "external-support-framework.md").read_text(
    encoding="utf-8"
)


def _section(doc: str, heading: str) -> str:
    """Slice one `### <heading>` section up to the next same-or-higher heading."""
    m = re.search(rf"^#+\s*{re.escape(heading)}.*?$", doc, re.MULTILINE)
    assert m, f"doc missing section heading {heading!r}"
    rest = doc[m.end():]
    nxt = re.search(r"^#{1,3}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _green(score=7.0):
    return IndustryInput("g", score, TrackBLevel.GREEN, Outlook.STABLE)


def _all_green_metrics():
    return ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )


# --------------------------------------------------------------------------
# SRI thermometer bands (systemic-warning-framework §三)
# --------------------------------------------------------------------------

def test_doc_states_thermometer_band_edges():
    """§3.1 四级定义 states the 0.5 / 1.0 / 1.8 band edges."""
    for token in ("SRI < 0.5", "0.5 ≤ SRI < 1.0", "1.0 ≤ SRI < 1.8", "SRI ≥ 1.8"):
        assert token in SRI_DOC, f"doc missing thermometer band edge {token!r}"


def test_code_thermometer_boundaries_match_doc():
    """thermometer_level honours the documented band edges."""
    assert thermometer_level(0.49) == "normal"
    assert thermometer_level(0.5) == "watch"
    assert thermometer_level(1.0) == "alert"
    assert thermometer_level(1.8) == "danger"


# --------------------------------------------------------------------------
# SRI Track-A base + Track-B penalties (systemic-warning-framework §2.2)
# --------------------------------------------------------------------------

def test_doc_states_track_a_base_and_track_b_penalties():
    """§2.2 states the Track-A base bands and the red/orange/yellow penalty magnitudes."""
    # Track-A base: worst band (<3.0) → 3分, best band (≥6.0) → 0分
    assert "轨道A评分 < 3.0" in SRI_DOC
    assert re.search(r"→\s+3分", SRI_DOC), "doc missing Track-A worst-band '→ 3分'"
    # Track-B penalty magnitudes by colour (yellow/orange/red)
    for token in ("+0.5分", "+1.0分", "+1.5分"):
        assert token in SRI_DOC, f"doc missing Track-B penalty {token!r}"
    for colour in ("🟡", "🟠", "🔴"):
        assert colour in SRI_DOC


def test_code_track_b_penalty_ordering_matches_doc():
    """industry_risk_score penalises RED > ORANGE > YELLOW > GREEN, per the doc concept."""
    base = dict(track_a_score=7.0, outlook=Outlook.STABLE)
    green = industry_risk_score(IndustryInput("i", track_b_level=TrackBLevel.GREEN, **base))
    yellow = industry_risk_score(IndustryInput("i", track_b_level=TrackBLevel.YELLOW, **base))
    orange = industry_risk_score(IndustryInput("i", track_b_level=TrackBLevel.ORANGE, **base))
    red = industry_risk_score(IndustryInput("i", track_b_level=TrackBLevel.RED, **base))
    assert red > orange > yellow > green
    # exact documented magnitudes: green 0, yellow 0.5, orange 1.0, red 1.5
    assert (green, yellow, orange, red) == (0.0, 0.5, 1.0, 1.5)


def test_code_track_a_base_matches_doc():
    """Track-A base: <3.0 → 3分; ≥6.0 (green/stable) → 0分."""
    assert industry_risk_score(_green(score=2.0)) == 3.0  # CCC/B band → base 3
    assert industry_risk_score(_green(score=7.0)) == 0.0  # A-and-above band → base 0


# --------------------------------------------------------------------------
# Concentration §8.2 five-dim weights
# --------------------------------------------------------------------------

def test_doc_states_five_dim_weights():
    """§8.2 states industry 25 / region 20 / rating 20 / maturity 20 / channel 15.

    Pinned to the §8.2 section (each dimension label on the same table row as its
    weight) — not the whole doc, since the same percentages recur in the §8.4
    dynamic-adjustment baseline row.
    """
    sec = _section(CONC_DOC, "8.2")
    for dim, weight in (
        ("行业集中度", "25%"),
        ("区域集中度", "20%"),
        ("评级集中度", "20%"),
        ("期限集中度", "20%"),
        ("融资渠道集中度", "15%"),
    ):
        assert any(
            dim in line and weight in line for line in sec.splitlines()
        ), f"§8.2 missing row for {dim} = {weight}"


def test_code_default_weights_match_doc():
    """concentration_risk_score's default weights equal the documented (0.25,0.20,0.20,0.20,0.15)."""
    metrics = _all_green_metrics()
    default = concentration_risk_score(metrics)
    explicit = concentration_risk_score(metrics, weights=(0.25, 0.20, 0.20, 0.20, 0.15))
    assert default == explicit


# --------------------------------------------------------------------------
# Concentration §7.2 non-linear stacking + §7.3 BB-cap
# --------------------------------------------------------------------------

def test_doc_states_stacking_and_bb_cap():
    """§7.2 states the non-linear stacking values; §7.3 states the BB-cap trigger."""
    assert "非线性" in CONC_DOC
    for token in ("-0.5", "-2.5", "上限BB"):
        assert token in CONC_DOC, f"doc missing stacking/BB-cap token {token!r}"


def test_code_stacking_all_green_is_zero():
    """Canonical all-green case → adjustment 0.0 and no BB-cap (§7.2 baseline)."""
    adj = rating_adjustment(_all_green_metrics())
    assert adj["adjustment"] == 0.0
    assert adj["bb_cap_triggered"] is False


def test_code_stacking_two_reds_is_minus_2_5():
    """Documented multi-red case (2维🔴) → adjustment -2.5 (§7.2); BB-cap not yet tripped."""
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,          # industry red via HHI
        single_province_share=0.50, weak_region_share=0.02,  # region red via province
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert sum(1 for lvl in adj["levels"].values() if lvl == "red") == 2
    assert adj["adjustment"] == -2.5
    assert adj["bb_cap_triggered"] is False


def test_code_bb_cap_triggers_on_documented_condition():
    """§7.3: ≥3 red dimensions triggers the 组合极端集中上限 (BB-cap)."""
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,
        single_province_share=0.50, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.35,   # third red (rating)
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert sum(1 for lvl in adj["levels"].values() if lvl == "red") == 3
    assert adj["bb_cap_triggered"] is True


# --------------------------------------------------------------------------
# SRI linked escalation parity (systemic-warning-framework §十四 × §6.2)
# --------------------------------------------------------------------------

def test_sri_linked_escalation_parity():
    """升级因子触发 → contagion_coefficients 变化 → portfolio_sri 重算 — 链路通畅。"""
    from src.contagion_engine import (
        load_matrix,
        contagion_coefficients as cc,
        apply_escalation,
    )
    from src.sri_calculator import portfolio_sri, IndustryInput, TrackBLevel, Outlook

    matrix = load_matrix()
    # 选取 3 个真实行业做最小验证（名称与传染矩阵一致）
    inds = [
        IndustryInput(
            "光伏/储能", 5.0, TrackBLevel.YELLOW, Outlook.STABLE,
        ),
        IndustryInput(
            "半导体/集成电路", 7.5, TrackBLevel.GREEN, Outlook.STABLE,
        ),
        IndustryInput(
            "城投债 / LGFV", 3.0, TrackBLevel.RED, Outlook.NEGATIVE,
        ),
    ]
    holdings = {"光伏/储能": 0.3, "半导体/集成电路": 0.2, "城投债 / LGFV": 0.5}

    # 从全 13 行业系数中提取子集（linked_sri 需要全行业传递，此处手动拆链验证）
    all_coeffs = cc(matrix)
    coeffs = {k: all_coeffs[k] for k in holdings}

    # 施加升级因子 → 系数应变化
    stressed_matrix = apply_escalation(matrix, ["信息不对称"])
    stressed_all = cc(stressed_matrix)
    stressed_coeffs = {k: stressed_all[k] for k in holdings}
    assert coeffs != stressed_coeffs, "升级因子未改变传染力系数"

    # 分别计算基准 SRI 与压力 SRI
    base = portfolio_sri(holdings, inds, coeffs)
    stressed = portfolio_sri(holdings, inds, stressed_coeffs)
    delta = round(stressed["sri"] - base["sri"], 4)

    assert "sri" in base and "sri" in stressed
    assert "thermometer" in base and "thermometer" in stressed
    assert isinstance(delta, float)


# --------------------------------------------------------------------------
# WP-M0-02 dual engines: LGD (lgd-recovery-framework) + external support
# (external-support-framework) — doc-text anchors + code-behaviour parity
# --------------------------------------------------------------------------

_SUPPORT_ALL_STRONG = {  # §4.1 全 3 分 → capacity 3.0（强档）
    "一般公共预算收入": 4000, "财政自给率": 85, "政府显性债务率": 70,
    "GDP增速": 7, "人口趋势": "持续净流入", "转移支付依赖度": 15,
}


def _support_input(**kw):
    base = dict(
        support_type="政府支持",
        indicators=_SUPPORT_ALL_STRONG,
        willingness_signals={"战略地位": "强"},
        signal_level="L5",
        standalone_rating="AA",
        supporter_is_central_gov=True,
    )
    base.update(kw)
    return SupportInput(**base)


def test_doc_states_lgd_seniority_base():
    """lgd §3.2 公式块 states the four seniority Base_LGD values."""
    sec = _section(LGD_DOC, "3.2")
    for token in ("Base_LGD = 45%", "Base_LGD = 60%", "Base_LGD = 75%", "Base_LGD = 90%"):
        assert token in sec, f"§3.2 missing Base_LGD anchor {token!r}"


def test_code_lgd_seniority_base_matches_doc():
    """compute_lgd with all Δ neutral yields exactly the documented Base_LGD."""
    for seniority, base in (
        ("有担保优先", 45.0), ("无担保优先", 60.0), ("次级", 75.0), ("劣后", 90.0),
    ):
        r = compute_lgd(
            seniority,
            CollateralInput(kind="none"),
            GuaranteeInput(guarantee_type="无"),
            "高端装备",        # §8.2 0pp 行业（覆盖内、Δ=0）
            "重整-空心化",     # §9.4 Δ=0 情景
            "湖北",            # §10.3「其他」档 Δ=0
            EvasionFlags(),
            "A",               # §2.2 A-BBB 无约束桶
            "中期票据（MTN）",
        )
        assert r.lgd_pct == base
        assert r.breakdown[0].name == "Base_LGD" and r.breakdown[0].value == base


def test_doc_states_guarantee_table():
    """lgd §7.2 担保类型表 states 中债增 Δ=-15pp and 专业担保 Δ=-10pp to -15pp."""
    sec = _section(LGD_DOC, "7.2")
    assert "中债信用增进公司" in sec and "Δ=-15pp" in sec
    assert "中投保/中证增等专业担保" in sec and "Δ=-10pp to -15pp" in sec


def test_code_guarantee_deltas_match_doc():
    """§7.2 parsed deltas and delta_guarantee behaviour honour the documented values."""
    tables = load_lgd_tables()
    assert tables.guarantee_deltas["中债信用增进公司"] == (-15.0, -15.0)
    assert tables.guarantee_deltas["中投保/中证增等专业担保"] == (-10.0, -15.0)
    item = delta_guarantee(GuaranteeInput(guarantee_type="中债信用增进公司"), tables)
    assert item.value == -15.0


def test_doc_states_strength_matrix():
    """support §6.1 states the 3×3 支持强度判定矩阵 (意愿 × 能力)."""
    sec = _section(SUPPORT_DOC, "6.1")
    assert "支持意愿 ↓ 支持能力 →" in sec
    assert "非常高" in sec


def test_code_strength_matrix_matches_doc():
    """§6.1 matrix: 意愿高 × 能力强 → 非常高 (table and compute_support agree)."""
    tables = load_support_tables()
    assert tables.strength_matrix["高"]["强"] == "非常高"
    assert tables.strength_matrix["低"]["弱"] == "低/无"
    r = compute_support(_support_input())
    assert r.capacity_band == "强" and r.willingness_band == "高"
    assert r.strength == "非常高"


def test_doc_states_uplift_map():
    """support §6.2 states the 上调幅度映射 (+2~3子级 / +1~2子级 / 0)."""
    sec = _section(SUPPORT_DOC, "6.2")
    for token in ("+2~3子级", "+1~2子级"):
        assert token in sec, f"§6.2 missing uplift anchor {token!r}"


def test_code_uplift_map_matches_doc():
    """§6.2 uplift ranges parsed correctly; 非常高 × 意愿高 takes the range upper end."""
    tables = load_support_tables()
    assert tables.uplift_map["非常高"] == (2, 3)
    assert tables.uplift_map["高"] == (1, 2)
    assert tables.uplift_map["低/无"] == (0, 0)
    # standalone 取 A+ 避开 AAA 梯顶截断（终审 I-1 后 uplift_notches 为实际变动）
    r = compute_support(_support_input(standalone_rating="A+"))
    assert r.uplift_notches == 3  # D4：意愿高 → 区间上限

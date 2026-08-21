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
from dataclasses import replace
from pathlib import Path

import pytest

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
from src.esg_scorer import (
    _QUICK_BANDS,
    EsgEvent,
    compute_esg,
    load_esg_tables,
)
from src.governance_scorer import compute_governance
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
from src.stress_scorer import (
    ScenarioResult,
    bond_mv_stress,
    concentration_stress,
    load_stress_tables,
    resolve_severe_params,
    safety_verdict,
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
DD_DOC = (ROOT / "dev" / "engine" / "financial-deep-dive.md").read_text(
    encoding="utf-8"
)
GOV_DOC = (ROOT / "dev" / "engine" / "governance-fraud-risk.md").read_text(
    encoding="utf-8"
)
ESG_DOC = (ROOT / "dev" / "engine" / "esg-framework.md").read_text(
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


# --------------------------------------------------------------------------
# WP-M4-04 stress engine: financial-deep-dive §E + concentration §9.2
# doc-text anchors + code-behaviour parity
# --------------------------------------------------------------------------

def _bear_result(interest_coverage=5.0, fcf_interest=3.0, cash_runway_months=24.0):
    """Minimal ScenarioResult for E.5 band-boundary probes (safety_verdict
    only reads the three safety metrics)."""
    return ScenarioResult(
        scenario="Bear", industry="parity-probe",
        revenue=0, gross_profit=0, ebitda=0, net_profit=0, cfo=0, capex=0,
        fcf=0, interest=0,
        interest_coverage=interest_coverage, fcf_interest=fcf_interest,
        cash_runway_months=cash_runway_months,
    )


# ---- E.1 校准锚（financial-deep-dive :231-239） ----

def test_doc_states_severe_anchor_pv():
    """E.1 校准锚表 states 光伏/储能 收入最大降幅 -35%、毛利率最大压缩 -20pp。"""
    sec = _section(DD_DOC, "E.1 三场景参数设定")
    assert any(
        "光伏/储能" in line and "-35%" in line and "-20pp" in line
        for line in sec.splitlines()
    ), "E.1 校准锚表 missing 光伏/储能 -35%/-20pp row"


def test_code_severe_anchor_pv_matches_doc():
    """resolve_severe_params 命中 E.1 锚：光伏/储能 → -35%/-20pp（不再乘 E.8 因子）。"""
    tables = load_stress_tables()
    assert tables.severe_anchors["光伏/储能"] == {
        "revenue_change": -35.0,
        "margin_change_pp": -20.0,
    }
    p = resolve_severe_params("光伏/储能", tables)
    assert p["source"] == "E.1锚"
    assert p["revenue_change"] == -35.0 and p["margin_change_pp"] == -20.0


# ---- E.8 分行业偏离因子（financial-deep-dive :352-363） ----

def test_doc_states_deviation_factor_nev_supply_chain():
    """E.8 因子表 states 新能源车—供应链 Severe 收入偏离度 1.3x。"""
    sec = _section(DD_DOC, "E.8 场景分行业校准说明")
    assert any(
        "新能源车—供应链" in line and "1.3x" in line for line in sec.splitlines()
    ), "E.8 missing 新能源车—供应链 1.3x row"


def test_code_deviation_factor_matches_doc():
    """E.1 锚未命中 → 默认 Severe × E.8 因子：收入 -30%×1.3=-39%、毛利率 -15pp×1.1。"""
    tables = load_stress_tables()
    assert tables.deviation_factors["新能源车—供应链"]["severe_revenue"] == 1.3
    p = resolve_severe_params("新能源车—供应链", tables)
    assert p["source"] == "E.8因子"
    assert p["revenue_change"] == pytest.approx(-39.0)    # -30 × 1.3
    assert p["margin_change_pp"] == pytest.approx(-16.5)  # -15 × 1.1


# ---- §9.2 阈值跳升表（concentration-framework :777-783） ----

def test_doc_states_threshold_jump_lgfv():
    """§9.2 states 城投展期潮：弱区域占比阈值从 10%/20%/35% 收紧至 5%/15%/25%。"""
    sec = _section(CONC_DOC, "9.2 压力场景下的阈值跳升")
    assert any(
        "区域性城投展期潮" in line and "收紧至5%/15%/25%" in line
        for line in sec.splitlines()
    ), "§9.2 missing 区域性城投展期潮 jump row"


def test_code_threshold_jump_lgfv_matches_doc():
    """弱区域占比 0.18：默认档（10%/20%/35%）为绿；收紧后（5%/15%/25%）跳橙。"""
    tables = load_stress_tables()
    m = replace(_all_green_metrics(), weak_region_share=0.18)
    out = concentration_stress(m, "区域性城投展期潮", tables)
    assert out["jumps"] == [{"dim": "region", "from": "green", "to": "orange"}]
    assert out["composite_normal"] == pytest.approx(2.2)
    assert out["composite_stressed"] == pytest.approx(3.0)


# ---- E.5 安全边际阈值（financial-deep-dive :294-299） ----

def test_doc_states_safety_band_edges():
    """E.5 states the 🟢/🔴 open edges (>3.0x / <1.0x) and the 🟠 closed band 1.0-1.5x."""
    sec = _section(DD_DOC, "E.5 安全边际判定标准")
    for token in (">3.0x", "<1.0x", "1.0-1.5x"):
        assert token in sec, f"E.5 missing band edge {token!r}"


def test_code_safety_band_boundaries_match_doc():
    """开/闭区间直译：恰 3.0x → 🟡（>3.0 开区间不归属🟢）；恰 1.0x → 🟠。"""
    tables = load_stress_tables()
    v = safety_verdict(_bear_result(interest_coverage=3.0), tables)
    assert v["interest_coverage"]["emoji"] == "🟡"
    v = safety_verdict(_bear_result(interest_coverage=1.0), tables)
    assert v["interest_coverage"]["emoji"] == "🟠"


# ---- E.10.2 情景概率（financial-deep-dive :508-517） ----

def test_doc_states_mv_scenario_probabilities():
    """E.10.2 标准情景模板 states 四档历史概率 20%/10%/3%/1%（附 -2.90% 定量示例）。"""
    sec = _section(DD_DOC, "E.10.2")
    for token in ("历史概率约20%", "历史概率约10%", "历史概率约3%", "历史概率约1%"):
        assert token in sec, f"E.10.2 missing probability {token!r}"
    assert "-2.90%" in sec  # 定量估算示例（3年期中票、YTM=3.5%）轻度承压 ΔP


def test_code_mv_probabilities_and_weighting_match_doc():
    """四档概率运行时解析；轻度承压 ΔP≈-2.90%（文档示例复算）；weighted = ΔP×S。"""
    tables = load_stress_tables()
    assert [s["probability_pct"] for s in tables.mv_scenarios] == [20.0, 10.0, 3.0, 1.0]
    out = bond_mv_stress(3.0, 0.035, tables)
    first = out["scenarios"][0]
    assert first["name"] == "轻度承压"
    assert first["delta_ytm"] == pytest.approx(0.01)        # +50bp 无风险 +50bp 利差
    assert first["delta_p"] == pytest.approx(-0.029, abs=1e-3)  # 文档示例 -2.90%
    assert first["weighted"] == pytest.approx(first["delta_p"] * 0.20)


# --------------------------------------------------------------------------
# WP-X-04 dual engines: governance (governance-fraud-risk §6.2/§6.3) +
# ESG (esg-framework §5.1/§5.3) — doc-text anchors + code-behaviour parity
# --------------------------------------------------------------------------

# ---- gov §6.2 评分衔接规则矩阵行（:320-323） ----

def test_doc_states_gov_matrix_rows():
    """gov §6.2 states 关注档 L4 上限 7 + 评级前置减半档；高档 L4 上限 4 + 评级上限 B。"""
    sec = _section(GOV_DOC, "6.2 评分衔接规则")
    assert any(
        "2-3个中强度信号" in line and "L4财务层评分上限从10分降至7分" in line
        for line in sec.splitlines()
    ), "§6.2 missing 关注档矩阵行"
    assert any(
        "L4财务层评分上限锁定为4分" in line and "评级上限锁定为B" in line
        for line in sec.splitlines()
    ), "§6.2 missing 高档矩阵行"


def test_code_gov_matrix_rows_match_doc():
    """2 中强度信号 → 关注档（l4_cap 7 + outlook_flag）；1 高强度 → 高档（l4_cap 4 + cap B）。

    T2 序列化口径：(risk_grade, l4_cap, rating_cap, outlook_flag) 是通用红旗
    计数叠加与 §6.2 矩阵两条并行规则的独立输出——2 中强度信号时 grade 经
    计数叠加（≥2 面升一级）升为「高」，不得以 grade 反查矩阵行。
    """
    r = compute_governance(
        {"q4_revenue_share": 0.45, "impairment": 40, "prior_3y_profit_sum": 100},
        {},
    )
    assert r.l4_cap == 7 and r.rating_cap is None and r.outlook_flag is True
    assert r.risk_grade == "高"          # 计数叠加独立输出，非矩阵行反查
    r1 = compute_governance({"non_recurring_to_net_profit": 0.6}, {})
    assert (r1.risk_grade, r1.l4_cap, r1.rating_cap, r1.outlook_flag) == (
        "高", 4, "B", False,
    )


# ---- gov §6.3 一票否决行（:344-349） ----

def test_doc_states_gov_veto_rows():
    """gov §6.3 states 一票否决 → 综合评级上限锁定为CCC（含立案调查财务造假行）。"""
    sec = _section(GOV_DOC, "6.3 一票否决条件")
    assert "综合评级上限锁定为CCC" in sec
    assert "被证监会/监管机构立案调查且涉及财务造假" in sec


def test_code_gov_veto_matches_doc():
    """事件轨触发 v1 → 严重 + CCC；l4_cap=None 原样直传（不得默认填数值）。"""
    r = compute_governance(
        {}, {"v1_csrc_fraud_investigation": "立案告知书（财务造假）"},
    )
    assert r.veto_triggers == ["v1"]
    assert r.risk_grade == "严重" and r.rating_cap == "CCC"
    assert r.l4_cap is None and r.outlook_flag is False


# ---- esg §5.1 核心映射行（:419-432） ----

def test_doc_states_esg_mapping_row():
    """esg §5.1 states 重大环保处罚（责令停产）→ -0.5~-1子级。"""
    sec = _section(ESG_DOC, "5.1 核心映射关系")
    assert any(
        "重大环保处罚（责令停产）" in line and "-0.5~-1子级" in line
        for line in sec.splitlines()
    ), "§5.1 missing 重大环保处罚映射行"


def test_code_esg_mapping_row_matches_doc():
    """§5.1 运行时解析：env_shutdown 基值区间 (-1.0, -0.5)（数值轴有序）+ 单元格原文留痕。"""
    tables = load_esg_tables()
    row = tables.mapping["env_shutdown"]
    assert (row.lo, row.hi) == (-1.0, -0.5)
    assert "-0.5~-1子级" in row.adjust_text


# ---- esg §5.3 调整规则速查行（:458-464） ----

def test_doc_states_esg_quick_rows():
    """esg §5.3 states 中等信号 -0.5子级 与 强信号 -0.5~-1子级。"""
    sec = _section(ESG_DOC, "5.3 调整规则速查表")
    assert any(
        "中等信号" in line and "-0.5子级" in line for line in sec.splitlines()
    ), "§5.3 missing 中等信号速查行"
    assert any(
        "强信号" in line and "-0.5~-1子级" in line for line in sec.splitlines()
    ), "§5.3 missing 强信号速查行"


def test_code_esg_quick_bands_match_doc():
    """_QUICK_BANDS ↔ §5.3 速查行回读（T3 ⚠️1：强信号带硬编码副本 parity）。

    强信号带为硬编码副本（无运行时解析回读），此处断言速查表强信号行
    adjustment 原文 ↔ _QUICK_BANDS["强信号"] 一致——文档带漂移即测试失败。
    """
    tables = load_esg_tables()
    quick = {r["strength"]: r for r in tables.quick_ref}
    assert quick["中等信号"]["adjustment"] == "-0.5子级"
    assert _QUICK_BANDS["中等信号"] == (-0.5, -0.5)
    assert quick["强信号"]["adjustment"] == "-0.5~-1子级"
    assert _QUICK_BANDS["强信号"] == (-1.0, -0.5)
    # 行为面：单事件 II 级 → 中等信号，累计 -0.5 落于速查带内（无带外 advisory）
    r = compute_esg(
        [EsgEvent(
            dimension="G", category="disclosure_violation", severity="II",
            evidence="纪律处分", source="交易所公告",
        )],
        {"interest_coverage": 1.5, "cash_runway_months": 3},
        "城投",
    )
    assert r.signal_strength == "中等信号"
    assert r.per_dimension["G"]["score"] == -0.5
    assert not any("带外" in n for n in r.notes)

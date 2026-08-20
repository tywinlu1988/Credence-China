import pytest

from src.concentration_scorer import (
    ConcentrationMetrics,
    channel_score,
    concentration_risk_score,
    industry_score,
    maturity_score,
    rating_adjustment,
    rating_score,
    region_score,
)


def test_high_concentration():
    metrics = ConcentrationMetrics(
        hhi=2600,
        cr3=0.85,
        cr5=0.92,
        max1=0.65,
        single_province_share=0.40,
        weak_region_share=0.25,
        aaa_share=0.75,
        pseudo_high_rating_share=0.35,
        maturity_12m_share=0.75,
        single_month_peak=0.35,
        top_channel_share=0.80,
        top_channel_is_contracting=True,
    )
    assert concentration_risk_score(metrics) >= 6.0


def test_low_concentration():
    metrics = ConcentrationMetrics(
        hhi=500,
        cr3=0.30,
        cr5=0.50,
        max1=0.15,
        single_province_share=0.10,
        weak_region_share=0.02,
        aaa_share=0.20,
        pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20,
        single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert concentration_risk_score(metrics) <= 4.0


def test_all_five_dimensions_contribute():
    high = ConcentrationMetrics(
        hhi=2600,
        cr3=0.85,
        cr5=0.92,
        max1=0.65,
        single_province_share=0.50,
        weak_region_share=0.35,
        aaa_share=0.75,
        pseudo_high_rating_share=0.35,
        maturity_12m_share=0.75,
        single_month_peak=0.35,
        top_channel_share=0.80,
        top_channel_is_contracting=True,
    )
    assert industry_score(high) >= 8
    assert region_score(high) >= 8
    assert rating_score(high) >= 8
    assert maturity_score(high) >= 8
    assert channel_score(high) >= 8
    assert concentration_risk_score(high) >= 8.0


def test_channel_contraction_bonus():
    contracting = ConcentrationMetrics(
        hhi=500,
        cr3=0.30,
        cr5=0.50,
        max1=0.15,
        single_province_share=0.10,
        weak_region_share=0.02,
        aaa_share=0.20,
        pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20,
        single_month_peak=0.05,
        top_channel_share=0.60,
        top_channel_is_contracting=True,
    )
    relaxed = ConcentrationMetrics(
        hhi=500,
        cr3=0.30,
        cr5=0.50,
        max1=0.15,
        single_province_share=0.10,
        weak_region_share=0.02,
        aaa_share=0.20,
        pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20,
        single_month_peak=0.05,
        top_channel_share=0.60,
        top_channel_is_contracting=False,
    )
    assert channel_score(contracting) > channel_score(relaxed)


def test_rating_orange_and_danger_bands():
    # 20% pseudo-high-rating is in the documented alert (orange) band.
    orange = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.20,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert rating_score(orange) == 7

    # 75% AAA share is in the documented danger band.
    danger = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.75, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert rating_score(danger) == 9


def test_maturity_orange_band():
    # 60% 12-month maturity is in the documented alert (orange) band.
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.60, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert maturity_score(metrics) == 7


def test_region_danger_band():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.50, weak_region_share=0.35,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert region_score(metrics) == 9


def test_concentration_weights_must_sum_to_one():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    with pytest.raises(ValueError):
        concentration_risk_score(metrics, weights=(0.25, 0.25, 0.25, 0.25, 0.10))


def test_concentration_weights_must_have_length_five():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    with pytest.raises(ValueError):
        concentration_risk_score(metrics, weights=(0.25, 0.25, 0.25, 0.25))


def test_rating_adjustment_all_green():
    low = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(low)
    assert adj["adjustment"] == 0.0
    assert adj["bb_cap_triggered"] is False


def test_rating_adjustment_two_oranges():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.25,
        aaa_share=0.20, pseudo_high_rating_share=0.20,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert adj["levels"]["region"] == "orange"
    assert adj["levels"]["rating"] == "orange"
    assert adj["adjustment"] == -1.0
    assert adj["bb_cap_triggered"] is False


def test_rating_adjustment_one_red_one_orange():
    # Industry red driven by HHI only, avoiding the single-industry proxy.
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.20,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert adj["levels"]["industry"] == "red"
    assert adj["levels"]["rating"] == "orange"
    assert adj["adjustment"] == -1.5
    assert adj["bb_cap_triggered"] is False


def test_rating_adjustment_two_reds():
    # Industry red via HHI; region red via single province (not weak region).
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,
        single_province_share=0.50, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert adj["levels"]["industry"] == "red"
    assert adj["levels"]["region"] == "red"
    assert adj["adjustment"] == -2.5
    assert adj["bb_cap_triggered"] is False


def test_rating_adjustment_three_reds():
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,
        single_province_share=0.50, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.35,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert sum(1 for lvl in adj["levels"].values() if lvl == "red") == 3
    assert adj["bb_cap_triggered"] is True


def test_bb_cap_weak_region_threshold():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.40,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert adj["bb_cap_triggered"] is True


def test_bb_cap_pseudo_high_rating_threshold():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.45,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert adj["bb_cap_triggered"] is True


def test_bb_cap_maturity_channel_overlap():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.75, single_month_peak=0.05,
        top_channel_share=0.75,
    )
    adj = rating_adjustment(metrics)
    assert adj["bb_cap_triggered"] is True


def test_bb_cap_channel_freeze_threshold():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.95, top_channel_is_contracting=True,
    )
    adj = rating_adjustment(metrics)
    assert adj["bb_cap_triggered"] is True


def test_risk_level_boundaries():
    from src.concentration_scorer import _risk_level
    assert _risk_level(2) == "green"
    assert _risk_level(3) == "green"
    assert _risk_level(4) == "yellow"
    assert _risk_level(5) == "yellow"
    assert _risk_level(6) == "orange"
    assert _risk_level(7) == "orange"
    assert _risk_level(8) == "red"
    assert _risk_level(9) == "red"
    assert _risk_level(10) == "red"


def test_rating_adjustment_four_oranges():
    metrics = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.25,
        aaa_share=0.20, pseudo_high_rating_share=0.20,
        maturity_12m_share=0.60, single_month_peak=0.05,
        top_channel_share=0.80,
    )
    adj = rating_adjustment(metrics)
    assert sum(1 for lvl in adj["levels"].values() if lvl == "orange") == 4
    assert adj["adjustment"] == -2.0
    assert adj["bb_cap_triggered"] is False


def test_rating_adjustment_one_red_zero_orange():
    metrics = ConcentrationMetrics(
        hhi=2600, cr3=0.55, cr5=0.65, max1=0.30,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    adj = rating_adjustment(metrics)
    assert sum(1 for lvl in adj["levels"].values() if lvl == "red") == 1
    assert sum(1 for lvl in adj["levels"].values() if lvl == "orange") == 0
    assert adj["adjustment"] == -1.0
    assert adj["bb_cap_triggered"] is False


def test_bb_cap_single_industry_boundary():
    at_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.50,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    below_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.49,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert rating_adjustment(at_cap)["bb_cap_triggered"] is True
    assert rating_adjustment(below_cap)["bb_cap_triggered"] is False


def test_bb_cap_weak_region_boundary():
    at_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.36,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    below_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.34,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert rating_adjustment(at_cap)["bb_cap_triggered"] is True
    assert rating_adjustment(below_cap)["bb_cap_triggered"] is False


def test_bb_cap_pseudo_high_rating_boundary():
    at_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.41,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    below_cap = ConcentrationMetrics(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.39,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    assert rating_adjustment(at_cap)["bb_cap_triggered"] is True
    assert rating_adjustment(below_cap)["bb_cap_triggered"] is False


# ================= WP-M4-04 T3：阈值注入扩展（默认 None=旧行为） =================

def _mid_metrics():
    return ConcentrationMetrics(
        hhi=1200, cr3=0.55, cr5=0.72, max1=0.30,
        single_province_share=0.25, weak_region_share=0.15,
        aaa_share=0.40, pseudo_high_rating_share=0.10,
        maturity_12m_share=0.40, single_month_peak=0.15,
        top_channel_share=0.60,
    )


def test_concentration_risk_score_default_override_parity():
    """thresholds_override 默认 None / 空 dict 时行为与现状完全一致（parity 锚点）。"""
    m = _mid_metrics()
    expected = (
        industry_score(m) * 0.25 + region_score(m) * 0.20 + rating_score(m) * 0.20
        + maturity_score(m) * 0.20 + channel_score(m) * 0.15
    )
    assert concentration_risk_score(m) == pytest.approx(expected)
    assert concentration_risk_score(m, thresholds_override=None) == pytest.approx(expected)
    assert concentration_risk_score(m, thresholds_override={}) == pytest.approx(expected)


def test_concentration_risk_score_thresholds_override_recomputes():
    """注入阈值按新阈值重算档位；未注入维度不受影响。"""
    m = _mid_metrics()  # weak_region_share=0.15
    base = concentration_risk_score(m)
    # 默认 (0.10,0.20,0.35)：0.15 ∈ [0.10,0.20) → 3；收紧 (0.05,0.15,0.25)：≥0.15 → 7
    stressed = concentration_risk_score(
        m, thresholds_override={"region": {"weak_region_share": (0.05, 0.15, 0.25)}}
    )
    assert stressed == pytest.approx(base + (7 - 3) * 0.20)
    assert stressed != base


def test_concentration_risk_score_override_validation():
    """未知维度/未知指标/非升序阈值 → raise（失败可观测纪律）。"""
    m = _mid_metrics()
    with pytest.raises(ValueError):
        concentration_risk_score(m, thresholds_override={"sector": {}})
    with pytest.raises(ValueError):
        concentration_risk_score(m, thresholds_override={"region": {"foo": (0.1, 0.2, 0.3)}})
    with pytest.raises(ValueError):
        concentration_risk_score(
            m, thresholds_override={"region": {"weak_region_share": (0.2, 0.1, 0.3)}}
        )

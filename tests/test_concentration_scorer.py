import pytest

from src.concentration_scorer import (
    ConcentrationMetrics,
    channel_score,
    concentration_risk_score,
    industry_score,
    maturity_score,
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
    with pytest.raises(ValueError):
        concentration_risk_score(metrics, weights=(0.25, 0.25, 0.25, 0.25, 0.10))

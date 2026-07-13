from dataclasses import dataclass


@dataclass
class ConcentrationMetrics:
    """Five-dimensional concentration metrics.

    Note: this dataclass does not currently include an explicit portfolio
    single-industry exposure share.  In ``rating_adjustment`` we proxy that
    exposure with ``max1`` (largest single industry share) per
    dev/engine/concentration-framework.md §7.3.
    """

    hhi: float
    cr3: float
    cr5: float
    max1: float
    single_province_share: float
    weak_region_share: float
    aaa_share: float
    pseudo_high_rating_share: float
    maturity_12m_share: float
    single_month_peak: float
    top_channel_share: float
    top_channel_is_contracting: bool = False


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rating_band(value: float, normal_max: float, watch_max: float, alert_max: float) -> int:
    """Map a share to a representative 1-10 risk score using document-specific bands.

    Bands are the upper bounds of each documented risk level:
      - value < normal_max            → 2 (normal / 1-3)
      - normal_max ≤ value < watch_max → 3 (watch / 4-5)
      - watch_max ≤ value < alert_max  → 7 (alert / 6-7)
      - value ≥ alert_max              → 9 (danger / 8-10)
    """
    if value >= alert_max:
        return 9
    if value >= watch_max:
        return 7
    if value >= normal_max:
        return 3
    return 2


def industry_score(metrics: ConcentrationMetrics) -> int:
    """D1: Industry concentration (HHI/CR3/CR5/MAX1)."""
    if metrics.max1 >= 0.60:
        return 9
    if metrics.cr3 >= 0.80 or metrics.cr5 >= 0.90 or metrics.hhi >= 2500:
        return 8
    if metrics.max1 >= 0.40 or metrics.cr3 >= 0.65 or metrics.cr5 >= 0.80 or metrics.hhi >= 1500:
        return 6
    if metrics.max1 >= 0.25 or metrics.cr3 >= 0.50 or metrics.cr5 >= 0.70 or metrics.hhi >= 1000:
        return 4
    return 2


def region_score(metrics: ConcentrationMetrics) -> int:
    """D2: Regional concentration (single province + weak region share)."""
    province = _rating_band(metrics.single_province_share, 0.20, 0.35, 0.50)
    weak = _rating_band(metrics.weak_region_share, 0.10, 0.20, 0.35)
    return max(province, weak)


def rating_score(metrics: ConcentrationMetrics) -> int:
    """D3: Rating concentration (external AAA + pseudo-high-rating share)."""
    aaa = _rating_band(metrics.aaa_share, 0.30, 0.50, 0.70)
    pseudo = _rating_band(metrics.pseudo_high_rating_share, 0.05, 0.15, 0.30)
    return max(aaa, pseudo)


def maturity_score(metrics: ConcentrationMetrics) -> int:
    """D4: Maturity concentration (12-month share + single-month peak)."""
    m12 = _rating_band(metrics.maturity_12m_share, 0.30, 0.50, 0.70)
    peak = _rating_band(metrics.single_month_peak, 0.10, 0.20, 0.30)
    return max(m12, peak)


def channel_score(metrics: ConcentrationMetrics) -> int:
    """D5: Financing-channel concentration (top channel share + contraction flag)."""
    base = _rating_band(metrics.top_channel_share, 0.50, 0.70, 0.90)
    if metrics.top_channel_is_contracting and base < 9:
        base += 2
    return int(_clamp(base, 2, 10))


def _risk_level(score: int) -> str:
    """Map a 1-10 risk score to a four-level traffic-light classification."""
    if score >= 8:
        return "red"
    if score >= 6:
        return "orange"
    if score >= 4:
        return "yellow"
    return "green"


def rating_adjustment(metrics: ConcentrationMetrics) -> dict:
    """Return rating adjustment in notches and flags per concentration-framework.md §7.

    Implements the non-linear multi-dimensional stacking table in §7.2 and the
    threshold-based BB-cap trigger conditions in §7.3.
    """
    levels = {
        "industry": _risk_level(industry_score(metrics)),
        "region": _risk_level(region_score(metrics)),
        "rating": _risk_level(rating_score(metrics)),
        "maturity": _risk_level(maturity_score(metrics)),
        "channel": _risk_level(channel_score(metrics)),
    }

    red_count = sum(1 for lvl in levels.values() if lvl == "red")
    orange_count = sum(1 for lvl in levels.values() if lvl == "orange")

    # Non-linear stacking lookup per §7.2.
    if red_count == 0:
        if orange_count == 0:
            adjustment = 0.0
        elif orange_count == 1:
            adjustment = -0.5
        elif orange_count == 2:
            adjustment = -1.0
        elif orange_count == 3:
            adjustment = -1.5
        elif orange_count == 4:
            adjustment = -2.0
        else:  # 5 oranges
            adjustment = -2.5
    elif red_count == 1:
        if orange_count == 0:
            adjustment = -1.0
        elif orange_count == 1:
            adjustment = -1.5
        else:
            # Extend linearly beyond the documented 1-red+1-orange case:
            # -0.5 per additional orange, capped at the 2-red value.
            adjustment = max(-2.5, -1.5 - 0.5 * (orange_count - 1))
    elif red_count == 2:
        adjustment = -2.5
    else:  # red_count >= 3
        adjustment = -2.5

    # Threshold-based BB-cap trigger per §7.3.
    # Condition #1 (single industry >50% + downturn + super-spreader) is not
    # directly observable because ConcentrationMetrics lacks an explicit
    # single-industry share.  We proxy single-industry exposure with max1
    # (largest single industry share) per the dataclass note above.
    single_industry_proxy = metrics.max1 >= 0.50

    bb_cap_triggered = (
        red_count >= 3
        or orange_count == 5
        or single_industry_proxy
        # Weak-region cap: the documented condition also requires
        # "该区域内过去12个月有国企违约", which is not available in
        # ConcentrationMetrics.
        or metrics.weak_region_share > 0.35
        or metrics.pseudo_high_rating_share > 0.40
        or (metrics.maturity_12m_share > 0.70 and metrics.top_channel_share > 0.70)
        or (metrics.top_channel_share > 0.90 and metrics.top_channel_is_contracting)
    )

    return {
        "adjustment": adjustment,
        "levels": levels,
        "bb_cap_triggered": bb_cap_triggered,
    }


def concentration_risk_score(
    metrics: ConcentrationMetrics,
    weights: tuple[float, float, float, float, float] = (0.25, 0.20, 0.20, 0.20, 0.15),
) -> float:
    """Five-dimensional weighted concentration risk score (1-10 scale).

    Default weights follow dev/engine/concentration-framework.md §8.2:
    industry 25%, region 20%, rating 20%, maturity 20%, channel 15%.
    """
    if len(weights) != 5:
        raise ValueError("weights must contain exactly 5 values")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("weights must sum to 1.0")

    scores = (
        industry_score(metrics),
        region_score(metrics),
        rating_score(metrics),
        maturity_score(metrics),
        channel_score(metrics),
    )
    return sum(s * w for s, w in zip(scores, weights))

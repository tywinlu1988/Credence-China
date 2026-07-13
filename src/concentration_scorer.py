from dataclasses import dataclass


@dataclass
class ConcentrationMetrics:
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


def concentration_risk_score(
    metrics: ConcentrationMetrics,
    weights: tuple[float, float, float, float, float] = (0.25, 0.20, 0.20, 0.20, 0.15),
) -> float:
    """Five-dimensional weighted concentration risk score (1-10 scale).

    Default weights follow dev/engine/concentration-framework.md §8.2:
    industry 25%, region 20%, rating 20%, maturity 20%, channel 15%.
    """
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

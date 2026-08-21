from dataclasses import dataclass


@dataclass
class ConcentrationMetrics:
    """Five-dimensional concentration metrics.

    Note: this dataclass does not currently include an explicit portfolio
    single-industry exposure share.  In ``rating_adjustment`` we proxy that
    exposure with ``max1`` (largest single industry share) per
    engine/concentration-framework.md §7.3.
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


# 五维加权默认权重（concentration-framework.md §8.2）：
# 行业 25% / 区域 20% / 评级 20% / 期限 20% / 渠道 15%。
DEFAULT_WEIGHTS = (0.25, 0.20, 0.20, 0.20, 0.15)

# 五维默认阈值（硬编码 + 文档出处；WP-M4-04 T3 阈值注入扩展的默认值）。
# 每指标三元组 = (关注下界, 警示下界, 危险下界)，闭区间（>= 归属本档）：
#   value < 关注下界 → 正常档代表分；≥ 关注下界 → 关注；≥ 警示下界 → 警示；
#   ≥ 危险下界 → 危险（D₁ 行业例外：MAX1 越危险界 → 9，其余指标 → 8，见
#   industry_score 原实现，档位语义与 §2.2.4 危险档 8-10 一致）。
DEFAULT_THRESHOLDS = {
    "industry": {
        "max1": (0.25, 0.40, 0.60),        # §2.2.4 MAX1
        "cr3": (0.50, 0.65, 0.80),         # §2.2.2 CR3
        "cr5": (0.70, 0.80, 0.90),         # §2.2.3 CR5
        "hhi": (1000.0, 1500.0, 2500.0),   # §2.2.1 HHI
    },
    "region": {
        "single_province_share": (0.20, 0.35, 0.50),  # §3.3.1 单一省份占比
        "weak_region_share": (0.10, 0.20, 0.35),      # §3.3.2 弱区域合计占比
    },
    "rating": {
        "aaa_share": (0.30, 0.50, 0.70),                # §4.3.1 外部AAA占比
        "pseudo_high_rating_share": (0.05, 0.15, 0.30),  # §4.3.2 伪高评级占比
    },
    "maturity": {
        "maturity_12m_share": (0.30, 0.50, 0.70),  # §5.3.1 未来12个月到期占比
        "single_month_peak": (0.10, 0.20, 0.30),   # §5.3.4 单月到期峰值
    },
    "channel": {
        "top_channel_share": (0.50, 0.70, 0.90),  # §6.2.1 单一渠道占比
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _resolve_thresholds(dim: str, thresholds: dict | None) -> dict:
    """维度阈值解析：None → 该维默认阈值（旧行为零变化）；部分覆盖时与
    该维默认值合并（调用方校验见 concentration_risk_score._merge_thresholds）。"""
    if thresholds is None:
        return DEFAULT_THRESHOLDS[dim]
    return {**DEFAULT_THRESHOLDS[dim], **thresholds}


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


def industry_score(metrics: ConcentrationMetrics, thresholds: dict | None = None) -> int:
    """D1: Industry concentration (HHI/CR3/CR5/MAX1)."""
    t = _resolve_thresholds("industry", thresholds)
    if metrics.max1 >= t["max1"][2]:
        return 9
    if (
        metrics.cr3 >= t["cr3"][2]
        or metrics.cr5 >= t["cr5"][2]
        or metrics.hhi >= t["hhi"][2]
    ):
        return 8
    if (
        metrics.max1 >= t["max1"][1]
        or metrics.cr3 >= t["cr3"][1]
        or metrics.cr5 >= t["cr5"][1]
        or metrics.hhi >= t["hhi"][1]
    ):
        return 6
    if (
        metrics.max1 >= t["max1"][0]
        or metrics.cr3 >= t["cr3"][0]
        or metrics.cr5 >= t["cr5"][0]
        or metrics.hhi >= t["hhi"][0]
    ):
        return 4
    return 2


def region_score(metrics: ConcentrationMetrics, thresholds: dict | None = None) -> int:
    """D2: Regional concentration (single province + weak region share)."""
    t = _resolve_thresholds("region", thresholds)
    province = _rating_band(metrics.single_province_share, *t["single_province_share"])
    weak = _rating_band(metrics.weak_region_share, *t["weak_region_share"])
    return max(province, weak)


def rating_score(metrics: ConcentrationMetrics, thresholds: dict | None = None) -> int:
    """D3: Rating concentration (external AAA + pseudo-high-rating share)."""
    t = _resolve_thresholds("rating", thresholds)
    aaa = _rating_band(metrics.aaa_share, *t["aaa_share"])
    pseudo = _rating_band(metrics.pseudo_high_rating_share, *t["pseudo_high_rating_share"])
    return max(aaa, pseudo)


def maturity_score(metrics: ConcentrationMetrics, thresholds: dict | None = None) -> int:
    """D4: Maturity concentration (12-month share + single-month peak)."""
    t = _resolve_thresholds("maturity", thresholds)
    m12 = _rating_band(metrics.maturity_12m_share, *t["maturity_12m_share"])
    peak = _rating_band(metrics.single_month_peak, *t["single_month_peak"])
    return max(m12, peak)


def channel_score(metrics: ConcentrationMetrics, thresholds: dict | None = None) -> int:
    """D5: Financing-channel concentration (top channel share + contraction flag)."""
    t = _resolve_thresholds("channel", thresholds)
    base = _rating_band(metrics.top_channel_share, *t["top_channel_share"])
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


def _merge_thresholds(override: dict | None) -> dict:
    """thresholds_override 并入默认值（按维度按指标部分覆盖）。

    结构：{维度: {指标: (关注下界, 警示下界, 危险下界)}}；未知维度/指标、
    非三元组或非升序阈值 → raise（失败可观测纪律）。
    """
    merged = {dim: dict(bounds) for dim, bounds in DEFAULT_THRESHOLDS.items()}
    for dim, metrics_override in (override or {}).items():
        if dim not in merged:
            raise ValueError(f"thresholds_override 未知维度: {dim!r}")
        for key, bounds in metrics_override.items():
            if key not in merged[dim]:
                raise ValueError(f"thresholds_override 未知指标: {dim}.{key}")
            bounds = tuple(bounds)
            if len(bounds) != 3 or not bounds[0] <= bounds[1] <= bounds[2]:
                raise ValueError(
                    f"thresholds_override {dim}.{key} 阈值须为升序三元组: {bounds!r}"
                )
            merged[dim][key] = bounds
    return merged


def concentration_risk_score(
    metrics: ConcentrationMetrics,
    weights: tuple[float, float, float, float, float] = DEFAULT_WEIGHTS,
    thresholds_override: dict | None = None,
) -> float:
    """Five-dimensional weighted concentration risk score (1-10 scale).

    Default weights follow engine/concentration-framework.md §8.2:
    industry 25%, region 20%, rating 20%, maturity 20%, channel 15%.

    thresholds_override（WP-M4-04 T3 扩展）：{维度: {指标: (关注, 警示, 危险)}}
    按维度按指标部分覆盖默认阈值重算档位；默认 None 时行为与扩展前完全一致
    （parity 锚点见 tests/test_concentration_scorer.py）。
    """
    if len(weights) != 5:
        raise ValueError("weights must contain exactly 5 values")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("weights must sum to 1.0")

    t = _merge_thresholds(thresholds_override)
    scores = (
        industry_score(metrics, t["industry"]),
        region_score(metrics, t["region"]),
        rating_score(metrics, t["rating"]),
        maturity_score(metrics, t["maturity"]),
        channel_score(metrics, t["channel"]),
    )
    return sum(s * w for s, w in zip(scores, weights))

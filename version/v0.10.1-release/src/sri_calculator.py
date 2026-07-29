from dataclasses import dataclass
from enum import Enum


class TrackBLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class Outlook(str, Enum):
    POSITIVE = "positive"
    STABLE = "stable"
    NEGATIVE = "negative"


@dataclass
class IndustryInput:
    name: str
    track_a_score: float  # 0-10
    track_b_level: TrackBLevel
    outlook: Outlook
    veto_triggered: bool = False


def industry_risk_score(ind: IndustryInput) -> float:
    if ind.veto_triggered:
        return 3.0

    if ind.track_a_score < 3.0:
        base = 3.0
    elif ind.track_a_score < 5.0:
        base = 2.0
    elif ind.track_a_score < 6.0:
        base = 1.0
    else:
        base = 0.0

    outlook_penalty = 0.5 if ind.outlook == Outlook.NEGATIVE else 0.0
    if ind.track_b_level == TrackBLevel.RED:
        track_b_penalty = 1.5
    elif ind.track_b_level == TrackBLevel.ORANGE:
        track_b_penalty = 1.0
    elif ind.track_b_level == TrackBLevel.YELLOW:
        track_b_penalty = 0.5
    else:
        track_b_penalty = 0.0

    # Cap non-veto scores at 3.0 to keep the SRI component on the declared 0-3+ scale.
    return min(base + outlook_penalty + track_b_penalty, 3.0)


def sri(industries: list[IndustryInput], weights: list[float]) -> float:
    if len(industries) != len(weights):
        raise ValueError("industries and weights must have same length")
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError("weights must sum to 1.0")

    return sum(industry_risk_score(ind) * w for ind, w in zip(industries, weights))


def thermometer_level(sri_value: float) -> str:
    if sri_value >= 1.8:
        return "danger"
    if sri_value >= 1.0:
        return "alert"
    if sri_value >= 0.5:
        return "watch"
    return "normal"


def m2_background_downgrade(sri: float) -> float:
    """Return notch downgrade for individual issuers based on systemic-warning-framework.md §M2."""
    if sri >= 1.8:  # danger
        return 1.0
    if sri >= 1.0:  # alert
        return 0.5
    return 0.0


def m4_concentration_weight_adjustment(sri: float) -> float:
    """Return multiplicative adjustment for concentration score weights based on SRI."""
    if sri >= 1.8:
        return 1.2
    if sri >= 1.0:
        return 1.1
    if sri >= 0.5:
        return 1.0
    return 0.9

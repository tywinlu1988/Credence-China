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


@dataclass
class SRIReading:
    date: str
    sri_value: float
    thermometer: str
    industry_scores: dict[str, float]
    weights: dict[str, float]
    contagion_coeffs: dict[str, float]


@dataclass
class ShockScenario:
    name: str
    description: str
    industry_shocks: dict[str, float]
    contagion_escalation: list[str]
    outlook_shifts: dict[str, str]


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


def portfolio_sri(holdings: dict[str, float], industries: list[IndustryInput],
                  contagion_coeffs: dict[str, float]) -> dict:
    """持仓权重 × 传染力系数 → 归一化 → SRI + 温度计 + 分解。"""
    if not holdings:
        raise ValueError("holdings 不能为空")
    if len(industries) != len(holdings):
        raise ValueError("industries 与 holdings 长度不一致")
    ind_names = {i.name for i in industries}
    if set(holdings) != set(contagion_coeffs) or set(holdings) != ind_names:
        raise ValueError("holdings/industries/coefficients 行业集不一致")
    if any(v < 0 for v in holdings.values()):
        raise ValueError("holdings 不允许负值")

    raw = {k: holdings[k] * contagion_coeffs[k] for k in holdings}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("加权总和必须为正")
    weights = {k: v / total for k, v in raw.items()}

    scores = {}
    for ind in industries:
        scores[ind.name] = industry_risk_score(ind)

    val = sum(scores[k] * weights[k] for k in scores)
    return {
        "sri": round(val, 4),
        "thermometer": thermometer_level(val),
        "industry_scores": scores,
        "weights_used": weights,
        "raw_inputs": list(industries),
        "coeffs_used": dict(contagion_coeffs),
        "raw_holdings": dict(holdings),
    }


# 预定义压力情景（行业名用 13 行业真实名，值参考 systemic §X+2）
PREDEFINED_SCENARIOS = {
    "moderate": ShockScenario(
        name="温和冲击",
        description="最大红色行业 track_a -1，无传染升级",
        industry_shocks={},
        contagion_escalation=[],
        outlook_shifts={},
    ),
    "severe": ShockScenario(
        name="中度冲击",
        description="红色行业 track_a -2，对应升级因子生效",
        industry_shocks={},
        contagion_escalation=["信用事件"],
        outlook_shifts={},
    ),
    "extreme": ShockScenario(
        name="极端冲击",
        description="全部红色行业 track_a -3，全量升级因子，展望全负面",
        industry_shocks={},
        contagion_escalation=["信用事件", "流动性危机", "政策突变"],
        outlook_shifts={},
    ),
}


def stress_test(base_result: dict, scenario: ShockScenario, matrix=None) -> dict:
    """施加冲击 → 重算 → 返回对比。base_result 为 portfolio_sri 输出。"""
    from src.contagion_engine import apply_escalation, contagion_coefficients as cc

    baseline_sri = base_result["sri"]
    baseline_thermo = base_result["thermometer"]

    # 构造冲击后的 IndustryInput 列表（track_a_score 下调 + outlook 调降）
    raw_inputs = base_result["raw_inputs"]
    shocked_industries = []
    for ind in raw_inputs:
        shock = scenario.industry_shocks.get(ind.name, 0.0)
        new_track_a = max(ind.track_a_score - shock, 0.0)
        if ind.name in scenario.outlook_shifts:
            new_outlook = Outlook(scenario.outlook_shifts[ind.name])
        else:
            new_outlook = ind.outlook
        shocked_industries.append(IndustryInput(
            name=ind.name,
            track_a_score=new_track_a,
            track_b_level=ind.track_b_level,
            outlook=new_outlook,
            veto_triggered=ind.veto_triggered,
        ))

    # 确定新传染力系数（有 matrix + escalation → apply_escalation）
    raw_holdings = base_result["raw_holdings"]
    if matrix is not None and scenario.contagion_escalation:
        stressed_matrix = apply_escalation(matrix, scenario.contagion_escalation)
        new_coeffs = cc(stressed_matrix)
    else:
        new_coeffs = base_result["coeffs_used"]

    # 重算组合 SRI
    stressed = portfolio_sri(raw_holdings, shocked_industries, new_coeffs)

    # 行业级 delta
    industry_deltas = {}
    for name in base_result["industry_scores"]:
        industry_deltas[name] = round(
            stressed["industry_scores"][name] - base_result["industry_scores"][name], 4
        )

    return {
        "baseline_sri": baseline_sri,
        "stressed_sri": stressed["sri"],
        "delta": round(stressed["sri"] - baseline_sri, 4),
        "thermometer_before": baseline_thermo,
        "thermometer_after": stressed["thermometer"],
        "industry_deltas": industry_deltas,
    }

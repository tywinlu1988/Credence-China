import pytest

from src.sri_calculator import (
    IndustryInput,
    Outlook,
    TrackBLevel,
    industry_risk_score,
    m2_background_downgrade,
    m4_concentration_weight_adjustment,
    sri,
    thermometer_level,
    # new
    SRIReading,
    ShockScenario,
    PREDEFINED_SCENARIOS,
    portfolio_sri,
    stress_test,
    # v0.10.3 T2
    compute_trend,
    detect_tipping_points,
    sri_time_series,
    linked_sri,
)


def test_industry_risk_score_normal():
    ind = IndustryInput(
        name="test",
        track_a_score=7.0,
        track_b_level=TrackBLevel.GREEN,
        outlook=Outlook.STABLE,
    )
    assert industry_risk_score(ind) == 0.0


def test_industry_risk_score_negative_outlook_and_orange_track_b():
    ind = IndustryInput(
        name="test",
        track_a_score=7.0,
        track_b_level=TrackBLevel.ORANGE,
        outlook=Outlook.NEGATIVE,
    )
    assert industry_risk_score(ind) == 1.5


def test_veto_overrides_everything():
    ind = IndustryInput(
        name="test",
        track_a_score=9.0,
        track_b_level=TrackBLevel.GREEN,
        outlook=Outlook.STABLE,
        veto_triggered=True,
    )
    assert industry_risk_score(ind) == 3.0


def test_non_veto_score_capped_at_three():
    # Worst non-veto band (track_a < 3.0) with both penalties should still cap at 3.0.
    ind = IndustryInput(
        name="test",
        track_a_score=2.0,
        track_b_level=TrackBLevel.RED,
        outlook=Outlook.NEGATIVE,
    )
    assert industry_risk_score(ind) == 3.0


def test_veto_equals_maximum_non_veto():
    veto = IndustryInput(
        name="veto",
        track_a_score=9.0,
        track_b_level=TrackBLevel.GREEN,
        outlook=Outlook.STABLE,
        veto_triggered=True,
    )
    worst = IndustryInput(
        name="worst",
        track_a_score=2.0,
        track_b_level=TrackBLevel.RED,
        outlook=Outlook.NEGATIVE,
    )
    assert industry_risk_score(veto) == industry_risk_score(worst) == 3.0


def test_track_b_penalties():
    base = IndustryInput("base", 7.0, TrackBLevel.GREEN, Outlook.STABLE)
    assert industry_risk_score(base) == 0.0
    yellow = IndustryInput("yellow", 7.0, TrackBLevel.YELLOW, Outlook.STABLE)
    assert industry_risk_score(yellow) == 0.5
    orange = IndustryInput("orange", 7.0, TrackBLevel.ORANGE, Outlook.STABLE)
    assert industry_risk_score(orange) == 1.0
    red = IndustryInput("red", 7.0, TrackBLevel.RED, Outlook.STABLE)
    assert industry_risk_score(red) == 1.5


def test_worst_non_veto_with_red_track_b_and_negative_outlook():
    ind = IndustryInput("worst", 2.0, TrackBLevel.RED, Outlook.NEGATIVE)
    assert industry_risk_score(ind) == 3.0


def test_sri_matches_2026q2_example():
    # Approximate 2026Q2 example from systemic-warning-framework.md §8.3.
    # Residual weight is distributed across the placeholder industries so the
    # vector sums to 1.0; the placeholder industries have zero risk score.
    industries = [
        IndustryInput("LGV", 5.25, TrackBLevel.YELLOW, Outlook.STABLE),
        IndustryInput("PV", 5.0, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("NEV", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("Retail", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
    ] + [
        IndustryInput(f"other_{i}", 7.0, TrackBLevel.GREEN, Outlook.STABLE)
        for i in range(9)
    ]
    weights = [0.25, 0.0233, 0.0222, 0.04] + [0.0] * 9
    residual = 1.0 - sum(weights[:4])
    valid_weights = weights[:4] + [residual / 9] * 9
    result = sri(industries, valid_weights)
    assert 0.54 <= result <= 0.60


def test_sri_validates_weights():
    industries = [IndustryInput("a", 7.0, TrackBLevel.GREEN, Outlook.STABLE)]
    assert sri(industries, [1.0]) == 0.0


def test_sri_rejects_mismatched_weights():
    industries = [
        IndustryInput("a", 7.0, TrackBLevel.GREEN, Outlook.STABLE),
        IndustryInput("b", 7.0, TrackBLevel.GREEN, Outlook.STABLE),
    ]
    with pytest.raises(ValueError):
        sri(industries, [1.0])


def test_sri_rejects_weights_not_summing_to_one():
    industries = [
        IndustryInput("a", 7.0, TrackBLevel.GREEN, Outlook.STABLE),
        IndustryInput("b", 7.0, TrackBLevel.GREEN, Outlook.STABLE),
    ]
    with pytest.raises(ValueError):
        sri(industries, [0.5, 0.4])


def test_thermometer():
    assert thermometer_level(0.2) == "normal"
    assert thermometer_level(0.6) == "watch"
    assert thermometer_level(1.2) == "alert"
    assert thermometer_level(2.0) == "danger"


def test_thermometer_boundary_values():
    assert thermometer_level(0.5) == "watch"
    assert thermometer_level(1.0) == "alert"
    assert thermometer_level(1.8) == "danger"


def test_m2_background_downgrade():
    assert m2_background_downgrade(0.3) == 0.0
    assert m2_background_downgrade(1.2) == 0.5
    assert m2_background_downgrade(2.0) == 1.0


def test_m4_weight_adjustment():
    assert m4_concentration_weight_adjustment(0.3) == 0.9
    assert m4_concentration_weight_adjustment(0.7) == 1.0
    assert m4_concentration_weight_adjustment(1.2) == 1.1
    assert m4_concentration_weight_adjustment(2.0) == 1.2


def test_portfolio_sri_normalizes_holdings():
    ind = IndustryInput(name="test", track_a_score=7.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.STABLE)
    result = portfolio_sri({"test": 50.0}, [ind], {"test": 1.0})
    assert "sri" in result and "thermometer" in result and "industry_scores" in result
    assert abs(sum(result["weights_used"].values()) - 1.0) < 1e-6


def test_portfolio_sri_matches_flat_sri():
    """全 1 系数 + 等权重 = 与裸 sri() 一致"""
    inds = [IndustryInput(name=f"ind{i}", track_a_score=7.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.STABLE)
            for i in range(3)]
    holdings = {"ind0": 1.0, "ind1": 1.0, "ind2": 1.0}
    coeffs = {"ind0": 1.0, "ind1": 1.0, "ind2": 1.0}
    result = portfolio_sri(holdings, inds, coeffs)
    expected_sri = sri(inds, [1/3, 1/3, 1/3])
    assert abs(result["sri"] - expected_sri) < 1e-6


def test_portfolio_sri_industry_mismatch():
    ind = IndustryInput(name="A", track_a_score=7.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.STABLE)
    with pytest.raises(ValueError):
        portfolio_sri({"B": 1.0}, [ind], {"B": 1.0})  # B not in industry_inputs


def test_stress_test_delta_positive():
    ind = IndustryInput(name="光伏", track_a_score=3.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.NEGATIVE)
    base = portfolio_sri({"光伏": 1.0}, [ind], {"光伏": 1.0})
    scenario = ShockScenario(name="test", description="光伏 -2 shock",
                             industry_shocks={"光伏": 2.0}, contagion_escalation=[],
                             outlook_shifts={})
    result = stress_test(base, scenario)
    assert result["stressed_sri"] > result["baseline_sri"]
    assert result["delta"] > 0


def test_stress_test_predefined_scenarios():
    assert "moderate" in PREDEFINED_SCENARIOS and "severe" in PREDEFINED_SCENARIOS and "extreme" in PREDEFINED_SCENARIOS
    for name in ("moderate", "severe", "extreme"):
        s = PREDEFINED_SCENARIOS[name]
        assert isinstance(s, ShockScenario)
        # Shock values filled in Task 3; structure is verified here


# ── v0.10.3 T2: 时间序列 + 传染联动 ──


def _reading(val, thermo=None):
    return SRIReading(date=f"2026-07-{val*10:02.0f}", sri_value=val,
                      thermometer=thermo or thermometer_level(val),
                      industry_scores={}, weights={}, contagion_coeffs={})


def test_time_series_trend_up():
    readings = [_reading(0.3), _reading(0.5), _reading(0.7), _reading(0.9)]
    assert compute_trend(readings) == "上升"


def test_time_series_trend_down():
    readings = [_reading(0.9), _reading(0.7), _reading(0.5), _reading(0.3)]
    assert compute_trend(readings) == "下降"


def test_time_series_trend_flat():
    readings = [_reading(0.55), _reading(0.52), _reading(0.58), _reading(0.54)]
    assert compute_trend(readings) == "平稳"


def test_time_series_insufficient():
    assert compute_trend([_reading(0.5), _reading(0.6)], window=4) == "insufficient"


def test_detect_tipping_points():
    readings = [
        _reading(0.3, "normal"), _reading(0.6, "watch"), _reading(1.1, "alert"),
    ]
    events = detect_tipping_points(readings)
    assert len(events) == 2  # normal→watch, watch→alert
    assert events[0]["from"] == "normal" and events[0]["to"] == "watch"


def test_detect_tipping_points_no_events():
    readings = [_reading(0.3, "normal"), _reading(0.4, "normal"), _reading(0.45, "normal")]
    assert detect_tipping_points(readings) == []


def test_sri_time_series_basic():
    readings = [_reading(0.3), _reading(0.6), _reading(0.9)]
    result = sri_time_series(readings)
    assert "trend" in result and "tipping_points" in result and "latest" in result and "count" in result
    assert result["count"] == 3


def test_linked_sri_escalation_delta_nonzero():
    from src.contagion_engine import ContagionMatrix, ContagionCell
    cells = {
        ("A", "B"): ContagionCell("A", "B", 1, set(), ""),
        ("B", "A"): ContagionCell("B", "A", 1, set(), ""),
    }
    matrix = ContagionMatrix(["A", "B"], cells)
    inds = [IndustryInput(name="A", track_a_score=7.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.STABLE),
            IndustryInput(name="B", track_a_score=3.0, track_b_level=TrackBLevel.RED, outlook=Outlook.NEGATIVE)]
    result = linked_sri(inds, {"A": 0.5, "B": 0.5}, matrix, ["年末效应"])
    assert "baseline_sri" in result and "stressed_sri" in result and "explanation" in result


def test_linked_sri_unknown_factor_rejected():
    from src.contagion_engine import ContagionMatrix, ContagionCell
    cells = {
        ("A", "B"): ContagionCell("A", "B", 1, set(), ""),
        ("B", "A"): ContagionCell("B", "A", 1, set(), ""),
    }
    matrix = ContagionMatrix(["A", "B"], cells)
    inds = [IndustryInput(name="A", track_a_score=7.0, track_b_level=TrackBLevel.GREEN, outlook=Outlook.STABLE),
            IndustryInput(name="B", track_a_score=3.0, track_b_level=TrackBLevel.RED, outlook=Outlook.NEGATIVE)]
    with pytest.raises(ValueError, match="未知升级因子"):
        linked_sri(inds, {"A": 0.5, "B": 0.5}, matrix, ["不存在的因子"])

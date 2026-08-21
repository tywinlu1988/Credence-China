"""Tests for the v0.7.8 executable orchestrator (src/pipeline.py).

T9.1-T9.7 cover the thin orchestrator: stage-plan construction from the contract doc,
end-to-end execution of the wired coded engines (WP-M4-01 concentration, WP-M4-02 contagion,
WP-M4-03 SRI, WP-X-05 outlook), graceful LLM-orchestrated skipping for unwired paths,
planned-path 待开发 notices, contract-sourced stage names, and invalid-sheet rejection.
Deliverable 3 (chaining-edge endpoint referential integrity) is also covered here.
"""

from pathlib import Path

import pytest

from src.concentration_scorer import ConcentrationMetrics
from src.path_sheet import load_registry_paths
from src.pipeline import (
    EXECUTABLE_ENGINES,
    load_contract,
    load_stage_plan,
    planned_path_notice,
    run_executable_stages,
)
from src.sri_calculator import IndustryInput, Outlook, TrackBLevel

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "dev" / "engine" / "pipeline-contract.md"
REGISTRY = ROOT / "dev" / "engine" / "work-path-registry.md"


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def contract():
    return load_contract(CONTRACT)


@pytest.fixture(scope="module")
def registry_paths():
    return load_registry_paths(REGISTRY)


def _sheet(path_id, **overrides) -> dict:
    """A valid sheet for an M4 wired path; overridable per-test."""
    base = {
        "WP-M4-03": {
            "role": "M4",
            "object": "market",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M4-03",
            "engine_reading_order": ["dev/engine/systemic-warning-framework.md"],
            "quality_gates": ["温度计四级 (dev/engine/systemic-warning-framework.md §三)"],
            "notes": "",
        },
        "WP-M4-01": {
            "role": "M4",
            "object": "portfolio",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M4-01",
            "engine_reading_order": ["dev/engine/concentration-framework.md"],
            "quality_gates": ["五维集中度 (dev/engine/concentration-framework.md §一)"],
            "notes": "",
        },
        "WP-M4-02": {
            "role": "M4",
            "object": "portfolio",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M4-02",
            "engine_reading_order": [
                "dev/engine/contagion-matrix.md",
                "dev/engine/contagion-theory.md",
            ],
            "quality_gates": ["传染矩阵 (dev/engine/contagion-matrix.md §二)"],
            "notes": "",
        },
        "WP-X-05": {
            "role": "meta",
            "object": "single-issuer",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-X-05",
            "engine_reading_order": ["dev/engine/outlook-monitoring-framework.md"],
            "quality_gates": ["评级展望 (dev/engine/outlook-monitoring-framework.md §二)"],
            "notes": "",
        },
        "WP-M0-01": {
            "role": "M0",
            "object": "single-issuer",
            "depth": "L2",
            "mode": "A",
            "path_id": "WP-M0-01",
            "engine_reading_order": ["dev/engine/industry-framework.md"],
            "quality_gates": ["一票否决 (dev/engine/industry-framework.md §五)"],
            "notes": "",
        },
        "WP-M0-02": {
            "role": "M0",
            "object": "single-issuer",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M0-02",
            "engine_reading_order": [
                "dev/engine/lgd-recovery-framework.md",
                "dev/engine/external-support-framework.md",
            ],
            "quality_gates": ["LGD五级分类 (dev/engine/lgd-recovery-framework.md §二)"],
            "notes": "",
        },
        "WP-M4-04": {
            "role": "M4",
            "object": "portfolio",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M4-04",
            "engine_reading_order": [
                "dev/engine/concentration-framework.md",
                "dev/engine/financial-deep-dive.md",
            ],
            "quality_gates": [
                "压力测试 (dev/engine/concentration-framework.md §九)",
                "场景敏感性 (dev/engine/financial-deep-dive.md §E)",
            ],
            "notes": "",
        },
        "WP-X-04": {
            "role": "meta",
            "object": "single-issuer",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-X-04",
            "engine_reading_order": [
                "dev/engine/esg-framework.md",
                "dev/engine/governance-fraud-risk.md",
            ],
            "quality_gates": ["ESG (dev/engine/esg-framework.md §一)"],
            "notes": "",
        },
        "WP-M1-01": {
            "role": "M1",
            "object": "single-issuer",
            "depth": "L2",
            "mode": "A",
            "path_id": "WP-M1-01",
            "engine_reading_order": ["dev/engine/multi-stakeholder.md"],
            "quality_gates": ["四维 (dev/engine/multi-stakeholder.md §二)"],
            "notes": "",
        },
        "WP-M2-01": {
            "role": "M2",
            "object": "single-issuer",
            "depth": "专项",
            "mode": "A",
            "path_id": "WP-M2-01",
            "engine_reading_order": [],
            "quality_gates": [],
            "notes": "",
        },
    }[path_id]
    base.update(overrides)
    return base


def _sri_2026q2_inputs() -> dict:
    """The known 2026Q2 SRI fixture (mirrors test_sri_matches_2026q2_example)."""
    industries = [
        IndustryInput("LGV", 5.25, TrackBLevel.YELLOW, Outlook.STABLE),
        IndustryInput("PV", 5.0, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("NEV", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
        IndustryInput("Retail", 5.5, TrackBLevel.YELLOW, Outlook.NEGATIVE),
    ] + [
        IndustryInput(f"other_{i}", 7.0, TrackBLevel.GREEN, Outlook.STABLE)
        for i in range(9)
    ]
    weights = [0.25, 0.0233, 0.0222, 0.04]
    residual = 1.0 - sum(weights)
    valid_weights = weights + [residual / 9] * 9
    return {"industries": industries, "weights": valid_weights}


def _concentration_inputs() -> dict:
    """An all-green ConcentrationMetrics fixture (low concentration)."""
    return {
        "metrics": ConcentrationMetrics(
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
    }


# --------------------------------------------------------------------------
# T9.1 — WP-M4-03 yields 4 ordered stages; analysis is executable
# --------------------------------------------------------------------------

def test_t9_1_stage_plan_order_and_executable(contract, registry_paths):
    plan = load_stage_plan(_sheet("WP-M4-03"), registry_paths, contract)
    assert [s.name for s in plan] == ["intake", "analysis", "report", "qa"]
    analysis = plan[1]
    assert analysis.executable is True
    # the other three stages are never executable
    assert all(not s.executable for s in (plan[0], plan[2], plan[3]))
    # analysis reads the sheet's engine_reading_order
    assert analysis.inputs == ["dev/engine/systemic-warning-framework.md"]


# --------------------------------------------------------------------------
# T9.2 — SRI stage runs end-to-end against the 2026Q2 fixture
# --------------------------------------------------------------------------

def test_t9_2_sri_end_to_end_matches_2026q2(contract, registry_paths):
    plan = load_stage_plan(_sheet("WP-M4-03"), registry_paths, contract)
    manifest = run_executable_stages(plan, _sri_2026q2_inputs())
    assert manifest["path_id"] == "WP-M4-03"
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    sri_value = analysis["outputs"]["sri"]
    assert 0.54 <= sri_value <= 0.60
    assert analysis["outputs"]["thermometer"] == "watch"


# --------------------------------------------------------------------------
# T9.3 — WP-M4-01 wired: concentration score + rating_adjustment
# --------------------------------------------------------------------------

def test_t9_3_concentration_wired(contract, registry_paths):
    plan = load_stage_plan(_sheet("WP-M4-01"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, _concentration_inputs())
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert out["score"] <= 4.0  # all-green fixture → low concentration
    assert out["adjustment"] == 0.0
    assert out["bb_cap_triggered"] is False
    assert set(out["levels"]) == {"industry", "region", "rating", "maturity", "channel"}


# --------------------------------------------------------------------------
# T9.4 — unwired path (WP-M1-01): analysis not executable, graceful skip
# --------------------------------------------------------------------------

def test_t9_4_unwired_path_skips_gracefully(contract, registry_paths):
    assert "WP-M1-01" not in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-M1-01"), registry_paths, contract)
    assert plan[1].executable is False
    manifest = run_executable_stages(plan, {})
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "llm-orchestrated"
    assert analysis["outputs"] is None
    # every stage of an unwired path is LLM-orchestrated
    assert all(s["mode"] == "llm-orchestrated" for s in manifest["stages"])


# --------------------------------------------------------------------------
# T9.5 — planned path (WP-M2-01): 待开发 notice, no execution
# --------------------------------------------------------------------------

def test_t9_5_planned_path_notice(registry_paths):
    # 注册表当前无 planned 路径：以 WP-M2-01 注入 planned 状态验证待开发提示机制
    fake = {**registry_paths, "WP-M2-01": {**registry_paths["WP-M2-01"], "status": "planned"}}
    notice = planned_path_notice(_sheet("WP-M2-01"), fake)
    assert notice is not None
    assert "待开发" in notice
    assert "WP-M2-01" in notice
    # an active path yields no notice
    assert planned_path_notice(_sheet("WP-M4-03"), registry_paths) is None


# --------------------------------------------------------------------------
# T9.6 — stage names come from the contract doc, not hardcoded
# --------------------------------------------------------------------------

def test_t9_6_stage_names_sourced_from_contract(tmp_path, registry_paths):
    renamed = tmp_path / "contract.md"
    renamed.write_text(
        "# contract fixture\n\n"
        "| 阶段 | 产物 | 承载 skill | 上游 | 下游 |\n"
        "|---|---|---|---|---|\n"
        "| S1 ingest | 工作路径单 | `credit-analysis-router` | — | S2 |\n"
        "| S2 deep-analysis | 分析产物 | `fixed-income-credit-analysis` | S1 | S3 |\n"
        "| S3 render | 交付单 | `credit-report-builder` | S2 | S4 |\n"
        "| S4 verify | 质检裁决 | `credit-qa-verifier` | S1+S2+S3 | — |\n",
        encoding="utf-8",
    )
    renamed_contract = load_contract(renamed)
    plan = load_stage_plan(_sheet("WP-M4-03"), registry_paths, renamed_contract)
    # names reflect the renamed contract, not hardcoded intake/analysis/report/qa
    assert [s.name for s in plan] == ["ingest", "deep-analysis", "render", "verify"]
    # ... while positional chain semantics are preserved (analysis still executable)
    assert plan[1].executable is True


# --------------------------------------------------------------------------
# T9.7 — invalid sheet rejected via validate_path_sheet
# --------------------------------------------------------------------------

def test_t9_7_invalid_sheet_rejected(contract, registry_paths):
    # illegal enum value
    with pytest.raises(ValueError):
        load_stage_plan(_sheet("WP-M4-03", mode="C"), registry_paths, contract)
    # unknown path_id
    bad = _sheet("WP-M4-03")
    bad["path_id"] = "WP-M9-99"
    with pytest.raises(ValueError):
        load_stage_plan(bad, registry_paths, contract)


# --------------------------------------------------------------------------
# Deliverable 3 — chaining-edge endpoint referential integrity (v0.7.7 carryover)
# --------------------------------------------------------------------------

def test_chaining_edge_endpoints_resolve(contract, registry_paths):
    edges = contract["chaining_edges"]
    assert edges, "contract must define chaining_edges"
    for edge in edges:
        # every `from` endpoint resolves to a registered path_id
        assert edge["from"] in registry_paths, f"{edge['id']}: unknown from {edge['from']}"
        to = edge.get("to") or []
        if not to:
            # open set: must carry a to_ref pointer instead of enumerated ids
            assert edge.get("to_ref"), f"{edge['id']}: open `to` set missing to_ref"
            continue
        # every enumerated `to` endpoint resolves to a registered path_id
        for target in to:
            assert target in registry_paths, f"{edge['id']}: unknown to {target}"


# --------------------------------------------------------------------------
# T9.8 — WP-M4-02 wired: contagion engine executes at analysis stage
# --------------------------------------------------------------------------

def test_t9_8_contagion_wired_and_runs(contract, registry_paths):
    assert "WP-M4-02" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-M4-02"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, {
        "holdings": {"光伏/储能": 0.4, "半导体/集成电路": 0.35, "食品饮料": 0.25},
        "escalation_factors": ["市场恐慌"],
    })
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"exposure", "links", "factors_applied"}
    assert out["factors_applied"] == ["市场恐慌"]
    assert len(out["exposure"]) == 3 and out["links"]
    # 显式跳升生效：半导体→光伏 在压力矩阵中为 5
    jump = [l for l in out["links"] if l["source"] == "半导体/集成电路" and l["target"] == "光伏/储能"]
    assert jump and jump[0]["intensity"] == 5


# --------------------------------------------------------------------------
# T9.9 — WP-X-05 wired: outlook engine executes at analysis stage
# --------------------------------------------------------------------------

def test_t9_9_outlook_wired_and_runs(contract, registry_paths):
    assert "WP-X-05" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-X-05"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, {
        "signals": [
            {"layer": "L1", "direction": "negative"},
            {"layer": "外部支持", "direction": "negative"},
        ],
        "rating": "AA",
        "paradigm": "政策驱动型",
        "watchlist_triggers": [{"side": "negative", "event": "被监管立案调查"}],
    })
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"outlook", "confidence", "net_score", "watchlist", "migration"}
    assert out["outlook"] == "负面" and out["watchlist"]["side"] == "负面观察"
    assert out["migration"]["下调"] == "15-20%"


# --------------------------------------------------------------------------
# T9.10 — WP-M0-01 wired: composite scorer executes at analysis stage
# --------------------------------------------------------------------------

def test_t9_10_composite_wired_and_runs(contract, registry_paths):
    assert "WP-M0-01" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-M0-01"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, {
        "d_scores": {"D1": 4, "D2": 4, "D3": 5, "D4": 4, "D5": 3,
                     "D6": 3, "D7": 2, "D8": 2, "D9": 3, "D10": 3},
        "layer_scores": {"L1": 8, "L2": 7, "L3": 6, "L4": 7},
        "industry": "光伏/储能",
    })
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"paradigm", "composite", "rating", "veto_capped", "conflict", "out_of_scope"}
    assert out["paradigm"] == "政策驱动型" and out["rating"] == "A"
    # 特殊结构诚实降级：半导体 → out_of_scope
    manifest2 = run_executable_stages(plan, {
        "d_scores": {"D1": 4}, "layer_scores": {"L1": 8, "L2": 7, "L3": 6, "L4": 7},
        "industry": "半导体/集成电路",
    })
    out2 = next(s for s in manifest2["stages"] if s["name"] == "analysis")["outputs"]
    assert out2["out_of_scope"] and out2["composite"] is None


# --------------------------------------------------------------------------
# T9.11 — WP-M0-02 wired: dual engines (LGD + external support) at analysis stage
# --------------------------------------------------------------------------

def _m002_inputs() -> dict:
    """WP-M0-02 fixture：光伏无担保优先中票（江苏）+ 政府支持全强。"""
    return {
        "lgd": {
            "seniority": "无担保优先",
            "collateral": {"kind": "none"},
            "guarantee": {"guarantee_type": "无"},
            "industry_key": "光伏制造",
            "recovery_scenario": "重整-资产尚可",
            "province": "江苏",
            "evasion": {},
            "pd_rating": "AA",
            "bond_type": "中期票据（MTN）",
        },
        "support": {
            "support_type": "政府支持",
            "indicators": {
                "一般公共预算收入": 4000, "财政自给率": 85, "政府显性债务率": 70,
                "GDP增速": 7, "人口趋势": "持续净流入", "转移支付依赖度": 15,
            },
            "willingness_signals": {"战略地位": "强", "历史救助": "强"},
            "signal_level": "L5",
            "standalone_rating": "A+",
            "supporter_is_central_gov": True,
        },
    }


def test_t9_11_m002_dual_engine_wired_and_runs(contract, registry_paths):
    assert "WP-M0-02" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-M0-02"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, _m002_inputs())
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"lgd", "support"}
    # LGD 子结果：Base 60 + 光伏 +5 + 重整尚可 -5 + 江苏 -5 = 55 → LGD3
    lgd = out["lgd"]
    assert lgd["lgd_pct"] == 55.0 and lgd["lgd_level"] == "LGD3"
    assert lgd["breakdown"][0]["name"] == "Base_LGD"
    assert lgd["prior_check"]["within_prior"] is True
    # 支持子结果：能力强 × 意愿高 → 非常高 → +3 子级（上限取 hi）
    # （standalone 取 A+ 避开 AAA 梯顶截断——终审 I-1 后 uplift_notches 为实际变动）
    sup = out["support"]
    assert sup["strength"] == "非常高" and sup["uplift_notches"] == 3
    assert sup["final_rating"] == "AA+"


# --------------------------------------------------------------------------
# T9.12 — WP-M4-04 wired: stress engine (§E + §九 + E.10 + SRI 复用) at analysis stage
# --------------------------------------------------------------------------

def _m004_inputs() -> dict:
    """WP-M4-04 fixture：2 标的小型组合（光伏 E.1 锚命中 + 数据中心 E.1 锚），
    附 §九 集中度、E.10 债券、SRI 复用三类可选输入（键序同 _run_m004 契约）。"""
    return {
        "financials": {
            "IssuerA": {  # 光伏/储能：E.1 校准锚 -35%/-20pp
                "industry": "光伏/储能",
                "revenue": 1000.0, "gross_margin": 0.30, "period_expenses": 150.0,
                "tax_rate": 0.25, "da": 50.0, "capex": 80.0,
                "interest_expense": 40.0, "cash": 500.0, "unused_credit": 100.0,
                "inventory": 150.0, "dso_days": 60.0, "dio_days": 60.0,
                "base_funding_rate": 0.04,
            },
            "IssuerB": {  # 数据中心：E.1 校准锚 -15%/-10pp
                "industry": "数据中心",
                "revenue": 500.0, "gross_margin": 0.40, "period_expenses": 120.0,
                "tax_rate": 0.25, "da": 30.0, "capex": 60.0,
                "interest_expense": 20.0, "cash": 200.0, "unused_credit": 50.0,
                "inventory": 30.0, "dso_days": 45.0, "dio_days": 30.0,
                "base_funding_rate": 0.05,
            },
        },
        "concentration_metrics": {
            "hhi": 500, "cr3": 0.30, "cr5": 0.50, "max1": 0.15,
            "single_province_share": 0.10, "weak_region_share": 0.18,
            "aaa_share": 0.20, "pseudo_high_rating_share": 0.01,
            "maturity_12m_share": 0.20, "single_month_peak": 0.05,
            "top_channel_share": 0.30,
        },
        "scenario": "区域性城投展期潮",
        "bonds": {"IssuerA": {"years": 3.0, "ytm": 0.035}},
        "sri": {
            "industries": [
                {"name": "光伏/储能", "track_a_score": 5.0,
                 "track_b_level": "yellow", "outlook": "stable"},
                {"name": "半导体/集成电路", "track_a_score": 7.5,
                 "track_b_level": "green", "outlook": "stable"},
            ],
            "holdings": {"光伏/储能": 0.6, "半导体/集成电路": 0.4},
            # 自定义 ShockScenario（子集组合不能用 contagion_escalation——
            # stress_test 矩阵升级路径按全市场组合重算系数，见 _run_m004 docstring）
            "scenario": {
                "name": "光伏下调",
                "description": "光伏 track_a -1 冲击",
                "industry_shocks": {"光伏/储能": 1.0},
                "contagion_escalation": [],
                "outlook_shifts": {},
            },
        },
    }


def test_t9_12_m004_stress_wired_and_runs(contract, registry_paths):
    assert "WP-M4-04" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-M4-04"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, _m004_inputs())
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"concentration", "scenarios", "bond_mv", "sri_stress"}

    # §E 场景矩阵复算（IssuerA：Bear -10%/-5pp/+100bp，基准利率 4% → 利息 ×1.25）
    a = out["scenarios"]["IssuerA"]
    assert set(a) == {
        "bear", "severe", "safety", "tail_risk", "tail_risk_warning", "reverse",
    }
    assert a["bear"]["revenue"] == pytest.approx(900.0)          # 1000 × (1-10%)
    assert a["bear"]["interest"] == pytest.approx(50.0)          # 40 × (1+100bp/4%)
    assert a["bear"]["interest_coverage"] == pytest.approx(2.5)  # (225-150+50)/50
    assert a["safety"]["overall"]["emoji"] == "🟠"               # FCF/利息 0.525 ∈ [0.5,1.0]
    # Severe：E.1 锚 -35%/-20pp + 二阶融资 +50bp → 40×1.5 + 40×0.125 = 65
    assert a["severe"]["interest"] == pytest.approx(65.0)
    assert a["tail_risk"] is True                                # Severe FCF/利息 <0 → 🔴
    assert "尾部风险警告" in a["tail_risk_warning"]
    assert a["reverse"]["critical_revenue_drop_pct"] is not None
    # IssuerB：E.1 锚（数据中心 -15%/-10pp）对 Severe 生效
    b = out["scenarios"]["IssuerB"]
    assert b["bear"]["revenue"] == pytest.approx(450.0)          # 500 × 0.9
    assert b["severe"]["revenue"] == pytest.approx(425.0)        # 500 × (1-15%)

    # §九 压力传导复算（城投展期潮：弱区域 0.18 绿跳橙，综合分 2.2→3.0）
    conc = out["concentration"]
    assert conc["jumps"] == [{"dim": "region", "from": "green", "to": "orange"}]
    assert conc["composite_normal"] == pytest.approx(2.2)
    assert conc["composite_stressed"] == pytest.approx(3.0)

    # E.10 债券市值复算（3 年 / YTM 3.5% → D≈2.8986；轻度承压 +100bp → ≈-2.90%）
    mv = out["bond_mv"]["IssuerA"]
    assert mv["d_approx"] == pytest.approx(3.0 / 1.035)
    first = mv["scenarios"][0]
    assert first["delta_ytm"] == pytest.approx(0.01)
    assert first["delta_p"] == pytest.approx(-0.029, abs=1e-3)

    # SRI 复用（sri_calculator.stress_test 输出原样透传，不重写）
    sri_out = out["sri_stress"]
    assert set(sri_out) == {
        "baseline_sri", "stressed_sri", "delta",
        "thermometer_before", "thermometer_after", "industry_deltas",
    }
    # 光伏 track_a 5.0→4.0（跨 5.0 档界）：行业分 1.5→2.5，组合 SRI 严格上行
    assert sri_out["industry_deltas"]["光伏/储能"] == pytest.approx(1.0)
    assert sri_out["delta"] > 0


def test_t9_12b_m004_optional_dimensions_none():
    """缺可选输入时四键恒在、对应维度为 None（financials 为唯一必选）。"""
    from src.pipeline import _run_m004

    out = _run_m004({"financials": _m004_inputs()["financials"]})
    assert set(out) == {"concentration", "scenarios", "bond_mv", "sri_stress"}
    assert out["concentration"] is None
    assert out["bond_mv"] is None
    assert out["sri_stress"] is None
    assert set(out["scenarios"]) == {"IssuerA", "IssuerB"}
    # concentration_metrics 与 scenario 须成对：半套输入即 raise（不静默降级）
    with pytest.raises(ValueError):
        _run_m004({**_m004_inputs(), "scenario": None})
    with pytest.raises(ValueError):
        _run_m004({**_m004_inputs(), "concentration_metrics": None})
    # sri 子集组合 + contagion_escalation → 前置 raise（stress_test 存量约束，
    # 不静默吞掉升级因子）
    bad = _m004_inputs()
    bad["sri"] = {**bad["sri"], "scenario": {
        "name": "恐慌", "description": "升级",
        "industry_shocks": {}, "contagion_escalation": ["市场恐慌"],
        "outlook_shifts": {},
    }}
    with pytest.raises(ValueError, match="全市场组合|覆盖传染矩阵全部"):
        _run_m004(bad)


# --------------------------------------------------------------------------
# T9.13 — WP-X-04 wired: dual engines (governance + ESG) at analysis stage
# --------------------------------------------------------------------------

def _x004_inputs() -> dict:
    """WP-X-04 最小复算 fixture：1 面高强度治理红旗（FIN-05 非经常性损益占比
    0.6 > 50%，§1 :39）+ 1 个 ESG 事件（信披违规 II 级，弹性弱，城投 G 中敏感）。"""
    return {
        "measured": {"non_recurring_to_net_profit": 0.6},
        "gov_events": {},
        "esg_events": [
            {
                "dimension": "G",
                "category": "disclosure_violation",
                "severity": "II",
                "evidence": "定期报告更正被交易所纪律处分",
                "source": "交易所公告",
                "event_id": "esg-2026-001",
            },
        ],
        "elasticity": {"interest_coverage": 1.5, "cash_runway_months": 3},
        "industry": "城投",
    }


def test_t9_13_x004_dual_engine_wired_and_runs(contract, registry_paths):
    assert "WP-X-04" in EXECUTABLE_ENGINES
    plan = load_stage_plan(_sheet("WP-X-04"), registry_paths, contract)
    assert plan[1].executable is True
    manifest = run_executable_stages(plan, _x004_inputs())
    analysis = next(s for s in manifest["stages"] if s["name"] == "analysis")
    assert analysis["mode"] == "code"
    out = analysis["outputs"]
    assert set(out) == {"governance", "esg"}

    # 治理子结果复算：1 面 HIGH 红旗 → §6.2 高档（l4_cap 4 + 评级上限 B）；
    # 通用红旗 1 面未达 ≥2 升级线；无否决
    gov = out["governance"]
    assert gov["risk_grade"] == "高"
    assert gov["l4_cap"] == 4 and gov["rating_cap"] == "B"
    assert gov["outlook_flag"] is False and gov["veto_triggers"] == []
    assert any(f["note"].startswith("FIN-05 命中") for f in gov["red_flags"])

    # ESG 子结果复算：II 级 ∩ §5.1 信披违规 -0.5子级 → -0.5；弹性弱取最重端；
    # 城投 G 中敏感不 ×1.5；D4 落地 0 + negative_flag；单事件 II → 中等信号
    esg = out["esg"]
    assert esg["notch_adjustment"] == 0 and esg["flags"] == ["negative_flag"]
    assert esg["signal_strength"] == "中等信号"
    assert esg["per_dimension"]["G"]["score"] == -0.5
    assert esg["trigger_events"][0]["event_id"] == "esg-2026-001"


def test_t9_13b_x004_veto_none_passthrough():
    """否决下 l4_cap=None 原样直传（T2 序列化口径：不得默认填数值）。"""
    from src.pipeline import _run_x004

    inputs = _x004_inputs()
    inputs["gov_events"] = {"v1_csrc_fraud_investigation": "立案告知书（财务造假）"}
    gov = _run_x004(inputs)["governance"]
    assert gov["veto_triggers"] == ["v1"]
    assert gov["risk_grade"] == "严重" and gov["rating_cap"] == "CCC"
    assert gov["l4_cap"] is None

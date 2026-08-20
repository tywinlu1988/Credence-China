"""WP-M4-04 stress_scorer 解析层测试（T1）。

单一事实源纪律：E.1 三场景参数与七行业校准锚、E.8 偏离因子、E.5 安全边际
四档均运行时解析自 financial-deep-dive.md；§9.2 阈值跳升表运行时解析自
concentration-framework.md。测试断言解析结果与文档锚点一致；任何一张表解析
失败即 raise（不裸复制数值副本）。resolve_severe_params 为 D1 裁决逻辑
（锚表命中→锚值；未命中→默认 Severe × E.8 因子；E.8 也无→纯默认）。
"""

import pytest

from dataclasses import replace

from src.path_sheet import engine_dir
from src.concentration_scorer import ConcentrationMetrics
from src.stress_scorer import (
    IssuerFinancials,
    ScenarioResult,
    StressTables,
    TAIL_RISK_WARNING,
    bond_mv_stress,
    concentration_stress,
    load_stress_tables,
    normalize_industry,
    resolve_severe_params,
    reverse_stress,
    run_scenario,
    safety_verdict,
    second_order,
    tail_risk_flag,
)

DEEP_DIVE = engine_dir() / "financial-deep-dive.md"
CONCENTRATION = engine_dir() / "concentration-framework.md"


@pytest.fixture(scope="module")
def tables():
    return load_stress_tables(DEEP_DIVE, CONCENTRATION)


# ---------------- E.1 三场景参数（:216-220） ----------------

def test_scenario_params(tables):
    sp = tables.scenario_params
    assert set(sp) == {"Base", "Bear", "Severe"}
    # Base 行三参数均为「基准」（None）
    assert sp["Base"] == {
        "revenue_change": None,
        "margin_change_pp": None,
        "funding_cost_change_bp": None,
    }
    # Bear：收入 -10%、毛利率 -5pp、融资成本 +100bp
    assert sp["Bear"]["revenue_change"] == -10.0
    assert sp["Bear"]["margin_change_pp"] == -5.0
    assert sp["Bear"]["funding_cost_change_bp"] == 100.0
    # Severe：收入 -30%（尾部全角括注锚点须剥离）、毛利率 -15pp、融资成本 +200bp
    assert sp["Severe"]["revenue_change"] == -30.0
    assert sp["Severe"]["margin_change_pp"] == -15.0
    assert sp["Severe"]["funding_cost_change_bp"] == 200.0


# ---------------- E.1 七行业 Severe 校准锚（:231-239） ----------------

def test_severe_anchors(tables):
    anchors = tables.severe_anchors
    assert len(anchors) == 7
    # 光伏/储能：收入最大降幅 -35%、毛利率最大压缩 -20pp
    assert anchors["光伏/储能"] == {"revenue_change": -35.0, "margin_change_pp": -20.0}
    assert anchors["数据中心"] == {"revenue_change": -15.0, "margin_change_pp": -10.0}


# ---------------- E.8 分行业偏离因子（:352-363） ----------------

def test_deviation_factors(tables):
    factors = tables.deviation_factors
    # 光伏/储能：Bear收入 1.0x、Severe收入 1.2x、Bear毛利率 1.0x、Severe毛利率 1.3x
    pv = factors["光伏/储能"]
    assert pv == {
        "bear_revenue": 1.0,
        "severe_revenue": 1.2,
        "bear_margin": 1.0,
        "severe_margin": 1.3,
    }
    # 新能源车—供应链：Severe收入 1.3x（D1 因子分支测试用例）
    assert factors["新能源车—供应链"]["severe_revenue"] == 1.3
    assert factors["新能源车—供应链"]["severe_margin"] == 1.1
    # 生物医药—Biotech「不适用」→ 四因子均 None（收入端压力测试不适用，改用现金跑道）
    bio = factors["生物医药—Biotech"]
    assert bio == {
        "bear_revenue": None,
        "severe_revenue": None,
        "bear_margin": None,
        "severe_margin": None,
    }


# ---------------- E.5 安全边际四档（:294-299） ----------------

def test_safety_bands(tables):
    bands = tables.safety_bands
    assert len(bands) == 4
    by_emoji = {b["emoji"]: b for b in bands}
    green = by_emoji["🟢"]
    assert green["name"] == "强健"
    # 🟢：利息覆盖 >3.0x（开区间下界）、FCF/利息 >2.0x、现金跑道 >18个月
    assert green["interest_coverage"] == (3.0, None, True, False)
    assert green["fcf_interest"] == (2.0, None, True, False)
    assert green["cash_runway_months"] == (18.0, None, True, False)
    # 🟡：1.5-3.0x 闭区间
    assert by_emoji["🟡"]["interest_coverage"] == (1.5, 3.0, False, False)
    assert by_emoji["🟡"]["cash_runway_months"] == (12.0, 18.0, False, False)
    # 🔴：<1.0x 开区间上界
    assert by_emoji["🔴"]["interest_coverage"] == (None, 1.0, False, True)
    assert by_emoji["🔴"]["cash_runway_months"] == (None, 6.0, False, True)


# ---------------- §9.2 阈值跳升表（concentration-framework.md :777-783） ----------------

def test_threshold_jumps(tables):
    jumps = tables.threshold_jumps
    assert set(jumps) == {
        "市场恐慌(VIX>30)",
        "区域性城投展期潮",
        "评级泡沫破裂",
        "市场窗口冻结",
        "传染矩阵高传染链路激活",
    }
    assert jumps["市场恐慌(VIX>30)"]["dimensions"] == "所有维度"
    assert "上移一个等级" in jumps["市场恐慌(VIX>30)"]["rule"]
    # 评级泡沫破裂：伪高评级阈值收紧至 3%/10%/20%
    assert jumps["评级泡沫破裂"]["dimensions"] == "D₃评级"
    assert "3%/10%/20%" in jumps["评级泡沫破裂"]["rule"]
    assert jumps["传染矩阵高传染链路激活"]["dimensions"] == "D₁行业"


# ---------------- E.10.2 标准情景模板（:508-513） ----------------

def test_mv_scenarios(tables):
    scenarios = tables.mv_scenarios
    assert len(scenarios) == 4
    by_name = {s["name"]: s for s in scenarios}
    assert set(by_name) == {"轻度承压", "中度承压", "严重承压", "极端尾部"}
    tail = by_name["极端尾部"]
    # 极端尾部：无风险利率 +300bp、信用利差 +400bp、多档下调至CCC、概率约 1%
    assert tail["risk_free_bp"] == 300.0
    assert tail["spread_bp"] == 400.0
    assert tail["rating"] == "多档下调至CCC"
    assert tail["liquidity"] == "流动性枯竭"
    assert tail["probability_pct"] == 1.0
    assert by_name["轻度承压"]["probability_pct"] == 20.0


# ---------------- D1：resolve_severe_params 裁决 ----------------

def test_resolve_severe_params_anchor_hit(tables):
    """D1 分支一：E.1 锚表命中行业 → 锚值（不乘 E.8 因子）。"""
    params = resolve_severe_params("光伏/储能", tables)
    assert params["revenue_change"] == -35.0
    assert params["margin_change_pp"] == -20.0
    assert params["source"] == "E.1锚"
    # 锚表不含融资成本校准 → 沿用 E.1 默认 Severe +200bp
    assert params["funding_cost_change_bp"] == 200.0


def test_resolve_severe_params_deviation_factor(tables):
    """D1 分支二：锚表未命中但 E.8 有因子 → 默认 Severe × 偏离因子。"""
    params = resolve_severe_params("新能源车—供应链", tables)
    # -30% × 1.3 = -39%；-15pp × 1.1 = -16.5pp
    assert params["revenue_change"] == pytest.approx(-39.0)
    assert params["margin_change_pp"] == pytest.approx(-16.5)
    assert params["funding_cost_change_bp"] == 200.0
    assert params["source"] == "E.8因子"


def test_resolve_severe_params_pure_default(tables):
    """D1 分支三：E.8 也无该行业 → 纯默认 Severe 参数。"""
    params = resolve_severe_params("纺织服装", tables)
    assert params["revenue_change"] == -30.0
    assert params["margin_change_pp"] == -15.0
    assert params["funding_cost_change_bp"] == 200.0
    assert params["source"] == "默认"


def test_resolve_severe_params_not_applicable(tables):
    """D1 分支三变体：E.8 有该行业但因子「不适用」（Biotech）→ 纯默认 + 注记。"""
    params = resolve_severe_params("生物医药—Biotech", tables)
    assert params["revenue_change"] == -30.0
    assert params["margin_change_pp"] == -15.0
    assert params["source"] == "默认"
    assert "不适用" in params["note"]


# ---------------- 失败即 raise 纪律 ----------------

def test_load_raises_on_truncated_doc(tmp_path):
    """截断文档（缺 E.5 节）时 load_stress_tables 必须 raise，不容忍稀疏结果。"""
    truncated = tmp_path / "financial-deep-dive.md"
    text = DEEP_DIVE.read_text(encoding="utf-8")
    cut = text.find("### E.5")
    assert cut != -1
    truncated.write_text(text[:cut], encoding="utf-8")
    with pytest.raises(ValueError):
        load_stress_tables(truncated, CONCENTRATION)


# ---------------- IssuerFinancials 基础类型 ----------------

def test_issuer_financials_fields():
    fin = IssuerFinancials(
        revenue=100.0,
        gross_margin=0.20,
        period_expenses=8.0,
        tax_rate=0.25,
        da=5.0,
        capex=6.0,
        interest_expense=3.0,
        cash=20.0,
        unused_credit=10.0,
        inventory=15.0,
        dso_days=60.0,
        dio_days=45.0,
    )
    assert fin.revenue == 100.0
    assert fin.dio_days == 45.0


# ================= T2：D5 行业名归一 =================

def test_normalize_industry_key_mapping():
    """D5 映射层：别名 → E.1/E.8 表键；同名行业直取无注记。"""
    assert normalize_industry("新能源车—OEM") == (
        "新能源汽车—OEM", "D5：「新能源车—OEM」归一至表键「新能源汽车—OEM」"
    )
    assert normalize_industry("光伏/储能") == ("光伏/储能", None)
    assert normalize_industry("高端装备/工业母机")[0] == "高端装备/机床"
    assert normalize_industry("数据中心/算力基建")[0] == "数据中心"


def test_normalize_nev_alias_parity(tables):
    """D5 parity 锚点：E.1「新能源汽车—OEM」与 E.8「新能源车—OEM」（文档原文
    两种拼写）归一后产出一致参数；canonical「新能源汽车」同口径。"""
    a = resolve_severe_params("新能源汽车—OEM", tables)
    b = resolve_severe_params("新能源车—OEM", tables)
    c = resolve_severe_params("新能源汽车", tables)
    for params in (a, b, c):
        assert params["source"] == "E.1锚"
        assert params["revenue_change"] == -30.0
        assert params["margin_change_pp"] == -15.0
    # 归一路径留痕
    assert "归一" in b["note"]
    assert "归一" in c["note"]


def test_normalize_semiconductor_bare_and_subtype(tables):
    """D5：半导体裸名 → E.1 锚裸键「半导体/IC」+ 子类型注记；子类型键直取
    （锚表无子类型键 → D1 因子分支）。"""
    bare = resolve_severe_params("半导体/集成电路", tables)
    assert bare["source"] == "E.1锚"
    assert bare["revenue_change"] == -25.0
    assert bare["margin_change_pp"] == -12.0
    assert "子类型" in bare["note"]
    foundry = resolve_severe_params("半导体—Foundry", tables)
    assert foundry["source"] == "E.8因子"
    # -30% × 1.1 = -33%；-15pp × 1.1 = -16.5pp
    assert foundry["revenue_change"] == pytest.approx(-33.0)
    assert foundry["margin_change_pp"] == pytest.approx(-16.5)


def test_normalize_bio_bare_default(tables):
    """D5：生物医药裸名（无 E.1/E.8 裸键）→ D1 默认分支 + 子类型注记。"""
    bare = resolve_severe_params("生物医药/创新药", tables)
    assert bare["source"] == "默认"
    assert bare["revenue_change"] == -30.0
    assert "子类型" in bare["note"]


def test_normalize_canonical_aliases(tables):
    """D5：canonical 13 行业别名 → 锚表键（高端装备/工业母机、数据中心/算力基建）。"""
    equip = resolve_severe_params("高端装备/工业母机", tables)
    assert equip["source"] == "E.1锚"
    assert equip["revenue_change"] == -25.0
    assert equip["margin_change_pp"] == -10.0
    idc = resolve_severe_params("数据中心/算力基建", tables)
    assert idc["source"] == "E.1锚"
    assert idc["revenue_change"] == -15.0


def test_normalize_supply_chain_alias(tables):
    """Fix R2：「新能源汽车—供应链」→ E.8 键「新能源车—供应链」（与 OEM 不同行，
    归一后仍区分）。"""
    sc = resolve_severe_params("新能源汽车—供应链", tables)
    direct = resolve_severe_params("新能源车—供应链", tables)
    assert sc["source"] == "E.8因子"
    assert sc["revenue_change"] == pytest.approx(-39.0)   # -30% × 1.3
    assert sc["margin_change_pp"] == pytest.approx(-16.5)  # -15pp × 1.1
    assert "归一" in sc["note"]
    assert sc["revenue_change"] == direct["revenue_change"]
    # OEM（E.1 锚 -30%）与供应链（E.8 因子 -39%）为不同行，归一不混淆
    assert sc["revenue_change"] != resolve_severe_params("新能源汽车", tables)["revenue_change"]


# ================= T2：E.3 线性传导链 =================

@pytest.fixture
def fin():
    """E.3 算例基准（brief T2 Step 1）：收入 100 亿/毛利率 20%/费用 8 亿/
    税率 25%/D&A 3 亿/Capex 4 亿/利息 2 亿/现金 10 亿。"""
    return IssuerFinancials(
        revenue=100.0,
        gross_margin=0.20,
        period_expenses=8.0,
        tax_rate=0.25,
        da=3.0,
        capex=4.0,
        interest_expense=2.0,
        cash=10.0,
        unused_credit=5.0,
        inventory=20.0,
        dso_days=60.0,
        dio_days=45.0,
    )


def test_run_scenario_base_passthrough(fin, tables):
    """Base 行「基准」（None）= 零冲击：链上各值即基准推导值。"""
    r = run_scenario(fin, tables.scenario_params["Base"], "光伏/储能", tables)
    assert r.revenue == pytest.approx(100.0)
    assert r.gross_profit == pytest.approx(20.0)
    assert r.net_profit == pytest.approx(9.0)        # (20-8) × 0.75
    assert r.cfo == pytest.approx(12.0)
    assert r.fcf == pytest.approx(8.0)
    assert r.interest_coverage == pytest.approx(7.5)  # (20-8+3) / 2
    assert r.second_order_effects == ()


def test_run_scenario_bear_chain(fin, tables):
    """E.3（:264-273）Bear 链（-10%/-5pp/+100bp）逐值复算。"""
    r = run_scenario(fin, tables.scenario_params["Bear"], "光伏/储能", tables)
    assert r.revenue == pytest.approx(90.0)
    assert r.gross_profit == pytest.approx(13.5)      # 90 × (0.20-0.05)
    assert r.ebitda == pytest.approx(8.5)             # 13.5 - 8 + 3
    assert r.net_profit == pytest.approx(4.125)       # (13.5-8) × 0.75
    assert r.cfo == pytest.approx(7.125)              # 4.125 + 3
    assert r.fcf == pytest.approx(3.125)              # 7.125 - 4
    # E.3:271 变动后利息 = 基准 × (1+融资成本变动)，bp→比率直译 ×1.01
    assert r.interest == pytest.approx(2.02)
    assert r.interest_coverage == pytest.approx(8.5 / 2.02)
    assert r.fcf_interest == pytest.approx(3.125 / 2.02)
    assert r.cash_runway_months == 999.0              # D2：fcf≥0 → 999
    assert r.second_order_effects == ()               # 非 Severe 不启用二阶


def test_run_scenario_severe_second_order(fin, tables):
    """Severe（纯默认 -30%/-15pp/+200bp，D1 默认分支）叠加 E.7 二阶修正终值。"""
    params = resolve_severe_params("纺织服装", tables)
    r = run_scenario(fin, params, "纺织服装", tables, severe=True)
    # 线性基链值
    assert r.revenue == pytest.approx(70.0)
    assert r.gross_profit == pytest.approx(3.5)       # 70 × (0.20-0.15)
    assert r.ebitda == pytest.approx(-1.5)            # 3.5 - 8 + 3
    # 二阶效应（E.7 :340-346）
    effects = {e.name: e for e in r.second_order_effects}
    assert effects["存货跌价"].triggered
    assert effects["存货跌价"].amount == pytest.approx(2.0)       # 存货20 × 10%
    wc = 70 / 365 * 20 + 66.5 / 365 * 30                         # 变动后成本=70-3.5
    assert effects["营运资金冻结"].triggered
    assert effects["营运资金冻结"].amount == pytest.approx(wc)
    assert effects["融资成本二阶"].triggered
    assert effects["融资成本二阶"].amount == pytest.approx(0.01)  # 2 × 50bp（D3）
    # 中间 fcf=-15.676、跑道≈7.65<12 → Capex 削减 50%
    assert effects["Capex削减"].triggered
    assert effects["Capex削减"].amount == pytest.approx(2.0)
    assert effects["资产减值注记"].triggered                       # 场景净利<0
    # 二阶修正后终值
    assert r.net_profit == pytest.approx(-5.375)                  # -3.375 - 2
    assert r.cfo == pytest.approx(-0.375 - 2.0 - wc)
    fcf = -0.375 - 2.0 - wc - 4.0 + 2.0
    assert r.fcf == pytest.approx(fcf)
    assert r.interest == pytest.approx(2.05)                      # 2 × 1.025
    assert r.interest_coverage == pytest.approx(-1.5 / 2.05)
    assert r.fcf_interest == pytest.approx(fcf / 2.05)
    assert r.cash_runway_months == pytest.approx(10 / (-fcf / 12))  # D2


# ================= T2：E.7 二阶效应规则 =================

def test_run_scenario_funding_rate_e9_semantics(fin, tables):
    """Fix R1：E.9 口径——基准利率 4% 时 +100bp → ×1.25、+200bp → ×1.5。"""
    fin_r = replace(fin, base_funding_rate=0.04)
    r = run_scenario(fin_r, tables.scenario_params["Bear"], "光伏/储能", tables)
    assert r.interest == pytest.approx(2.5)   # 2 × (1 + 0.01/0.04)
    assert r.note == ""                        # 利率提供 → 无回退注记
    params = resolve_severe_params("纺织服装", tables)
    r = run_scenario(fin_r, params, "纺织服装", tables, severe=True)
    # 一阶 2 × 1.5 = 3.0；二阶 +50bp → 2 × 0.005/0.04 = 0.25 → 3.25
    assert r.interest == pytest.approx(3.25)
    eff = {e.name: e for e in r.second_order_effects}
    assert eff["融资成本二阶"].amount == pytest.approx(0.25)


def test_run_scenario_funding_rate_fallback_note(fin, tables):
    """Fix R1：基准利率缺失 → 回退 E.3 字面口径（×1.01）+ 注记留 LLM 判断。"""
    r = run_scenario(fin, tables.scenario_params["Bear"], "光伏/储能", tables)
    assert r.interest == pytest.approx(2.02)
    assert "基准融资利率缺失" in r.note
    assert "低估冲击" in r.note
    out = reverse_stress(fin, tables.scenario_params["Bear"])
    assert "基准融资利率缺失" in out["note"]


def _params(rev, margin, bp=200.0):
    return {
        "revenue_change": rev,
        "margin_change_pp": margin,
        "funding_cost_change_bp": bp,
    }


def test_second_order_writedown_trigger_strictness(fin, tables):
    """存货跌价：收入降幅>20% 且毛利率压缩>10pp（严格大于，E.7:342）。"""
    # 恰降 20%（非 >20%）不触发，即使毛利率压缩 15pp
    params = _params(-20.0, -15.0)
    base = run_scenario(fin, params, "x", tables)
    eff = {e.name: e for e in second_order(fin, params, base)}
    assert not eff["存货跌价"].triggered
    # 收入 -25% 但毛利率仅压缩 5pp（非 >10pp）不触发
    params = _params(-25.0, -5.0)
    base = run_scenario(fin, params, "x", tables)
    eff = {e.name: e for e in second_order(fin, params, base)}
    assert not eff["存货跌价"].triggered


def test_second_order_freeze_strictness_and_amount(fin, tables):
    """营运资金冻结：收入降幅>25% 严格大于；占用 = 收入/365×20 + 成本/365×30。"""
    params = _params(-25.0, -5.0)  # 恰 25% 不触发
    base = run_scenario(fin, params, "x", tables)
    eff = {e.name: e for e in second_order(fin, params, base)}
    assert not eff["营运资金冻结"].triggered
    params = _params(-26.0, -5.0)  # -26% 触发
    base = run_scenario(fin, params, "x", tables)
    eff = {e.name: e for e in second_order(fin, params, base)}
    assert eff["营运资金冻结"].triggered
    # 变动后收入 74、变动后成本 = 74 - 74×0.15 = 62.9
    assert eff["营运资金冻结"].amount == pytest.approx(74 / 365 * 20 + 62.9 / 365 * 30)


def test_second_order_capex_cut_requires_both_conditions(fin, tables):
    """Capex 削减：FCF<0 且跑道<12 个月双条件（E.7:345）。FCF<0 但跑道充裕不触发。"""
    params = _params(-15.0, -10.0)
    base = run_scenario(fin, params, "x", tables)
    # 线性链：毛利 8.5、净利 0.375、CFO 3.375、FCF -0.625（<0）
    assert base.fcf == pytest.approx(-0.625)
    eff = {e.name: e for e in second_order(fin, params, base)}
    # 跑道 = 10/(0.625/12) = 192 个月 ≥12 → 不触发
    assert not eff["Capex削减"].triggered
    assert not eff["存货跌价"].triggered        # -15% 非 >20%
    assert not eff["资产减值注记"].triggered     # 净利 0.375 > 0
    assert eff["融资成本二阶"].triggered         # D3：Severe 恒触发 +50bp
    assert eff["融资成本二阶"].amount == pytest.approx(0.01)


# ================= T2：E.5 安全边际判定 =================

def _result(coverage, fcf_int, runway):
    return ScenarioResult(
        scenario="Bear",
        industry="测试",
        revenue=0.0,
        gross_profit=0.0,
        ebitda=0.0,
        net_profit=0.0,
        cfo=0.0,
        capex=0.0,
        fcf=0.0,
        interest=1.0,
        interest_coverage=coverage,
        fcf_interest=fcf_int,
        cash_runway_months=runway,
    )


def test_safety_verdict_band_boundaries(tables):
    """E.5 四档边界（:294-299）：">X" 开区间、"X-Y" 闭区间直译。"""
    # 闭区间下界归属本档：3.0x/2.0x/18月 → 全 🟡
    v = safety_verdict(_result(3.0, 2.0, 18.0), tables)
    assert v["interest_coverage"]["emoji"] == "🟡"
    assert v["fcf_interest"]["emoji"] == "🟡"
    assert v["cash_runway_months"]["emoji"] == "🟡"
    assert v["overall"]["emoji"] == "🟡"
    # 严格大于下界 → 全 🟢
    assert safety_verdict(_result(3.01, 2.01, 18.01), tables)["overall"]["emoji"] == "🟢"
    # 1.0x/0.5x/6月 → 全 🟠（闭区间下界）
    assert safety_verdict(_result(1.0, 0.5, 6.0), tables)["overall"]["emoji"] == "🟠"
    # 低于 🟠 下界 → 全 🔴
    assert safety_verdict(_result(0.99, 0.49, 5.99), tables)["overall"]["emoji"] == "🔴"


def test_safety_verdict_overall_is_worst(tables):
    """综合档取三指标最差。"""
    v = safety_verdict(_result(4.0, 3.0, 5.0), tables)  # 🟢/🟢/🔴
    assert v["overall"]["emoji"] == "🔴"
    v = safety_verdict(_result(4.0, 1.2, 20.0), tables)  # 🟢/🟡/🟢
    assert v["overall"]["emoji"] == "🟡"


def test_tail_risk_flag(tables):
    """E.5 补充判定（:301）：Severe 任一指标🔴 → True（警告不降级）。"""
    assert tail_risk_flag(_result(-6.7, -6.0, 4.4), tables) is True   # E.9.6 隆基式全🔴
    assert tail_risk_flag(_result(4.0, 3.0, 5.0), tables) is True     # 单一指标🔴即触发
    assert tail_risk_flag(_result(2.0, 1.5, 15.0), tables) is False
    assert "尾部风险警告" in TAIL_RISK_WARNING
    assert "不自动降级" in TAIL_RISK_WARNING


# ================= T2：E.6 逆向压力测试 =================

def test_reverse_stress(fin, tables):
    """E.6 三临界值代数验证（其他参数取 Bear 档；EBITDA 口径同 E.3/E.9）。"""
    out = reverse_stress(fin, tables.scenario_params["Bear"])
    # 临界收入降幅：变动后利息 2.02、Bear 毛利率 0.15
    # 临界收入 = (2.02+8-3)/0.15 = 46.8 → 可承受降幅 53.2%
    assert out["critical_revenue_drop_pct"] == pytest.approx(53.2)
    # 临界毛利率：Bear 收入 90 → 临界毛利率 = 7.02/90 = 7.8% → 压缩 12.2pp
    assert out["critical_margin_compression_pp"] == pytest.approx(12.2)
    # 临界融资成本升幅：Bear EBITDA 8.5 → x = 8.5/2 - 1 = 3.25
    assert out["critical_funding_cost_rise"] == pytest.approx(3.25)
    assert out["critical_funding_cost_rise_bp"] == pytest.approx(32500.0)


def test_reverse_stress_funding_bp_e9_semantics(fin, tables):
    """Fix R2：E.9 加点口径下临界加点 = rise × 基准融资利率 × 10000；
    缺省回退口径 = rise × 10000（与利息口径自洽）。"""
    fin_r = replace(fin, base_funding_rate=0.04)
    out = reverse_stress(fin_r, tables.scenario_params["Bear"])
    assert out["critical_funding_cost_rise"] == pytest.approx(3.25)
    # E.9 自洽：达成 4.25× 利息放大所需加点 = 3.25 × 4% = 13% = 1300bp
    assert out["critical_funding_cost_rise_bp"] == pytest.approx(1300.0)
    assert "加点口径" in out["note"]
    # 缺省（无基准利率）→ 回退口径
    out = reverse_stress(fin, tables.scenario_params["Bear"])
    assert out["critical_funding_cost_rise_bp"] == pytest.approx(32500.0)
    assert "回退口径" in out["note"]


# ================= T3：§九 压力传导（concentration_stress） =================

_DIMS = ("industry", "region", "rating", "maturity", "channel")


def _low_metrics(**overrides):
    """全绿基准组合（五维评分均 2）。"""
    base = dict(
        hhi=500, cr3=0.30, cr5=0.50, max1=0.15,
        single_province_share=0.10, weak_region_share=0.02,
        aaa_share=0.20, pseudo_high_rating_share=0.01,
        maturity_12m_share=0.20, single_month_peak=0.05,
        top_channel_share=0.30,
    )
    return ConcentrationMetrics(**(base | overrides))


def test_concentration_stress_market_panic_shifts_all_dimensions(tables):
    """市场恐慌：全维度档位上移一级（不重算阈值）→ 五维全绿跳全黄。"""
    out = concentration_stress(_low_metrics(), "市场恐慌(VIX>30)", tables)
    assert out["normal_levels"] == {d: "green" for d in _DIMS}
    assert out["stressed_levels"] == {d: "yellow" for d in _DIMS}
    assert len(out["jumps"]) == 5
    assert all(j["from"] == "green" and j["to"] == "yellow" for j in out["jumps"])
    assert out["composite_normal"] == pytest.approx(2.0)
    assert out["composite_stressed"] == pytest.approx(4.0)
    assert out["triple_concentration"] is False


def test_concentration_stress_market_panic_red_clamped(tables):
    """市场恐慌：🔴封顶——已红维度保持红、不计跳档，综合分不变。"""
    m = _low_metrics(
        hhi=2600, cr3=0.85, cr5=0.92, max1=0.65,
        single_province_share=0.50, weak_region_share=0.35,
        aaa_share=0.75, pseudo_high_rating_share=0.35,
        maturity_12m_share=0.75, single_month_peak=0.35,
        top_channel_share=0.80, top_channel_is_contracting=True,
    )
    out = concentration_stress(m, "市场恐慌(VIX>30)", tables)
    assert out["normal_levels"] == {d: "red" for d in _DIMS}
    assert out["stressed_levels"] == {d: "red" for d in _DIMS}
    assert out["jumps"] == []
    assert out["composite_stressed"] == pytest.approx(out["composite_normal"])
    assert out["triple_concentration"] is True  # 五维皆🔴 ≥3


def test_concentration_stress_lgfv_tightens_weak_region(tables):
    """城投展期潮：D₂ 弱区域阈值 10%/20%/35% → 5%/15%/25% 重算（0.18 跳档）。"""
    out = concentration_stress(
        _low_metrics(weak_region_share=0.18), "区域性城投展期潮", tables
    )
    # 默认：0.18 ∈ [0.10,0.20) → 3（绿）；收紧后：≥0.15 → 7（橙）
    assert out["normal_levels"]["region"] == "green"
    assert out["stressed_levels"]["region"] == "orange"
    assert out["jumps"] == [{"dim": "region", "from": "green", "to": "orange"}]
    assert out["composite_normal"] == pytest.approx(2.2)   # region 3
    assert out["composite_stressed"] == pytest.approx(3.0)  # region 7
    assert out["triple_concentration"] is False


def test_concentration_stress_rating_bubble_triple_concentration(tables):
    """评级泡沫破裂：伪高评级 5%/15%/30% → 3%/10%/20%；三重集中触发/不触发。"""
    # 触发：压力前 2 橙（区域/期限），评级跳橙 → 3 橙 → 三重集中
    m = _low_metrics(
        weak_region_share=0.25, pseudo_high_rating_share=0.12,
        maturity_12m_share=0.60,
    )
    out = concentration_stress(m, "评级泡沫破裂", tables)
    assert out["normal_levels"]["rating"] == "green"
    assert out["stressed_levels"]["rating"] == "orange"
    assert out["jumps"] == [{"dim": "rating", "from": "green", "to": "orange"}]
    assert out["triple_concentration"] is True
    # 不触发：仅评级一维跳橙
    out = concentration_stress(
        _low_metrics(pseudo_high_rating_share=0.12), "评级泡沫破裂", tables
    )
    assert out["stressed_levels"]["rating"] == "orange"
    assert out["triple_concentration"] is False


def test_concentration_stress_window_freeze(tables):
    """市场窗口冻结：D₄ 12个月到期 30%/50%/70% → 20%/40%/60%；
    D₅ 债券渠道>50%即触发警示（警示下界收紧至 50%）。"""
    m = _low_metrics(maturity_12m_share=0.45, top_channel_share=0.55)
    out = concentration_stress(m, "市场窗口冻结", tables)
    # 期限：默认 [0.30,0.50) → 3（绿）；收紧后 ≥0.40 → 7（橙）
    assert out["normal_levels"]["maturity"] == "green"
    assert out["stressed_levels"]["maturity"] == "orange"
    # 渠道：默认 [0.50,0.70) → 3（绿）；收紧后 ≥0.50 → 7（橙）
    assert out["normal_levels"]["channel"] == "green"
    assert out["stressed_levels"]["channel"] == "orange"
    assert {j["dim"] for j in out["jumps"]} == {"maturity", "channel"}
    assert out["triple_concentration"] is False


def test_concentration_stress_contagion_max1_and_llm_passthrough(tables):
    """传染链路激活：D₁ MAX1 上限 20%→15%（操作化为关注下界 25%→15%）；
    「集群A总敞口上限25%」无对应指标 → 注记留 LLM 判断并透传规则原文。"""
    out = concentration_stress(_low_metrics(max1=0.18), "传染矩阵高传染链路激活", tables)
    assert out["normal_levels"]["industry"] == "green"
    assert out["stressed_levels"]["industry"] == "yellow"
    assert out["jumps"] == [{"dim": "industry", "from": "green", "to": "yellow"}]
    assert any("集群A" in n and "留 LLM 判断" in n for n in out["notes"])
    assert any("收紧至15%" in n for n in out["notes"])  # 规则原文透传


def test_concentration_stress_unknown_scenario_raises(tables):
    with pytest.raises(ValueError):
        concentration_stress(_low_metrics(), "不存在的情景", tables)


def test_concentration_stress_anchor_drift_raises(tables):
    """parity 锚点：文档 §9.2 规则文本变更（不含锚点片段）→ 映射失锚即 raise。"""
    bad = replace(tables, threshold_jumps={
        **tables.threshold_jumps,
        "区域性城投展期潮": {"dimensions": "D₂区域", "rule": "规则文本已被改写"},
    })
    with pytest.raises(ValueError):
        concentration_stress(
            _low_metrics(weak_region_share=0.18), "区域性城投展期潮", bad
        )


# ================= T3：E.10 债券市值维度（bond_mv_stress） =================

def test_bond_mv_stress_standard_scenarios(tables):
    """E.10 算例复算：3 年期 YTM=3.5% → D≈2.90；轻度/中度/严重/极端四档 ΔP
    与概率加权总影响（:517 定量估算示例锚点）。"""
    out = bond_mv_stress(3.0, 0.035, tables, None)
    d = 3.0 / 1.035
    assert out["d_approx"] == pytest.approx(d)
    by = {s["name"]: s for s in out["scenarios"]}
    assert set(by) == {"轻度承压", "中度承压", "严重承压", "极端尾部"}
    # ΔYTM = 无风险利率 + 信用利差合计
    assert by["轻度承压"]["delta_ytm"] == pytest.approx(0.01)
    assert by["极端尾部"]["delta_ytm"] == pytest.approx(0.07)
    # ΔP = -D × ΔYTM（精确公式复算）
    assert by["轻度承压"]["delta_p"] == pytest.approx(-d * 0.01)
    assert by["中度承压"]["delta_p"] == pytest.approx(-d * 0.02)
    assert by["严重承压"]["delta_p"] == pytest.approx(-d * 0.04)
    assert by["极端尾部"]["delta_p"] == pytest.approx(-d * 0.07)
    # :517 定量估算示例锚点（文档按 D≈2.90 取整：-2.90%/-5.80%/-11.60%/-20.30%）
    assert by["轻度承压"]["delta_p"] * 100 == pytest.approx(-2.90, abs=0.02)
    assert by["中度承压"]["delta_p"] * 100 == pytest.approx(-5.80, abs=0.02)
    assert by["严重承压"]["delta_p"] * 100 == pytest.approx(-11.60, abs=0.02)
    assert by["极端尾部"]["delta_p"] * 100 == pytest.approx(-20.30, abs=0.02)
    # 概率与加权
    assert by["轻度承压"]["probability"] == pytest.approx(0.20)
    assert by["极端尾部"]["probability"] == pytest.approx(0.01)
    assert by["轻度承压"]["weighted"] == pytest.approx(-d * 0.01 * 0.20)
    total = -(d * 0.01 * 0.20 + d * 0.02 * 0.10 + d * 0.04 * 0.03 + d * 0.07 * 0.01)
    assert out["weighted_total"] == pytest.approx(total)
    # D4 附注（E.10.2 原文）
    assert "独立假设可能低估总影响，误差约10-20%" in out["note"]
    assert out["custom_scenarios"] == []


def test_bond_mv_stress_custom_shocks(tables):
    """自定义冲击：dict 形（含概率→并入加权）与数值形（纯信息不并入）。"""
    out = bond_mv_stress(3.0, 0.035, tables, {
        "自定义冲击": {"delta_ytm_bp": 150.0, "probability_pct": 5.0},
        "纯信息冲击": 250.0,
    })
    d = 3.0 / 1.035
    custom = {s["name"]: s for s in out["custom_scenarios"]}
    assert custom["自定义冲击"]["delta_ytm"] == pytest.approx(0.015)
    assert custom["自定义冲击"]["delta_p"] == pytest.approx(-d * 0.015)
    assert custom["自定义冲击"]["weighted"] == pytest.approx(-d * 0.015 * 0.05)
    assert custom["纯信息冲击"]["delta_p"] == pytest.approx(-d * 0.025)
    assert custom["纯信息冲击"]["probability"] is None
    assert custom["纯信息冲击"]["weighted"] is None
    base_total = -(d * 0.01 * 0.20 + d * 0.02 * 0.10 + d * 0.04 * 0.03 + d * 0.07 * 0.01)
    assert out["weighted_total"] == pytest.approx(base_total - d * 0.015 * 0.05)


def test_bond_mv_stress_validation(tables):
    with pytest.raises(ValueError):
        bond_mv_stress(0.0, 0.035, tables, None)
    with pytest.raises(ValueError):
        bond_mv_stress(3.0, -1.0, tables, None)
    with pytest.raises(ValueError):
        bond_mv_stress(3.0, 0.035, tables, {"坏冲击": {"probability_pct": 5.0}})

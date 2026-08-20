"""WP-M4-04 stress_scorer 解析层测试（T1）。

单一事实源纪律：E.1 三场景参数与七行业校准锚、E.8 偏离因子、E.5 安全边际
四档均运行时解析自 financial-deep-dive.md；§9.2 阈值跳升表运行时解析自
concentration-framework.md。测试断言解析结果与文档锚点一致；任何一张表解析
失败即 raise（不裸复制数值副本）。resolve_severe_params 为 D1 裁决逻辑
（锚表命中→锚值；未命中→默认 Severe × E.8 因子；E.8 也无→纯默认）。
"""

import pytest

from src.path_sheet import engine_dir
from src.stress_scorer import (
    IssuerFinancials,
    StressTables,
    load_stress_tables,
    resolve_severe_params,
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

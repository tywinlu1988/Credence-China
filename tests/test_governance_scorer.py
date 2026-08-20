"""WP-X-04 T1 — governance_scorer 信号规则库测试（TDD 先行）。

parity 锚点（D2 裁决：检测条件异构 → 规则硬编码 + 逐条文档行号锚点，
concentration_scorer 先例）：每条规则的 doc_anchor 指向
dev/engine/governance-fraud-risk.md 的具体行，本测试回读该行断言锚点文本
存在——文档阈值漂移即测试失败。真树测试版本无关：不断言文档版本头。
"""

import re
from pathlib import Path

import pytest

from src.governance_scorer import (
    ALTMAN_Z_HIGH_RISK_THRESHOLD,
    BENEISH_M_MANIPULATION_THRESHOLD,
    CORE_EARNINGS_SUSPICION_THRESHOLD,
    DATA_NOTE_PREFIX,
    DEFAULT_DEMAND_DEPOSIT_RATE,
    RULES,
    RedFlag,
    Strength,
    altman_z,
    beneish_m,
    core_earnings,
    evaluate_signals,
    repayment_willingness,
)

DOC_PATH = (
    Path(__file__).resolve().parent.parent
    / "dev" / "engine" / "governance-fraud-risk.md"
)
DOC_LINES = DOC_PATH.read_text(encoding="utf-8").splitlines()


def _anchor_line(rule) -> str:
    m = re.fullmatch(r"governance-fraud-risk\.md:(\d+)", rule.doc_anchor)
    assert m, f"{rule.id} doc_anchor 格式非法: {rule.doc_anchor!r}"
    return DOC_LINES[int(m.group(1)) - 1]


# 逐条 parity 锚点：rule.id → 文档该行必须包含的锚点文本。
ANCHORS = {
    # §1 财务（:29-:64）
    "FIN-01": "收入增速 × 1.3",
    "FIN-02": "连续8个季度CFO/净利润 < 0.7",
    "FIN-03": "Q4收入占全年 > 40%",
    "FIN-04": "季度末关联交易收入占比激增 > 50%",
    "FIN-05": "非经常性损益/净利润 > 50%",
    "FIN-06": "占前3年利润总和 > 30%",
    "FIN-07": "研发资本化率突然从<30%跳升至>70%",
    "FIN-08": "货币资金余额×活期利率",
    "FIN-09": "其他应收款/总资产 > 5%",
    "FIN-10": "受限资产/总资产 > 30%",
    "FIN-11": "商誉/净资产 > 30%",
    "FIN-12": "审计费用单年增长 > 50%",
    # §2 治理（:86-:124）
    "GOV-01": "已质押比例 > 60%",
    "GOV-02": "实控人质押 > 80%",
    "GOV-03": "近3年内实控人发生变更",
    "GOV-04": "近3年CFO/财务总监更换≥2次",
    "GOV-05": "3名以上核心高管",
    "GOV-06": "连续3任总经理任期均<2年",
    "GOV-07": "独立董事 < 董事会总人数的1/3",
    "GOV-08": "累计金额 > 当前市值50%",
    "GOV-09": "信息披露违规",
    "GOV-10": "标的金额 > 净资产10%",
    # §3 关联（:140-:161）
    "REL-01": "全年关联交易总额 / 营业收入 > 20%",
    "REL-02": "关联交易已经超过自主经营收入",
    "REL-03": "> 10pp",
    "REL-04": "关联销售收入增速 > 总收入增速 × 3",
    "REL-05": "前五大关联供应商占全部关联采购 > 80%",
    "REL-06": "关联方其他应收款/总资产 > 3%",
    "REL-07": "账龄>1年",
    "REL-08": "对外担保余额 / 净资产 > 50%",
    "REL-09": "对外担保总额 / 净资产 > 100%",
    # §4 逃废债（:209/:212）
    "DEBT-01": "母公司负债率突破90%",
    "DEBT-02": "超过30天",
}


def _hit_ids(measured: dict) -> set:
    return {
        f.note.split(" ")[0]
        for f in evaluate_signals(measured)
        if not f.note.startswith(DATA_NOTE_PREFIX)
    }


# --------------------------------------------------------------------------
# Strength 统一枚举（D3）
# --------------------------------------------------------------------------

def test_strength_enum_values_and_ordering():
    assert (
        Strength.LOW
        < Strength.LOW_MID
        < Strength.MID
        < Strength.MID_HIGH
        < Strength.HIGH
        < Strength.VETO
    )
    assert [s.value for s in Strength] == [1, 2, 3, 4, 5, 6]


# --------------------------------------------------------------------------
# 规则集结构 + 逐条 parity 锚点
# --------------------------------------------------------------------------

def test_rules_count_and_unique_ids():
    assert len(RULES) == 33  # 12 财务 + 10 治理 + 9 关联 + 2 逃废债（两档各计一条）
    ids = [r.id for r in RULES]
    assert len(set(ids)) == len(ids)
    assert set(ids) == set(ANCHORS), "规则集与锚点表不一致（漏规则或漏锚点）"


def test_rules_doc_anchor_parity():
    """每条规则的 doc_anchor 行必须包含文档锚点文本（阈值漂移即失败）。"""
    for rule in RULES:
        assert ANCHORS[rule.id] in _anchor_line(rule), (
            f"{rule.id} 锚点 {ANCHORS[rule.id]!r} 不在 {rule.doc_anchor}: "
            f"{_anchor_line(rule)!r}"
        )


def test_rules_strength_mapping():
    """文档信号强度映射：🔴 强 → HIGH，🟡 中 → MID（本规则集仅这两档）。"""
    for rule in RULES:
        assert rule.strength in (Strength.MID, Strength.HIGH), (
            f"{rule.id} 强度 {rule.strength} 超出文档映射"
        )


# --------------------------------------------------------------------------
# §1 财务规则边界
# --------------------------------------------------------------------------

def test_fin01_ar_growth_boundary():
    """应收增速恰 1.3 倍不命中（严格 >），1.31 倍命中（:29）。"""
    assert "FIN-01" not in _hit_ids({"ar_growth": 0.26, "revenue_growth": 0.20})
    assert "FIN-01" in _hit_ids({"ar_growth": 0.262, "revenue_growth": 0.20})


def test_fin02_cfo_net_profit_boundary():
    """CFO/净利 0.69 命中 / 恰 0.7 不命中（严格 <，:30）。"""
    assert "FIN-02" in _hit_ids({"cfo_to_net_profit": 0.69})
    assert "FIN-02" not in _hit_ids({"cfo_to_net_profit": 0.70})


def test_fin03_q4_share_boundary():
    assert "FIN-03" not in _hit_ids({"q4_revenue_share": 0.40})
    assert "FIN-03" in _hit_ids({"q4_revenue_share": 0.41})


def test_fin06_impairment_boundary():
    """减值恰为前 3 年利润 30% 不命中，超出命中（:41）。"""
    base = {"impairment": 0.30, "prior_3y_profit_sum": 1.0}
    assert "FIN-06" not in _hit_ids(base)
    assert "FIN-06" in _hit_ids({"impairment": 0.31, "prior_3y_profit_sum": 1.0})


def test_fin07_rd_capitalization_jump():
    """<30% → >70% 双向严格：0.30 起跳或 0.70 落点均不命中（:42）。"""
    assert "FIN-07" in _hit_ids(
        {"rd_capitalization_prev": 0.29, "rd_capitalization_curr": 0.71}
    )
    assert "FIN-07" not in _hit_ids(
        {"rd_capitalization_prev": 0.30, "rd_capitalization_curr": 0.71}
    )
    assert "FIN-07" not in _hit_ids(
        {"rd_capitalization_prev": 0.29, "rd_capitalization_curr": 0.70}
    )


def test_fin08_cash_interest_mismatch():
    """货币资金×活期利率 vs 利息收入：差异恰 30% 不命中，超出命中（:48）。

    活期利率参数化：默认 0.3%，可经 measured["demand_deposit_rate"] 覆盖。
    """
    assert DEFAULT_DEMAND_DEPOSIT_RATE == pytest.approx(0.003)
    # cash×0.3% = 30 万；利息收入 = 30万/1.3 → 差异恰 30% → 不命中
    exact = {"cash": 100_000_000, "interest_income": 300_000 / 1.3}
    assert "FIN-08" not in _hit_ids(exact)
    hit = {"cash": 100_000_000, "interest_income": 200_000}
    assert "FIN-08" in _hit_ids(hit)
    # 覆盖利率参数：利率 0.1% → 预期 10 万 < 利息 20 万 → 不命中
    override = dict(hit, demand_deposit_rate=0.001)
    assert "FIN-08" not in _hit_ids(override)


# --------------------------------------------------------------------------
# §2 治理规则边界
# --------------------------------------------------------------------------

def test_gov_pledge_two_tiers():
    """质押率 59/61/81 三值两档：61 仅命中 60% 档，81 双档齐中（:86/:87）。"""
    assert "GOV-01" not in _hit_ids({"pledge_ratio": 0.59})
    assert "GOV-02" not in _hit_ids({"pledge_ratio": 0.59})
    assert _hit_ids({"pledge_ratio": 0.61}) == {"GOV-01"}
    assert _hit_ids({"pledge_ratio": 0.81}) == {"GOV-01", "GOV-02"}


def test_gov04_cfo_changes_boundary():
    assert "GOV-04" not in _hit_ids({"cfo_changes_3y": 1})
    assert "GOV-04" in _hit_ids({"cfo_changes_3y": 2})


def test_gov05_exec_departures_boundary():
    assert "GOV-05" not in _hit_ids({"core_exec_departures": 2})
    assert "GOV-05" in _hit_ids({"core_exec_departures": 3})


def test_gov06_gm_tenures():
    """连续 3 任总经理任期均 <2 年才命中：任一任 ≥2 年或不足 3 任不命中（:100）。"""
    assert "GOV-06" in _hit_ids({"gm_recent_tenure_years": (1.5, 1.0, 1.9)})
    assert "GOV-06" not in _hit_ids({"gm_recent_tenure_years": (1.5, 1.0, 2.0)})
    assert "GOV-06" not in _hit_ids({"gm_recent_tenure_years": (1.5, 1.0)})


def test_gov07_independent_directors_boundary():
    """独董恰 1/3 达标不命中（公司法最低要求），低于命中（:108）。"""
    assert "GOV-07" not in _hit_ids({"independent_directors": 3, "board_size": 9})
    assert "GOV-07" in _hit_ids({"independent_directors": 2, "board_size": 9})


# --------------------------------------------------------------------------
# §3 关联规则边界
# --------------------------------------------------------------------------

def test_rel_revenue_two_tiers():
    """关联/收入 19/21/51 三值两档（:140/:141）。"""
    assert "REL-01" not in _hit_ids({"related_txn_to_revenue": 0.19})
    assert _hit_ids({"related_txn_to_revenue": 0.21}) == {"REL-01"}
    assert _hit_ids({"related_txn_to_revenue": 0.51}) == {"REL-01", "REL-02"}


def test_rel03_margin_deviation_boundary():
    """关联毛利率偏离恰 10pp 不命中，10.1pp 命中（双向取绝对值，:142）。"""
    base = {"related_gross_margin": 0.30, "non_related_gross_margin": 0.20}
    assert "REL-03" not in _hit_ids(base)
    assert "REL-03" in _hit_ids(
        {"related_gross_margin": 0.301, "non_related_gross_margin": 0.20}
    )
    assert "REL-03" in _hit_ids(
        {"related_gross_margin": 0.089, "non_related_gross_margin": 0.20}
    )


def test_rel06_related_other_receivables():
    """关联其他应收：>总资产 3% 或绝对额 >5 亿，双轨任一命中（:150）。"""
    # 恰 3% 且不足 5 亿 → 不命中
    assert "REL-06" not in _hit_ids(
        {"related_other_receivables": 300_000_000, "total_assets": 10_000_000_000}
    )
    # 比率 4% → 命中
    assert "REL-06" in _hit_ids(
        {"related_other_receivables": 400_000_000, "total_assets": 10_000_000_000}
    )
    # 比率不足 3% 但 6 亿 → 绝对额轨命中
    assert "REL-06" in _hit_ids(
        {"related_other_receivables": 600_000_000, "total_assets": 100_000_000_000}
    )


def test_rel_guarantee_two_tiers():
    """担保/净资产 49/51/101 三值两档（:159/:161）。"""
    assert "REL-08" not in _hit_ids({"guarantee_to_net_assets": 0.49})
    assert _hit_ids({"guarantee_to_net_assets": 0.51}) == {"REL-08"}
    assert _hit_ids({"guarantee_to_net_assets": 1.01}) == {"REL-08", "REL-09"}


# --------------------------------------------------------------------------
# §4 逃废债机械项边界
# --------------------------------------------------------------------------

def test_debt_boundaries():
    assert "DEBT-01" not in _hit_ids({"parent_debt_ratio": 0.90})
    assert "DEBT-01" in _hit_ids({"parent_debt_ratio": 0.91})
    assert "DEBT-02" not in _hit_ids({"annual_report_delay_days": 30})
    assert "DEBT-02" in _hit_ids({"annual_report_delay_days": 31})


# --------------------------------------------------------------------------
# 4 公式（:73/:74/:76）+ parity 锚点
# --------------------------------------------------------------------------

def test_doc_states_formula_anchors():
    assert "-2.22" in DOC_LINES[72]                       # :73 Beneish
    assert "1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5" in DOC_LINES[73]  # :74 Altman
    assert "1.81" in DOC_LINES[73]
    assert "持续 < 0.5" in DOC_LINES[75]                  # :76 Core Earnings


def test_altman_z_formula_and_threshold():
    """Z = 1.8 → 高风险（<1.81）；Z = 1.9 → 安全（:74）。"""
    z_low = altman_z(0.5, 0.0, 0.0, 0.0, 1.2)   # 0.6 + 1.2 = 1.8
    z_high = altman_z(0.5, 0.0, 0.0, 0.0, 1.3)  # 0.6 + 1.3 = 1.9
    assert z_low == pytest.approx(1.8)
    assert z_high == pytest.approx(1.9)
    assert z_low < ALTMAN_Z_HIGH_RISK_THRESHOLD <= z_high
    # 系数 parity：全 1.0 → 1.2+1.4+3.3+0.6+1.0 = 7.5
    assert altman_z(1, 1, 1, 1, 1) == pytest.approx(7.5)


def test_beneish_m_threshold():
    """8 变量全中性（=1，TATA=0）→ -2.48 不嫌疑；SGI 抬升 → >-2.22 嫌疑（:73）。"""
    neutral = beneish_m(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
    assert neutral == pytest.approx(-2.48)
    assert neutral <= BENEISH_M_MANIPULATION_THRESHOLD
    inflated = beneish_m(1.0, 1.0, 1.0, 1.5, 1.0, 1.0, 0.0, 1.0)
    assert inflated > BENEISH_M_MANIPULATION_THRESHOLD


def test_core_earnings_ratio():
    """（CFO - 非经常）/ 净利：0.4 可疑 / 0.75 正常（:76）；净利为 0 raise。"""
    assert core_earnings(100, 20, 200) == pytest.approx(0.4)
    assert core_earnings(100, 20, 200) < CORE_EARNINGS_SUSPICION_THRESHOLD
    assert core_earnings(170, 20, 200) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        core_earnings(100, 20, 0)


# --------------------------------------------------------------------------
# 还款意愿评分（§4.3 :219-232）
# --------------------------------------------------------------------------

def test_doc_states_willingness_anchors():
    sec = "\n".join(DOC_LINES[218:232])
    for token in ("-30分", "-25分", "-20分", "-80~-100", "-50~-79", "-20~-49", "0~-19"):
        assert token in sec, f"§4.3 missing willingness anchor {token!r}"


def test_repayment_willingness_bands():
    # -75 = 划转30 + 政府25 + 历史20 → 🟠 中高度嫌疑
    assert repayment_willingness(1, 1, 0, 1) == (-75, "🟠 中高度嫌疑")
    # -30 = 仅划转 → 🟡 有风险点
    assert repayment_willingness(1, 0, 0, 0) == (-30, "🟡 有风险点")
    # 档界：-100/-80 🔴、-50 🟠、-49/-20 🟡、-19/0 🟢
    assert repayment_willingness(1, 1, 1, 1) == (-100, "🔴 高度逃废债嫌疑")
    assert repayment_willingness(1, 1, 1, 0)[1] == "🔴 高度逃废债嫌疑"   # -80
    assert repayment_willingness(0, 1, 1, 0) == (-50, "🟠 中高度嫌疑")
    assert repayment_willingness(0, 1, 0, 1) == (-45, "🟡 有风险点")
    assert repayment_willingness(0, 0, 0, 1) == (-20, "🟡 有风险点")
    assert repayment_willingness(0, 0, 0, 0) == (0, "🟢 还款意愿正常")


def test_repayment_willingness_rejects_invalid_input():
    with pytest.raises(ValueError):
        repayment_willingness(2, 0, 0, 0)


# --------------------------------------------------------------------------
# evaluate_signals：命中输出 + 缺失指标 data_note（不静默按 0 处理）
# --------------------------------------------------------------------------

def test_evaluate_signals_hit_flag_fields():
    flags = evaluate_signals({"pledge_ratio": 0.81, "parent_debt_ratio": 0.95})
    hits = {f.note.split(" ")[0]: f for f in flags
            if not f.note.startswith(DATA_NOTE_PREFIX)}
    assert set(hits) == {"GOV-01", "GOV-02", "DEBT-01"}
    for fid, f in hits.items():
        assert isinstance(f, RedFlag)
        assert f.strength == Strength.HIGH
        assert "pledge_ratio=0.81" in f.evidence or "parent_debt_ratio=0.95" in f.evidence
        assert f.source  # 数据来源列非空


def test_evaluate_signals_missing_metric_leaves_data_note():
    flags = evaluate_signals({"pledge_ratio": 0.61})
    notes = [f for f in flags if f.note.startswith(DATA_NOTE_PREFIX)]
    # 33 条规则中，仅 GOV-01/GOV-02 输入齐备（命中/未命中各一），其余 31 条留 data_note
    assert len(notes) == 31
    gov03 = next(f for f in notes if "GOV-03" in f.note)
    assert "controller_changed_within_3y" in gov03.note
    assert "不静默按 0 处理" in gov03.note


def test_evaluate_signals_no_silent_zero_treatment():
    """REL-04：若缺失的 related_sales_growth 被静默按 0 处理，
    0 > 3×(-0.1) 会误命中——必须跳过并留 data_note。"""
    flags = evaluate_signals({"total_revenue_growth": -0.1})
    rel04 = [f for f in flags if "REL-04" in f.note]
    assert len(rel04) == 1
    assert rel04[0].note.startswith(DATA_NOTE_PREFIX)


def test_evaluate_signals_bool_and_enum_rules():
    flags = evaluate_signals({
        "controller_changed_within_3y": True,
        "disclosure_violation_within_3y": False,
        "related_prepayment_aged_over_1y": True,
        "gm_recent_tenure_years": (1.0, 1.5, 1.9),
        "independent_directors": 2,
        "board_size": 9,
    })
    hits = _hit_ids({
        "controller_changed_within_3y": True,
        "disclosure_violation_within_3y": False,
        "related_prepayment_aged_over_1y": True,
        "gm_recent_tenure_years": (1.0, 1.5, 1.9),
        "independent_directors": 2,
        "board_size": 9,
    })
    assert hits == {"GOV-03", "GOV-06", "GOV-07", "REL-07"}
    assert isinstance(flags, list)

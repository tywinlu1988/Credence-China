"""WP-M0-02 lgd_scorer 解析层测试（T1）。

单一事实源纪律：五级表/品种先验/CI 表均从 lgd-recovery-framework.md 运行时
解析（§2.1/§5.1/§11.4），测试断言解析结果与文档锚点一致；SENIORITY_BASE /
DELTA_RANGES / pd_lgd_bounds 为 §3.2/§2.2 硬编码项，测试回读文档文本锚点做
parity 校验（防静默漂移）。
"""

import pytest

from src.lgd_scorer import (
    DELTA_RANGES,
    SENIORITY_BASE,
    CollateralInput,
    EvasionFlags,
    GuaranteeInput,
    LgdResult,
    clamp,
    compute_lgd,
    delta_collateral,
    delta_guarantee,
    delta_industry,
    delta_legal,
    delta_recovery_path,
    load_lgd_tables,
    pd_lgd_bounds,
)
from src.path_sheet import engine_dir

DOC = engine_dir() / "lgd-recovery-framework.md"


@pytest.fixture(scope="module")
def tables():
    return load_lgd_tables(DOC)


# ---------------- 解析层（真实文档漂移门） ----------------

def test_load_lgd_tables(tables):
    # §2.1 五级齐全
    assert len(tables.levels) == 5
    by_name = {row[0]: row for row in tables.levels}
    assert set(by_name) == {"LGD1", "LGD2", "LGD3", "LGD4", "LGD5"}
    # LGD1：预期损失率 <20%，预期回收率 >80%（开区间端点落在 20/80）
    _, loss_low, loss_high, rec_low, rec_high = by_name["LGD1"]
    assert (loss_low, loss_high) == (0.0, 20.0)
    assert (rec_low, rec_high) == (80.0, 100.0)
    # §5.1 品种先验：可交换公司债 → LGD1 - LGD3
    assert tables.bond_priors["可交换公司债"] == ("LGD1", "LGD3")
    # §11.4 CI 表：LGD5 中国调整后回收率范围 2% - 15%
    assert tables.ci_ranges["LGD5"] == (2.0, 15.0)
    assert len(tables.ci_ranges) == 5


# ---------------- PD-LGD 交互约束（§2.2 硬编码 + parity） ----------------

def test_pd_bounds():
    assert pd_lgd_bounds("AA+") == (None, "LGD4")   # AAA-AA → 上限 LGD4
    assert pd_lgd_bounds("BB") == ("LGD2", None)    # BB-B → 下限 LGD2
    assert pd_lgd_bounds("CCC") == ("LGD3", None)   # CCC-D → 下限 LGD3
    assert pd_lgd_bounds("A") == (None, None)       # A-BBB → 无约束
    with pytest.raises(ValueError):
        pd_lgd_bounds("ZZZ")


# ---------------- §3.2 硬编码锚点 parity ----------------

def test_seniority_base_parity():
    text = DOC.read_text(encoding="utf-8")
    # §3.2 公式块文本锚点仍在（文档漂移时本测试先红）
    assert "无担保优先级债券：Base_LGD = 60%" in text
    assert SENIORITY_BASE == {
        "有担保优先": 45.0,
        "无担保优先": 60.0,
        "次级": 75.0,
        "劣后": 90.0,
    }
    # Δ 范围锚点（§3.2 调整项）
    for anchor in ("-25pp 至 +10pp", "-15pp 至 +5pp"):
        assert anchor in text
    assert DELTA_RANGES["collateral"] == (-25.0, 10.0)
    assert DELTA_RANGES["guarantee"] == (-15.0, 5.0)


def test_clamp():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(99.0, 0.0, 10.0) == 10.0


# ---------------- 解析层加固（伪造文档负例） ----------------

_FAKE_LEVELS = """### 2.1 LGD等级定义
| LGD1 | <20% | >80% | a |
| LGD2 | 20% - 40% | 60% - 80% | a |
| LGD3 | 40% - 60% | 40% - 60% | a |
| LGD4 | 60% - 80% | 20% - 40% | a |
| LGD5 | >80% | <20% | a |
"""

_FAKE_CI = """### 11.4 CI
| LGD1 | 85% | 70% - 98% | 65% - 98%（x） |
| LGD2 | 70% | 50% - 85% | 45% - 80%（x） |
| LGD3 | 50% | 30% - 70% | 25% - 65%（x） |
| LGD4 | 25% | 10% - 45% | 10% - 40%（x） |
| LGD5 | 8% | 2% - 20% | 2% - 15%（x） |
"""


def test_bond_priors_row_floor(tmp_path):
    """§5.1 行首加粗丢失 → 解析行数低于下界即 raise（不容忍静默丢行）。"""
    fake = tmp_path / "fake.md"
    fake.write_text(
        _FAKE_LEVELS
        + "### 5.1 品种\n"
        + "\n".join(
            f"| **品种{i}** | x | LGD1 - LGD3 | a |" for i in range(5)  # 仅 5 行 < 下界 8
        )
        + "\n"
        + _FAKE_CI,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="§5.1"):
        load_lgd_tables(fake)


def test_section_anchor_boundary(tmp_path):
    """节号前缀相邻（### 2.10）与正文提及（非行首 ### 2.1）均不得误锚。"""
    fake = tmp_path / "fake.md"
    fake.write_text(
        "### 2.10 诱饵章节（无前缀边界时会被 ### 2\\.1 误锚）\n"
        "| LGD1 | <20% | >80% | a |\n"
        "正文提及 ### 2.1 字样（无行首锁时会被误锚）\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="§2.1 段落缺失"):
        load_lgd_tables(fake)


# ================= T2：五路 Δ 分量 =================

# ---------------- §7.2/§8.2 运行时解析表（结构断言） ----------------

def test_guarantee_industry_tables_loaded(tables):
    # §7.2 八类担保（区间原样保留，保守端在 delta_guarantee 内取）
    assert len(tables.guarantee_deltas) == 8
    assert tables.guarantee_deltas["中债信用增进公司"] == (-15.0, -15.0)
    assert tables.guarantee_deltas["中投保/中证增等专业担保"] == (-10.0, -15.0)
    assert tables.guarantee_deltas["母公司/集团担保（关联担保）"] == (0.0, -5.0)
    # §8.2 八行业
    assert len(tables.industry_deltas) == 8
    assert tables.industry_deltas["生物医药"] == (5.0, 10.0)
    assert tables.industry_deltas["高端装备"] == (0.0, 0.0)


# ---------------- Δ_Collateral ----------------

def _equity(**kw):
    return CollateralInput(kind="equity_pledge", **kw)


def test_collateral_cash_and_none():
    # §6.1.1-6.1.2 区间 -20~-25 取保守端（绝对值最小端 -20）
    item = delta_collateral(CollateralInput(kind="cash_or_treasury"))
    assert item.value == -20.0
    assert "留 LLM 判断" in item.note
    assert delta_collateral(CollateralInput(kind="none")).value == 0.0
    with pytest.raises(ValueError):
        delta_collateral(CollateralInput(kind="bogus_kind"))


def test_equity_pledge_tree_six_branches():
    """§6.1.3 决策树六档各一例（按序首条命中）。"""
    assert delta_collateral(_equity(
        pledge_ratio=45, volatility_30d=20, turnover_rate=2,
    )).value == -20.0
    assert delta_collateral(_equity(
        pledge_ratio=55, volatility_30d=35,
    )).value == -15.0
    assert delta_collateral(_equity(
        pledge_ratio=65, volatility_30d=45,
    )).value == -10.0
    assert delta_collateral(_equity(
        pledge_ratio=75, maintenance_ratio=160,
    )).value == -5.0
    assert delta_collateral(_equity(pledge_ratio=85)).value == 0.0
    assert delta_collateral(_equity(
        pledge_ratio=55, volatility_30d=45, concentration=60,
    )).value == 5.0
    # 控股股东且涉法律纠纷同样触发 +5 档
    assert delta_collateral(_equity(
        pledge_ratio=55, volatility_30d=45,
        pledgor_is_controlling=True, pledgor_in_legal_dispute=True,
    )).value == 5.0


def test_equity_pledge_first_match_order():
    """首条命中：优质三指标与集中度>50% 同时成立时仍取 -20 档。"""
    assert delta_collateral(_equity(
        pledge_ratio=45, volatility_30d=20, turnover_rate=2, concentration=60,
    )).value == -20.0


def test_equity_pledge_uncovered():
    """输入缺失/树覆盖外 → 0 + 低置信注记（留 LLM 判断）。"""
    item = delta_collateral(_equity())
    assert item.value == 0.0
    assert item.confidence == "低"
    assert item.note


def test_real_estate_formula_d2():
    """§6.1.4 公式 + D2 映射（×2/3 取 5pp 档）三算例。"""
    assert delta_collateral(CollateralInput(
        kind="real_estate", ltv=60, city_tier="二线",
    )).value == -15.0
    assert delta_collateral(CollateralInput(
        kind="real_estate", ltv=80, city_tier="三线",
    )).value == -10.0
    assert delta_collateral(CollateralInput(
        kind="real_estate", ltv=90, city_tier="三线及以下",
    )).value == -5.0
    # 缺 LTV → 0 + 低置信
    item = delta_collateral(CollateralInput(kind="real_estate", city_tier="一线"))
    assert item.value == 0.0 and item.confidence == "低"


def test_collateral_manual_kinds():
    """receivables/equipment 取 LLM 落档值并 clamp 到各自区间。"""
    assert delta_collateral(CollateralInput(
        kind="receivables", manual_delta=8,
    )).value == 5.0    # clamp [-5,+5]
    assert delta_collateral(CollateralInput(
        kind="equipment", manual_delta=12,
    )).value == 10.0   # clamp [-5,+10]
    assert delta_collateral(CollateralInput(
        kind="equipment", manual_delta=-3,
    )).value == -3.0
    item = delta_collateral(CollateralInput(kind="receivables"))
    assert item.value == 0.0 and item.confidence == "低"


# ---------------- Δ_Guarantee ----------------

def test_guarantee_eight_types():
    """§7.2 八类取保守端（绝对值最小端）。"""
    expected = {
        "中债信用增进公司": -15.0,
        "中投保/中证增等专业担保": -10.0,
        "省级担保公司": -5.0,
        "母公司/集团担保（独立信用好）": -5.0,
        "母公司/集团担保（关联担保）": 0.0,
        "个人连带责任担保": 0.0,
        "地方政府安慰函/支持函": 0.0,
        "银行备用信用证/保函": -10.0,
    }
    for gtype, val in expected.items():
        item = delta_guarantee(GuaranteeInput(guarantee_type=gtype))
        assert item.value == val, gtype
        assert "留 LLM 判断" in item.note


def test_guarantee_relation_rules():
    """§7.3 关联规则：母担子减半 / 子担母不适用 / 互保减半 / 实控人担保门控。"""
    assert delta_guarantee(GuaranteeInput(
        "中债信用增进公司", relation="母担子",
    )).value == -7.5
    assert delta_guarantee(GuaranteeInput(
        "中债信用增进公司", relation="子担母",
    )).value == 0.0
    assert delta_guarantee(GuaranteeInput(
        "中债信用增进公司", relation="互保",
    )).value == -7.5
    assert delta_guarantee(GuaranteeInput(
        "中债信用增进公司", relation="实控人担保",
    )).value == 0.0
    assert delta_guarantee(GuaranteeInput(
        "中债信用增进公司", relation="实控人担保", executability_confirmed=True,
    )).value == -15.0
    # 无担保 / 未覆盖类型 → 0
    assert delta_guarantee(GuaranteeInput("无")).value == 0.0
    item = delta_guarantee(GuaranteeInput("某未收录担保"))
    assert item.value == 0.0 and item.confidence == "低"


# ---------------- Δ_Industry ----------------

def test_industry_eight_keys_and_uncovered():
    expected = {
        "光伏制造": 5.0,
        "半导体-Foundry": -5.0,
        "半导体-Fabless": 10.0,
        "生物医药": 5.0,      # +5~+10 取保守端
        "数据中心": -5.0,
        "新能源汽车": 10.0,
        "高端装备": 0.0,
        "医疗器械": 0.0,
    }
    for key, val in expected.items():
        assert delta_industry(key).value == val, key
    item = delta_industry("钢铁")
    assert item.value == 0.0
    assert item.confidence == "低"
    assert item.note


# ---------------- Δ_RecoveryPath ----------------

def test_recovery_path_four_scenarios():
    assert delta_recovery_path("重整-资产尚可").value == -5.0
    assert delta_recovery_path("重整-空心化").value == 0.0
    assert delta_recovery_path("清算").value == 5.0       # +5~+10 取保守端
    assert delta_recovery_path("庭外-谈判强").value == 5.0
    item = delta_recovery_path("未知情景")
    assert item.value == 0.0 and item.confidence == "低"


# ---------------- Δ_Legal（§10.3 区域 + §10.2 逃废债） ----------------

_NO_EVASION = EvasionFlags()


def test_legal_region_mapping():
    assert delta_legal("广东", _NO_EVASION).value == -5.0
    assert delta_legal("辽宁省", _NO_EVASION).value == 5.0   # 后缀归一化
    assert delta_legal("浙江", _NO_EVASION).value == -5.0
    shanxi = delta_legal("山西", _NO_EVASION)
    assert shanxi.value == 0.0
    assert "山西" in shanxi.note   # §10.3 Δ 列表未列名 → 0 并注记
    assert delta_legal("甘肃", _NO_EVASION).value == 5.0     # 西部 +5~+10 取保守端


def test_legal_region_west_boundary():
    """西部名单收窄裁决：四川/陕西等边界省份归「其他」0pp + 留 LLM 注记。"""
    for prov in ("四川", "陕西", "重庆", "云南", "贵州", "广西", "内蒙古"):
        item = delta_legal(prov, _NO_EVASION)
        assert item.value == 0.0, prov
        assert "留 LLM 判断" in item.note, prov
    # 收窄后五省区仍取 +5
    for prov in ("甘肃", "青海", "新疆", "宁夏", "西藏"):
        assert delta_legal(prov, _NO_EVASION).value == 5.0, prov


def test_legal_evasion_stacking_and_clamp():
    """两触发 +5+10=+15 → clamp 到 legal 区间上限 +10。"""
    ev = EvasionFlags(major_asset_disposal_6m=True,
                      controller_detained_or_absconded=True)
    assert delta_legal("山西", ev).value == 10.0
    single = EvasionFlags(local_soe_in_prior_evidence_province=True)
    assert delta_legal("山西", single).value == 5.0
    # 区域与逃废债可叠加：广东 -5 + 单触发 +5 → 0
    assert delta_legal("广东", single).value == 0.0


# ---------------- T2 硬编码规则 parity 锚点 ----------------

def test_equity_tree_parity():
    """§6.1.3 决策树六行文本锚点仍在（文档漂移时本测试先红）。"""
    text = DOC.read_text(encoding="utf-8")
    for anchor in (
        "-20pp  IF (质押率<50% AND 波动率<30% AND 换手率>1%)",
        "-15pp  IF (质押率50-60% AND 波动率<40%)",
        "-10pp  IF (质押率60-70% AND 波动率<50%)",
        "-5pp   IF (质押率70-80% AND 维持担保比例>150%)",
        "0pp    IF (质押率>80% OR 维持担保比例<130%)",
        "+5pp   IF (集中度>50% OR 质押方为控股股东且法律纠纷中)",
    ):
        assert anchor in text


def test_real_estate_parity():
    """§6.1.4 系数行 + 三算例锚点（D2 映射的文档依据）。"""
    text = DOC.read_text(encoding="utf-8")
    assert "一线0.75, 二线0.65, 三线及以下0.55" in text
    assert "-21% → Δ_Collateral = -15pp" in text
    assert "-16% → Δ_Collateral = -10pp" in text
    assert "-10.5% → Δ_Collateral = -5pp" in text


def test_recovery_path_parity():
    """§9.4 四情景表行锚点。"""
    text = DOC.read_text(encoding="utf-8")
    assert "| 预计为破产重整，且发行人资产质量尚可 | -5pp |" in text
    assert "| 预计为破产重整，但发行人资产已空心化 | 0pp |" in text
    assert "| 预计为破产清算 | +5pp to +10pp |" in text
    assert "| 预计为庭外重组但发行人谈判能力强 | +5pp |" in text


def test_evasion_block_parity():
    """§10.2 逃废债 if 块四触发锚点。"""
    text = DOC.read_text(encoding="utf-8")
    for anchor in (
        "+5pp   IF (发行人为地方国企且所在省份此前有逃废债案例)",
        "+5pp   IF (发行人在违约前6个月内仍有大额资产处置/分红的)",
        "+10pp  IF (发行人实际控制人已被采取强制措施或境外失联)",
        "+10pp  IF (发行人存在系统性关联交易和资产转移嫌疑)",
    ):
        assert anchor in text


def test_legal_region_parity():
    """§10.3 Δ_Legal 区域列表锚点。"""
    text = DOC.read_text(encoding="utf-8")
    for anchor in (
        "- 北京/上海/广东：-5pp",
        "- 江苏/浙江：-5pp",
        "- 辽宁/吉林/黑龙江：+5pp",
        "- 河南/河北：+5pp",
        "- 西部省份：+5pp to +10pp",
        "- 其他：0pp",
    ):
        assert anchor in text


# ================= T3：compute_lgd 顶层合成 =================
#
# 合成公式（D6 裁决）：LGD = Base + ΣΔ（加法式，Δ 带符号，负值降低 LGD）。
# 管线：Base + ΣΔ → clamp [0,100] → 五级映射（§2.1 运行时 levels，左闭右开）
# → §2.2 PD 约束钳制等级（不回改 lgd_pct 合成原值）→ CI/先验交叉/缺口清单。

def _base_kwargs(**kw):
    """中性默认：无抵押/无担保/高端装备(0pp)/重整-空心化(0pp)/湖北(其他 0pp)/
    无逃废债/A 评级(§2.2 无约束)/公司债（普通）(先验 LGD3-4)。"""
    d = dict(
        seniority="无担保优先",
        collateral=CollateralInput(kind="none"),
        guarantee=GuaranteeInput("无"),
        industry_key="高端装备",
        recovery_scenario="重整-空心化",
        province="湖北",
        evasion=_NO_EVASION,
        pd_rating="A",
        bond_type="公司债（普通）",
    )
    d.update(kw)
    return d


def test_compute_lgd_unsecured_with_cbci_guarantee():
    """brief 算例 1：无担保优先 60 + 中债增担保 -15 = 45% → LGD3，
    落在保证担保先验 LGD2-4 内。"""
    r = compute_lgd(**_base_kwargs(
        guarantee=GuaranteeInput("中债信用增进公司"),
        bond_type="有担保公司债（保证担保）",
    ))
    assert isinstance(r, LgdResult)
    assert r.lgd_pct == 45.0
    assert r.lgd_level == "LGD3"
    assert r.recovery_range == (40.0, 60.0)
    assert r.ci_range == (25.0, 65.0)
    assert r.prior_check == {"expected_range": ("LGD2", "LGD4"), "within_prior": True}


def test_compute_lgd_secured_equity_pledge_lgd1():
    """brief 算例 2：有担保优先 45 + 股权质押优质档 -20 + Foundry -5
    + 上海 -5 = 15% → LGD1。"""
    r = compute_lgd(**_base_kwargs(
        seniority="有担保优先",
        collateral=CollateralInput(
            kind="equity_pledge",
            pledge_ratio=45, volatility_30d=20, turnover_rate=2,
        ),
        industry_key="半导体-Foundry",
        province="上海",
        bond_type="有担保公司债（抵押/质押）",
    ))
    assert r.lgd_pct == 15.0
    assert r.lgd_level == "LGD1"
    assert r.recovery_range == (80.0, 100.0)
    assert r.ci_range == (65.0, 98.0)
    assert r.prior_check["within_prior"] is True


def test_compute_lgd_pd_floor_ccc():
    """brief 算例 3：合成 LGD2（25%）但 CCC 评级下限 LGD3 → 等级钳制至 LGD3，
    lgd_pct 保留合成原值（钳制留痕于 breakdown）。"""
    r = compute_lgd(**_base_kwargs(
        seniority="有担保优先",
        collateral=CollateralInput(kind="cash_or_treasury"),
        pd_rating="CCC",
        bond_type="有担保公司债（抵押/质押）",
    ))
    assert r.lgd_pct == 25.0
    assert r.lgd_level == "LGD3"
    assert r.recovery_range == (40.0, 60.0)
    pd_items = [i for i in r.breakdown if i.name == "PD约束钳制"]
    assert len(pd_items) == 1
    assert "CCC" in pd_items[0].note and "LGD3" in pd_items[0].note


def test_compute_lgd_subordinated_liquidation_liaoning():
    """brief 算例 4：次级 75 + 清算 +5 + 辽宁 +5 = 85% → LGD5。"""
    r = compute_lgd(**_base_kwargs(
        seniority="次级",
        recovery_scenario="清算",
        province="辽宁",
        pd_rating="B",
        bond_type="次级债券/二级资本债",
    ))
    assert r.lgd_pct == 85.0
    assert r.lgd_level == "LGD5"
    assert r.recovery_range == (0.0, 20.0)
    assert r.ci_range == (2.0, 15.0)
    assert r.prior_check == {"expected_range": ("LGD4", "LGD5"), "within_prior": True}


def test_compute_lgd_prior_out_of_range():
    """prior_check 越界：LGD5 落在保证担保先验 LGD2-4 之外 → within_prior False。"""
    r = compute_lgd(**_base_kwargs(
        seniority="次级", recovery_scenario="清算", province="辽宁",
        pd_rating="B", bond_type="有担保公司债（保证担保）",
    ))
    assert r.lgd_level == "LGD5"
    assert r.prior_check == {"expected_range": ("LGD2", "LGD4"), "within_prior": False}


def test_compute_lgd_breakdown_structure():
    """breakdown = Base_LGD + 五路 Δ（全中性输入 → 60% → 边界 60 左闭 → LGD4）。"""
    r = compute_lgd(**_base_kwargs())
    names = [i.name for i in r.breakdown]
    assert names == [
        "Base_LGD", "Δ_Collateral", "Δ_Guarantee",
        "Δ_Industry", "Δ_RecoveryPath", "Δ_Legal",
    ]
    assert r.breakdown[0].value == 60.0
    assert r.lgd_pct == 60.0 and r.lgd_level == "LGD4"


def test_compute_lgd_level_boundary_left_closed():
    """五级映射左闭右开：40% → LGD3（非 LGD2）。"""
    r = compute_lgd(**_base_kwargs(
        collateral=CollateralInput(kind="cash_or_treasury"),  # 60 - 20 = 40
    ))
    assert r.lgd_pct == 40.0 and r.lgd_level == "LGD3"


def test_compute_lgd_pd_cap_aaa():
    """AAA 上限 LGD4：合成 85%（LGD5）钳制至 LGD4（仍落次级先验 LGD4-5 内）。"""
    r = compute_lgd(**_base_kwargs(
        seniority="次级", recovery_scenario="清算", province="辽宁",
        pd_rating="AAA", bond_type="次级债券/二级资本债",
    ))
    assert r.lgd_pct == 85.0
    assert r.lgd_level == "LGD4"
    assert r.prior_check["within_prior"] is True


def test_compute_lgd_clamp_upper_100():
    """劣后 90 + 新能源汽车 +10 + 清算 +5 = 105 → clamp 100 → LGD5。"""
    r = compute_lgd(**_base_kwargs(
        seniority="劣后", industry_key="新能源汽车", recovery_scenario="清算",
        pd_rating="B", bond_type="资产支持证券次级/劣后",
    ))
    assert r.lgd_pct == 100.0 and r.lgd_level == "LGD5"
    assert r.prior_check == {"expected_range": ("LGD5", "LGD5"), "within_prior": True}


def test_compute_lgd_out_of_scope_and_data_gaps():
    """覆盖外输入 → out_of_scope；缺输入 → data_gaps。"""
    r = compute_lgd(**_base_kwargs(industry_key="钢铁", bond_type="某未收录品种"))
    assert any("Δ_Industry" in e for e in r.out_of_scope)
    assert any("某未收录品种" in e for e in r.out_of_scope)
    assert r.prior_check == {"expected_range": None, "within_prior": None}
    # 房地产缺 LTV → 低置信缺口入 data_gaps
    r2 = compute_lgd(**_base_kwargs(
        collateral=CollateralInput(kind="real_estate", city_tier="一线"),
    ))
    assert any("Δ_Collateral" in e for e in r2.data_gaps)


def test_compute_lgd_unknown_seniority():
    with pytest.raises(ValueError):
        compute_lgd(**_base_kwargs(seniority="超级优先"))


def test_formula_sign_parity():
    """§3.2 公式为加法式（D6 裁决修正减号笔误）+ 修正注记在档。"""
    text = DOC.read_text(encoding="utf-8")
    assert "LGD估计值 = Base_LGD  +  Adjustments" in text
    assert "LGD估计值 = Base_LGD  -  Adjustments" not in text
    assert "修正原文减号笔误，与 Δ 语义及 §5.1 先验对齐" in text

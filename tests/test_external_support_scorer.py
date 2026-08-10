"""WP-M0-02 external_support_scorer 测试（T4 能力侧 + T5 意愿/合成/门控/陷阱）。

单一事实源纪律：§4.1 关键指标阈值参考表（6 指标 × 4 档）、§3.2 矩阵使用规则、
§6.1 支持强度判定矩阵、§6.2 上调幅度映射、§7.3 陷阱信号行动规则、§8.2 政策信号
映射均从 external-support-framework.md 运行时解析，测试断言解析结果与文档锚点
一致；INDICATOR_TO_FACTOR 为 §4.1 四维模型表结构归属（硬编码 + 本文件回读锚点
parity 校验，防静默漂移）。

边界语义（与实现 docstring 同源）：">X"/"<X" 为开区间端点（如 3000亿 落
中等档），"X-Y" 为闭区间；矩阵分档 D5 左闭右开（强/高 [2.5,3.0]、中 [1.5,2.5)、
弱/低 [0,1.5)）；断言数值全部来自文档表格当前内容，版本无关。
"""

import dataclasses
import re

import pytest

from src.external_support_scorer import (
    INDICATOR_TO_FACTOR,
    SupportInput,
    SupportResult,
    SupportTables,
    capacity_score,
    compute_support,
    load_support_tables,
    score_indicator,
    willingness_score,
)
from src.path_sheet import engine_dir

DOC = engine_dir() / "external-support-framework.md"


@pytest.fixture(scope="module")
def tables():
    return load_support_tables(DOC)


# ---------------- 解析层（真实文档漂移门） ----------------

def test_load_support_tables(tables):
    assert isinstance(tables, SupportTables)
    # §4.1 阈值分档表六指标齐全，每指标 4 档（3→0 降序）
    assert set(tables.thresholds) == set(INDICATOR_TO_FACTOR)
    assert len(tables.thresholds) == 6
    for name, tiers in tables.thresholds.items():
        assert len(tiers) == 4
        assert [t.score for t in tiers] == [3, 2, 1, 0]
    # 一般公共预算收入：>3000亿 / 1000-3000亿 / 300-1000亿 / <300亿
    rev = {t.score: t for t in tables.thresholds["一般公共预算收入"]}
    assert rev[3].lo == 3000.0 and rev[3].lo_open and rev[3].hi is None
    assert (rev[2].lo, rev[2].hi) == (1000.0, 3000.0)
    assert (rev[1].lo, rev[1].hi) == (300.0, 1000.0)
    assert rev[0].hi == 300.0 and rev[0].hi_open and rev[0].lo is None
    # 人口趋势为枚举档，四档标签与文档一致
    pop = tables.thresholds["人口趋势"]
    assert [t.label for t in pop] == ["持续净流入", "波动平衡", "持续净流出", "大幅净流出"]
    assert all(t.lo is None and t.hi is None for t in pop)
    # §3.2 矩阵使用规则：A/B/C/D 四区齐全（T5 运行时解析）
    assert set(tables.matrix_rules) == {"A", "B", "C", "D"}
    assert tables.matrix_rules["A"]["confidence"] == "高（80-90%）"
    assert tables.matrix_rules["A"]["uplift_text"] == "+2~3子级"
    assert tables.matrix_rules["D"]["uplift_text"] == "0"
    assert "支持方实力强且意愿明确" in tables.matrix_rules["A"]["annotation"]
    # §6.1 支持强度判定 3×3 矩阵（意愿行 × 能力列）
    assert tables.strength_matrix == {
        "高": {"强": "非常高", "中": "高", "弱": "中等"},
        "中": {"强": "高", "中": "中等", "弱": "低"},
        "低": {"强": "中等", "中": "低", "弱": "低/无"},
    }
    # §6.2 上调幅度映射（子级区间）
    assert tables.uplift_map == {
        "非常高": (2, 3), "高": (1, 2), "中等": (0, 1), "低/无": (0, 0),
    }
    # §7.3 陷阱信号行动规则 4 条（kind 结构归类 + 文档原文留痕）
    assert len(tables.trap_actions) == 4
    assert sorted(r["kind"] for r in tables.trap_actions) == [
        "fiscal", "orange2", "orange_asset", "red",
    ]
    red = next(r for r in tables.trap_actions if r["kind"] == "red")
    assert "🔴" in red["trigger"] and "重新评估" in red["response"]
    # §8.2 政策信号映射（行数下界校验 + 方向锚点）
    assert len(tables.policy_map) >= 9
    assert tables.policy_map["中央转移支付增加"] == "正向"
    assert tables.policy_map["省内其他国企违约未获救助"] == "极负向"
    assert tables.policy_map['隐性债务化解"清零"要求'] == "负向"


def test_indicator_to_factor_parity():
    # §4.1 四维模型表结构归属锚点（文档漂移时本测试先红）
    text = DOC.read_text(encoding="utf-8")
    for anchor in ("**F1 财政实力**", "**F2 债务负担**", "**F3 经济基础**", "**F4 资源调动能力**"):
        assert anchor in text
    assert INDICATOR_TO_FACTOR == {
        "一般公共预算收入": "F1",
        "财政自给率": "F1",
        "政府显性债务率": "F2",
        "GDP增速": "F3",
        "人口趋势": "F3",
        "转移支付依赖度": "F4",
    }


# ---------------- 分档函数（§4.1 阈值表） ----------------

def test_score_revenue(tables):
    assert score_indicator("一般公共预算收入", 4000, tables) == 3
    assert score_indicator("一般公共预算收入", 2500, tables) == 2
    assert score_indicator("一般公共预算收入", 500, tables) == 1
    assert score_indicator("一般公共预算收入", 200, tables) == 0
    # 边界：">3000亿" 为开区间 → 3000 落中等档（闭区间 "1000-3000亿"）
    assert score_indicator("一般公共预算收入", 3000, tables) == 2


def test_score_self_sufficiency(tables):
    assert score_indicator("财政自给率", 75, tables) == 2
    assert score_indicator("财政自给率", 85, tables) == 3
    assert score_indicator("财政自给率", 40, tables) == 1
    assert score_indicator("财政自给率", 20, tables) == 0
    assert score_indicator("财政自给率", 80, tables) == 2  # ">80%" 开区间


def test_score_debt_ratio(tables):
    # 政府显性债务率为反向指标（越低越强）：<80%→3 / 80-150%→2 / 150-250%→1 / >250%→0
    assert score_indicator("政府显性债务率", 90, tables) == 2
    assert score_indicator("政府显性债务率", 260, tables) == 0
    assert score_indicator("政府显性债务率", 70, tables) == 3
    assert score_indicator("政府显性债务率", 200, tables) == 1


def test_score_gdp_growth(tables):
    assert score_indicator("GDP增速", 5, tables) == 2
    assert score_indicator("GDP增速", 7, tables) == 3
    assert score_indicator("GDP增速", 3, tables) == 1
    assert score_indicator("GDP增速", 1, tables) == 0     # "<2%或负增长" → 极弱档
    assert score_indicator("GDP增速", -1, tables) == 0    # 负增长同档


def test_score_transfer_dependency(tables):
    # 转移支付依赖度为反向指标：<20%→3 / 20-40%→2 / 40-60%→1 / >60%→0
    assert score_indicator("转移支付依赖度", 15, tables) == 3
    assert score_indicator("转移支付依赖度", 55, tables) == 1
    assert score_indicator("转移支付依赖度", 30, tables) == 2
    assert score_indicator("转移支付依赖度", 65, tables) == 0


def test_score_population_enum(tables):
    assert score_indicator("人口趋势", "持续净流入", tables) == 3
    assert score_indicator("人口趋势", "波动平衡", tables) == 2
    assert score_indicator("人口趋势", "持续净流出", tables) == 1
    assert score_indicator("人口趋势", "大幅净流出", tables) == 0
    with pytest.raises(ValueError):
        score_indicator("人口趋势", "净流入", tables)  # 非枚举原文
    with pytest.raises(ValueError):
        score_indicator("人口趋势", 3, tables)         # 枚举档不收数值


def test_score_unknown_indicator(tables):
    with pytest.raises(ValueError):
        score_indicator("人均GDP", 10, tables)  # §4.1 阈值表未收录（四维表有、阈值表无）
    with pytest.raises(ValueError):
        score_indicator("财政自给率", "高", tables)  # 数值档不收字符串


# ---------------- capacity 合成（六指标 → F 均值 → capacity 均值） ----------------

def test_capacity_score_full(tables):
    result = capacity_score({
        "一般公共预算收入": 4000,   # 3
        "财政自给率": 75,           # 2 → F1 = 2.5
        "政府显性债务率": 90,       # 2 → F2 = 2.0
        "GDP增速": 5,               # 2
        "人口趋势": "持续净流入",   # 3 → F3 = 2.5
        "转移支付依赖度": 15,       # 3 → F4 = 3.0
    }, tables)
    assert result["F1"] == pytest.approx(2.5)
    assert result["F2"] == pytest.approx(2.0)
    assert result["F3"] == pytest.approx(2.5)
    assert result["F4"] == pytest.approx(3.0)
    assert result["capacity"] == pytest.approx(2.5)  # (2.5+2.0+2.5+3.0)/4
    per = {e["indicator"]: e for e in result["per_indicator"]}
    assert len(per) == 6
    assert per["一般公共预算收入"]["score"] == 3
    assert per["人口趋势"]["factor"] == "F3"


def test_capacity_score_partial(tables):
    # 缺输入：F 均值按已提供指标计算，缺项 score=None 且注记（不静默填补）
    result = capacity_score({"一般公共预算收入": 4000}, tables)
    assert result["F1"] == pytest.approx(3.0)
    assert result["F2"] is None and result["F3"] is None and result["F4"] is None
    assert result["capacity"] == pytest.approx(3.0)  # 仅 F1 可用
    per = {e["indicator"]: e for e in result["per_indicator"]}
    assert per["财政自给率"]["score"] is None
    assert "缺输入" in per["财政自给率"]["note"]
    with pytest.raises(ValueError):
        capacity_score({"人均GDP": 10}, tables)


# ---------------- 解析层加固（伪造文档负例） ----------------

_FAKE_SECTION = """### 4.1 地方政府支持能力评估（四维模型）

**关键指标阈值参考**：

| 指标 | 强（3分） | 中等（2分） | 弱（1分） | 极弱（0分） |
|------|----------|-----------|----------|-----------|
| 一般公共预算收入 | >3000亿 | 1000-3000亿 | 300-1000亿 | <300亿 |
| 财政自给率 | >80% | 50-80% | 30-50% | <30% |
| 政府显性债务率 | <80% | 80-150% | 150-250% | >250% |
| GDP增速（近3年均值） | >6% | 4-6% | 2-4% | <2%或负增长 |
| 转移支付依赖度 | <20% | 20-40% | 40-60% | >60% |
"""


def test_threshold_row_floor(tmp_path):
    """§4.1 阈值表缺行（人口趋势丢失）→ 解析即 raise（不容忍静默丢行）。"""
    fake = tmp_path / "fake.md"
    fake.write_text(_FAKE_SECTION, encoding="utf-8")  # 仅 5 行，缺人口趋势
    with pytest.raises(ValueError, match="人口趋势"):
        load_support_tables(fake)


def test_threshold_header_missing(tmp_path):
    """§4.1 表头漂移（档位列名改动）→ 解析即 raise。"""
    fake = tmp_path / "fake.md"
    fake.write_text(
        _FAKE_SECTION.replace("强（3分）", "很强（3分）")
        + "| 人口趋势 | 持续净流入 | 波动平衡 | 持续净流出 | 大幅净流出 |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="表头"):
        load_support_tables(fake)


def test_section_missing(tmp_path):
    fake = tmp_path / "fake.md"
    fake.write_text("### 4.2 其他\n| x | y |\n", encoding="utf-8")
    with pytest.raises(ValueError, match="4.1"):
        load_support_tables(fake)


def test_threshold_duplicate_row(tmp_path):
    """§4.1 阈值表重行（财政自给率出现两次）→ 解析即 raise（防静默覆盖）。"""
    fake = tmp_path / "fake.md"
    fake.write_text(
        _FAKE_SECTION
        + "| 人口趋势 | 持续净流入 | 波动平衡 | 持续净流出 | 大幅净流出 |\n"
        + "| 财政自给率 | >80% | 50-80% | 30-50% | <30% |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="重复出现"):
        load_support_tables(fake)


def test_threshold_unit_mixed(tmp_path):
    """§4.1 阈值表行内单位不一致（% 与 亿 混排）→ 解析即 raise（疑似表格错位）。"""
    fake = tmp_path / "fake.md"
    fake.write_text(
        _FAKE_SECTION.replace("50-80%", "50-80亿")
        + "| 人口趋势 | 持续净流入 | 波动平衡 | 持续净流出 | 大幅净流出 |\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="单位不一致"):
        load_support_tables(fake)


def test_indicator_attribution_parity():
    """parity 加深：§4.1 四维模型表逐块回读，验证六指标 → F1-F4 归属关系。

    以 "**F1 财政实力**" 等行首加粗锚点切片各维度块，核对每个阈值表指标落在
    INDICATOR_TO_FACTOR 声明的维度块内（GDP增速 在四维表行名为 "GDP总量及增速"）。
    """
    text = DOC.read_text(encoding="utf-8")
    anchors = ["**F1 财政实力**", "**F2 债务负担**", "**F3 经济基础**", "**F4 资源调动能力**"]
    pos = [text.index(a) for a in anchors]
    pos.append(text.index("**关键指标阈值参考**"))  # F4 块右界
    blocks = {f: text[pos[i]:pos[i + 1]] for i, f in enumerate(("F1", "F2", "F3", "F4"))}
    expected = {
        "F1": ["一般公共预算收入", "财政自给率"],
        "F2": ["政府显性债务率"],
        "F3": ["GDP总量及增速", "人口趋势"],  # GDP增速（阈值表行名归一）四维表原文
        "F4": ["转移支付依赖度"],
    }
    for factor, names in expected.items():
        for n in names:
            assert n in blocks[factor], f"{n} 未落入 {factor} 块（归属漂移）"
    # 反向抽查：F2 指标不得出现在 F1 块
    assert "政府显性债务率" not in blocks["F1"]
    assert "转移支付依赖度" not in blocks["F3"]


# ================= T5：意愿等权 + 合成 + 门控 + 陷阱 =================

# 指标组合（档位分数见 §4.1 阈值表；capacity = 可用 F 均值）
ALL_STRONG = {  # 全 3 分 → capacity 3.0（强）
    "一般公共预算收入": 4000, "财政自给率": 85, "政府显性债务率": 70,
    "GDP增速": 7, "人口趋势": "持续净流入", "转移支付依赖度": 15,
}
ALL_MID = {  # 全 2 分 → capacity 2.0（中）
    "一般公共预算收入": 2500, "财政自给率": 75, "政府显性债务率": 90,
    "GDP增速": 5, "人口趋势": "波动平衡", "转移支付依赖度": 30,
}
ALL_WEAK = {  # 全 1 分 → capacity 1.0（弱）
    "一般公共预算收入": 500, "财政自给率": 40, "政府显性债务率": 200,
    "GDP增速": 3, "人口趋势": "持续净流出", "转移支付依赖度": 55,
}
CAP_2_5 = {  # F=(2.5, 2.0, 2.5, 3.0) → capacity 2.5（D5 强档下界）
    "一般公共预算收入": 4000, "财政自给率": 75, "政府显性债务率": 90,
    "GDP增速": 5, "人口趋势": "持续净流入", "转移支付依赖度": 15,
}


def _signals(strong=0, mid=0, weak=0):
    """D1 意愿信号：强=3 / 中=1.5 / 弱=0。"""
    sig = {}
    for i in range(strong):
        sig[f"维度强{i}"] = "强"
    for i in range(mid):
        sig[f"维度中{i}"] = "中"
    for i in range(weak):
        sig[f"维度弱{i}"] = "弱"
    return sig


def _inp(**kw):
    """默认输入：能力 3.0（强）× 意愿 3.0（高）+ L5 + 中央政府 + standalone A+。

    无陷阱时：强度 非常高 → +2~3 子级取上限 3 → A+ +3 = AA+（不受上限约束）。
    """
    base = dict(
        support_type="政府支持",
        indicators=ALL_STRONG,
        willingness_signals=_signals(strong=3),
        signal_level="L5",
        standalone_rating="A+",
        supporter_is_central_gov=True,
    )
    base.update(kw)
    return SupportInput(**base)


# ---------------- 意愿等权评分（D1） ----------------

def test_willingness_score():
    # brief 算例：三强一弱 → (3×3+0)/4 = 2.25
    assert willingness_score(_signals(strong=3, weak=1)) == pytest.approx(2.25)
    assert willingness_score(_signals(mid=4)) == pytest.approx(1.5)
    assert willingness_score(_signals(strong=1, mid=1, weak=1)) == pytest.approx(1.5)
    assert willingness_score(_signals(strong=2)) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        willingness_score({})  # 空信号不静默
    with pytest.raises(ValueError):
        willingness_score({"维度": "很强"})  # 非法档位


# ---------------- §6.1 矩阵九象限（D5 分档） ----------------

@pytest.mark.parametrize("indicators,sigs,expected", [
    (ALL_STRONG, _signals(strong=2), "非常高"),  # 意愿高 × 能力强
    (ALL_STRONG, _signals(mid=2), "高"),         # 意愿中 × 能力强
    (ALL_STRONG, _signals(weak=2), "中等"),      # 意愿低 × 能力强
    (ALL_MID, _signals(strong=2), "高"),
    (ALL_MID, _signals(mid=2), "中等"),
    (ALL_MID, _signals(weak=2), "低"),
    (ALL_WEAK, _signals(strong=2), "中等"),
    (ALL_WEAK, _signals(mid=2), "低"),
    (ALL_WEAK, _signals(weak=2), "低/无"),
])
def test_strength_matrix_quadrants(tables, indicators, sigs, expected):
    r = compute_support(_inp(indicators=indicators, willingness_signals=sigs), tables)
    assert isinstance(r, SupportResult)
    assert r.strength == expected


def test_d5_band_boundaries(tables):
    # 2.5 左闭入强/高档
    r = compute_support(
        _inp(indicators=CAP_2_5, willingness_signals=_signals(strong=2, mid=1)), tables,
    )
    assert r.capacity == pytest.approx(2.5) and r.capacity_band == "强"
    assert r.willingness == pytest.approx(2.5) and r.willingness_band == "高"
    assert r.strength == "非常高"
    # 1.5 左闭入中档（capacity 部分缺输入：仅 F1 可用，(2+1)/2=1.5）
    r2 = compute_support(_inp(
        indicators={"一般公共预算收入": 2500, "财政自给率": 40},
        willingness_signals=_signals(mid=1),
    ), tables)
    assert r2.capacity == pytest.approx(1.5) and r2.capacity_band == "中"
    assert r2.willingness == pytest.approx(1.5) and r2.willingness_band == "中"
    assert r2.strength == "中等"  # 意愿中 × 能力中


# ---------------- §6.2 上调区间 + D4 落点 ----------------

def test_uplift_very_high_upper(tables):
    # 意愿 2.6（11强4中：(33+6)/15）≥2.5 → 非常高 +2~3 取上限 +3
    r = compute_support(_inp(willingness_signals=_signals(strong=11, mid=4)), tables)
    assert r.willingness == pytest.approx(2.6)
    assert r.strength == "非常高" and r.uplift_notches == 3
    assert r.final_rating == "AA+" and not r.capped  # A+ +3 子级（D3 档序步进）
    assert r.disclaimer["region"] == "A"
    assert r.confidence == tables.matrix_rules["A"]["confidence"]


def test_uplift_high_midpoint(tables):
    # 意愿 1.6（1强14中：(3+21)/15）∈[1.5,2.5) → 高 +1~2 取中位 round(1.5)=2
    r = compute_support(_inp(
        willingness_signals=_signals(strong=1, mid=14), standalone_rating="BBB+",
    ), tables)
    assert r.willingness == pytest.approx(1.6) and r.willingness_band == "中"
    assert r.strength == "高" and r.uplift_notches == 2
    assert r.final_rating == "A"  # BBB+ +2 子级


def test_uplift_clamp_3(tables):
    # §6.4 单次上限 ≤3 子级（篡改映射表触发防御 clamp，非文档行为）
    tampered = dataclasses.replace(
        tables, uplift_map={**tables.uplift_map, "非常高": (4, 5)},
    )
    r = compute_support(_inp(), tampered)
    assert r.uplift_notches == 3


# ---------------- 门控（§5.1 信号等级 / §6.4 最低触发条件） ----------------

def test_gate_signal_level(tables):
    for lv in ("L1", "L2"):
        r = compute_support(_inp(signal_level=lv), tables)
        assert r.uplift_notches == 0 and r.final_rating == "A+"
        assert any(lv in g and "需关注" in g for g in r.gate_reasons)


def test_gate_strength(tables):
    # 意愿 1.2（4中1弱：6/5）低 × 能力强 → 中等 → 未达"高/非常高"触发条件 → 0
    r = compute_support(_inp(willingness_signals=_signals(mid=4, weak=1)), tables)
    assert r.willingness == pytest.approx(1.2)
    assert r.strength == "中等" and r.uplift_notches == 0
    assert r.final_rating == "A+"
    assert any("最低触发条件" in g for g in r.gate_reasons)


# ---------------- 支持方上限（§6.3） ----------------

def test_supporter_cap(tables):
    # standalone AA- +2 子级 = AA+（D3：0.5 分/子级 × 18 档步进），支持方 AA- → 压回 AA-
    r = compute_support(_inp(
        willingness_signals=_signals(strong=1, mid=14),
        standalone_rating="AA-", supporter_is_central_gov=False, supporter_rating="AA-",
    ), tables)
    assert r.uplift_notches == 2
    assert r.final_rating == "AA-" and r.capped
    # 中央政府例外：上限 = 主权评级 AAA → 不封顶
    r2 = compute_support(_inp(
        willingness_signals=_signals(strong=1, mid=14), standalone_rating="AA-",
    ), tables)
    assert r2.final_rating == "AA+" and not r2.capped


def test_supporter_missing_note(tables):
    # 支持方评级缺失：上限原则不适用，留注记（不静默封顶/不静默跳过）
    r = compute_support(
        _inp(supporter_is_central_gov=False, supporter_rating=None), tables,
    )
    assert r.uplift_notches == 3 and r.final_rating == "AA+" and not r.capped
    assert "上限原则未适用" in r.disclaimer["cap_note"]


# ---------------- 陷阱信号行动规则（§7.3，陷阱先行） ----------------

def test_trap_red(tables):
    r = compute_support(_inp(red_traps=1), tables)
    assert r.uplift_notches == 0 and r.final_rating == "A+"
    red = [a for a in r.trap_actions if a["kind"] == "red"]
    assert red and "LLM" in red[0]["note"]  # 可转负调整留 LLM 判断
    assert "重新评估" in red[0]["action"]    # §7.3 文档原文留痕


def test_trap_orange_downgrade(tables):
    r = compute_support(_inp(orange_traps=2), tables)
    assert r.willingness == pytest.approx(3.0)  # 原始分保留（审计留痕）
    assert r.willingness_band == "低"           # 档位降至"低"重算强度
    assert r.strength == "中等" and r.uplift_notches == 0  # 低×强=中等 → 门控归 0
    assert any(a["kind"] == "orange2" for a in r.trap_actions)


def test_trap_orange_asset(tables):
    # 单 🟠 + 资产划转：不降档不归零，但要求"无支持情景"分析
    r = compute_support(_inp(orange_traps=1, asset_transfer=True), tables)
    assert r.uplift_notches == 3 and r.final_rating == "AA+"
    a = [x for x in r.trap_actions if x["kind"] == "orange_asset"]
    assert a and a[0]["requires_no_support_scenario"] is True


def test_trap_fiscal(tables):
    # 财政持续恶化 2 年：capacity 降一档（强 2.5→中）+ 上调再减 1 子级
    r = compute_support(_inp(indicators=CAP_2_5, fiscal_decline_2y=True), tables)
    assert r.capacity == pytest.approx(2.5)
    assert r.capacity_band == "中"   # 强 → 降一档
    assert r.strength == "高"        # 意愿高 × 能力中
    assert r.uplift_notches == 1     # +1~2 取上限 2，再减 1
    assert r.final_rating == "AA-"   # A+ +1 子级
    assert any(a["kind"] == "fiscal" for a in r.trap_actions)


# ---------------- §3.2 区域标签 + §8.2 政策 advisory ----------------

def test_region_d(tables):
    r = compute_support(
        _inp(indicators=ALL_WEAK, willingness_signals=_signals(weak=2)), tables,
    )
    assert r.disclaimer["region"] == "D"
    assert r.confidence == tables.matrix_rules["D"]["confidence"]
    assert r.uplift_notches == 0  # 低/无 → 门控归 0


def test_policy_advisory(tables):
    r = compute_support(_inp(policy_signals=(
        "中央转移支付增加", "省内其他国企违约未获救助",
    )), tables)
    assert [(a["signal"], a["direction"]) for a in r.policy_advisory] == [
        ("中央转移支付增加", "正向"),
        ("省内其他国企违约未获救助", "极负向"),
    ]
    assert r.uplift_notches == 3  # 政策信号仅方向 advisory，无数值影响
    with pytest.raises(ValueError):
        compute_support(_inp(policy_signals=("不存在的政策信号",)), tables)


# ---------------- 输入校验 ----------------

def test_input_validation(tables):
    with pytest.raises(ValueError):
        compute_support(_inp(signal_level="L9"), tables)
    with pytest.raises(ValueError):
        compute_support(_inp(standalone_rating="AA++"), tables)
    with pytest.raises(ValueError):
        compute_support(_inp(supporter_rating="AA++"), tables)
    with pytest.raises(ValueError):
        compute_support(_inp(support_type="亲友支持"), tables)  # §2.1 三类型之外
    with pytest.raises(ValueError):
        compute_support(_inp(indicators={}), tables)  # capacity 全缺输入 → 不可判定

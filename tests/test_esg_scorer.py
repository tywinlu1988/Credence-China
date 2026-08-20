"""WP-X-04 esg_scorer 测试（T3：事件映射链 + 互斥归并）。

单一事实源纪律：§5.1 十二行映射表、§5.3 速查表、附录A 行业敏感度表、§7.1
可得性表均从 esg-framework.md 运行时解析，测试断言解析结果与文档锚点一致；
§5.2 修正因子（严重性档/弹性阈值/行业 ×1.5）为硬编码 + 本文件回读锚点 parity
校验（D2 先例）。CATEGORY_MAP 为 §5.1 行名 → 类别键结构归属（硬编码 + parity）。

链语义（与实现 docstring 同源）：① §5.1 基值区间 ∩ §5.2 严重性档区间；
② 弹性（弱→取上限/强→减半档，缺省取最轻端）+ 行业高敏感 ×1.5（0.5 子级格
点吸附：减半向零、×1.5 远离零）；③ §5.3 速查归并（信号强度分级 + 带外
advisory）；④ 互斥（同 event_id 计 1 次取最重）+ 累计钳 ±1；⑤ D4 落地
（-0.5→0+negative_flag、-1→-1、+0.5→0+positive_flag）。断言数值全部来自
文档当前内容，版本无关。
"""

import re

import pytest

from src.esg_scorer import (
    CATEGORY_MAP,
    SEVERITY_RANGE,
    EsgEvent,
    EsgResult,
    EsgTables,
    compute_esg,
    load_esg_tables,
)
from src.path_sheet import engine_dir

DOC = engine_dir() / "esg-framework.md"


@pytest.fixture(scope="module")
def tables():
    return load_esg_tables(DOC)


def ev(category, severity, dimension=None, **kw):
    """构造事件；dimension 缺省取 CATEGORY_MAP 归属（测维度一致性时显式覆盖）。"""
    dim = dimension if dimension is not None else CATEGORY_MAP.get(category, ("", "E", ""))[1]
    return EsgEvent(
        dimension=dim,
        category=category,
        severity=severity,
        evidence=kw.pop("evidence", "测试证据"),
        source=kw.pop("source", "测试"),
        **kw,
    )


# ---------------- 解析层（真实文档漂移门） ----------------

def test_load_esg_tables_structure(tables):
    assert isinstance(tables, EsgTables)
    # §5.1 十二行映射表：类别键全集 + 基值区间（文档「调整幅度」列）
    assert set(tables.mapping) == set(CATEGORY_MAP)
    assert len(tables.mapping) == 12
    rng = {k: (r.lo, r.hi) for k, r in tables.mapping.items()}
    assert rng["env_shutdown"] == (-1.0, -0.5)      # **-0.5~-1子级**
    assert rng["env_fine"] == (-0.5, 0.0)           # **0~-0.5子级**（通常不调整）
    assert rng["carbon_transition"] == (-0.5, -0.5)  # **-0.5子级**（仅标志性事件触发）
    assert rng["green_finance"] == (0.0, 0.5)       # **0~+0.5子级**
    assert rng["safety_shutdown"] == (-1.0, -0.5)
    assert rng["food_drug_scandal"] == (-1.0, -0.5)
    assert rng["product_recall"] == (-0.5, -0.5)
    assert rng["labor_dispute"] == (-0.5, 0.0)
    assert rng["control_contest"] == (-0.5, 0.0)
    assert rng["disclosure_violation"] == (-0.5, -0.5)
    assert rng["director_dissent"] == (-0.5, -0.5)
    assert rng["related_party_unfair"] == (-0.5, -0.5)
    # 传导路径/速度原文留痕
    assert "停产" in tables.mapping["env_shutdown"].transmission
    assert "快" in tables.mapping["env_shutdown"].speed
    # §5.3 速查表：五档信号强度齐全
    strengths = [r["strength"] for r in tables.quick_ref]
    assert strengths == ["无信号", "弱信号", "中等信号", "强信号", "极端信号"]
    mid = tables.quick_ref[2]
    assert mid["adjustment"] == "-0.5子级"
    assert "II级事件" in mid["trigger"]
    # 附录A 行业敏感度：19 行下界 + 锚点行业三维度档
    assert len(tables.industry_sensitivity) >= 19
    coal = tables.industry_sensitivity["煤炭"]
    assert (coal["E"], coal["S"], coal["G"]) == ("高", "高", "中")
    assert tables.industry_sensitivity["食品饮料"]["S"] == "高"
    assert tables.industry_sensitivity["银行/券商"]["G"] == "高"
    assert tables.industry_sensitivity["半导体"]["E"] == "中"
    assert tables.industry_sensitivity["城投"]["E"] == "低-中"
    # §7.1 可得性参数表：9 行 + 低覆盖锚点（诚实降级数据源）
    assert len(tables.availability) == 9
    assert tables.availability["E（环境-碳排放）"]["coverage"] == "20-30%"
    assert tables.availability["S（劳工纠纷）"]["coverage"] == "20-30%"
    assert tables.availability["E（环境-处罚/事故）"]["coverage"] == "60-70%"


def test_category_map_parity():
    """CATEGORY_MAP 结构归属锚点（§5.1 行名逐条回读，文档漂移时本测试先红）。"""
    text = DOC.read_text(encoding="utf-8")
    sec = re.search(r"^### 5\.1\s.*?(?=\n### |\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert sec, "§5.1 段落缺失"
    body = sec.group(0)
    for key, (row_name, dim, taxonomy) in CATEGORY_MAP.items():
        assert f"**{row_name}**" in body, f"§5.1 缺行 {key}: {row_name}"
        assert dim in ("E", "S", "G")
        assert re.fullmatch(r"[ESG][1-4]", taxonomy)


def test_hardcoded_52_parity_anchors():
    """§5.2 硬编码修正因子的文档锚点（严重性档/弹性阈值/行业权重）。"""
    text = DOC.read_text(encoding="utf-8")
    for anchor in (
        "I级（致命）",
        "II级（重大）",
        "III级（中等）",
        "IV级（轻微）",
        "利息覆盖 > 5x + 现金跑道 > 12个月",
        "利息覆盖 < 2x + 现金跑道 < 6个月",
        "高碳行业（环境事件权重×1.5）",
        "消费品牌（产品质量事件权重×1.5）",
        "金融企业（治理/合规事件权重×1.5）",
    ):
        assert anchor in text, f"§5.2 锚点缺失: {anchor}"
    # 严重性档区间与文档 :440-444 一一对应
    assert SEVERITY_RANGE == {
        "I": (-1.0, -1.0),
        "II": (-1.0, -0.5),
        "III": (-0.5, -0.5),
        "IV": (0.0, 0.0),
        "POSITIVE": (0.0, 0.5),
    }


def test_parse_failure_raises(tmp_path):
    """表头/章节漂移 → 解析即 raise（不容忍静默错列/丢表）。"""
    text = DOC.read_text(encoding="utf-8")
    bad51 = text.replace(
        "| ESG事件类型 | 信用传导路径 | 传导速度 | 影响维度 | 调整幅度 |",
        "| ESG事件类型 | 传导路径 |", 1,
    )
    p = tmp_path / "bad51.md"
    p.write_text(bad51, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="5.1"):
        load_esg_tables(p)
    bad_a = text.replace("## 附录A：各行业ESG敏感度对照", "## 附录A：已删除", 1)
    p2 = tmp_path / "badA.md"
    p2.write_text(bad_a, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="附录A"):
        load_esg_tables(p2)


# ---------------- ① §5.1 基值映射 + ② §5.2 修正 ----------------

def test_base_mapping_env_shutdown(tables):
    """停产整顿 II级（中性弹性/低敏感行业）→ 区间最轻端 -0.5 → D4 flag。"""
    r = compute_esg([ev("env_shutdown", "II")], {}, "城投", tables)
    t = r.trigger_events[0]
    assert (t["base_lo"], t["base_hi"]) == (-1.0, -0.5)
    assert t["adjustment"] == -0.5
    assert r.notch_adjustment == 0
    assert "negative_flag" in r.flags
    assert "positive_flag" not in r.flags


def test_base_mapping_env_fine(tables):
    """大额罚款 III级 → -0.5 flag；IV级 → 0（标注不调整，§5.2 :443）。"""
    r3 = compute_esg([ev("env_fine", "III")], {}, "城投", tables)
    assert r3.trigger_events[0]["adjustment"] == -0.5
    assert "negative_flag" in r3.flags
    r4 = compute_esg([ev("env_fine", "IV")], {}, "城投", tables)
    assert r4.trigger_events[0]["adjustment"] == 0.0
    assert r4.notch_adjustment == 0
    assert r4.flags == []
    assert r4.signal_strength == "弱信号"


def test_severity_I_full_notch(tables):
    """I级（致命）→ -1 子级（§5.2 :440）；行业 S 中 → 不触发 ×1.5。"""
    r = compute_esg([ev("safety_shutdown", "I")], {}, "物流/运输", tables)
    assert r.trigger_events[0]["adjustment"] == -1.0
    assert r.notch_adjustment == -1
    assert "negative_flag" not in r.flags  # -1 为真实降档，非 flag


def test_strong_elasticity_halves(tables):
    """覆盖>5x 且跑道>12月 → 调整幅度减半档（:447）：-1→-0.5；-0.5→0（向零吸附）。"""
    strong = {"interest_coverage": 6.0, "cash_runway_months": 13}
    r = compute_esg([ev("safety_shutdown", "I")], strong, "物流/运输", tables)
    assert r.trigger_events[0]["adjustment"] == -0.5
    assert r.notch_adjustment == 0
    assert "negative_flag" in r.flags
    assert any("减半" in n for n in r.notes)
    r2 = compute_esg([ev("env_shutdown", "II")], strong, "城投", tables)
    assert r2.trigger_events[0]["adjustment"] == 0.0
    assert r2.flags == []


def test_weak_elasticity_takes_upper(tables):
    """覆盖<2x 且跑道<6月 → 调整幅度取上限（:448，最重端）。"""
    weak = {"interest_coverage": 1.5, "cash_runway_months": 3}
    r = compute_esg([ev("env_shutdown", "II")], weak, "城投", tables)
    assert r.trigger_events[0]["adjustment"] == -1.0
    assert r.notch_adjustment == -1


def test_elasticity_band_boundaries(tables):
    """>5x/<2x 为严格开区间（恰等不命中）；缺键 → 未知带 + 注记（不静默按中处理）。"""
    base = [ev("env_shutdown", "II")]
    r_eq = compute_esg(base, {"interest_coverage": 5.0, "cash_runway_months": 12}, "城投", tables)
    assert r_eq.elasticity_factors["band"] == "中"
    assert r_eq.trigger_events[0]["adjustment"] == -0.5
    r_eq2 = compute_esg(base, {"interest_coverage": 2.0, "cash_runway_months": 6}, "城投", tables)
    assert r_eq2.elasticity_factors["band"] == "中"
    assert r_eq2.trigger_events[0]["adjustment"] == -0.5
    r_miss = compute_esg(base, {"interest_coverage": 1.0}, "城投", tables)
    assert r_miss.elasticity_factors["band"] == "未知"
    assert any("弹性" in n for n in r_miss.notes)


def test_industry_sensitivity_multiplier(tables):
    """行业高敏感维度 ×1.5（:450-453）：-0.5→-0.75→远离零吸附 -1；仅事件维度档=高 触发。"""
    r = compute_esg([ev("env_fine", "III")], {}, "化工", tables)  # 化工 E=高
    assert r.trigger_events[0]["adjustment"] == -1.0
    assert r.notch_adjustment == -1
    r2 = compute_esg([ev("env_fine", "III")], {}, "城投", tables)  # 城投 E=低-中
    assert r2.trigger_events[0]["adjustment"] == -0.5
    # 水泥 E=高 但 S=中：S 事件不乘
    r3 = compute_esg([ev("safety_shutdown", "II")], {}, "水泥", tables)
    assert r3.trigger_events[0]["adjustment"] == -0.5
    # 煤炭 S=高：S 事件乘
    r4 = compute_esg([ev("safety_shutdown", "II")], {}, "煤炭", tables)
    assert r4.trigger_events[0]["adjustment"] == -1.0


# ---------------- ③ §5.3 速查归并 ----------------

def test_signal_strength_classification(tables):
    assert compute_esg([], {}, "城投", tables).signal_strength == "无信号"
    assert compute_esg([ev("env_fine", "IV")], {}, "城投", tables).signal_strength == "弱信号"
    assert compute_esg([ev("env_fine", "III")], {}, "城投", tables).signal_strength == "弱信号"
    assert compute_esg([ev("env_shutdown", "II")], {}, "城投", tables).signal_strength == "中等信号"
    two_iii = [ev("env_fine", "III", evidence="罚1"), ev("disclosure_violation", "III")]
    assert compute_esg(two_iii, {}, "城投", tables).signal_strength == "中等信号"
    assert compute_esg([ev("safety_shutdown", "I")], {}, "物流/运输", tables).signal_strength == "强信号"
    # II级 + 弹性弱 + 行业高敏感 → 强信号（:463）
    r = compute_esg(
        [ev("safety_shutdown", "II")],
        {"interest_coverage": 1.0, "cash_runway_months": 2},
        "煤炭", tables,
    )
    assert r.signal_strength == "强信号"
    assert r.trigger_events[0]["adjustment"] == -1.0


def test_quick_ref_band_advisory(tables):
    """修正因子使累计值落于速查表带外 → advisory 注记（以链式计算为准）。"""
    strong = {"interest_coverage": 8.0, "cash_runway_months": 24}
    r = compute_esg([ev("env_shutdown", "II")], strong, "城投", tables)
    assert r.signal_strength == "中等信号"  # 速查带 -0.5
    assert r.trigger_events[0]["adjustment"] == 0.0  # 强弹性减半 → 0
    assert any("速查" in n for n in r.notes)


# ---------------- ④ 互斥归并 + ±1 总限 ----------------

def test_dedup_same_event_id(tables):
    """§6.3 :521/:523——同一事件只触发一次调整，取最重。"""
    dup = [
        ev("env_fine", "III", event_id="EV-1", evidence="处罚决定书A"),
        ev("env_fine", "IV", event_id="EV-1", evidence="媒体转载A"),
    ]
    r = compute_esg(dup, {}, "城投", tables)
    assert len(r.trigger_events) == 2
    counted = [t for t in r.trigger_events if t["counted"]]
    assert len(counted) == 1
    assert counted[0]["adjustment"] == -0.5  # 取最重
    assert r.notch_adjustment == 0
    assert "negative_flag" in r.flags
    # 无 event_id 时 (维度, 类别, 证据) 全同 → 同一事件
    r2 = compute_esg([ev("env_fine", "III"), ev("env_fine", "III")], {}, "城投", tables)
    assert sum(1 for t in r2.trigger_events if t["counted"]) == 1


def test_cumulative_clamp(tables):
    """多事件累计 -1.5 → 钳 -1（§6.3 :522/§7.3 :565 ±1 子级上限）。"""
    events = [
        ev("disclosure_violation", "III", evidence="信披处罚"),
        ev("director_dissent", "III", evidence="独董反对"),
        ev("related_party_unfair", "III", evidence="关联质疑"),
    ]
    r = compute_esg(events, {}, "城投", tables)  # 城投 G=中 → 无 ×1.5
    assert r.per_dimension["G"]["score"] == -1.5  # 钳前留痕
    assert r.notch_adjustment == -1
    assert any("钳" in n or "上限" in n for n in r.notes)


# ---------------- ⑤ D4 落地 ----------------

def test_d4_positive_flag(tables):
    """绿色金融 POSITIVE → +0.5 → 0 + positive_flag（正向不落地为子级）。"""
    r = compute_esg([ev("green_finance", "POSITIVE")], {}, "光伏/风电", tables)
    assert r.trigger_events[0]["adjustment"] == 0.5
    assert r.notch_adjustment == 0
    assert "positive_flag" in r.flags
    assert "negative_flag" not in r.flags


def test_empty_events(tables):
    r = compute_esg([], {}, "城投", tables)
    assert isinstance(r, EsgResult)
    assert r.notch_adjustment == 0
    assert r.flags == []
    assert r.signal_strength == "无信号"
    assert set(r.per_dimension) == {"E", "S", "G"}
    assert all(r.per_dimension[d]["score"] == 0.0 for d in "ESG")


# ---------------- 诚实降级（E1 碳排放 / S2 劳工） ----------------

def test_low_coverage_forced_notes(tables):
    """E1/S2 类事件 → 强制 data_availability 注记（覆盖率 20-30%，§7.1 :534/:537）。"""
    r = compute_esg([ev("carbon_transition", "III")], {}, "电力", tables)
    assert any("20-30%" in n for n in r.data_availability["notes"])
    assert "E1" in r.data_availability["low_coverage_taxonomies"]
    r2 = compute_esg([ev("labor_dispute", "III")], {}, "纺织/服装", tables)
    assert any("20-30%" in n for n in r2.data_availability["notes"])
    assert "S2" in r2.data_availability["low_coverage_taxonomies"]
    # 高覆盖类别（E2 处罚 60-70%）不强制注记
    r3 = compute_esg([ev("env_fine", "III")], {}, "城投", tables)
    assert r3.data_availability["low_coverage_taxonomies"] == []
    assert not any("20-30%" in n for n in r3.data_availability["notes"])


# ---------------- 输入校验（失败可观测） ----------------

def test_validation_raises(tables):
    with pytest.raises(ValueError, match="类别"):
        compute_esg([ev("no_such_category", "III")], {}, "城投", tables)
    with pytest.raises(ValueError, match="维度"):
        compute_esg([ev("env_fine", "III", dimension="G")], {}, "城投", tables)
    with pytest.raises(ValueError, match="严重性"):
        compute_esg([ev("env_fine", "V")], {}, "城投", tables)
    with pytest.raises(ValueError, match="区间"):
        # POSITIVE 严重性 × 纯负向基值类别（基值不含 0）→ 区间交集为空
        compute_esg([ev("env_shutdown", "POSITIVE")], {}, "城投", tables)
    # POSITIVE × 含 0 基值类别 → 交集为单点 0（合法，标注不调整）
    r0 = compute_esg([ev("env_fine", "POSITIVE")], {}, "城投", tables)
    assert r0.trigger_events[0]["adjustment"] == 0.0


def test_unknown_industry_note(tables):
    """附录A 未收录行业 → 行业修正不适用 + 注记（不 raise、不静默乘 1）。"""
    r = compute_esg([ev("env_fine", "III")], {}, "某新兴行业", tables)
    assert r.trigger_events[0]["adjustment"] == -0.5
    assert any("附录A" in n for n in r.notes)


def test_per_dimension_summary(tables):
    events = [
        ev("env_fine", "III", evidence="罚款"),
        ev("labor_dispute", "III", evidence="罢工"),
    ]
    r = compute_esg(events, {}, "纺织/服装", tables)  # 纺织 E=中 S=高
    # S=高 → 劳工纠纷 -0.5×1.5 → -0.75 → -1；E=中 → -0.5；累计 -1.5 钳 -1
    assert r.per_dimension["E"]["score"] == -0.5
    assert r.per_dimension["S"]["score"] == -1.0
    assert r.per_dimension["G"]["score"] == 0.0
    assert "劳工" in r.per_dimension["S"]["summary"]
    assert r.notch_adjustment == -1

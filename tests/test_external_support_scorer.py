"""WP-M0-02 external_support_scorer 能力侧测试（T4）。

单一事实源纪律：§4.1 关键指标阈值参考表（6 指标 × 4 档）从
external-support-framework.md 运行时解析，测试断言解析结果与文档锚点一致；
INDICATOR_TO_FACTOR 为 §4.1 四维模型表结构归属（硬编码 + 本文件回读锚点
parity 校验，防静默漂移）。

边界语义（与实现 docstring 同源）：">X"/"<X" 为开区间端点（如 3000亿 落
中等档），"X-Y" 为闭区间；断言数值全部来自文档表格当前内容，版本无关。
"""

import pytest

from src.external_support_scorer import (
    INDICATOR_TO_FACTOR,
    SupportTables,
    capacity_score,
    load_support_tables,
    score_indicator,
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
    # T5 占位字段当前为 None（§3.2/§6.1/§6.2/§7.3 解析属 T5）
    assert tables.matrix_rules is None
    assert tables.strength_matrix is None
    assert tables.uplift_map is None
    assert tables.trap_actions is None


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

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
    clamp,
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

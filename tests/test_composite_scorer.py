"""WP-M0-01 composite_scorer 测试。

单一事实源纪律：解析层漂移门的期望值从文档运行时解析（规则条数、模板数、
行业判定表、特殊结构），计算层测试用 fixture。
"""

import pytest

from src.composite_scorer import (
    composite_score,
    judge_paradigm,
    load_industry_paradigms,
    load_paradigm_rules,
    load_special_structures,
    load_weight_templates,
    map_to_rating,
    rate,
)
from src.path_sheet import engine_dir

DOC = engine_dir() / "industry-framework.md"


@pytest.fixture(scope="module")
def parsed():
    return (
        load_paradigm_rules(DOC),
        load_weight_templates(DOC),
        load_industry_paradigms(DOC),
        load_special_structures(DOC),
    )


# ---------------- 解析层（真实文档漂移门） ----------------

def test_rules_parse(parsed):
    rules, *_ = parsed
    assert len(rules) == 4
    for paradigm, conds in rules.items():
        assert conds, paradigm
        for dim, op, t in conds:
            assert dim.startswith("D") and op in (">=", "<=", ">", "<") and 1 <= t <= 5


def test_templates_parse(parsed):
    _, templates, *_ = parsed
    assert len(templates) == 6  # 4 标准 + 品牌+渠道型 + 网络+流量型
    for paradigm, layers in templates.items():
        assert set(layers) == {"L1", "L2", "L3", "L4"}, paradigm
        assert sum(pct for _, pct in layers.values()) == 100, paradigm


def test_industry_paradigms_cover_nine(parsed):
    _, templates, ind_map, specials = parsed
    covered = [
        ind for ind, p in ind_map.items()
        if p in templates and "特殊" not in p
        and not any(ind[:3] == frag[:3] for frag in specials)
    ]
    assert len(covered) == 9  # 光伏/高端装备/医疗器械/数据中心 + E×2 + F×3


def test_special_structures_parse(parsed):
    *_, specials = parsed
    assert len(specials) == 3  # 半导体 5 层、新能源车双轨、生物医药双轨


# ---------------- 判定（fixture） ----------------

POLICY_D = {"D1": 4, "D2": 4, "D3": 5, "D4": 4, "D5": 3, "D6": 3, "D7": 2, "D8": 2, "D9": 3, "D10": 3}


def test_judge_unique(parsed):
    rules, _, ind_map, specials = parsed
    j = judge_paradigm(POLICY_D, None, rules, ind_map, specials)
    assert j["paradigm"] == "政策驱动型" and not j["conflict"]


def test_judge_industry_mapping_short_circuits(parsed):
    rules, _, ind_map, specials = parsed
    # 商贸零售形式上触发存量博弈型，但 §七 归为网络+流量型（模板可用）
    d = dict(POLICY_D, D2=2, D10=3, D1=5, D8=3)
    j = judge_paradigm(d, "商贸零售", rules, ind_map, specials)
    assert j["paradigm"] == "网络+流量型" and not j["out_of_scope"]


def test_judge_conflict_default_consolidation(parsed):
    rules, _, ind_map, specials = parsed
    d = dict(POLICY_D, D2=2, D10=4)  # 政策驱动(D3,D4) + 存量博弈(D2,D10) 双触发
    j = judge_paradigm(d, None, rules, ind_map, specials)
    assert j["conflict"] and j["paradigm"] == "存量博弈型"  # Consolidation 优先（§3.1 规则1）
    assert set(j["candidates"]) == {"政策驱动型", "存量博弈型"}


def test_judge_out_of_scope(parsed):
    rules, _, ind_map, specials = parsed
    assert judge_paradigm(POLICY_D, "半导体/集成电路", rules, ind_map, specials)["out_of_scope"]
    assert judge_paradigm(POLICY_D, "新能源汽车-OEM", rules, ind_map, specials)["out_of_scope"]
    assert judge_paradigm(POLICY_D, "城投债 / LGFV", rules, ind_map, specials)["out_of_scope"]


def test_judge_no_trigger_raises(parsed):
    rules, _, ind_map, specials = parsed
    with pytest.raises(ValueError):
        judge_paradigm({"D1": 1}, None, rules, ind_map, specials)


# ---------------- 聚合与映射 ----------------

def test_composite_score_math(parsed):
    _, templates, *_ = parsed
    s = composite_score({"L1": 8, "L2": 7, "L3": 6, "L4": 7}, templates["政策驱动型"])
    # 8×.35 + 7×.30 + 6×.20 + 7×.15 = 7.15
    assert abs(s - 7.15) < 1e-9
    with pytest.raises(ValueError):
        composite_score({"L1": 8}, templates["政策驱动型"])
    with pytest.raises(ValueError):
        composite_score({"L1": 8, "L2": 7, "L3": 6, "L4": 11}, templates["政策驱动型"])


def test_map_to_rating_boundaries():
    assert map_to_rating(9.5) == "AAA"
    assert map_to_rating(9.45) == "AA+"  # 间隙值向下一档归并
    assert map_to_rating(7.15) == "A"
    assert map_to_rating(1.0) == "CCC"
    assert map_to_rating(0.95) == "D"


# ---------------- rate() 全链 ----------------

def test_rate_full_chain():
    r = rate(POLICY_D, {"L1": 8, "L2": 7, "L3": 6, "L4": 7}, industry="光伏/储能")
    assert r["paradigm"] == "政策驱动型"
    assert abs(r["composite"] - 7.15) < 1e-9 and r["rating"] == "A"
    assert not r["veto_capped"] and not r["conflict"] and not r["out_of_scope"]


def test_rate_veto_cap_and_special():
    capped = rate(POLICY_D, {"L1": 8, "L2": 7, "L3": 6, "L4": 7},
                  veto_conditions=["制裁断裂"], industry="光伏/储能")
    assert capped["rating"] == "CCC" and capped["veto_capped"]
    worse = rate(POLICY_D, {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
                 veto_conditions=["制裁断裂"], industry="光伏/储能")
    assert worse["rating"] == "D"  # D 保持 D（上限锁定只下压更好评级）
    oos = rate(POLICY_D, {"L1": 8, "L2": 7, "L3": 6, "L4": 7}, industry="半导体/集成电路")
    assert oos["out_of_scope"] and oos["composite"] is None

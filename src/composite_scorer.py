"""WP-M0-01 → industry-framework.md 的聚合可执行实现（范式判定 + 复合评分 + 评级映射）。

单一事实源：§3.1 判定规则、§3.2 四标准范式权重模板、§七 行业→范式判定表、§3.3 特殊
结构、paradigm-brand-channel.md/paradigm-network-traffic.md 的 E/F 权重模板，均运行时
解析；18 档评级映射复用 consistency_check.CANONICAL_RATING_INTERVALS（import 同源）。
覆盖 9/13 行业（4 标准范式 + E×2 + F×3）；半导体 5 层/新能源车/生物医药双轨/城投特殊
返回 out_of_scope 标记，由 LLM 按对应规格文档编排（诚实降级）。
"""

import re
import sys
from pathlib import Path

from src.path_sheet import engine_dir

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from consistency_check import CANONICAL_RATING_INTERVALS  # noqa: E402  18 档单源，不复制

_EF_TEMPLATE_SOURCES = {
    "品牌+渠道型": "paradigm-brand-channel.md",
    "网络+流量型": "paradigm-network-traffic.md",
}

_RULE_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(D\d+[^|]*?)\s*\|", re.MULTILINE)
_COND_RE = re.compile(r"(D\d+)\s*(>=|<=|>|<)\s*(\d+)")


def _read(path) -> str:
    p = Path(path) if path else engine_dir() / "industry-framework.md"
    return p.read_text(encoding="utf-8")


def load_paradigm_rules(path=None) -> dict:
    """§3.1 → {paradigm: [(dim, op, threshold)]}。"""
    sec = re.search(r"### 3\.1 .*?(?=\n### |\Z)", _read(path), re.DOTALL)
    if not sec:
        raise ValueError("§3.1 判定条件段落缺失")
    rules = {}
    for row in _RULE_ROW_RE.finditer(sec.group(0)):
        conds = [(d, op, int(t)) for d, op, t in _COND_RE.findall(row.group(2))]
        if conds:
            rules[row.group(1).strip()] = conds
    if len(rules) != 4:
        raise ValueError(f"§3.1 应有 4 条范式判定规则，实际 {len(rules)}")
    return rules


def load_weight_templates(path=None) -> dict:
    """§3.2 四标准范式 + E/F 独立规格文档 → {paradigm: {L1..L4: (label, pct)}}。"""
    templates = {}
    sec = re.search(r"### 3\.2 .*?(?=\n### |\Z)", _read(path), re.DOTALL)
    if not sec:
        raise ValueError("§3.2 权重模板段落缺失")
    for row in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(\d+)%\s*([^|]+?)\s*\|\s*(\d+)%\s*([^|]+?)\s*\|"
        r"\s*(\d+)%\s*([^|]+?)\s*\|\s*(\d+)%\s*([^|]+?)\s*\|",
        sec.group(0), re.MULTILINE,
    ):
        name = row.group(1).strip()
        templates[name] = {
            f"L{i}": (row.group(2 * i + 1).strip(), int(row.group(2 * i)))
            for i in range(1, 5)
        }
    if len(templates) != 4:
        raise ValueError(f"§3.2 应有 4 个标准权重模板，实际 {len(templates)}")
    base = Path(path).parent if path else engine_dir()
    for paradigm, fname in _EF_TEMPLATE_SOURCES.items():
        t2 = (base / fname).read_text(encoding="utf-8")
        layers = re.findall(r"^\|\s*\*\*(L\d)\s+([^|]+?)\*\*\s*\|\s*(\d+)%\s*\|", t2, re.MULTILINE)
        if len(layers) != 4:
            raise ValueError(f"{fname} 应有 4 层权重行，实际 {len(layers)}")
        templates[paradigm] = {l: (label.strip(), int(pct)) for l, label, pct in layers}
    return templates


def load_industry_paradigms(path=None) -> dict:
    """§七 → {industry: 主要范式}（含 E/F 与 LGFV 特殊标记）。"""
    sec = re.search(r"## 七、各行业类型判定结果\s*\n(.*?)(?=\n## |\Z)", _read(path), re.DOTALL)
    if not sec:
        raise ValueError("§七 行业判定表段落缺失")
    out = {}
    for row in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", sec.group(1), re.MULTILINE):
        ind, paradigm = row.group(1).strip(), row.group(2).strip()
        if ind in ("行业",) or set(ind) <= set("-| "):
            continue
        out[ind] = paradigm
    if not out:
        raise ValueError("§七 判定表解析为空")
    return out


def load_special_structures(path=None) -> set:
    """§3.3 → 特殊结构行业名片段集合（半导体/新能源车/生物医药）。"""
    sec = re.search(r"### 3\.3 .*?(?=\n### |\Z)", _read(path), re.DOTALL)
    if not sec:
        raise ValueError("§3.3 特殊结构段落缺失")
    return set(re.findall(r"^\|\s*\*\*(.+?)\*\*\s*\|", sec.group(0), re.MULTILINE))


def _lookup_industry(ind_map: dict, industry: str):
    if industry in ind_map:
        return ind_map[industry]
    for key, val in ind_map.items():
        if industry in key or key in industry:
            return val
    return None


def _is_special(specials: set, industry: str) -> bool:
    """特殊结构匹配按名前 3 字（§3.3 "新能源车" 对 §七 "新能源汽车-OEM" 亦命中）。"""
    return any(industry[:3] == frag[:3] for frag in specials)


def _eval_cond(d_scores: dict, cond) -> bool:
    dim, op, threshold = cond
    if dim not in d_scores:
        raise ValueError(f"d_scores 缺少 {dim}")
    v = d_scores[dim]
    return {">=": v >= threshold, "<=": v <= threshold,
            ">": v > threshold, "<": v < threshold}[op]


def judge_paradigm(d_scores: dict, industry, rules: dict, ind_map: dict, specials: set) -> dict:
    """判定范式：industry 优先按 §七 表 → 特殊/LGFV 降级、E/F/标准直接取；否则按 §3.1 规则。"""
    result = {"paradigm": None, "conflict": False, "candidates": [], "out_of_scope": None}
    if industry:
        if _is_special(specials, industry):
            result["out_of_scope"] = "特殊结构（5层/双轨制），按对应规格由 LLM 编排"
            return result
        mapped = _lookup_industry(ind_map, industry)
        if mapped:
            if "特殊" in mapped:
                result["out_of_scope"] = f"特殊类别（{mapped}）"
                return result
            result["paradigm"] = mapped
            return result
    triggered = [p for p, conds in rules.items()
                 if all(_eval_cond(d_scores, c) for c in conds)]
    if not triggered:
        raise ValueError("无任何范式命中且未提供可映射行业")
    result["candidates"] = triggered
    if len(triggered) > 1:
        result["conflict"] = True
        # §3.1 优先级规则1：生存位势/利润要塞（Consolidation=存量博弈型）优先
        result["paradigm"] = "存量博弈型" if "存量博弈型" in triggered else triggered[0]
    else:
        result["paradigm"] = triggered[0]
    return result


def composite_score(layer_scores: dict, template: dict) -> float:
    """composite = Σ(层分 × 层权重)。layer_scores 按 L1-L4 给 0-10 分（LLM 产出）。"""
    total = 0.0
    for layer, (label, pct) in template.items():
        if layer not in layer_scores:
            raise ValueError(f"layer_scores 缺少 {layer}（{label}）")
        s = float(layer_scores[layer])
        if not 0 <= s <= 10:
            raise ValueError(f"{layer} 层分 {s} 超出 0-10")
        total += s * pct / 100.0
    return round(total, 4)


def map_to_rating(score: float) -> str:
    """18 档映射（复用 CANONICAL_RATING_INTERVALS）；间隙值向下一档归并。"""
    for low, _high, label in CANONICAL_RATING_INTERVALS:  # 已按高→低排序
        if score >= low:
            return label
    raise ValueError(f"score {score} 超出 0-10")


def rate(d_scores: dict, layer_scores: dict, veto_conditions=None,
         industry=None, paradigm_override=None, path=None) -> dict:
    """全链：范式判定 → 权重模板 → 复合分 → 18 档映射 → 否决上限锁 CCC。"""
    rules = load_paradigm_rules(path)
    templates = load_weight_templates(path)
    ind_map = load_industry_paradigms(path)
    specials = load_special_structures(path)
    if paradigm_override:
        if paradigm_override not in templates:
            raise ValueError(f"paradigm_override 未知: {paradigm_override!r}")
        paradigm, conflict = paradigm_override, False
    else:
        j = judge_paradigm(d_scores, industry, rules, ind_map, specials)
        if j["out_of_scope"]:
            return {"paradigm": j["paradigm"], "composite": None, "rating": None,
                    "veto_capped": False, "conflict": False,
                    "out_of_scope": j["out_of_scope"]}
        paradigm, conflict = j["paradigm"], j["conflict"]
    comp = composite_score(layer_scores, templates[paradigm])
    rating = map_to_rating(comp)
    capped = bool(veto_conditions)
    ccc_rank = next(i for i, (_, _, l) in enumerate(CANONICAL_RATING_INTERVALS) if l == "CCC")
    cur_rank = next(i for i, (_, _, l) in enumerate(CANONICAL_RATING_INTERVALS) if l == rating)
    if capped and cur_rank < ccc_rank:
        rating = "CCC"  # 上限锁定：只把更好评级压到 CCC，D 保持 D
    return {"paradigm": paradigm, "composite": comp, "rating": rating,
            "veto_capped": capped, "conflict": conflict, "out_of_scope": None}

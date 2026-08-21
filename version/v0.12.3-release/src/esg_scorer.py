"""WP-X-04 → esg-framework.md 的 ESG 事件映射链引擎（T3）。

单一事实源：§5.1 十二行核心映射表（:419-432）、§5.3 调整规则速查表（:458-464）、
附录A 各行业 ESG 敏感度对照（:614-634）、§7.1 数据可得性表（:531-541）均运行时
解析，解析失败即 raise（不裸复制数值副本）。§5.2 调整幅度判定规则（:436-454）
为异构自然语言修正因子 → 硬编码 + parity 锚点（D2 先例，tests 回读锚点文本）。

已裁决设计决策（SDD 2026-08-20-wp-x-04-esg-governance / M0-02 沿用）：
- D2：§5.2 修正规则硬编码 + parity；CATEGORY_MAP 为 §5.1 行名 → 类别键的
  结构归属（硬编码 + parity，同 INDICATOR_TO_FACTOR 先例）。
- D4 落点：-0.5 → 0 + negative_flag；-1 → -1 降档；+0.5 → 0 + positive_flag
  （正向不落地为子级——§1.2 原则 4 非对称调整）。
- D6：无阈值不新造——极端信号一票否决路径（§5.3 :464）不由本引擎判定，
  I 级事件仅留复核注记。

链语义（compute_esg 五步）：
① §5.1 基值区间 ∩ §5.2 严重性档区间（交集为空即 raise，失败可观测）；
② 修正：弹性弱（覆盖<2x 且跑道<6 月，严格开区间）→ 取区间最重端；
   弹性强（覆盖>5x 且跑道>12 月）→ 调整幅度减半档（0.5 子级格点向零吸附）；
   缺省/中 → 取最轻端；行业事件维度敏感度=高（附录A）→ ×1.5（格点远离零吸附），
   单事件钳 [-1, +0.5]；
③ §5.3 速查归并：信号强度分级（无/弱/中/强）+ 累计值带外 advisory 注记；
④ 互斥（§6.3 :521-523）：同 event_id（缺省退化为 维度+类别+证据）计 1 次
   取最重；累计钳 ±1 子级（:522/:565）；
⑤ D4 落地。
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.path_sheet import engine_dir

_DOC_NAME = "esg-framework.md"

# --------------------------------------------------------------------------
# 硬编码结构归属与 §5.2 修正因子（D2：parity 锚点见 tests/test_esg_scorer.py）
# --------------------------------------------------------------------------

# §5.1 行名 → (维度, 分类体系归属)。分类归属锚点：E1=§2.2 高碳转型、E2=§2.3
# 环保处罚、E4=§2.5 绿色机遇、S1=§3.2 安全、S2=§3.3 劳工、S3=§3.4 产品质量、
# G1=§4.2 股权、G2=§4.3 董事会、G3=§4.4 信披、G4=§4.5 中小股东（:400 关联交易
# 不公允属 §4.5 表内行 → G4）。
CATEGORY_MAP = {
    "env_shutdown": ("重大环保处罚（责令停产）", "E", "E2"),
    "env_fine": ("环保罚款（金额大但未停产）", "E", "E2"),
    "carbon_transition": ("高碳行业转型风险暴露", "E", "E1"),
    "green_finance": ("新增绿色债券发行/绿色金融支持", "E", "E4"),
    "safety_shutdown": ("重大安全事故（停产）", "S", "S1"),
    "food_drug_scandal": ("产品质量丑闻（食品/药品）", "S", "S3"),
    "product_recall": ("产品召回（非食品/药品）", "S", "S3"),
    "labor_dispute": ("劳工纠纷（罢工/欠薪争议）", "S", "S2"),
    "control_contest": ("股权争夺/控制权不稳定", "G", "G1"),
    "disclosure_violation": ("信息披露违规被处罚", "G", "G3"),
    "director_dissent": ("独立董事集体辞职/反对票", "G", "G2"),
    "related_party_unfair": ("关联交易不公允被质疑", "G", "G4"),
}

# §5.2 事件严重性档（:440-444）：档 → (区间下限, 区间上限)（子级，负=下调）。
SEVERITY_RANGE = {
    "I": (-1.0, -1.0),         # I级（致命）：核心业务停产/核心产品遭禁/许可证被吊销
    "II": (-1.0, -0.5),        # II级（重大）：重大安全事故/食品药品丑闻/停产
    "III": (-0.5, -0.5),       # III级（中等）：批量召回/重罚/股权争议
    "IV": (0.0, 0.0),          # IV级（轻微）：小额罚款/轻微通报（标注但不调整）
    "POSITIVE": (0.0, 0.5),    # 正向（绿色）：绿色债券/碳减排收益（极少）
}

# §5.2 财务弹性权重（:447-448）：">"/"<" 为严格开区间（恰等不命中）。
_ELAST_STRONG_COVERAGE = 5    # 利息覆盖 > 5x
_ELAST_STRONG_RUNWAY = 12     # 现金跑道 > 12个月
_ELAST_WEAK_COVERAGE = 2      # 利息覆盖 < 2x
_ELAST_WEAK_RUNWAY = 6        # 现金跑道 < 6个月

# §5.2 行业特征权重（:450-453）：高敏感维度事件权重 ×1.5。
_INDUSTRY_MULTIPLIER = 1.5

# 单事件调整钳制带（§5.3 :462-463 单事件最深 -1；§5.2 :444 正向至多 +0.5）。
_EVENT_LO, _EVENT_HI = -1.0, 0.5
# 累计钳 ±1 子级（§6.3 :522 / §7.3 :565 / §1.2 原则 3）。
_TOTAL_LO, _TOTAL_HI = -1.0, 1.0

# 诚实降级：低覆盖分类 → §7.1 行键（覆盖率从可得性表运行时取值，不裸复制）。
TAXONOMY_AVAILABILITY_ROW = {
    "E1": "E（环境-碳排放）",   # :534 覆盖 20-30%，影响「严重」
    "S2": "S（劳工纠纷）",      # :537 覆盖 20-30%，影响「严重」
}

_DIMENSIONS = ("E", "S", "G")


# --------------------------------------------------------------------------
# 解析层
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class MappingRow:
    """§5.1 映射表单一行。lo/hi 为基值区间（子级，负=下调；lo≤hi 沿数值轴）。"""

    category: str
    name: str            # §5.1 行名原文（去加粗）
    dimension: str
    taxonomy: str        # E1-G4 分类体系归属
    lo: float
    hi: float
    transmission: str    # 信用传导路径原文
    speed: str           # 传导速度原文
    impact: str          # 影响维度原文
    adjust_text: str     # 调整幅度单元格原文（审计留痕）


@dataclass(frozen=True)
class EsgTables:
    """esg-framework.md 可解析表的运行时解析结果。

    mapping: §5.1 → {类别键: MappingRow}（十二行全量，缺一即 raise）。
    quick_ref: §5.3 → 5 档 dict（strength 为去括注档名；adjustment/trigger 原文）。
    industry_sensitivity: 附录A → {行业: {"E"/"S"/"G": 档位, "most_sensitive",
        "note"}}（档位 ∈ {高, 中, 低, 低-中}）。
    availability: §7.1 → {维度行名: {"coverage", "source", "gap", "impact"}}（9 行）。
    """

    mapping: dict
    quick_ref: tuple
    industry_sensitivity: dict
    availability: dict


def _read(path) -> str:
    p = Path(path) if path else engine_dir() / _DOC_NAME
    return p.read_text(encoding="utf-8")


def _section(text: str, num: str) -> str:
    """按节号切片。``^### `` 行首锁防正文提及误锚；``(?!\\d)`` 节号边界防
    ``### 5.1`` 误锚 ``### 5.10`` 之类的前缀误锚（锚点须为独立小节标题行）。"""
    sec = re.search(
        rf"^### {re.escape(num)}(?!\d)\s.*?(?=\n### |\n## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if not sec:
        raise ValueError(f"§{num} 段落缺失")
    return sec.group(0)


def _table_rows(sec: str, header_re: re.Pattern, header_desc: str):
    """锚定表头行后顺序采集数据行 → 数据行单元格列表。

    表头漂移即 raise；分隔行（|---|---|）跳过；数据行一开始后遇到首个非表格行
    （空行/正文）即停止（防越界吞并后续段落）。
    """
    m = header_re.search(sec)
    if not m:
        raise ValueError(f"{header_desc} 表头缺失（疑似表格漂移）")
    line_end = sec.find("\n", m.end())
    rows = []
    for line in sec[line_end if line_end != -1 else len(sec):].splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue  # 分隔行
        rows.append(cells)
    return rows


# §5.1 映射表表头锚点（:419）。
_MAP_HEADER_RE = re.compile(
    r"^\|\s*ESG事件类型\s*\|\s*信用传导路径\s*\|\s*传导速度\s*\|\s*影响维度\s*\|\s*调整幅度\s*\|",
    re.MULTILINE,
)
# 调整幅度单元格："**-0.5~-1子级**" / "**0~+0.5子级**（极少触发上调）" / "**-0.5子级**（…）"。
_ADJ_RANGE = re.compile(r"([+-]?\d+(?:\.\d+)?)~([+-]?\d+(?:\.\d+)?)子级")
_ADJ_SINGLE = re.compile(r"([+-]?\d+(?:\.\d+)?)子级")


def _parse_adjust_cell(cell: str, row_name: str) -> tuple:
    """§5.1 调整幅度单元格 → (lo, hi)（数值轴有序；区间双端取 min/max）。"""
    text = cell.replace("*", "").strip()
    m = _ADJ_RANGE.search(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (min(a, b), max(a, b))
    m = _ADJ_SINGLE.search(text)
    if m:
        v = float(m.group(1))
        return (v, v)
    raise ValueError(f"§5.1 调整幅度单元格无法解析（行 {row_name!r}）: {cell!r}")


def _parse_mapping(text: str) -> dict:
    """§5.1 → {类别键: MappingRow}；十二行缺一/重行/列数不足即 raise。"""
    sec = _section(text, "5.1")
    rows = _table_rows(sec, _MAP_HEADER_RE, "§5.1 核心映射表")
    by_name = {name: key for key, (name, _, _) in CATEGORY_MAP.items()}
    out = {}
    for cells in rows:
        if len(cells) < 5:
            raise ValueError(f"§5.1 映射表行列数不足: {cells!r}")
        name = cells[0].replace("*", "").strip()
        if name not in by_name:
            continue  # 杂行不入（行名漂移由十二行下界兜底）
        key = by_name[name]
        if key in out:
            raise ValueError(f"§5.1 映射行 {name!r} 重复出现")
        _, dim, taxonomy = CATEGORY_MAP[key]
        lo, hi = _parse_adjust_cell(cells[4], name)
        out[key] = MappingRow(
            category=key, name=name, dimension=dim, taxonomy=taxonomy,
            lo=lo, hi=hi, transmission=cells[1], speed=cells[2],
            impact=cells[3], adjust_text=cells[4],
        )
    missing = [k for k in CATEGORY_MAP if k not in out]
    if missing:
        raise ValueError(
            f"§5.1 核心映射表应有 12 行，缺 {missing}"
            f"（实际解析 {len(out)} 行，疑似表格漂移致静默丢行）"
        )
    return out


# §5.3 速查表表头锚点（:458）。
_QUICK_HEADER_RE = re.compile(
    r"^\|\s*信号强度\s*\|\s*ESG调整幅度\s*\|\s*触发条件\s*\|",
    re.MULTILINE,
)
_QUICK_STRENGTHS = ("无信号", "弱信号", "中等信号", "强信号", "极端信号")


def _parse_quick_ref(text: str) -> tuple:
    """§5.3 → 5 档 dict（文档顺序）；档名去括注归一，五档缺一即 raise。"""
    sec = _section(text, "5.3")
    rows = _table_rows(sec, _QUICK_HEADER_RE, "§5.3 调整规则速查表")
    out = []
    for cells in rows:
        if len(cells) < 3:
            raise ValueError(f"§5.3 速查表行列数不足: {cells!r}")
        strength = cells[0].split("（")[0].strip()
        if strength not in _QUICK_STRENGTHS:
            continue
        out.append({
            "strength": strength,
            "strength_raw": cells[0],
            "adjustment": cells[1],
            "trigger": cells[2],
        })
    if [r["strength"] for r in out] != list(_QUICK_STRENGTHS):
        raise ValueError(
            f"§5.3 速查表应为 {list(_QUICK_STRENGTHS)} 五档（顺序），"
            f"实际 {[r['strength'] for r in out]}"
        )
    return tuple(out)


def _appendix_a_section(text: str) -> str:
    """附录A 切片（``## `` 级标题；终于下一个 ``## `` 或文末）。"""
    sec = re.search(
        r"^## 附录A：各行业ESG敏感度对照.*?(?=\n## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if not sec:
        raise ValueError("附录A 段落缺失（疑似章节漂移）")
    return sec.group(0)


# 附录A 表头锚点（:614）。
_INDUSTRY_HEADER_RE = re.compile(
    r"^\|\s*行业\s*\|\s*E环境敏感度\s*\|\s*S社会敏感度\s*\|\s*G治理敏感度\s*\|"
    r"\s*最敏感的ESG维度\s*\|\s*备注\s*\|",
    re.MULTILINE,
)
_INDUSTRY_MIN_ROWS = 19  # 行数下界（防静默丢行）
_SENSITIVITY_LEVELS = ("高", "中", "低", "低-中")


def _parse_level(cell: str, industry: str, dim: str) -> str:
    """敏感度单元格 → 档位（去加粗/去括注；非法档即 raise）。"""
    level = cell.replace("*", "").split("（")[0].strip()
    if level not in _SENSITIVITY_LEVELS:
        raise ValueError(
            f"附录A 行业 {industry!r} {dim} 维度敏感度档位非法: {cell!r}"
            f"（允许值：{_SENSITIVITY_LEVELS}）"
        )
    return level


def _parse_industry_sensitivity(text: str) -> dict:
    """附录A → {行业: {E/S/G 档位, most_sensitive, note}}；行数低于下界/重行即 raise。"""
    sec = _appendix_a_section(text)
    rows = _table_rows(sec, _INDUSTRY_HEADER_RE, "附录A 行业敏感度表")
    out = {}
    for cells in rows:
        if len(cells) < 6:
            raise ValueError(f"附录A 行业行列数不足: {cells!r}")
        industry = cells[0].replace("*", "").strip()
        if industry in out:
            raise ValueError(f"附录A 行业 {industry!r} 重复出现")
        out[industry] = {
            "E": _parse_level(cells[1], industry, "E"),
            "S": _parse_level(cells[2], industry, "S"),
            "G": _parse_level(cells[3], industry, "G"),
            "most_sensitive": cells[4],
            "note": cells[5],
        }
    if len(out) < _INDUSTRY_MIN_ROWS:
        raise ValueError(
            f"附录A 行业敏感度表行数 {len(out)} 低于下界 {_INDUSTRY_MIN_ROWS}"
            "（疑似表格漂移致静默丢行）"
        )
    return out


# §7.1 可得性表表头锚点（:531）。
_AVAIL_HEADER_RE = re.compile(
    r"^\|\s*维度\s*\|\s*可观测比例（估算）\s*\|\s*主要数据来源\s*\|\s*关键缺口\s*\|\s*空缺的影响\s*\|",
    re.MULTILINE,
)
_AVAIL_MIN_ROWS = 9


def _parse_availability(text: str) -> dict:
    """§7.1 → {维度行名: {coverage, source, gap, impact}}；行数低于下界/重行即 raise。"""
    sec = _section(text, "7.1")
    rows = _table_rows(sec, _AVAIL_HEADER_RE, "§7.1 数据可得性表")
    out = {}
    for cells in rows:
        if len(cells) < 5:
            raise ValueError(f"§7.1 可得性表行列数不足: {cells!r}")
        dim = cells[0].replace("*", "").strip()
        if dim in out:
            raise ValueError(f"§7.1 维度行 {dim!r} 重复出现")
        out[dim] = {
            "coverage": cells[1], "source": cells[2],
            "gap": cells[3], "impact": cells[4],
        }
    if len(out) < _AVAIL_MIN_ROWS:
        raise ValueError(
            f"§7.1 可得性表行数 {len(out)} 低于下界 {_AVAIL_MIN_ROWS}"
            "（疑似表格漂移致静默丢行）"
        )
    # 诚实降级的覆盖率单一事实源：E1/S2 锚定行必须存在（缺行即 raise）。
    for row_key in TAXONOMY_AVAILABILITY_ROW.values():
        if row_key not in out:
            raise ValueError(f"§7.1 可得性表缺锚定行 {row_key!r}（E1/S2 降级注记数据源）")
    return out


def load_esg_tables(path=None) -> EsgTables:
    """运行时解析 §5.1/§5.3/附录A/§7.1 四表；任一解析失败即 raise。"""
    text = _read(path)
    return EsgTables(
        mapping=_parse_mapping(text),
        quick_ref=_parse_quick_ref(text),
        industry_sensitivity=_parse_industry_sensitivity(text),
        availability=_parse_availability(text),
    )


# --------------------------------------------------------------------------
# 评分层
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EsgEvent:
    """ESG 事件输入（LLM 采集/判断，引擎确定计算）。

    event_id 为互斥归并键（§6.3：同一事件只触发一次调整）；缺省退化为
    (维度, 类别, 证据) 三元组——全同即同一事件。llm_judged=True 标注该事件
    为 LLM 判断输入（留痕，不改变计算）。
    """

    dimension: str          # "E" | "S" | "G"
    category: str           # CATEGORY_MAP 类别键（§5.1 十二行之一）
    severity: str           # "I" | "II" | "III" | "IV" | "POSITIVE"
    evidence: str
    source: str
    llm_judged: bool = False
    event_id: str = ""


@dataclass(frozen=True)
class EsgResult:
    """compute_esg 输出（字段口径见 compute_esg docstring）。"""

    notch_adjustment: int        # -1 | 0（D4：±0.5 不落地为子级）
    flags: list                  # "negative_flag" | "positive_flag"
    signal_strength: str         # §5.3 速查档：无信号/弱信号/中等信号/强信号
    per_dimension: dict          # E/S/G 各 {score（钳前合计）, summary}
    trigger_events: list         # 每事件留痕 dict（含 counted 互斥标记）
    elasticity_factors: dict     # {interest_coverage, cash_runway_months, band}
    data_availability: dict      # {notes, low_coverage_taxonomies}
    notes: list


def _snap(value: float, mode: str) -> float:
    """0.5 子级格点吸附。恰在半格时：mode="zero" 向零、mode="away" 远离零。"""
    u = value * 2.0
    f = math.floor(u)
    frac = u - f
    if frac < 0.5:
        r = f
    elif frac > 0.5:
        r = f + 1
    else:  # 恰在半格
        if mode == "away":
            r = f + 1 if u >= 0 else f
        else:
            r = f if u >= 0 else f + 1
    return r * 0.5


def _elasticity_band(elasticity: dict) -> tuple:
    """§5.2 :447-448 弹性分带 → (带, 注记|None)。缺键 → 未知（不静默按中处理）。"""
    cov = elasticity.get("interest_coverage")
    run = elasticity.get("cash_runway_months")
    if cov is None or run is None:
        return "未知", "弹性数据缺键（interest_coverage/cash_runway_months），按默认（区间最轻端）取值"
    if cov > _ELAST_STRONG_COVERAGE and run > _ELAST_STRONG_RUNWAY:
        return "强", None
    if cov < _ELAST_WEAK_COVERAGE and run < _ELAST_WEAK_RUNWAY:
        return "弱", None
    return "中", None


def _event_adjustment(event: EsgEvent, row: MappingRow, band: str,
                      industry_levels: dict, notes: list) -> float:
    """①② 单事件链：基值 ∩ 严重性档 → 弹性选点/减半 → 行业 ×1.5 → 单事件钳。"""
    sev_lo, sev_hi = SEVERITY_RANGE[event.severity]
    lo, hi = max(row.lo, sev_lo), min(row.hi, sev_hi)
    if lo > hi:
        raise ValueError(
            f"事件 {event.category!r} 严重性 {event.severity} 区间 "
            f"{SEVERITY_RANGE[event.severity]} 与 §5.1 基值区间 ({row.lo}, {row.hi}) "
            "交集为空（输入矛盾，失败可观测）"
        )
    # 弹性选点：弱 → 区间最重端（取上限，:448）；其余 → 最轻端（缺省保守口径）
    point = lo if band == "弱" else hi
    if band == "强" and point != 0.0:
        halved = _snap(point / 2, "zero")
        notes.append(
            f"事件 {row.name}：财务弹性强（:447）→ 调整幅度减半档 "
            f"{point}→{halved}（0.5 子级格点向零吸附）"
        )
        point = halved
    if industry_levels is not None and industry_levels[row.dimension] == "高":
        scaled = _snap(point * _INDUSTRY_MULTIPLIER, "away")
        if scaled != point:
            notes.append(
                f"事件 {row.name}：行业 {row.dimension} 维度敏感度=高（附录A/:450-453）"
                f"→ ×{_INDUSTRY_MULTIPLIER} {point}→{scaled}（格点远离零吸附）"
            )
        point = scaled
    clamped = max(_EVENT_LO, min(_EVENT_HI, point))
    if clamped != point:
        notes.append(f"事件 {row.name}：单事件钳制 [{_EVENT_LO}, {_EVENT_HI}] {point}→{clamped}")
    return clamped


# §5.3 信号强度 → 速查带（lo, hi）（:460-463；极端信号不由本引擎判定，D6）。
_QUICK_BANDS = {
    "无信号": (0.0, 0.0),
    "弱信号": (0.0, 0.0),
    "中等信号": (-0.5, -0.5),
    "强信号": (-1.0, -0.5),
}


def _signal_strength(counted: list, band: str, industry_levels) -> str:
    """§5.3 :460-463 分级。「2个以上III级」按含本数口径 ≥2（:462）。"""
    if not counted:
        return "无信号"
    severities = [t["severity"] for t in counted]
    if "I" in severities:
        return "强信号"
    n_ii = severities.count("II")
    n_iii = severities.count("III")
    if n_ii >= 1:
        # II级 + 财务弹性弱 + 行业高敏感 → 强信号（:463）
        if band == "弱" and industry_levels is not None:
            for t in counted:
                if t["severity"] == "II" and industry_levels[t["dimension"]] == "高":
                    return "强信号"
        return "中等信号"
    if n_iii >= 2:
        return "中等信号"
    return "弱信号"


def compute_esg(events: list, elasticity: dict, industry: str,
                tables: EsgTables = None) -> EsgResult:
    """ESG 事件映射链：① §5.1 基值 → ② §5.2 修正 → ③ §5.3 归并 → ④ 互斥+±1
    总限 → ⑤ D4 落地。

    events 契约：EsgEvent 列表；category 须为 CATEGORY_MAP 十二键之一，
    dimension 须与类别归属维度一致，severity 须为五档之一（否则 raise）。
    elasticity 契约：{"interest_coverage": x 倍, "cash_runway_months": 月}；
    缺键 → 未知带（默认最轻端 + 注记）。industry 为附录A 行业名原文
    （如 "煤炭"/"银行/券商"）；未收录 → 行业修正不适用 + 注记（不 raise）。
    """
    tables = tables if tables is not None else load_esg_tables()
    notes: list = []
    flags: list = []

    band, band_note = _elasticity_band(elasticity or {})
    if band_note:
        notes.append(band_note)
    elasticity_factors = {
        "interest_coverage": (elasticity or {}).get("interest_coverage"),
        "cash_runway_months": (elasticity or {}).get("cash_runway_months"),
        "band": band,
    }

    industry_levels = None
    if industry:
        industry_levels = tables.industry_sensitivity.get(industry)
        if industry_levels is None:
            notes.append(
                f"行业 {industry!r} 未收录于附录A，行业敏感性修正（×1.5）不适用"
            )
    else:
        notes.append("未提供行业，行业敏感性修正（×1.5）不适用")

    # ①② 逐事件映射 + 修正
    per_event = []
    for event in events:
        if event.category not in CATEGORY_MAP:
            raise ValueError(
                f"未知事件类别 {event.category!r}"
                f"（允许值：{tuple(CATEGORY_MAP)}）"
            )
        row = tables.mapping[event.category]
        if event.dimension not in _DIMENSIONS:
            raise ValueError(
                f"事件维度 {event.dimension!r} 非法（允许值：{_DIMENSIONS}）"
            )
        if event.dimension != row.dimension:
            raise ValueError(
                f"事件 {event.category!r} 维度 {event.dimension!r} 与 §5.1 归属 "
                f"{row.dimension!r} 不一致（输入矛盾）"
            )
        if event.severity not in SEVERITY_RANGE:
            raise ValueError(
                f"事件严重性 {event.severity!r} 非法"
                f"（允许值：{tuple(SEVERITY_RANGE)}）"
            )
        adj = _event_adjustment(event, row, band, industry_levels, notes)
        per_event.append({
            "event_id": event.event_id,
            "dimension": row.dimension,
            "category": event.category,
            "taxonomy": row.taxonomy,
            "name": row.name,
            "severity": event.severity,
            "base_lo": row.lo,
            "base_hi": row.hi,
            "adjustment": adj,
            "evidence": event.evidence,
            "source": event.source,
            "llm_judged": event.llm_judged,
            "counted": True,
        })

    # ④ 互斥归并（§6.3 :521/:523）：同一事件计 1 次取最重（|adjustment| 最大；
    # 并列取负向——§1.2 原则 4 非对称调整）
    groups = {}
    for rec in per_event:
        key = rec["event_id"] or (rec["dimension"], rec["category"], rec["evidence"])
        groups.setdefault(key, []).append(rec)
    counted, deduped = [], 0
    for key, members in groups.items():
        if len(members) == 1:
            counted.append(members[0])
            continue
        deduped += len(members) - 1
        heaviest = max(
            members,
            key=lambda r: (abs(r["adjustment"]), r["adjustment"] < 0),
        )
        for r in members:
            if r is heaviest:
                counted.append(r)
            else:
                r["counted"] = False
        notes.append(
            f"互斥归并（§6.3）：事件键 {key!r} 重复 {len(members)} 次，计 1 次取最重 "
            f"（{heaviest['name']} severity={heaviest['severity']} → {heaviest['adjustment']}）"
        )
    if deduped:
        notes.append(f"互斥归并共去重 {deduped} 条重复事件记录")

    total = sum(r["adjustment"] for r in counted)
    clamped_total = max(_TOTAL_LO, min(_TOTAL_HI, total))
    if clamped_total != total:
        notes.append(
            f"累计调整 {total} 超出 ±1 子级上限（§6.3 :522/§7.3 :565）"
            f"→ 钳制为 {clamped_total}"
        )

    # ⑤ D4 落地（-1→降档；-0.5→negative_flag；+0.5→positive_flag）
    if clamped_total <= -1.0:
        notch = -1
    elif clamped_total < 0.0:
        notch = 0
        flags.append("negative_flag")
        notes.append("D4 落地：-0.5 子级不落地为降档 → 0 + negative_flag")
    elif clamped_total > 0.0:
        notch = 0
        flags.append("positive_flag")
        notes.append(
            "D4 落地：正向调整不落地为子级（§1.2 原则 4 非对称调整）→ 0 + positive_flag"
        )
    else:
        notch = 0

    # ③ §5.3 速查归并：信号强度分级 + 带外 advisory
    strength = _signal_strength(counted, band, industry_levels)
    lo_b, hi_b = _QUICK_BANDS[strength]
    if not (lo_b <= clamped_total <= hi_b):
        notes.append(
            f"速查归并 advisory：信号强度「{strength}」对应 §5.3 带 "
            f"[{lo_b}, {hi_b}]，累计调整 {clamped_total} 落于带外"
            "（弹性/行业修正因子所致），以链式计算为准"
        )
    if any(r["severity"] == "I" for r in counted):
        notes.append(
            "I 级事件在列：是否构成 §5.3 极端信号（核心业务不可逆丧失→一票否决）"
            "须由 LLM/调用方复核（D6：无阈值不新造，本引擎不判定否决）"
        )
    if any(r["llm_judged"] for r in counted):
        notes.append("含 LLM 判断输入事件（llm_judged=True），结论置信度须结合证据强度复核")

    # per_dimension：钳前合计 + 摘要（审计留痕）
    per_dimension = {}
    for dim in _DIMENSIONS:
        recs = [r for r in counted if r["dimension"] == dim]
        per_dimension[dim] = {
            "score": sum(r["adjustment"] for r in recs),
            "summary": "、".join(r["name"] for r in recs) if recs else "无异常事件",
        }

    # 诚实降级：E1 碳排放 / S2 劳工（§7.1 低覆盖，强制注记）
    avail_notes = []
    low_cov = sorted({r["taxonomy"] for r in counted if r["taxonomy"] in TAXONOMY_AVAILABILITY_ROW})
    for tax in low_cov:
        row_key = TAXONOMY_AVAILABILITY_ROW[tax]
        avail = tables.availability[row_key]
        avail_notes.append(
            f"{tax}（{row_key}）数据覆盖率仅 {avail['coverage']}（§7.1），"
            f"事件检测能力受限——{avail['impact'].split('——')[0]}，结论置信度须下调（诚实降级）"
        )

    return EsgResult(
        notch_adjustment=notch,
        flags=flags,
        signal_strength=strength,
        per_dimension=per_dimension,
        trigger_events=per_event,
        elasticity_factors=elasticity_factors,
        data_availability={
            "notes": avail_notes,
            "low_coverage_taxonomies": low_cov,
        },
        notes=notes,
    )

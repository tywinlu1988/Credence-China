"""WP-M0-02 → external-support-framework.md 的外部支持引擎（T4 能力侧 + T5 全链）。

单一事实源：§4.1「关键指标阈值参考」表（6 指标 × 4 档）、§4.3 集团/母公司
四档量化表（5 指标 × 4 档）、§4.4 战略投资者四档量化表（4 指标 × 4 档）、
§3.2 矩阵使用规则、§6.1 支持强度判定矩阵、§6.2 上调幅度映射、§7.3 陷阱信号
行动规则、§8.2 政策信号映射均运行时解析，解析失败即 raise（不裸复制数值副本）。

边界语义（全引擎统一，文档档位文本直译）：">X" / "<X" 为开区间端点
（3000亿 → 中等档），"X-Y" 为闭区间；GDP 增速极弱档 "<2%或负增长" 解析数值
部分（"或负增长"为文本修饰，负增长值天然落入 "<2%" 开区间）。§4.3/§4.4
四档量化表（v0.12.1 裁决表）语义独立：数值档 "≥X" 左闭、"<X" 开、
"[lo,hi)" 左闭右开；评级档 "X及以下" 沿 18 档序展开到底。

已裁决设计决策（SDD 2026-08-10-wp-m0-02，注释处标注）：
- D1 意愿等权：逐信号 强=3 / 中=1.5 / 弱=0，均值 ∈ [0,3]。
- D3 子级换算：1 子级 = 1 个 18 档步进 = 0.5 分（复用 src/rating_map.py 的
  CANONICAL_RATING_INTERVALS 档序做步进运算，不复制档位）。
- D4 落点：意愿档 高→区间上限；中→中位（round，银行家舍入已认可）；低→下限
  （意愿档界与 D5 分档完全对齐：高 [2.5,3.0]、中 [1.5,2.5)、低 [0,1.5)）。
- D5 矩阵分档边界：左闭右开（§6.1 表端点重叠的处理）。

v0.12.1 裁决补充（SDD 2026-08-13-v0.12.1-debt-repayment Task 1）：
- §4.3/§4.4 四档量化表为裁决扩展（强弱锚点为原文，中间档为裁决扩展），
  capacity_score 按 support_type ∈ {government, group, strategic} 分派：
  group 消费 §4.3 五指标、strategic 消费 §4.4 四指标，等权均值（无 F 维度）。
- §4.3 经营活动现金流 3 档「持续为正且覆盖利息」操作化为 coverage≥1（左闭）。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir
from src.rating_map import CANONICAL_RATING_INTERVALS  # 18 档单源，不复制

_DOC_NAME = "external-support-framework.md"

# §4.1 四维模型表（:194-211）的指标→维度结构归属（硬编码 + parity 锚定：
# tests/test_external_support_scorer.py 回读 "**F1 财政实力**" 等行首加粗锚点）。
# 注：阈值分档表仅覆盖四维模型 16 指标中的 6 个核心指标；GDP增速 在阈值表中的
# 行名为 "GDP增速（近3年均值）"，解析时剥离括注归一到本键。
INDICATOR_TO_FACTOR = {
    "一般公共预算收入": "F1",
    "财政自给率": "F1",
    "政府显性债务率": "F2",
    "GDP增速": "F3",
    "人口趋势": "F3",
    "转移支付依赖度": "F4",
}

_FACTORS = ("F1", "F2", "F3", "F4")

# §4.3 集团/母公司四档量化表（:251-262）指标行 → (输入键, 档位类型)
# （硬编码 + parity 锚定：tests/test_external_support_scorer.py 回读行名）。
# 档位类型：rating=18 档评级带 / numeric=数值区间 / enum=强中弱极弱标签。
GROUP_INDICATORS = {
    "母公司独立信用质量": ("parent_credit", "rating"),
    "未质押资产规模": ("unpledged_ratio", "numeric"),
    "融资渠道多样性": ("funding_channels", "enum"),
    "经营活动现金流": ("operating_cf_coverage", "numeric"),
    "资产流动性": ("asset_liquidity", "enum"),
}

# §4.4 战略投资者四档量化表（:264-274）指标行 → (输入键, 档位类型)。
STRATEGIC_INDICATORS = {
    "战投自身信用评级": ("investor_credit", "rating"),
    "投资金额vs战投资产规模": ("investment_share", "numeric"),
    "投资承诺的法律约束力": ("commitment", "enum"),
    "锁定期/退出安排": ("lockup_years", "numeric"),
}

# capacity_score 支持类型分派（v0.12.1）；未知类型 raise。
_CAPACITY_TYPES = ("government", "group", "strategic")


@dataclass(frozen=True)
class ThresholdTier:
    """§4.1 阈值分档表单一档。

    数值档：lo/hi 为区间端点（None = 该侧无界），lo_open/hi_open 标记开区间
    端点（">X"/"<X"），"X-Y" 闭区间两端均为 False；unit ∈ {"亿", "%"}。
    枚举档（人口趋势）：lo/hi 均 None、unit 为 ""，按 label 等值匹配。
    label 恒为文档单元格原文（审计留痕）。
    """

    score: int
    label: str
    lo: float = None
    hi: float = None
    lo_open: bool = False
    hi_open: bool = False
    unit: str = ""


@dataclass(frozen=True)
class CapacityTier:
    """§4.3/§4.4 四档量化表单一档（v0.12.1 裁决表）。

    kind ∈ {"numeric", "rating", "enum"}：
    - numeric：lo/hi 为区间端点（None = 该侧无界）；"≥X" 左闭（lo_open=False）、
      "<X" 开（hi_open=True）、"[lo,hi)" 左闭右开（hi_open=True）。
    - rating：ratings 为该档覆盖的 18 档标签集合（"X及以下" 沿档序展开到底）。
    - enum：enum_label ∈ {强, 中, 弱, 极弱}，输入标签等值匹配。
    label 恒为文档单元格原文（审计留痕；数值档允许尾部全角括注锚点）。
    """

    score: int
    label: str
    kind: str
    lo: float = None
    hi: float = None
    lo_open: bool = False
    hi_open: bool = False
    ratings: frozenset = None
    enum_label: str = None


@dataclass(frozen=True)
class SupportTables:
    """external-support-framework.md 可解析表的运行时解析结果。

    thresholds:     §4.1 阈值分档表 → {指标: (ThresholdTier ×4, 按 3→0 降序)}。
    group_thresholds: §4.3 集团/母公司四档量化表 → {输入键: (CapacityTier ×4,
                    3→0 降序)}（5 指标；v0.12.1）。
    strategic_thresholds: §4.4 战略投资者四档量化表 → {输入键: (CapacityTier ×4,
                    3→0 降序)}（4 指标；v0.12.1）。
    matrix_rules:   §3.2 矩阵使用规则表 → {区域("A"-"D"): {uplift_text,
                    confidence, annotation}}（文本均为文档单元格原文）。
    strength_matrix: §6.1 支持强度判定 3×3 矩阵 → {意愿档("高/中/低"):
                    {能力档("强/中/弱"): 强度}}。
    uplift_map:     §6.2 上调幅度映射 → {强度: (子级下限, 子级上限)}。
    trap_actions:   §7.3 陷阱信号行动规则表 → 4 条 dict（kind 为结构归类：
                    red / orange2 / orange_asset / fiscal；trigger/response/
                    impact 为文档原文）。
    policy_map:     §8.2 政策信号映射 → {政策信号: 综合影响方向}（"——"前原文）。
    """

    thresholds: dict
    matrix_rules: dict = None
    strength_matrix: dict = None
    uplift_map: dict = None
    trap_actions: tuple = None
    policy_map: dict = None
    group_thresholds: dict = None
    strategic_thresholds: dict = None


def _read(path) -> str:
    p = Path(path) if path else engine_dir() / _DOC_NAME
    return p.read_text(encoding="utf-8")


def _section(text: str, num: str) -> str:
    """按节号切片。``^### `` 行首锁防正文提及误锚；``(?!\\d)`` 节号边界防
    ``### 4.10`` 之类的前缀误锚（锚点须为独立小节标题行）。"""
    sec = re.search(
        rf"^### {re.escape(num)}(?!\d)\s.*?(?=\n### |\n## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if not sec:
        raise ValueError(f"§{num} 段落缺失")
    return sec.group(0)


# §4.1 阈值分档表表头锚点（档位列名漂移 → 解析即 raise，不容忍错列静默）。
_THRESHOLD_HEADER_RE = re.compile(
    r"^\|\s*指标\s*\|\s*强（3分）\s*\|\s*中等（2分）\s*\|\s*弱（1分）\s*\|\s*极弱（0分）\s*\|",
    re.MULTILINE,
)

_ROW_RE = re.compile(
    r"^\|\s*([^|*]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

_CELL_GT = re.compile(r">(\d+(?:\.\d+)?)(亿|%)")
_CELL_LT = re.compile(r"<(\d+(?:\.\d+)?)(亿|%)(?:或负增长)?")
_CELL_RANGE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(亿|%)")


def _parse_tier_cell(score: int, cell: str) -> ThresholdTier:
    """">3000亿" / "<2%或负增长" / "1000-3000亿" / 枚举原文 → ThresholdTier。"""
    label = cell.strip()
    m = _CELL_GT.fullmatch(label)
    if m:
        return ThresholdTier(score, label, lo=float(m.group(1)), lo_open=True, unit=m.group(2))
    m = _CELL_RANGE.fullmatch(label)
    if m:
        return ThresholdTier(
            score, label, lo=float(m.group(1)), hi=float(m.group(2)), unit=m.group(3),
        )
    m = _CELL_LT.fullmatch(label)
    if m:
        return ThresholdTier(score, label, hi=float(m.group(1)), hi_open=True, unit=m.group(2))
    if not re.search(r"\d", label):
        return ThresholdTier(score, label)  # 枚举档（人口趋势）
    raise ValueError(f"§4.1 阈值单元格无法解析: {label!r}")


def _validate_tier_row(name: str, tiers: tuple) -> None:
    """行内一致性：数值档与枚举档不得混排；数值档单位须一致。"""
    numeric = [t for t in tiers if t.unit]
    if numeric and len(numeric) != len(tiers):
        raise ValueError(f"§4.1 指标 {name!r} 数值档与枚举档混排（疑似表格错位）")
    if numeric and len({t.unit for t in numeric}) != 1:
        raise ValueError(f"§4.1 指标 {name!r} 各档单位不一致（疑似表格错位）")


def _parse_thresholds(text: str) -> dict:
    """§4.1 → {指标: (ThresholdTier ×4, 3→0 降序)}；六指标缺一即 raise。"""
    sec = _section(text, "4.1")
    if not _THRESHOLD_HEADER_RE.search(sec):
        raise ValueError(
            "§4.1 阈值分档表表头缺失（应有「指标 | 强（3分）| 中等（2分）| 弱（1分）| 极弱（0分）」）"
        )
    thresholds = {}
    for m in _ROW_RE.finditer(sec):
        raw_name = m.group(1).strip()
        name = re.sub(r"（[^）]*）\s*$", "", raw_name)  # "GDP增速（近3年均值）" → "GDP增速"
        if name not in INDICATOR_TO_FACTOR:
            continue  # 表头行/分隔行/四维模型表行（首列加粗或为空，天然不入）
        if name in thresholds:
            raise ValueError(f"§4.1 指标 {name!r} 重复出现")
        tiers = tuple(
            _parse_tier_cell(score, m.group(col))
            for score, col in ((3, 2), (2, 3), (1, 4), (0, 5))
        )
        _validate_tier_row(name, tiers)
        thresholds[name] = tiers
    missing = [n for n in INDICATOR_TO_FACTOR if n not in thresholds]
    if missing:
        raise ValueError(
            f"§4.1 阈值分档表应有 6 指标行，缺 {missing}"
            f"（实际解析 {len(thresholds)} 行，疑似表格漂移致静默丢行）"
        )
    return thresholds


# §4.3/§4.4 四档量化表表头锚点（7 列；档位列名漂移 → 解析即 raise）。
_FOURTIER_HEADER_RE = re.compile(
    r"^\|\s*指标\s*\|\s*评估方法\s*\|\s*数据来源\s*\|\s*强（3分）\s*"
    r"\|\s*中等（2分）\s*\|\s*弱（1分）\s*\|\s*极弱（0分）\s*\|",
    re.MULTILINE,
)

# §4.3/§4.4 单元格语法（v0.12.1 裁决表）：
# 数值档 "≥X"（左闭）/ "<X"（开）/ "[lo,hi)"（左闭右开），允许尾部全角括注锚点
# （如 "≥2（充裕覆盖子公司债务的2x+）"——强弱锚点原文留痕，解析前剥离）；
# 评级档 "AAA/AA+" 精确带 ∪ "X及以下（或无评级）"（沿 18 档序展开到底）；
# 枚举档 "标签：描述原文"，标签 ∈ {强, 中, 弱, 极弱} 且与分值 3/2/1/0 对齐。
_CT_GE = re.compile(r"≥(\d+(?:\.\d+)?)")
_CT_LT = re.compile(r"<(\d+(?:\.\d+)?)")
_CT_INTERVAL = re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)")
_CT_BELOW = re.compile(r"(.+?)及以下(?:或无评级)?")
_TRAILING_NOTE = re.compile(r"（[^）]*）\s*$")
_ENUM_LABEL_BY_SCORE = {3: "强", 2: "中", 1: "弱", 0: "极弱"}


def _parse_capacity_cell(kind: str, score: int, cell: str, sec: str) -> CapacityTier:
    """§4.3/§4.4 单元格 → CapacityTier；语法不符即 raise（不静默落档）。"""
    label = cell.strip()
    if kind == "numeric":
        text = _TRAILING_NOTE.sub("", label)  # 尾部锚点括注不入数值解析
        m = _CT_GE.fullmatch(text)
        if m:
            return CapacityTier(score, label, "numeric", lo=float(m.group(1)))
        m = _CT_INTERVAL.fullmatch(text)
        if m:
            return CapacityTier(
                score, label, "numeric",
                lo=float(m.group(1)), hi=float(m.group(2)), hi_open=True,
            )
        m = _CT_LT.fullmatch(text)
        if m:
            return CapacityTier(score, label, "numeric", hi=float(m.group(1)), hi_open=True)
        raise ValueError(f"{sec} 数值档单元格无法解析: {label!r}")
    if kind == "rating":
        ratings = set()
        for tok in label.split("/"):
            tok = tok.strip()
            if not tok or tok == "或无评级":
                continue  # "或无评级" 为文本修饰（无评级主体天然落入最低档语义）
            m = _CT_BELOW.fullmatch(tok)
            if m:
                base = m.group(1).strip()
                if base not in _RATING_INDEX:
                    raise ValueError(
                        f"{sec} 评级档基准 {base!r} 不在 18 档档序内: {label!r}"
                    )
                ratings.update(_LADDER[_RATING_INDEX[base]:])  # 及以下 → 展开到底
            elif tok in _RATING_INDEX:
                ratings.add(tok)
            else:
                raise ValueError(f"{sec} 评级档单元格无法解析: {label!r}")
        return CapacityTier(score, label, "rating", ratings=frozenset(ratings))
    # enum
    enum_label = label.split("：")[0].strip()
    if enum_label not in _ENUM_LABEL_BY_SCORE.values():
        raise ValueError(
            f"{sec} 枚举档单元格标签非法: {label!r}"
            f"（允许值：{tuple(_ENUM_LABEL_BY_SCORE.values())}）"
        )
    return CapacityTier(score, label, "enum", enum_label=enum_label)


def _validate_capacity_row(sec: str, name: str, kind: str, tiers: tuple) -> None:
    """行内一致性：枚举档标签与分值对齐；评级档各带不得重叠（疑似表格错位）。"""
    if kind == "enum":
        for t in tiers:
            if t.enum_label != _ENUM_LABEL_BY_SCORE[t.score]:
                raise ValueError(
                    f"{sec} 指标 {name!r} 枚举标签与分值错位"
                    f"（{t.score} 分档应为 {_ENUM_LABEL_BY_SCORE[t.score]!r}，"
                    f"实际 {t.enum_label!r}）"
                )
    if kind == "rating":
        seen = set()
        for t in tiers:
            overlap = seen & t.ratings
            if overlap:
                raise ValueError(f"{sec} 指标 {name!r} 评级带重叠 {sorted(overlap)}")
            seen |= t.ratings


def _parse_capacity_quads(text: str, num: str, indicator_map: dict) -> dict:
    """§4.3/§4.4 四档量化表 → {输入键: (CapacityTier ×4, 3→0 降序)}。

    行数下界 = 指标映射全量（缺行/重行即 raise，同 §4.1/§8.2 先例）；
    行名 → 输入键/档位类型为硬编码结构归属（parity 锚定见 tests）。
    """
    desc = f"§{num} 四档量化表"
    sec = _section(text, num)
    _, rows = _table_rows(sec, _FOURTIER_HEADER_RE, desc)
    out = {}
    for cells in rows:
        if len(cells) < 7:
            raise ValueError(f"{desc} 行列数不足: {cells!r}")
        name = cells[0]
        if name not in indicator_map:
            continue  # 杂行不入（行名漂移由行数下界兜底）
        key, kind = indicator_map[name]
        if key in out:
            raise ValueError(f"{desc} 指标 {name!r} 重复出现")
        tiers = tuple(
            _parse_capacity_cell(kind, score, cells[col], f"§{num}")
            for score, col in ((3, 3), (2, 4), (1, 5), (0, 6))
        )
        _validate_capacity_row(f"§{num}", name, kind, tiers)
        out[key] = tiers
    missing = [k for k, _ in indicator_map.values() if k not in out]
    if missing:
        raise ValueError(
            f"{desc} 应有 {len(indicator_map)} 指标行，缺 {missing}"
            f"（实际解析 {len(out)} 行，疑似表格漂移致静默丢行）"
        )
    return out


def _table_rows(sec: str, header_re: re.Pattern, header_desc: str):
    """锚定表头行后顺序采集数据行 → (表头单元格, 数据行单元格列表)。

    表头漂移即 raise；分隔行（|---|---|）跳过；数据行一开始后遇到首个非表格行
    （空行/正文）即停止（防越界吞并后续段落）。
    """
    m = header_re.search(sec)
    if not m:
        raise ValueError(f"{header_desc} 表头缺失（疑似表格漂移）")
    line_start = sec.rfind("\n", 0, m.start()) + 1
    line_end = sec.find("\n", m.end())
    header_line = sec[line_start: line_end if line_end != -1 else len(sec)]
    header = [c.strip() for c in header_line.strip().strip("|").split("|")]
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
    return header, rows


# §3.2 矩阵使用规则表表头锚点。
_REGION_HEADER_RE = re.compile(
    r"^\|\s*区域\s*\|\s*外部支持上调幅度\s*\|\s*置信度\s*\|\s*报告标注要求\s*\|",
    re.MULTILINE,
)
_REGION_CELL = re.compile(r"\*\*([ABCD])区\*\*")


def _parse_matrix_rules(text: str) -> dict:
    """§3.2 → {区域: {uplift_text, confidence, annotation}}；A/B/C/D 缺一即 raise。"""
    sec = _section(text, "3.2")
    _, rows = _table_rows(sec, _REGION_HEADER_RE, "§3.2 矩阵使用规则表")
    rules = {}
    for cells in rows:
        m = _REGION_CELL.fullmatch(cells[0])
        if not m:
            continue  # 非区域行（防御：表内杂行不入）
        if len(cells) < 4:
            raise ValueError(f"§3.2 区域行 {cells[0]!r} 列数不足（疑似表格错位）")
        region = m.group(1)
        if region in rules:
            raise ValueError(f"§3.2 区域 {region!r} 重复出现")
        rules[region] = {
            "uplift_text": cells[1], "confidence": cells[2], "annotation": cells[3],
        }
    missing = [r for r in "ABCD" if r not in rules]
    if missing:
        raise ValueError(f"§3.2 矩阵使用规则表应有 A/B/C/D 四区，缺 {missing}")
    return rules


# §6.1 支持强度判定矩阵表头锚点（"支持意愿 ↓ 支持能力 →"）。
_MATRIX_HEADER_RE = re.compile(
    r"^\|\s*支持意愿\s*↓\s*支持能力\s*→\s*\|", re.MULTILINE,
)
_BAND_COL = re.compile(r"(强|中|弱)\s*\(")
_BAND_ROW = re.compile(r"\*\*\s*(高|中|低)\s*\(")
# §6.1 单元格合法值（§6.2 强度行名 ∪ "低"——矩阵含独立"低"格，映射表并入"低/无"行）。
_STRENGTH_VALUES = ("非常高", "高", "中等", "低", "低/无")


def _parse_strength_matrix(text: str) -> dict:
    """§6.1 → {意愿档: {能力档: 强度}}；3×3 行列漂移/非法格值即 raise。"""
    sec = _section(text, "6.1")
    header, rows = _table_rows(sec, _MATRIX_HEADER_RE, "§6.1 支持强度判定矩阵")
    cols = []
    for cell in header[1:]:
        m = _BAND_COL.match(cell)
        if not m:
            raise ValueError(f"§6.1 矩阵列头无法解析: {cell!r}")
        cols.append(m.group(1))
    if cols != ["强", "中", "弱"]:
        raise ValueError(f"§6.1 矩阵列档应为 [强, 中, 弱]，实际 {cols}")
    matrix = {}
    for cells in rows:
        m = _BAND_ROW.match(cells[0])
        if not m:
            continue
        w_band = m.group(1)
        if w_band in matrix:
            raise ValueError(f"§6.1 意愿档 {w_band!r} 重复出现")
        if len(cells) < 4:
            raise ValueError(f"§6.1 意愿档 {w_band!r} 行格数不足（疑似表格错位）")
        values = cells[1:4]
        illegal = [v for v in values if v not in _STRENGTH_VALUES]
        if illegal:
            raise ValueError(f"§6.1 矩阵格值非法 {illegal}（允许值：{_STRENGTH_VALUES}）")
        matrix[w_band] = dict(zip(cols, values))
    missing = [b for b in ("高", "中", "低") if b not in matrix]
    if missing:
        raise ValueError(f"§6.1 矩阵应有 高/中/低 三意愿档行，缺 {missing}")
    return matrix


# §6.2 上调幅度映射表头锚点。
_UPLIFT_HEADER_RE = re.compile(
    r"^\|\s*支持强度\s*\|\s*支持方信用等级\s*\|\s*上调幅度\s*\|\s*典型场景\s*\|",
    re.MULTILINE,
)
_UPLIFT_RANGE = re.compile(r"\+?(\d+)~(\d+)子级")


def _parse_uplift_map(text: str) -> dict:
    """§6.2 → {强度: (子级下限, 子级上限)}；四档缺一/区间文本无法解析即 raise。"""
    sec = _section(text, "6.2")
    _, rows = _table_rows(sec, _UPLIFT_HEADER_RE, "§6.2 上调幅度映射表")
    out = {}
    for cells in rows:
        name = cells[0].strip("*").strip()
        if name not in ("非常高", "高", "中等", "低/无"):
            continue  # 表头/分隔/杂行
        if name in out:
            raise ValueError(f"§6.2 强度档 {name!r} 重复出现")
        cell = cells[2]
        if cell == "0":
            out[name] = (0, 0)
        else:
            m = _UPLIFT_RANGE.fullmatch(cell)
            if not m:
                raise ValueError(f"§6.2 上调幅度单元格无法解析: {cell!r}")
            out[name] = (int(m.group(1)), int(m.group(2)))
    missing = [n for n in ("非常高", "高", "中等", "低/无") if n not in out]
    if missing:
        raise ValueError(f"§6.2 上调幅度映射应有 非常高/高/中等/低/无 四档，缺 {missing}")
    return out


# §7.3 陷阱信号行动规则表表头锚点。
_TRAP_HEADER_RE = re.compile(
    r"^\|\s*触发情景\s*\|\s*分析响应\s*\|\s*对评级的影响\s*\|", re.MULTILINE,
)


def _parse_trap_actions(text: str) -> tuple:
    """§7.3 → 4 条规则（文档顺序）。kind 结构归类（谓词硬编码、文本原文留痕）：

    red=1个🔴极高；orange2=2个以上🟠；orange_asset=1个以上🟠+资产划转；
    fiscal=财政持续恶化超 2 年。四类缺一/多义即 raise。
    """
    sec = _section(text, "7.3")
    _, rows = _table_rows(sec, _TRAP_HEADER_RE, "§7.3 陷阱信号行动规则表")
    rules = []
    for cells in rows:
        if len(cells) < 3:
            raise ValueError(f"§7.3 规则行列数不足: {cells!r}")
        trigger, response, impact = cells[0], cells[1], cells[2]
        if "🔴" in trigger:
            kind = "red"
        elif "🟠" in trigger and "资产划转" in trigger:
            kind = "orange_asset"
        elif "🟠" in trigger:
            kind = "orange2"
        elif "财政持续恶化" in trigger:
            kind = "fiscal"
        else:
            raise ValueError(f"§7.3 触发情景无法归类: {trigger!r}")
        rules.append({
            "kind": kind, "trigger": trigger, "response": response, "impact": impact,
        })
    kinds = [r["kind"] for r in rules]
    for k in ("red", "orange2", "orange_asset", "fiscal"):
        if kinds.count(k) != 1:
            raise ValueError(f"§7.3 规则类别 {k!r} 应恰有 1 条，实际 {kinds.count(k)}")
    return tuple(rules)


# §8.2 政策信号映射表表头锚点。
_POLICY_HEADER_RE = re.compile(
    r"^\|\s*政策信号\s*\|\s*对支持能力的影响\s*\|\s*对支持意愿的影响\s*\|\s*综合影响\s*\|",
    re.MULTILINE,
)
_POLICY_MIN_ROWS = 9  # 行数下界校验（同 T1 bond_priors 先例；防静默丢行）


def _parse_policy_map(text: str) -> dict:
    """§8.2 → {政策信号: 综合影响方向}（"——"前原文；重行/行数低于下界即 raise）。"""
    sec = _section(text, "8.2")
    _, rows = _table_rows(sec, _POLICY_HEADER_RE, "§8.2 政策信号映射表")
    out = {}
    for cells in rows:
        if len(cells) < 4:
            raise ValueError(f"§8.2 政策信号行列数不足: {cells!r}")
        signal = cells[0]
        if signal in out:
            raise ValueError(f"§8.2 政策信号 {signal!r} 重复出现")
        out[signal] = cells[3].split("——")[0].strip()
    if len(out) < _POLICY_MIN_ROWS:
        raise ValueError(
            f"§8.2 政策信号映射表行数 {len(out)} 低于下界 {_POLICY_MIN_ROWS}"
            "（疑似表格漂移致静默丢行）"
        )
    return out


def load_support_tables(path=None) -> SupportTables:
    """运行时解析 §4.1/§4.3/§4.4/§3.2/§6.1/§6.2/§7.3/§8.2 八表；任一解析失败即 raise。"""
    text = _read(path)
    return SupportTables(
        thresholds=_parse_thresholds(text),
        group_thresholds=_parse_capacity_quads(text, "4.3", GROUP_INDICATORS),
        strategic_thresholds=_parse_capacity_quads(text, "4.4", STRATEGIC_INDICATORS),
        matrix_rules=_parse_matrix_rules(text),
        strength_matrix=_parse_strength_matrix(text),
        uplift_map=_parse_uplift_map(text),
        trap_actions=_parse_trap_actions(text),
        policy_map=_parse_policy_map(text),
    )


# ================= 分档与合成 =================


def _tier_hit(tier: ThresholdTier, v: float) -> bool:
    if tier.lo is not None and (v < tier.lo or (tier.lo_open and v == tier.lo)):
        return False
    if tier.hi is not None and (v > tier.hi or (tier.hi_open and v == tier.hi)):
        return False
    return True


def _score_capacity_indicator(name: str, value, thresholds: dict, sec: str) -> int:
    """§4.3/§4.4 四档量化表分档：数值档按文档阈值区间（3→0 降序首条命中）、
    评级档按档位带、枚举档按 强/中/弱/极弱 标签。未知指标、类型不符、
    非法标签均 raise（不静默落档）。
    """
    tiers = thresholds.get(name)
    if tiers is None:
        raise ValueError(
            f"{sec} 四档量化表未覆盖指标 {name!r}（允许值：{tuple(thresholds)}）"
        )
    kind = tiers[0].kind
    if kind == "numeric":
        if isinstance(value, str) or not isinstance(value, (int, float)):
            raise ValueError(f"指标 {name!r} 为数值档，值须为数值，实际 {value!r}")
        for t in tiers:
            if _tier_hit(t, float(value)):
                return t.score
        raise ValueError(  # 防御：档位并集应覆盖全域，命中失败即表格漂移
            f"指标 {name!r} 值 {value} 未落入 {sec} 任何档位（疑似表格区间断裂）"
        )
    if kind == "rating":
        if not isinstance(value, str) or value.strip() not in _RATING_INDEX:
            raise ValueError(
                f"指标 {name!r} 为评级档，值须为 18 档评级字符串，实际 {value!r}"
            )
        v = value.strip()
        for t in tiers:
            if v in t.ratings:
                return t.score
        raise ValueError(  # 防御：评级带并集应覆盖 18 档全域
            f"指标 {name!r} 评级 {value!r} 未落入 {sec} 任何档位带（疑似档位带断裂）"
        )
    # enum
    if not isinstance(value, str):
        raise ValueError(f"指标 {name!r} 为枚举档，值须为字符串标签，实际 {value!r}")
    v = value.strip()
    for t in tiers:
        if t.enum_label == v:
            return t.score
    raise ValueError(
        f"指标 {name!r} 未知档位标签 {value!r}"
        f"（允许值：{tuple(_ENUM_LABEL_BY_SCORE.values())}）"
    )


def score_indicator(name: str, value, tables: SupportTables = None,
                    support_type: str = "government") -> int:
    """阈值分档：指标值 → 0-3 分。

    support_type="government" → §4.1 阈值分档表（数值档按 3→0 降序首条命中，
    枚举档如人口趋势按 label 等值匹配）；"group" → §4.3 五指标四档量化表、
    "strategic" → §4.4 四指标四档量化表（v0.12.1 类型分派）。未知指标、
    未知支持类型、类型不符、未知枚举值均 raise（不静默落档）。
    """
    tables = tables if tables is not None else load_support_tables()
    if support_type == "group":
        return _score_capacity_indicator(name, value, tables.group_thresholds, "§4.3")
    if support_type == "strategic":
        return _score_capacity_indicator(name, value, tables.strategic_thresholds, "§4.4")
    if support_type != "government":
        raise ValueError(
            f"未知支持类型 {support_type!r}（允许值：{_CAPACITY_TYPES}）"
        )
    tiers = tables.thresholds.get(name)
    if tiers is None:
        raise ValueError(
            f"§4.1 阈值分档表未覆盖指标 {name!r}（允许值：{tuple(INDICATOR_TO_FACTOR)}）"
        )
    if not tiers[0].unit:  # 枚举档
        if not isinstance(value, str):
            raise ValueError(
                f"指标 {name!r} 为枚举档，值须为字符串标签，实际 {value!r}"
            )
        v = value.strip()
        for tier in tiers:
            if tier.label == v:
                return tier.score
        raise ValueError(
            f"指标 {name!r} 未知枚举值 {value!r}（允许值：{tuple(t.label for t in tiers)}）"
        )
    if isinstance(value, str) or not isinstance(value, (int, float)):
        raise ValueError(f"指标 {name!r} 为数值档，值须为数值，实际 {value!r}")
    for tier in tiers:
        if _tier_hit(tier, float(value)):
            return tier.score
    raise ValueError(  # 防御：档位并集应覆盖全域，命中失败即表格漂移
        f"指标 {name!r} 值 {value} 未落入 §4.1 任何档位（疑似表格区间断裂）"
    )


def _capacity_government(indicators: dict, tables: SupportTables) -> dict:
    """§4.1 政府口径：六指标 → F1-F4 维度均值 → capacity 均值（§6.1 公式口径：
    支持能力综合评分 = (F1 + F2 + F3 + F4) / 4）。

    返回 {F1: …, F2: …, F3: …, F4: …, capacity: …, per_indicator: [...]}。
    缺输入指标不计入维度均值（score=None + 「缺输入」注记，不静默填补）；
    整维度缺输入时该 F 为 None 且不计入 capacity 均值。未知指标键 raise。
    """
    unknown = [k for k in indicators if k not in INDICATOR_TO_FACTOR]
    if unknown:
        raise ValueError(
            f"未知指标 {unknown}（§4.1 阈值分档表允许值：{tuple(INDICATOR_TO_FACTOR)}）"
        )
    per_indicator = []
    factor_values = {f: [] for f in _FACTORS}
    for name, factor in INDICATOR_TO_FACTOR.items():
        if name in indicators:
            s = score_indicator(name, indicators[name], tables)
            per_indicator.append(
                {"indicator": name, "factor": factor, "score": s, "note": ""}
            )
            factor_values[factor].append(s)
        else:
            per_indicator.append({
                "indicator": name,
                "factor": factor,
                "score": None,
                "note": "缺输入，未计入维度均值（留 LLM 判断）",
            })
    result = {}
    available = []
    for f in _FACTORS:
        vals = factor_values[f]
        result[f] = sum(vals) / len(vals) if vals else None
        if result[f] is not None:
            available.append(result[f])
    result["capacity"] = sum(available) / len(available) if available else None
    result["per_indicator"] = per_indicator
    return result


def _capacity_quads(indicators: dict, support_type: str, tables: SupportTables) -> dict:
    """§4.3 集团 / §4.4 战投口径：指标等权均值 → capacity（v0.12.1 裁决：
    两表无 F 维度结构，逐指标 0-3 分直接等权）。

    返回 {support_type, capacity, per_indicator}。缺输入指标不计入均值
    （score=None + 「缺输入」注记，口径沿用 §4.1）；全缺输入 capacity=None；
    未知指标键 raise。
    """
    indicator_map = GROUP_INDICATORS if support_type == "group" else STRATEGIC_INDICATORS
    sec = "§4.3" if support_type == "group" else "§4.4"
    keys = tuple(k for k, _ in indicator_map.values())
    unknown = [k for k in indicators if k not in keys]
    if unknown:
        raise ValueError(f"未知指标 {unknown}（{sec} 四档量化表允许值：{keys}）")
    per_indicator = []
    scores = []
    for key, _ in indicator_map.values():
        if key in indicators:
            s = score_indicator(key, indicators[key], tables, support_type=support_type)
            per_indicator.append({"indicator": key, "score": s, "note": ""})
            scores.append(s)
        else:
            per_indicator.append({
                "indicator": key,
                "score": None,
                "note": "缺输入，未计入均值（留 LLM 判断）",
            })
    return {
        "support_type": support_type,
        "capacity": sum(scores) / len(scores) if scores else None,
        "per_indicator": per_indicator,
    }


def capacity_score(indicators: dict, support_type: str = "government",
                   tables: SupportTables = None) -> dict:
    """能力侧合成（v0.12.1 类型分派）。

    support_type="government" → §4.1 六指标 F1-F4 维度均值口径；
    "group" → §4.3 五指标等权均值；"strategic" → §4.4 四指标等权均值。
    未知 support_type、未知指标键均 raise；缺输入不静默填补（None + 注记）。
    """
    tables = tables if tables is not None else load_support_tables()
    if support_type not in _CAPACITY_TYPES:
        raise ValueError(
            f"未知支持类型 {support_type!r}（允许值：{_CAPACITY_TYPES}）"
        )
    if support_type == "government":
        return _capacity_government(indicators, tables)
    return _capacity_quads(indicators, support_type, tables)


# ================= 意愿评分与上调全链（T5） =================

# D1 意愿等权：强=3 / 中=1.5 / 弱=0。
_WILLINGNESS_LEVELS = {"强": 3.0, "中": 1.5, "弱": 0.0}

# §5.1 信号分级（L1-L5）；§2.1 外部支持三类型。
_SIGNAL_LEVELS = ("L1", "L2", "L3", "L4", "L5")
_SUPPORT_TYPES = ("政府支持", "集团支持", "战略投资者支持")

# §6.4 操作规则：单次上调 ≤3 子级（对标中诚信）；最低触发条件 = 强度"高/非常高"。
_MAX_UPLIFT_NOTCHES = 3
_TRIGGER_STRENGTHS = ("高", "非常高")

# §7.3 财政持续恶化：capacity 降一档。
_BAND_DOWN = {"强": "中", "中": "弱", "弱": "弱"}

# D3 子级换算：复用 CANONICAL 18 档序（高→低），1 子级 = 1 档步进（=0.5 分）。
_LADDER = [label for _, _, label in CANONICAL_RATING_INTERVALS]
_RATING_INDEX = {label: i for i, label in enumerate(_LADDER)}


# §2.1 三类型（SupportInput.support_type 文档原文）→ capacity_score 分派键
# （v0.12.1 fix：support_type 透传全链，集团/战投 capacity 由 §4.3/§4.4 驱动）。
_SUPPORT_TYPE_DISPATCH = {
    "政府支持": "government",
    "集团支持": "group",
    "战略投资者支持": "strategic",
}


@dataclass(frozen=True)
class SupportInput:
    """compute_support 输入（字段对齐 SDD brief；后七项带默认值故排序在后）。"""

    support_type: str                # §2.1 三类型之一
    indicators: dict                 # 能力指标子集 → capacity_score（口径随 support_type：
                                     # 政府=§4.1 六指标 / 集团=§4.3 五指标 / 战投=§4.4 四指标）
    willingness_signals: dict        # {维度: 强/中/弱}（D1 等权）
    signal_level: str                # §5.1 信号等级 L1-L5
    standalone_rating: str           # 剔除外部支持后的独立信用等级（18 档）
    red_traps: int = 0               # 🔴 极高危险信号计数（§7.2）
    orange_traps: int = 0            # 🟠 高危险信号计数
    asset_transfer: bool = False     # 核心资产划转（§7.2 资产变动）
    fiscal_decline_2y: bool = False  # 财政持续恶化超 2 年（§7.3）
    policy_signals: tuple = ()       # §8.2 政策信号名（方向 advisory，无数值影响）
    supporter_rating: str = None     # 支持方自身信用等级（§6.3 上限；None=缺失）
    supporter_is_central_gov: bool = False  # §6.3 例外：中央政府 → 上限 AAA


@dataclass(frozen=True)
class SupportResult:
    """compute_support 输出（字段对齐 SDD brief）。"""

    capacity: float
    willingness: float               # D1 原始分（陷阱降档不改写，审计留痕）
    capacity_band: str               # 强/中/弱（陷阱调整后生效档）
    willingness_band: str            # 高/中/低（陷阱调整后生效档）
    strength: str                    # §6.1 矩阵强度
    uplift_notches: int              # 最终上调子级数（门控/clamp/财政削减后）
    final_rating: str                # standalone + uplift，受 §6.3 上限约束
    capped: bool
    gate_reasons: tuple
    trap_actions: tuple
    confidence: str                  # §3.2 区域置信度原文
    policy_advisory: tuple
    disclaimer: dict                 # §6.5 隐含担保风险声明要素


def willingness_score(signals: dict) -> float:
    """D1 意愿等权：逐信号 强=3/中=1.5/弱=0，均值 ∈ [0,3]；空/非法档即 raise。"""
    if not signals:
        raise ValueError("意愿信号为空，无法合成意愿评分（不静默落档）")
    illegal = {k: v for k, v in signals.items() if v not in _WILLINGNESS_LEVELS}
    if illegal:
        raise ValueError(
            f"意愿信号档位非法 {illegal}（允许值：{tuple(_WILLINGNESS_LEVELS)}）"
        )
    return sum(_WILLINGNESS_LEVELS[v] for v in signals.values()) / len(signals)


def _capacity_band(score: float) -> str:
    """D5 左闭右开：强 [2.5,3.0]、中 [1.5,2.5)、弱 [0,1.5)。"""
    if score >= 2.5:
        return "强"
    if score >= 1.5:
        return "中"
    return "弱"


def _willingness_band(score: float) -> str:
    """D5 左闭右开：高 [2.5,3.0]、中 [1.5,2.5)、低 [0,1.5)。"""
    if score >= 2.5:
        return "高"
    if score >= 1.5:
        return "中"
    return "低"


def compute_support(inp: SupportInput, tables: SupportTables = None) -> SupportResult:
    """外部支持上调全链：陷阱先行 → §6.1 矩阵 → 门控 → §6.2 区间 → D4 落点 →
    ≤3 子级 clamp（§6.4）→ §6.3 支持方上限 → §3.2 区域标签+置信度 → §8.2 政策
    方向 advisory。
    """
    tables = tables if tables is not None else load_support_tables()
    if inp.support_type not in _SUPPORT_TYPES:
        raise ValueError(
            f"未知支持类型 {inp.support_type!r}（§2.1 允许值：{_SUPPORT_TYPES}）"
        )
    if inp.signal_level not in _SIGNAL_LEVELS:
        raise ValueError(
            f"未知信号等级 {inp.signal_level!r}（§5.1 允许值：{_SIGNAL_LEVELS}）"
        )
    if inp.standalone_rating not in _RATING_INDEX:
        raise ValueError(
            f"standalone_rating {inp.standalone_rating!r} 不在 18 档评级档序内"
        )
    if inp.supporter_rating is not None and inp.supporter_rating not in _RATING_INDEX:
        raise ValueError(
            f"supporter_rating {inp.supporter_rating!r} 不在 18 档评级档序内"
        )
    if inp.red_traps < 0 or inp.orange_traps < 0:
        raise ValueError("陷阱信号计数不得为负")

    # v0.12.1 fix：support_type 透传 capacity_score——集团/战投指标集由
    # §4.3/§4.4 四档量化表分档（不再落回 §4.1 政府口径；T8 观察还债）。
    capacity_type = _SUPPORT_TYPE_DISPATCH[inp.support_type]
    cap = capacity_score(inp.indicators, support_type=capacity_type, tables=tables)
    capacity = cap["capacity"]
    if capacity is None:
        raise ValueError(
            f"支持能力指标全缺输入，capacity 无法合成"
            f"（{inp.support_type} → {capacity_type} 口径）——不做上调判定"
        )
    willingness = willingness_score(inp.willingness_signals)
    capacity_band = _capacity_band(capacity)
    willingness_band = _willingness_band(willingness)

    # --- 陷阱先行（§7.3；谓词结构硬编码，规则文本来自运行时解析） ---
    rules = {r["kind"]: r for r in tables.trap_actions}
    trap_actions = []
    red_hit = inp.red_traps >= 1
    if red_hit:
        r = rules["red"]
        trap_actions.append({
            "kind": "red", "trigger": r["trigger"], "action": r["response"],
            "note": f"{r['impact']}——本引擎上调降至 0；是否转为负数留 LLM 判断",
        })
    if inp.orange_traps >= 2:
        r = rules["orange2"]
        willingness_band = "低"  # 意愿评分降至"低"档重算强度
        trap_actions.append({
            "kind": "orange2", "trigger": r["trigger"], "action": r["response"],
            "note": f"{r['impact']}——本引擎以意愿档降「低」重算实现下调",
        })
    if inp.orange_traps >= 1 and inp.asset_transfer:
        r = rules["orange_asset"]
        trap_actions.append({
            "kind": "orange_asset", "trigger": r["trigger"], "action": r["response"],
            "note": r["impact"], "requires_no_support_scenario": True,
        })
    if inp.fiscal_decline_2y:
        r = rules["fiscal"]
        capacity_band = _BAND_DOWN[capacity_band]
        trap_actions.append({
            "kind": "fiscal", "trigger": r["trigger"], "action": r["response"],
            "note": f"{r['impact']}——本引擎以 capacity 降一档 + 上调再减 1 子级实现",
        })

    # --- §6.1 支持强度判定矩阵（D5 分档，生效档位查表） ---
    strength = tables.strength_matrix[willingness_band][capacity_band]

    # --- 门控 + §6.2 区间 + D4 落点 ---
    gate_reasons = []
    if red_hit:
        uplift = 0  # 陷阱优先：🔴 直接归零（转负留 LLM，见 trap_actions 注记）
    elif inp.signal_level in ("L1", "L2"):
        # §5.1 核心规则：L1-L2 仅用于"需关注"方向，上调至少需 L3+
        uplift = 0
        gate_reasons.append(
            f"信号等级 {inp.signal_level} 仅用于「需关注」方向，"
            "基于支持意愿的评级上调至少需 L3+ 信号（§5.1）"
        )
    elif strength not in _TRIGGER_STRENGTHS:
        # §6.4 最低触发条件：强度须为"高"或"非常高"
        uplift = 0
        gate_reasons.append(
            f"支持强度「{strength}」未达最低触发条件（高/非常高，§6.4），上调幅度 0"
        )
    else:
        lo, hi = tables.uplift_map.get(strength, tables.uplift_map["低/无"])
        # D4 落点（意愿档界与 D5 对齐）：高→上限；中→中位（round）；低→下限
        if willingness_band == "高":
            uplift = hi
        elif willingness_band == "中":
            uplift = round((lo + hi) / 2)
        else:
            uplift = lo
    if inp.fiscal_decline_2y and uplift > 0:
        uplift = max(0, uplift - 1)  # §7.3：上调再减 1 子级
    uplift = min(uplift, _MAX_UPLIFT_NOTCHES)  # §6.4 单次上限 ≤3 子级

    # --- 最终评级（D3：18 档序步进） + §6.3 支持方上限 ---
    sa_idx = _RATING_INDEX[inp.standalone_rating]
    final_idx = max(0, sa_idx - uplift)
    capped = False
    cap_note = ""
    if uplift > 0:
        if inp.supporter_is_central_gov:
            cap_idx = 0  # §6.3 特殊例外：上限 = 中国主权评级 AAA
        elif inp.supporter_rating is not None:
            cap_idx = _RATING_INDEX[inp.supporter_rating]
        else:
            cap_idx = None
            cap_note = "支持方评级缺失，§6.3 上限原则未适用（留 LLM 判断）"
        if cap_idx is not None and final_idx < cap_idx:
            final_idx = cap_idx
            capped = True
            if final_idx > sa_idx:
                # 终审 I-1：支持方评级低于独立评级时，上限钳制不得把 final 压到
                # standalone 之下——final 档序位以 standalone 为下限并留注记。
                final_idx = sa_idx
                cap_note = (
                    f"支持方评级 {inp.supporter_rating} 低于独立评级 "
                    f"{inp.standalone_rating}：§6.3 上限钳制被独立评级下限截断，"
                    "final 不低于 standalone"
                )
        # 终审 I-1：uplift_notches 重算为 standalone→final 的真实子级数
        uplift = sa_idx - final_idx
    final_rating = _LADDER[final_idx]

    # --- §3.2 区域标签 + 置信度（二维矩阵按生效档位归区：强/高 为"强"侧） ---
    w_strong = willingness_band == "高"
    c_strong = capacity_band == "强"
    region = (
        "A" if (w_strong and c_strong)
        else "B" if w_strong
        else "C" if c_strong
        else "D"
    )
    region_rule = tables.matrix_rules[region]

    # --- §8.2 政策信号方向 advisory（无数值影响；未知信号即 raise） ---
    advisory = []
    for s in inp.policy_signals:
        if s not in tables.policy_map:
            raise ValueError(
                f"§8.2 政策信号映射表未覆盖 {s!r}"
                f"（允许值：{tuple(tables.policy_map)}）"
            )
        advisory.append({"signal": s, "direction": tables.policy_map[s]})

    # §6.5 隐含担保风险声明要素（模板文本见文档 §6.5 代码块，不上浮复制）。
    disclaimer = {
        "required": uplift > 0,
        "template_ref": "external-support-framework.md §6.5",
        "region": region,
        "region_annotation": region_rule["annotation"],
        "uplift_notches": uplift,
        "capacity": capacity,
        "willingness": willingness,
        "standalone_rating": inp.standalone_rating,
        "cap_note": cap_note,
        # 终审 M-3：§3.2 粗矩阵归区方向与 §6.1/§6.2 精矩阵上调幅度可能不一致
        "matrix_precedence": (
            "区域归区（§3.2 粗矩阵）与上调幅度（§6.1/§6.2 精矩阵）方向不同时，"
            "以精矩阵为准"
        ),
    }
    return SupportResult(
        capacity=capacity,
        willingness=willingness,
        capacity_band=capacity_band,
        willingness_band=willingness_band,
        strength=strength,
        uplift_notches=uplift,
        final_rating=final_rating,
        capped=capped,
        gate_reasons=tuple(gate_reasons),
        trap_actions=tuple(trap_actions),
        confidence=region_rule["confidence"],
        policy_advisory=tuple(advisory),
        disclaimer=disclaimer,
    )

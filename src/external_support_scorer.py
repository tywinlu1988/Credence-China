"""WP-M0-02 → external-support-framework.md 的外部支持引擎（T4 能力侧）。

单一事实源：§4.1「关键指标阈值参考」表（6 指标 × 4 档）运行时解析，解析失败
即 raise（不裸复制数值副本）。§3.2 矩阵使用规则表 / §6.1 支持强度判定矩阵 /
§6.2 上调幅度映射 / §7.3 陷阱信号行动规则表的运行时解析属 T5——SupportTables
已预留对应字段（当前为 None 占位），load_support_tables 骨架已就位。

边界语义（全引擎统一，文档档位文本直译）：">X" / "<X" 为开区间端点
（3000亿 → 中等档），"X-Y" 为闭区间；GDP 增速极弱档 "<2%或负增长" 解析数值
部分（"或负增长"为文本修饰，负增长值天然落入 "<2%" 开区间）。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir

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
class SupportTables:
    """external-support-framework.md 可解析表的运行时解析结果。

    thresholds:     §4.1 阈值分档表 → {指标: (ThresholdTier ×4, 按 3→0 降序)}。
    matrix_rules:   §3.2 矩阵使用规则表（T5 填充，当前 None 占位）。
    strength_matrix: §6.1 支持强度判定 3×3 矩阵（T5 填充，当前 None 占位）。
    uplift_map:     §6.2 上调幅度映射（T5 填充，当前 None 占位）。
    trap_actions:   §7.3 陷阱信号行动规则表（T5 填充，当前 None 占位）。
    """

    thresholds: dict
    matrix_rules: dict = None
    strength_matrix: dict = None
    uplift_map: dict = None
    trap_actions: tuple = None


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


def load_support_tables(path=None) -> SupportTables:
    """运行时解析 §4.1 阈值分档表；解析失败即 raise。

    §3.2/§6.1/§6.2/§7.3 四表解析属 T5，对应字段当前为 None 占位。
    """
    text = _read(path)
    return SupportTables(thresholds=_parse_thresholds(text))


# ================= 分档与合成 =================


def _tier_hit(tier: ThresholdTier, v: float) -> bool:
    if tier.lo is not None and (v < tier.lo or (tier.lo_open and v == tier.lo)):
        return False
    if tier.hi is not None and (v > tier.hi or (tier.hi_open and v == tier.hi)):
        return False
    return True


def score_indicator(name: str, value, tables: SupportTables = None) -> int:
    """§4.1 阈值分档：指标值 → 0-3 分。

    数值档按 3→0 降序首条命中（反向指标如债务率/依赖度由文档档位方向天然
    处理）；枚举档（人口趋势）按 label 等值匹配。未知指标、类型不符、未知
    枚举值均 raise（不静默落档）。
    """
    tables = tables if tables is not None else load_support_tables()
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


def capacity_score(indicators: dict, tables: SupportTables = None) -> dict:
    """能力侧合成：六指标 → F1-F4 维度均值 → capacity 均值（§6.1 公式口径：
    支持能力综合评分 = (F1 + F2 + F3 + F4) / 4）。

    返回 {F1: …, F2: …, F3: …, F4: …, capacity: …, per_indicator: [...]}。
    缺输入指标不计入维度均值（score=None + 「缺输入」注记，不静默填补）；
    整维度缺输入时该 F 为 None 且不计入 capacity 均值。未知指标键 raise。
    """
    tables = tables if tables is not None else load_support_tables()
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

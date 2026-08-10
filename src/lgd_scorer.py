"""WP-M0-02 → lgd-recovery-framework.md 的 LGD 引擎解析层与基础类型（T1）。

单一事实源：§2.1 LGD 五级定义表、§5.1 中国信用债品种优先级表、§11.4 统计不
确定区间表均运行时解析，解析失败即 raise（不裸复制数值副本）。硬编码项
（SENIORITY_BASE / DELTA_RANGES / pd_lgd_bounds）以 §3.2 / §2.2 文本为锚点，
由 tests/test_lgd_scorer.py 的 parity 测试回读文档校验防漂移。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.path_sheet import engine_dir
from src.rating_map import CANONICAL_RATING_INTERVALS  # 18 档单源，不复制

_DOC_NAME = "lgd-recovery-framework.md"

# §3.2 公式块 "Base_LGD 基准值（仅考虑优先级）" 四档（parity 锚定：
# tests/test_lgd_scorer.py 回读 "无担保优先级债券：Base_LGD = 60%" 等文本锚点）。
SENIORITY_BASE = {"有担保优先": 45.0, "无担保优先": 60.0, "次级": 75.0, "劣后": 90.0}

# §3.2 公式块 "调整项（Δ）" 五因子范围（单位 pp；parity 锚定 "-25pp 至 +10pp" 等）。
DELTA_RANGES = {
    "collateral": (-25.0, 10.0),
    "guarantee": (-15.0, 5.0),
    "industry": (-5.0, 10.0),
    "recovery_path": (-5.0, 10.0),
    "legal": (-5.0, 10.0),
}

# §2.2 PD 评级 → LGD 可达区间约束（硬编码 + parity；档位前缀按 18 档单源归桶）。
#   AAA-AA → 上限 LGD4；A-BBB → 无约束；BB-B → 下限 LGD2；CCC-D → 下限 LGD3。
_PD_LGD_BUCKETS = (
    (("AAA", "AA"), (None, "LGD4")),
    (("A", "BBB"), (None, None)),
    (("BB", "B"), ("LGD2", None)),
    (("CCC", "D"), ("LGD3", None)),
)

_KNOWN_RATINGS = {r for _, _, r in CANONICAL_RATING_INTERVALS}


@dataclass(frozen=True)
class LgdTables:
    """lgd-recovery-framework.md 三张可解析表的运行时解析结果。

    levels:      §2.1 五级表 → ((name, loss_low, loss_high, rec_low, rec_high), ...)
                 5 行，单位 %；开区间端点（<20% / >80%）以 0/100 闭合。
    bond_priors: §5.1 品种先验 → {品种: (LGD 下限, LGD 上限)}（单档区间两端相同）。
    ci_ranges:   §11.4 CI 表 → {LGD 等级: (中国调整后回收率低, 高)}（单位 %）。
    """

    levels: tuple
    bond_priors: dict
    ci_ranges: dict


def clamp(v: float, lo: float, hi: float) -> float:
    """把 v 截断到 [lo, hi]。"""
    return max(lo, min(hi, v))


def pd_lgd_bounds(rating: str) -> tuple:
    """§2.2：PD 评级 → (LGD 下限, LGD 上限)（None = 该侧无约束）。"""
    r = rating.strip().upper()
    if r not in _KNOWN_RATINGS:
        raise ValueError(f"未知评级 {rating!r}（不在 18 档单源内）")
    for prefixes, bounds in _PD_LGD_BUCKETS:
        if any(r.startswith(p) for p in prefixes):
            return bounds
    raise ValueError(f"评级 {rating!r} 未落入 §2.2 任何约束桶")  # 防御：单源扩档时暴露


def _read(path) -> str:
    p = Path(path) if path else engine_dir() / _DOC_NAME
    return p.read_text(encoding="utf-8")


def _section(text: str, anchor: str) -> str:
    sec = re.search(anchor + r"\s.*?(?=\n### |\n## |\Z)", text, re.DOTALL)
    if not sec:
        raise ValueError(f"{anchor} 段落缺失")
    return sec.group(0)


def _parse_levels(text: str) -> tuple:
    """§2.1 → ((name, loss_low, loss_high, rec_low, rec_high), ...)（5 行，%）。"""
    sec = _section(text, r"### 2\.1")
    rows = []
    for m in re.finditer(
        r"^\|\s*(LGD\d)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", sec, re.MULTILINE
    ):
        name, loss, rec = m.group(1), m.group(2), m.group(3)
        rows.append((name, *_parse_pct_range(loss), *_parse_pct_range(rec)))
    names = [r[0] for r in rows]
    if names != [f"LGD{i}" for i in range(1, 6)]:
        raise ValueError(f"§2.1 应有 LGD1-LGD5 顺序 5 行，实际 {names}")
    return tuple(rows)


def _parse_pct_range(cell: str) -> tuple:
    """"20% - 40%" → (20.0, 40.0)；"<20%" → (0.0, 20.0)；">80%" → (80.0, 100.0)。"""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)%\s*-\s*(\d+(?:\.\d+)?)%", cell)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.fullmatch(r"<(\d+(?:\.\d+)?)%", cell)
    if m:
        return 0.0, float(m.group(1))
    m = re.fullmatch(r">(\d+(?:\.\d+)?)%", cell)
    if m:
        return float(m.group(1)), 100.0
    raise ValueError(f"§2.1 百分比区间单元格无法解析: {cell!r}")


def _parse_bond_priors(text: str) -> dict:
    """§5.1 → {品种: (LGD 下限, LGD 上限)}（单档区间如 "LGD5" 两端相同）。"""
    sec = _section(text, r"### 5\.1")
    priors = {}
    for m in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|[^|]*\|\s*(LGD\d)(?:\s*-\s*(LGD\d))?\s*\|",
        sec, re.MULTILINE,
    ):
        lo, hi = m.group(2), m.group(3) or m.group(2)
        priors[m.group(1).strip()] = (lo, hi)
    if not priors:
        raise ValueError("§5.1 品种先验表解析为空")
    return priors


def _parse_ci_ranges(text: str) -> dict:
    """§11.4 → {LGD 等级: (中国调整后回收率低, 高)}（第 4 列 "65% - 98%（…）"）。"""
    sec = _section(text, r"### 11\.4")
    ranges = {}
    for m in re.finditer(
        r"^\|\s*(LGD\d)\s*\|\s*\d+%\s*\|\s*\d+%\s*-\s*\d+%\s*\|"
        r"\s*(\d+(?:\.\d+)?)%\s*-\s*(\d+(?:\.\d+)?)%",
        sec, re.MULTILINE,
    ):
        ranges[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    if sorted(ranges) != [f"LGD{i}" for i in range(1, 6)]:
        raise ValueError(f"§11.4 应有 LGD1-LGD5 共 5 行，实际 {sorted(ranges)}")
    return ranges


def load_lgd_tables(path=None) -> LgdTables:
    """运行时解析 §2.1/§5.1/§11.4 三张表；任何一张解析失败即 raise。"""
    text = _read(path)
    return LgdTables(
        levels=_parse_levels(text),
        bond_priors=_parse_bond_priors(text),
        ci_ranges=_parse_ci_ranges(text),
    )

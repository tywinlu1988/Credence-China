"""WP-X-05 → outlook-monitoring-framework.md 的可执行实现（展望计分 + 观察名单 + 迁移矩阵）。

单一事实源：§2.2 触发因子矩阵、§5.1 迁移矩阵、§5.3 行业修正从引擎文档运行时解析；
§2.3 计分逻辑（层级权重数值 v0.8.4 经用户批准补写进文档）、置信度分级、§3.2 名单管理
规则编码为代码逻辑（sri_calculator/contagion_engine 先例）。

消歧说明（文档重叠/未明处的编码解释）：
- 置信度"中"与"低"描述重叠 → 取连贯语义：高=≥4同向且≥3层、中高=≥3同向且≥2层、
  中=≥2同向且≥2层、低=其余有信号、极低=0 信号（以主导方向计）。
- 双方同触发观察名单 → 负面优先（§3.2 未规定，保守默认）。
- 发展中展望："强度接近" 解释为 |净方向| < 阈值（2.0）。
"""

import re
from pathlib import Path

from src.path_sheet import engine_dir

LAYER_WEIGHTS = {"L1": 1.5, "L2": 1.2, "L3": 1.0, "L4": 0.8, "外部支持": 1.2}  # §2.3
OUTLOOK_THRESHOLD = 2.0          # §2.3：净方向 ±2.0 且同向信号 ≥2
MIN_DIRECTION_SIGNALS = 2
DEVELOPING_MIN_SIGNALS = 3       # 发展中：正/负各 ≥3 且 |net| < 阈值

_LAYER_ROW_RE = re.compile(r"^\|\s*\*\*(L[1-4]|外部支持)[^|]*\*\*\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)


def load_factor_matrix(matrix_md_path=None) -> dict:
    """解析 §2.2 → {signal_text: (layer, direction)}，direction ∈ {"positive","negative"}。"""
    path = Path(matrix_md_path) if matrix_md_path else engine_dir() / "outlook-monitoring-framework.md"
    text = path.read_text(encoding="utf-8")
    out = {}
    for sec_name, direction in (("正面展望触发信号", "positive"), ("负面展望触发信号", "negative")):
        sec = re.search(r"#### " + sec_name + r"\n(.*?)(?=\n#### |\n### |\Z)", text, re.DOTALL)
        if not sec:
            raise ValueError(f"§2.2 缺少 {sec_name} 小节")
        for row in _LAYER_ROW_RE.finditer(sec.group(1)):
            out[row.group(2).strip()] = (row.group(1), direction)
    return out


def outlook_assessment(signals: list) -> dict:
    """§2.3：净方向计分 → 展望判定 + 置信度（判定序：发展中→正面→负面→稳定）。"""
    pos = neg = 0.0
    pos_items, neg_items = [], []
    for s in signals:
        layer, direction = s["layer"], s["direction"]
        if layer not in LAYER_WEIGHTS:
            raise ValueError(f"未知层级: {layer!r}（可选 {sorted(LAYER_WEIGHTS)}）")
        if direction == "positive":
            pos += LAYER_WEIGHTS[layer]
            pos_items.append(s)
        elif direction == "negative":
            neg += LAYER_WEIGHTS[layer]
            neg_items.append(s)
        else:
            raise ValueError(f"未知方向: {direction!r}")
    net = pos - neg
    if (len(pos_items) >= DEVELOPING_MIN_SIGNALS
            and len(neg_items) >= DEVELOPING_MIN_SIGNALS
            and abs(net) < OUTLOOK_THRESHOLD):
        outlook = "发展中"
    elif net >= OUTLOOK_THRESHOLD and len(pos_items) >= MIN_DIRECTION_SIGNALS:
        outlook = "正面"
    elif net <= -OUTLOOK_THRESHOLD and len(neg_items) >= MIN_DIRECTION_SIGNALS:
        outlook = "负面"
    else:
        outlook = "稳定"
    dominant = pos_items if pos >= neg else neg_items
    return {
        "outlook": outlook,
        "net_score": round(net, 4),
        "positive_score": round(pos, 4),
        "negative_score": round(neg, 4),
        "confidence": _confidence_tier(dominant),
        "counts": {"positive": len(pos_items), "negative": len(neg_items)},
    }


def _confidence_tier(dominant_items) -> str:
    n = len(dominant_items)
    layers = {s["layer"] for s in dominant_items}
    if n >= 4 and len(layers) >= 3:
        return "高"
    if n >= 3 and len(layers) >= 2:
        return "中高"
    if n >= 2 and len(layers) >= 2:
        return "中"
    if n >= 1:
        return "低"
    return "极低"


def watchlist_check(triggers: list) -> dict:
    """§3.1/§3.2：触发 → 名单侧 + 时限；双方同触发 → 负面优先。"""
    sides = set()
    for t in triggers:
        side = t["side"]
        if side not in ("negative", "positive"):
            raise ValueError(f"未知名单侧: {side!r}")
        sides.add(side)
    if not triggers:
        return {"entered": False, "side": None, "window_days": 0,
                "review": {}, "extension_max_days": 0, "note": ""}
    if "negative" in sides:
        note = "触发负面观察条件"
        if "positive" in sides:
            note += "；同时存在正面触发，按负面优先"
        return {"entered": True, "side": "负面观察", "window_days": 90,
                "review": {"initial_review_days": 30, "full_review_days": 60},
                "extension_max_days": 60, "note": note}
    return {"entered": True, "side": "正面观察", "window_days": 90,
            "review": {"full_review_days": 60},
            "extension_max_days": 60, "note": "触发正面观察条件"}


def load_migration_table(migration_md_path=None):
    """解析 §5.1 → {rating: {上调,维持,下调,违约}}；§5.3 → {paradigm: (target, low_pp, high_pp)}。"""
    path = Path(migration_md_path) if migration_md_path else engine_dir() / "outlook-monitoring-framework.md"
    text = path.read_text(encoding="utf-8")
    sec51 = re.search(r"### 5\.1 .*?(?=\n### |\Z)", text, re.DOTALL)
    if not sec51:
        raise ValueError("§5.1 段落缺失")
    table = {}
    for row in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|",
        sec51.group(0), re.MULTILINE,
    ):
        rating = row.group(1).strip()
        if rating == "当前评级":
            continue
        table[rating] = {
            "上调": row.group(2).strip(), "维持": row.group(3).strip(),
            "下调": row.group(4).strip(), "违约": row.group(5).strip(),
        }
    if len(table) != 12:
        raise ValueError(f"§5.1 应有 12 个评级行，实际 {len(table)}")
    sec53 = re.search(r"### 5\.3 .*?(?=\n### |\n## |\Z)", text, re.DOTALL)
    if not sec53:
        raise ValueError("§5.3 段落缺失")
    adj = {}
    for row in re.finditer(
        r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(上调|下调)概率\+(\d+)(?:-(\d+))?",
        sec53.group(0), re.MULTILINE,
    ):
        adj[row.group(1).strip()] = (row.group(2), int(row.group(3)), int(row.group(4) or row.group(3)))
    return table, adj


def _shift_range(range_text: str, low: int, high: int) -> str:
    """区间双界按 pp 平移（cap 100）；'<N%' → '<N+high%'；其他非数值文本原样保留。"""
    t = range_text.strip()
    m = re.match(r"^(\d+)(?:-(\d+))?%$", t)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        lo2, hi2 = min(lo + low, 100), min(hi + high, 100)
        return f"{lo2}-{hi2}%" if lo2 != hi2 else f"{lo2}%"
    m = re.match(r"^<(\d+(?:\.\d+)?)%$", t)
    if m:
        v = float(m.group(1)) + high
        return f"<{v:g}%"
    return range_text


def migration_range(rating: str, paradigm: str = None, path=None) -> dict:
    """§5.1 基础区间 + §5.3 行业修正；合并行（"A / A-"）接受任一子级。"""
    table, adj = load_migration_table(path)
    row = table.get(rating)
    if row is None:
        for key, cells in table.items():
            if "/" in key and rating in [p.strip() for p in key.split("/")]:
                row = cells
                break
    if row is None:
        raise ValueError(f"未知评级: {rating!r}")
    out = dict(row)
    note = ""
    if paradigm:
        if paradigm not in adj:
            raise ValueError(f"未知行业类型: {paradigm!r}（可选 {sorted(adj)}）")
        target, low, high = adj[paradigm]
        out[target] = _shift_range(row[target], low, high)
        note = f"{paradigm}：{target}概率+{low}%" if low == high else f"{paradigm}：{target}概率+{low}-{high}%"
    out["paradigm_note"] = note
    return out

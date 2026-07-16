"""工作路径单 schema 与校验器（v0.7.5 — 管线化基础）。

credit-analysis-router skill 在四问协议收敛后产出《工作路径单》（work-path
sheet），把"角色 × 对象 × 深度 × 数据模式"路由到 dev/engine/work-path-registry.md
中一条已注册的工作路径。本模块是路径单的机器可读单一事实源：

- 定义路径单四元组（role/object/depth/mode）与 registry 路径状态的枚举；
- 提供 PathSheet 数据类与 validate_path_sheet 校验器（结构合法性 + 引用完整性）;
- 提供 registry ```yaml 块解析器 load_registry_paths，供校验器与测试共用。

单一事实源原则：本模块只校验路径单的结构与引用，不复制任何引擎阈值/权重/层级
语义。L0/L1/L2 分层定义见 dev/engine/output-layered-framework.md，SRI 温度计
档位见 dev/engine/systemic-warning-framework.md。
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# registry ```yaml 围栏块（与 tests/test_work_path_registry.py 同一解析口径）。
YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


class Role(str, Enum):
    """Q1 角色：客户身份（M0-M5）或跨角色的元/专项路径。"""

    M0 = "M0"
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    META = "meta"


class Object(str, Enum):
    """Q2 对象：分析对象。"""

    SINGLE_ISSUER = "single-issuer"
    PORTFOLIO = "portfolio"
    INDUSTRY = "industry"
    MARKET = "market"
    META = "meta"


class Depth(str, Enum):
    """Q3 深度：三层输出（output-layered-framework §二）+ 专项。"""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    SPECIAL = "专项"


class Mode(str, Enum):
    """Q4 数据模式：A=仅公开数据；B=用户显式提供外部数据源。"""

    A = "A"
    B = "B"


class PathStatus(str, Enum):
    """registry 路径状态（work-path-registry §一）。"""

    ACTIVE = "active"
    PARTIAL = "partial"
    PLANNED = "planned"


# 路径单必填标量字段（须存在且非空）。
REQUIRED_SCALAR_FIELDS = ["role", "object", "depth", "mode", "path_id"]
# 路径单必填列表字段（须存在且为 list；planned 路径允许空数组）。
REQUIRED_LIST_FIELDS = ["engine_reading_order", "quality_gates"]
# 全部必填字段（notes 为可选）。
REQUIRED_SHEET_FIELDS = REQUIRED_SCALAR_FIELDS + REQUIRED_LIST_FIELDS

_ENUM_FIELDS = {
    "role": Role,
    "object": Object,
    "depth": Depth,
    "mode": Mode,
}

# `templates` 允许的非文件标记值（与 registry §schema 一致）。
TEMPLATE_MARKERS = ("planned", "L0-spec")


@dataclass
class PathSheet:
    """router 产出的结构化工作路径单（字段对齐 registry schema）。"""

    role: str
    object: str
    depth: str
    mode: str
    path_id: str
    engine_reading_order: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PathSheet":
        """从 router 产出的 yaml dict 构造（仅取已知字段，缺省留空）。"""
        return cls(
            role=str(data.get("role", "")),
            object=str(data.get("object", "")),
            depth=str(data.get("depth", "")),
            mode=str(data.get("mode", "")),
            path_id=str(data.get("path_id", "")),
            engine_reading_order=list(data.get("engine_reading_order") or []),
            quality_gates=list(data.get("quality_gates") or []),
            notes=str(data.get("notes", "")),
        )

    def to_dict(self) -> dict:
        """导出为与 router yaml 同构的 dict。"""
        return {
            "role": self.role,
            "object": self.object,
            "depth": self.depth,
            "mode": self.mode,
            "path_id": self.path_id,
            "engine_reading_order": list(self.engine_reading_order),
            "quality_gates": list(self.quality_gates),
            "notes": self.notes,
        }


def is_template_marker(entry: object) -> bool:
    """templates 条目为非文件标记（``planned`` / ``L0-spec: ...``）时返回 True。"""
    s = str(entry).strip()
    return any(s == m or s.startswith(m + ":") or s.startswith(m + " ") for m in TEMPLATE_MARKERS)


def load_registry_paths(registry_md_path) -> dict[str, dict]:
    """解析 registry markdown 中的 ```yaml 块，返回 ``{path_id: 解析后的 dict}``。

    解析口径与 tests/test_work_path_registry.py 一致：正则取围栏块 + yaml.safe_load，
    仅保留声明了 ``id`` 的 dict。此为 registry 解析的单一来源，供校验器与测试共用。
    """
    text = Path(registry_md_path).read_text(encoding="utf-8")
    paths: dict[str, dict] = {}
    for block in YAML_BLOCK_RE.findall(text):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "id" in data:
            paths[str(data["id"]).strip()] = data
    return paths


def is_planned(path_id: str, registry_paths: dict) -> bool:
    """path_id 存在且其 status 为 ``planned``（待开发）时返回 True。"""
    path = registry_paths.get(str(path_id).strip())
    if path is None:
        return False
    return str(path.get("status", "")).strip() == PathStatus.PLANNED.value


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _enum_values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


def validate_path_sheet(sheet: dict, registry_paths: dict, root=None) -> list[str]:
    """校验一张工作路径单，返回人类可读的错误字符串列表（空列表 = 合法）。

    校验项：

    - 必填字段存在且非空（标量非空；列表须为 list 且非空，仅 planned 路径允许空数组）；
    - ``role``/``object``/``depth``/``mode`` 各自落在合法枚举内（报出字段名与非法值）；
    - ``path_id`` 存在于 registry（报出未知 id）；
    - 解析到的路径若为 ``active``，其 ``templates`` 中每个非标记条目必须是磁盘真实文件。

    planned 路径不会仅因"待开发"而校验失败——调用方应另行用 is_planned /
    sheet_notice 向用户给出"待开发"提示，而非模板调用指令。``root`` 用于解析模板
    相对路径，默认仓库根。
    """
    if isinstance(sheet, PathSheet):
        sheet = sheet.to_dict()
    if not isinstance(sheet, dict):
        return [f"path sheet must be a mapping, got {type(sheet).__name__}"]

    base = Path(root) if root is not None else ROOT
    errors: list[str] = []

    # 必填标量字段：存在且非空。
    for name in REQUIRED_SCALAR_FIELDS:
        if name not in sheet:
            errors.append(f"missing required field: {name!r}")
        elif _is_empty(sheet[name]):
            errors.append(f"required field {name!r} is empty")

    # 解析 path_id 一次，供"空数组门槛"与"模板落盘"两处复用。
    pid_value = sheet.get("path_id")
    pid = "" if _is_empty(pid_value) else str(pid_value).strip()
    path = registry_paths.get(pid) if pid else None
    path_status = "" if path is None else str(path.get("status", "")).strip()
    planned = path_status == PathStatus.PLANNED.value

    # 必填列表字段：存在且为 list。非 planned 路径（active/partial）必须是可执行的
    # 非空序列——"空数组"仅 planned 路径允许（待开发，尚无引擎/质量门可登记）。
    for name in REQUIRED_LIST_FIELDS:
        if name not in sheet:
            errors.append(f"missing required field: {name!r}")
        elif not isinstance(sheet[name], (list, tuple)):
            errors.append(
                f"required field {name!r} must be a list, got {type(sheet[name]).__name__}"
            )
        elif len(sheet[name]) == 0 and path is not None and not planned:
            errors.append(
                f"required field {name!r} must not be empty for non-planned path {pid!r}"
            )

    # 枚举合法性（仅在该字段存在且非空时校验，避免重复报错）。
    for name, enum_cls in _ENUM_FIELDS.items():
        if name not in sheet or _is_empty(sheet[name]):
            continue
        raw = sheet[name].value if isinstance(sheet[name], Enum) else sheet[name]
        value = str(raw).strip()
        if value not in _enum_values(enum_cls):
            allowed = "|".join(_enum_values(enum_cls))
            errors.append(f"field {name!r} has illegal value {value!r} (allowed: {allowed})")

    # path_id 引用完整性 + active 路径模板落盘。
    if pid:
        if path is None:
            errors.append(f"unknown path_id {pid!r}: not found in work-path registry")
        elif path_status == PathStatus.ACTIVE.value:
            for tmpl in path.get("templates") or []:
                if is_template_marker(tmpl):
                    continue
                if not (base / str(tmpl)).exists():
                    errors.append(f"active path {pid!r} template missing on disk: {tmpl}")

    return errors


def sheet_notice(sheet: dict, registry_paths: dict) -> str | None:
    """返回路径单的"待开发"提示（非致命）；无提示时返回 None。

    指向 planned 路径的路径单不应触发模板调用指令——router 应据本提示如实告知
    用户"该路径待开发"，并改荐一条 active 路径。active/partial 路径与未知 id 返回 None。
    """
    if isinstance(sheet, PathSheet):
        sheet = sheet.to_dict()
    if not isinstance(sheet, dict):
        return None
    pid_value = sheet.get("path_id")
    if _is_empty(pid_value):
        return None
    pid = str(pid_value).strip()
    if is_planned(pid, registry_paths):
        name = str(registry_paths[pid].get("name", "")).strip()
        label = f"{pid}（{name}）" if name else pid
        return (
            f"路径 {label} 待开发（planned）：引擎/模板尚未落地。"
            "请如实告知用户，并改用一条 active 路径，不得伪造模板调用指令。"
        )
    return None

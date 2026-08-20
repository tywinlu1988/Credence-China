"""四段链可执行编排器（v0.7.8 — 可执行编排器 + 接编码引擎）。

本模块是四段链（intake → analysis → report → qa）的**薄编排器**。它把 router 产出的
《工作路径单》解析为一份有序的阶段计划（stage plan），并仅在路径已接线（wired）时调用
对应的**已编码引擎**；其余路径/阶段仍由 LLM 按引擎文档编排，优雅跳过。

设计约束（单一事实源）：

- **阶段定义不硬编码**：四个阶段的名称、承载 skill、产物标签均从
  `engine/pipeline-contract.md` 的阶段总览表解析而来（见 load_contract）。链式边
  （chaining_edges）同样从该契约的 yaml 块读取，供端点引用完整性校验复用。
- **不新编码任何引擎**：引擎文档是规范源，`src/sri_calculator.py`、`src/concentration_scorer.py`、
  `src/contagion_engine.py`、`src/outlook_engine.py`、`src/composite_scorer.py`、
  `src/lgd_scorer.py`、`src/external_support_scorer.py` 与 `src/stress_scorer.py` 是其
  **可执行实现**。编排器只在路径已接线时调用它们（EXECUTABLE_ENGINES），不复制任何
  阈值/权重/档位语义。
- **复用 path_sheet.py**：路径单校验、registry 解析、planned 判定与"待开发"提示一律
  复用 `src/path_sheet.py`，不重复实现。
"""

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from src.composite_scorer import rate
from src.concentration_scorer import (
    ConcentrationMetrics,
    concentration_risk_score,
    rating_adjustment,
)
from src.contagion_engine import (
    apply_escalation,
    contagion_coefficients,
    high_intensity_links,
    load_matrix,
    portfolio_exposure,
)
from src.external_support_scorer import SupportInput, compute_support
from src.lgd_scorer import (
    CollateralInput,
    EvasionFlags,
    GuaranteeInput,
    compute_lgd,
)
from src.outlook_engine import (
    migration_range,
    outlook_assessment,
    watchlist_check,
)
from src.path_sheet import (
    YAML_BLOCK_RE,
    is_planned,
    sheet_notice,
    validate_path_sheet,
)
from src.sri_calculator import (
    IndustryInput,
    Outlook,
    PREDEFINED_SCENARIOS,
    ShockScenario,
    TrackBLevel,
    portfolio_sri,
    sri,
    stress_test,
    thermometer_level,
)
from src.stress_scorer import (
    IssuerFinancials,
    TAIL_RISK_WARNING,
    bond_mv_stress,
    concentration_stress,
    load_stress_tables,
    resolve_severe_params,
    reverse_stress,
    run_scenario,
    safety_verdict,
    tail_risk_flag,
)

ROOT = Path(__file__).resolve().parent.parent

# 契约阶段总览表的数据行：`| S1 intake | 工作路径单（Path Sheet） | `credit-analysis-router` | … |`。
# 名称（intake/analysis/…）与承载 skill 均从该行解析，绝不在此硬编码阶段名。
_STAGE_ROW_RE = re.compile(
    r"^\|\s*(S\d+)\s+([A-Za-z][A-Za-z0-9_-]*)\s*\|([^|]*)\|\s*`?([A-Za-z0-9_-]+)`?\s*\|",
    re.MULTILINE,
)

# 四段链的**位序语义**：intake/analysis/report/qa 的先后次序是链式契约的固定拓扑
# （S1→S2→S3→S4）。阶段"做什么"按位序赋予，而阶段"叫什么/由谁承载"来自契约文档——
# 故契约中重命名某阶段会反映到计划里，而链式语义保持不变。
_INTAKE, _ANALYSIS, _REPORT, _QA = 0, 1, 2, 3


@dataclass
class Stage:
    """四段链中的一个阶段。

    ``name``/``skill`` 来自契约阶段总览表；``inputs``/``outputs`` 按位序语义从路径单与
    registry 解析而来；``executable`` 仅当该位序为 analysis 且路径已接线编码引擎时为 True。
    """

    name: str
    skill: str
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    executable: bool = False
    path_id: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "skill": self.skill,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "executable": self.executable,
            "path_id": self.path_id,
        }


def load_contract(contract_md_path) -> dict:
    """解析 pipeline-contract.md，返回阶段定义、产物 schema 与链式边。

    返回 ``{"stages": [...], "artifacts": [...], "chaining_edges": [...]}``：

    - ``stages``：阶段总览表解析出的有序列表 ``[{"id","name","skill","artifact"}]``，
      顺序即 S1→S2→S3→S4。阶段名/承载 skill 的**唯一来源**，编排器据此命名阶段。
    - ``artifacts``：§二 四份产物 schema（含 ``path_id`` 的 ```yaml 块），按文档顺序。
    - ``chaining_edges``：§三 链式边 yaml 块解析出的边列表（``id/from/to/trigger/…``）。
    """
    text = Path(contract_md_path).read_text(encoding="utf-8")

    stages = [
        {
            "id": m.group(1),
            "name": m.group(2),
            "artifact": m.group(3).strip(),
            "skill": m.group(4),
        }
        for m in _STAGE_ROW_RE.finditer(text)
    ]

    artifacts: list[dict] = []
    chaining_edges: list[dict] = []

    for block in YAML_BLOCK_RE.findall(text):
        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            continue
        if "chaining_edges" in data:
            chaining_edges = list(data.get("chaining_edges") or [])
        elif "path_id" in data:
            artifacts.append(data)

    return {"stages": stages, "artifacts": artifacts, "chaining_edges": chaining_edges}


def load_stage_plan(path_sheet: dict, registry_paths: dict, contract: dict) -> list[Stage]:
    """把一张工作路径单解析为有序的四阶段计划。

    先用 `validate_path_sheet` 校验路径单（非法枚举/未知 path_id/悬挂模板 → ValueError）；
    再按契约的阶段总览表（位序）发射四个阶段：intake（路径单自身）、analysis（引擎文档，
    仅当路径已接线编码引擎时 ``executable=True``）、report（registry 模板）、qa（质量门）。
    阶段名与承载 skill 取自 ``contract["stages"]``，不在此硬编码。
    """
    errors = validate_path_sheet(path_sheet, registry_paths)
    if errors:
        raise ValueError("invalid path sheet: " + "; ".join(errors))

    pid = str(path_sheet.get("path_id", "")).strip()
    registry_path = registry_paths.get(pid, {})

    contract_stages = contract.get("stages", [])
    if len(contract_stages) != 4:
        raise ValueError(
            f"contract must define exactly 4 stages, got {len(contract_stages)}"
        )
    # 位序语义依附于固定的 S1→S2→S3→S4 拓扑。若契约对阶段重排/错标，此处
    # 响亮失败，而非静默地把 executable 语义错配到错误的阶段（review #1）。
    stage_ids = [cs.get("id") for cs in contract_stages]
    if stage_ids != ["S1", "S2", "S3", "S4"]:
        raise ValueError(
            f"contract stages must be S1->S2->S3->S4 in order, got {stage_ids}"
        )

    # 位序语义 → 该阶段的 inputs/outputs/executable。名称与 skill 来自契约。
    positional = {
        _INTAKE: {
            "inputs": [path_sheet],
            "outputs": ["path_sheet"],
            "executable": False,
        },
        _ANALYSIS: {
            "inputs": list(path_sheet.get("engine_reading_order") or []),
            "outputs": ["analysis_artifact"],
            "executable": pid in EXECUTABLE_ENGINES,
        },
        _REPORT: {
            "inputs": list(registry_path.get("templates") or []),
            "outputs": list(registry_path.get("outputs") or []),
            "executable": False,
        },
        _QA: {
            "inputs": list(path_sheet.get("quality_gates") or []),
            "outputs": ["qa_verdict"],
            "executable": False,
        },
    }

    plan: list[Stage] = []
    for idx, cs in enumerate(contract_stages):
        sem = positional[idx]
        plan.append(
            Stage(
                name=cs["name"],
                skill=cs["skill"],
                inputs=sem["inputs"],
                outputs=sem["outputs"],
                executable=sem["executable"],
                path_id=pid,
            )
        )
    return plan


def run_executable_stages(plan: list[Stage], inputs: dict) -> dict:
    """执行计划中标记为可执行的阶段，返回 run manifest。

    对 ``executable=True`` 的阶段，按 ``stage.path_id`` 在 EXECUTABLE_ENGINES 中查到已接线
    的编码引擎并以 ``inputs`` 运行，标记 ``mode="code"``；其余阶段保持 LLM 编排，优雅跳过
    并标记 ``mode="llm-orchestrated"``。manifest 形如
    ``{"path_id": ..., "stages": [{"name","mode","outputs"}]}``。
    """
    path_id = plan[0].path_id if plan else ""
    stages_manifest = []
    for stage in plan:
        if stage.executable and stage.path_id in EXECUTABLE_ENGINES:
            engine = EXECUTABLE_ENGINES[stage.path_id]
            stages_manifest.append(
                {"name": stage.name, "mode": "code", "outputs": engine(inputs)}
            )
        else:
            stages_manifest.append(
                {"name": stage.name, "mode": "llm-orchestrated", "outputs": None}
            )
    return {"path_id": path_id, "stages": stages_manifest}


def planned_path_notice(path_sheet: dict, registry_paths: dict) -> str | None:
    """指向 planned（待开发）路径的路径单返回"待开发"提示，否则 None。

    复用 `path_sheet.sheet_notice`/`is_planned`；编排器对 planned 路径**不做任何执行**，
    仅如实把提示抛给上层（router 应改荐一条 active 路径）。
    """
    pid = str(path_sheet.get("path_id", "")).strip() if isinstance(path_sheet, dict) else ""
    if pid and is_planned(pid, registry_paths):
        return sheet_notice(path_sheet, registry_paths)
    return None


def _run_sri(inputs: dict) -> dict:
    """WP-M4-03 → systemic-warning-framework 的可执行实现（SRI + 温度计）。"""
    value = sri(inputs["industries"], inputs["weights"])
    return {"sri": value, "thermometer": thermometer_level(value)}


def _run_concentration(inputs: dict) -> dict:
    """WP-M4-01 → concentration-framework 的可执行实现（五维评分 + 评级调整）。"""
    metrics = inputs["metrics"]
    adj = rating_adjustment(metrics)
    return {
        "score": concentration_risk_score(metrics),
        "adjustment": adj["adjustment"],
        "levels": adj["levels"],
        "bb_cap_triggered": adj["bb_cap_triggered"],
    }


def _run_contagion(inputs: dict) -> dict:
    """WP-M4-02 → contagion-matrix 的可执行实现（组合暴露 + 高传染链路 + 压力跳升）。"""
    m = load_matrix()
    factors = list(inputs.get("escalation_factors") or [])
    if factors:
        m = apply_escalation(m, factors)
    holdings = inputs["holdings"]
    return {
        "exposure": portfolio_exposure(m, holdings),
        "links": [
            {
                "source": c.source,
                "target": c.target,
                "intensity": c.intensity,
                "types": list(c.types),
                "bidirectional": c.bidirectional,
            }
            for c in high_intensity_links(m, list(holdings))
        ],
        "factors_applied": factors,
    }


def _run_composite(inputs: dict) -> dict:
    """WP-M0-01 → industry-framework 的聚合可执行实现（范式判定+复合分+评级+否决封顶）。"""
    return rate(
        inputs["d_scores"],
        inputs["layer_scores"],
        veto_conditions=inputs.get("veto_conditions") or [],
        industry=inputs.get("industry"),
        paradigm_override=inputs.get("paradigm_override"),
    )


def _run_outlook(inputs: dict) -> dict:
    """WP-X-05 → outlook-monitoring-framework 的可执行实现（展望+名单+迁移矩阵）。"""
    assessment = outlook_assessment(inputs["signals"])
    watchlist = watchlist_check(inputs.get("watchlist_triggers") or [])
    migration = migration_range(inputs["rating"], inputs.get("paradigm"))
    return {
        "outlook": assessment["outlook"],
        "confidence": assessment["confidence"],
        "net_score": assessment["net_score"],
        "watchlist": watchlist,
        "migration": migration,
    }


def _run_m002(inputs: dict) -> dict:
    """WP-M0-02 → lgd-recovery + external-support 双引擎（LGD 合成 + 外部支持上调）。

    inputs 形如 ``{"lgd": {seniority, collateral, guarantee, industry_key, …},
    "support": {support_type, indicators, …}}``——子字典键即两引擎入参的字段名，
    在此展开为关键字构造（SupportInput 字段序与文档序不同，严禁位置调用）。
    """
    lg = inputs["lgd"]
    lgd = compute_lgd(
        seniority=lg["seniority"],
        collateral=CollateralInput(**lg["collateral"]),
        guarantee=GuaranteeInput(**lg["guarantee"]),
        industry_key=lg["industry_key"],
        recovery_scenario=lg["recovery_scenario"],
        province=lg["province"],
        evasion=EvasionFlags(**lg.get("evasion", {})),
        pd_rating=lg["pd_rating"],
        bond_type=lg["bond_type"],
    )
    support = compute_support(SupportInput(**inputs["support"]))
    return {"lgd": asdict(lgd), "support": asdict(support)}


def _run_m004(inputs: dict) -> dict:
    """WP-M4-04 → 组合压力测试的可执行实现（stress_scorer 三件套 + SRI 复用）。

    inputs 契约（子字典键即引擎入参字段名，在此展开构造，严禁位置调用）：

    - ``"financials"``（必）：``{标的: {"industry": 行业名, <IssuerFinancials 字段>…}}``
      ——``industry`` 键弹出，其余展开为 ``IssuerFinancials(**fields)``。每标的产出
      ``{"bear", "severe", "safety", "tail_risk", "tail_risk_warning", "reverse"}``：
      bear = E.3 线性链（E.1 Bear 参数）；severe = D1 裁决参数 + E.7 二阶修正；
      safety = E.5 四档判定（对 bear）；tail_risk = E.5 补充判定（对 severe，
      True 时 tail_risk_warning 附 TAIL_RISK_WARNING 文本，否则 None）；reverse =
      E.6 三临界值（其他参数取 Bear 档）。
    - ``"concentration_metrics"`` + ``"scenario"``（可选，须成对）：§9.1 五维压力
      传导（concentration_stress）；scenario 为 §9.2 登记情景名。只给一侧即 raise
      （半套输入是配置错误，不静默降级）；两侧均缺 → concentration=None。
    - ``"bonds"``（可选）：``{标的: {"years", "ytm", "custom_shocks"?}}`` → 每标的
      E.10 bond_mv_stress；缺省 → bond_mv=None。
    - ``"sri"``（可选）：``{"industries": [<IndustryInput 字段 dict>], "holdings":
      {行业: 权重}, "scenario"?: PREDEFINED_SCENARIOS 键（默认 "moderate"）或
      ShockScenario 字段 dict}`` → 复用 sri_calculator.portfolio_sri + stress_test
      （不重写；传染系数取自 contagion_engine.load_matrix，与 WP-M4-02 同源）。
      缺省 → sri_stress=None。两处 sri_calculator 存量注记：① PREDEFINED_SCENARIOS
      的 severe/extreme 升级因子原为非法枚举名（信用事件/流动性危机/政策突变），
      Fix R1 已按语义 1:1 映射为合法因子（详见 src/sri_calculator.py 注释与
      systemic-warning-framework §13.1 注记）；② stress_test 的矩阵升级路径
      按全市场组合重算系数——情景含 contagion_escalation 时 holdings 须覆盖
      传染矩阵全部行业，子集组合请以 industry_shocks/outlook_shifts 表达冲击
      （本适配器对此前置 raise，见下；sri 侧深修留下一版）。

    返回 ``{"concentration", "scenarios", "bond_mv", "sri_stress"}``——四键恒在，
    缺输入的维度为 None。
    """
    tables = load_stress_tables()
    bear_params = tables.scenario_params["Bear"]

    scenarios = {}
    for name, fields in inputs["financials"].items():
        fields = dict(fields)
        industry = fields.pop("industry")
        fin = IssuerFinancials(**fields)
        severe_params = resolve_severe_params(industry, tables)
        bear = run_scenario(fin, bear_params, industry, tables, scenario="Bear")
        severe = run_scenario(fin, severe_params, industry, tables, severe=True)
        tail = tail_risk_flag(severe, tables)
        scenarios[name] = {
            "bear": asdict(bear),
            "severe": asdict(severe),
            "safety": safety_verdict(bear, tables),
            "tail_risk": tail,
            "tail_risk_warning": TAIL_RISK_WARNING if tail else None,
            "reverse": reverse_stress(fin, bear_params),
        }

    metrics_d = inputs.get("concentration_metrics")
    scenario_name = inputs.get("scenario")
    if (metrics_d is None) != (not scenario_name):
        raise ValueError(
            "concentration_metrics 与 scenario 须成对提供（§9.1 五维压力传导）"
        )
    concentration = None
    if metrics_d is not None:
        concentration = concentration_stress(
            ConcentrationMetrics(**metrics_d), scenario_name, tables
        )

    bond_mv = None
    if inputs.get("bonds"):
        bond_mv = {
            name: bond_mv_stress(
                b["years"], b["ytm"], tables,
                custom_shocks=b.get("custom_shocks"),
            )
            for name, b in inputs["bonds"].items()
        }

    sri_stress = None
    sri_in = inputs.get("sri")
    if sri_in:
        industries = []
        for d in sri_in["industries"]:
            d = dict(d)
            d["track_b_level"] = TrackBLevel(d["track_b_level"])
            d["outlook"] = Outlook(d["outlook"])
            industries.append(IndustryInput(**d))
        matrix = load_matrix()
        coeffs = contagion_coefficients(matrix)
        holdings = sri_in["holdings"]
        base = portfolio_sri(holdings, industries, {k: coeffs[k] for k in holdings})
        scenario_spec = sri_in.get("scenario", "moderate")
        if isinstance(scenario_spec, dict):
            scenario_spec = ShockScenario(**scenario_spec)
        else:
            scenario_spec = PREDEFINED_SCENARIOS[scenario_spec]
        if scenario_spec.contagion_escalation and set(holdings) != set(coeffs):
            raise ValueError(
                "sri 情景含 contagion_escalation 时 holdings 须覆盖传染矩阵全部"
                f"行业（{len(coeffs)} 个）——sri_calculator.stress_test 的矩阵升级"
                "路径按全市场组合重算系数（存量约束），子集组合会以"
                "「行业集不一致」失败；子集组合请改用 industry_shocks/"
                "outlook_shifts 表达冲击"
            )
        sri_stress = stress_test(base, scenario_spec, matrix=matrix)

    return {
        "concentration": concentration,
        "scenarios": scenarios,
        "bond_mv": bond_mv,
        "sri_stress": sri_stress,
    }


# 已接线（wired）编码引擎登记表：path_id → 运行该路径编码引擎的可调用对象。
# 保持显式且极小——本系列接入 WP-M0-01(旗舰聚合)、WP-M0-02(LGD+外部支持双引擎)、
# WP-M4-01(集中度)、WP-M4-02(传染矩阵)、WP-M4-03(SRI)、WP-M4-04(组合压力测试)、
# WP-X-05(展望监控)。
EXECUTABLE_ENGINES = {
    "WP-M0-01": _run_composite,
    "WP-M0-02": _run_m002,
    "WP-M4-03": _run_sri,
    "WP-M4-01": _run_concentration,
    "WP-M4-02": _run_contagion,
    "WP-M4-04": _run_m004,
    "WP-X-05": _run_outlook,
}

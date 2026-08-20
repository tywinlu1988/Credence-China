"""WP-X-04 → governance-fraud-risk.md 的治理/欺诈风险信号规则库（T1）。

已裁决设计决策（SDD 2026-08-20-wp-x-04-esg-governance）：
- D2：检测条件为异构自然语言 → 规则硬编码 + 逐条 parity 锚点
  （concentration_scorer 先例）。每条规则 doc_anchor 标注文档行号出处，
  tests/test_governance_scorer.py 回读该行断言锚点文本存在。
- D3：Strength 统一枚举 LOW/LOW_MID/MID/MID_HIGH/HIGH/VETO 六档有序。
  文档信号强度映射：🔴 强 → HIGH，🟡 中 → MID（本规则集仅这两档）。
- D6：无阈值项不新造——RULES 只收机械阈值规则（33 条）；事件型/判断型
  信号（非标审计意见/核心资产划转/政府态度转变等）经 T2 events 输入，
  不在本规则库内。

T2（本文件下半部）：叠加合成 stack_severity（§6.2 矩阵 :318-323 + 通用
红旗计数叠加 :325-338，双口径并行、D5 取最严）+ 11 条一票否决 VETO_RULES
（§6.3 :344-349、§2.4 :128、§10.3 :714-717）+ compute_governance 合成入口。

边界语义（文档文本直译）：">" / "<" 为严格开区间（恰等不命中），
"≥" 为闭区间。两档规则（质押 60%/80%、关联收入 20%/50%、担保 50%/100%）
各自独立成条，高档命中时低档同中（档位语义叠加，与文档两行并列一致）。
"""

from dataclasses import dataclass
from enum import IntEnum


class Strength(IntEnum):
    """信号强度统一枚举（D3）：六档有序，VETO 为一票否决级。"""

    LOW = 1
    LOW_MID = 2
    MID = 3
    MID_HIGH = 4
    HIGH = 5
    VETO = 6


@dataclass(frozen=True)
class RedFlag:
    """evaluate_signals 输出条目。

    命中条目：note 为 "<rule.id> 命中（<doc_anchor>）"；
    数据缺失条目：strength=LOW（占位，非信号语义），note 以
    DATA_NOTE_PREFIX 开头——调用方按前缀过滤分流。
    """

    name: str
    strength: Strength
    evidence: str
    source: str
    note: str


@dataclass(frozen=True)
class SignalRule:
    """单条信号规则：check 接收 measured: dict 返回 bool（命中）。

    required 为 check 消费的 measured 键全集——evaluate_signals 据此
    判定缺输入跳过（留 data_note，不静默按 0 处理）。
    """

    id: str
    doc_anchor: str          # "governance-fraud-risk.md:<行号>"（parity 锚点）
    strength: Strength
    check: object            # callable[[dict], bool]
    name: str = ""
    source: str = ""         # 文档「数据来源」列原文
    required: tuple = ()


DATA_NOTE_PREFIX = "data_note："

# :48 货币资金与利息收入不匹配——活期利率参数化默认值 0.3%
# （文档未给数值，属参数假设；可经 measured["demand_deposit_rate"] 覆盖）。
DEFAULT_DEMAND_DEPOSIT_RATE = 0.003

# :73 Beneish M-Score（简化版）操纵嫌疑阈值；:74 Altman Z 高风险区；
# :76 Core Earnings Ratio 可疑线。
BENEISH_M_MANIPULATION_THRESHOLD = -2.22
ALTMAN_Z_HIGH_RISK_THRESHOLD = 1.81
CORE_EARNINGS_SUSPICION_THRESHOLD = 0.5


# --------------------------------------------------------------------------
# 复杂规则的 check 函数（简单阈值比较直接 lambda 内联于 RULES）
# --------------------------------------------------------------------------

def _check_fin06(m: dict) -> bool:
    # :41 资产减值"洗大澡"：减值 > 前 3 年利润总和 × 30%
    return m["impairment"] > 0.30 * m["prior_3y_profit_sum"]


def _check_fin07(m: dict) -> bool:
    # :42 研发资本化率突然从 <30% 跳升至 >70%（两端均严格）
    return m["rd_capitalization_prev"] < 0.30 and m["rd_capitalization_curr"] > 0.70


def _check_fin08(m: dict) -> bool:
    # :48 货币资金余额 × 活期利率 > 利息收入（差异 >30% → 预期 > 实际 × 1.3）
    rate = m.get("demand_deposit_rate", DEFAULT_DEMAND_DEPOSIT_RATE)
    return m["cash"] * rate > 1.3 * m["interest_income"]


def _check_gov06(m: dict) -> bool:
    # :100 连续 3 任总经理任期均 <2 年（不足 3 任不可判定 → 不命中）
    tenures = m["gm_recent_tenure_years"]
    return len(tenures) >= 3 and all(t < 2 for t in tenures[:3])


def _check_gov07(m: dict) -> bool:
    # :108 独立董事 < 董事会总人数 1/3（整数运算规避浮点：×3 比较）
    return m["independent_directors"] * 3 < m["board_size"]


def _check_gov08(m: dict) -> bool:
    # :112 连续 3 年再融资累计金额 > 当前市值 50%
    return m["refinancing_3y_total"] > 0.50 * m["market_cap"]


def _check_gov10(m: dict) -> bool:
    # :124 重大诉讼/仲裁标的金额 > 净资产 10%
    return m["litigation_amount"] > 0.10 * m["net_assets"]


def _check_rel03(m: dict) -> bool:
    # :142 关联交易毛利率 ± 非关联交易毛利率 > 10pp（双向取绝对值）
    return abs(m["related_gross_margin"] - m["non_related_gross_margin"]) > 0.10


def _check_rel06(m: dict) -> bool:
    # :150 关联方其他应收款/总资产 > 3%（或绝对金额 >5 亿）——双轨任一
    return (
        m["related_other_receivables"] > 0.03 * m["total_assets"]
        or m["related_other_receivables"] > 5e8
    )


# --------------------------------------------------------------------------
# 规则库（33 条；id 前缀：FIN=§1 财务 / GOV=§2 治理 / REL=§3 关联 / DEBT=§4 逃废债）
# --------------------------------------------------------------------------

RULES: tuple = (
    # ---- §1 财务欺诈红旗（12 条） ----
    SignalRule(  # :29 🔴 强
        "FIN-01", "governance-fraud-risk.md:29", Strength.HIGH,
        lambda m: m["ar_growth"] > 1.3 * m["revenue_growth"],
        "应收账款增速持续 > 收入增速 × 1.3", "季报/年报应收账款附注 + 收入",
        ("ar_growth", "revenue_growth"),
    ),
    SignalRule(  # :30 🔴 强；cfo_to_net_profit 为连续 8 季口径（调用方预聚合）
        "FIN-02", "governance-fraud-risk.md:30", Strength.HIGH,
        lambda m: m["cfo_to_net_profit"] < 0.7,
        "经营现金流与净利润持续背离", "现金流量表 + 利润表",
        ("cfo_to_net_profit",),
    ),
    SignalRule(  # :32 🟡 中
        "FIN-03", "governance-fraud-risk.md:32", Strength.MID,
        lambda m: m["q4_revenue_share"] > 0.40,
        "第四季度收入占比异常", "季报分季度数据",
        ("q4_revenue_share",),
    ),
    SignalRule(  # :33 🔴 强
        "FIN-04", "governance-fraud-risk.md:33", Strength.HIGH,
        lambda m: m["quarter_end_related_revenue_share"] > 0.50,
        "关联交易突击创收", "年报关联交易附注",
        ("quarter_end_related_revenue_share",),
    ),
    SignalRule(  # :39 🔴 强
        "FIN-05", "governance-fraud-risk.md:39", Strength.HIGH,
        lambda m: m["non_recurring_to_net_profit"] > 0.50,
        "非经常性损益占比过高", "利润表 + 非经常性损益明细",
        ("non_recurring_to_net_profit",),
    ),
    SignalRule(  # :41 🟡 中
        "FIN-06", "governance-fraud-risk.md:41", Strength.MID,
        _check_fin06,
        "资产减值“洗大澡”", "年报资产减值附注 + 历史利润表",
        ("impairment", "prior_3y_profit_sum"),
    ),
    SignalRule(  # :42 🟡 中
        "FIN-07", "governance-fraud-risk.md:42", Strength.MID,
        _check_fin07,
        "研发资本化率异常变动", "年报开发支出附注",
        ("rd_capitalization_prev", "rd_capitalization_curr"),
    ),
    SignalRule(  # :48 🔴 强
        "FIN-08", "governance-fraud-risk.md:48", Strength.HIGH,
        _check_fin08,
        "货币资金与利息收入不匹配", "年报货币资金附注 + 财务费用明细",
        ("cash", "interest_income"),
    ),
    SignalRule(  # :50 🔴 强
        "FIN-09", "governance-fraud-risk.md:50", Strength.HIGH,
        lambda m: m["other_receivables_to_assets"] > 0.05,
        "其他应收款激增", "年报其他应收款附注",
        ("other_receivables_to_assets",),
    ),
    SignalRule(  # :51 🟡 中
        "FIN-10", "governance-fraud-risk.md:51", Strength.MID,
        lambda m: m["restricted_assets_share"] > 0.30,
        "受限资产占比过高", "年报所有权受限资产说明",
        ("restricted_assets_share",),
    ),
    SignalRule(  # :53 🟡 中
        "FIN-11", "governance-fraud-risk.md:53", Strength.MID,
        lambda m: m["goodwill_to_net_assets"] > 0.30,
        "商誉占比过高", "年报商誉附注",
        ("goodwill_to_net_assets",),
    ),
    SignalRule(  # :64 🔴 强
        "FIN-12", "governance-fraud-risk.md:64", Strength.HIGH,
        lambda m: m["audit_fee_growth"] > 0.50,
        "审计费用异常变动", "董事会关于审计费用的公告",
        ("audit_fee_growth",),
    ),
    # ---- §2 管理层/治理红旗（10 条；质押两档独立成条） ----
    SignalRule(  # :86 🔴 强（60% 档）
        "GOV-01", "governance-fraud-risk.md:86", Strength.HIGH,
        lambda m: m["pledge_ratio"] > 0.60,
        "股权质押率 > 60%", "年报股东情况 / 质押公告",
        ("pledge_ratio",),
    ),
    SignalRule(  # :87 🔴 强（80% 档，濒临强制平仓）
        "GOV-02", "governance-fraud-risk.md:87", Strength.HIGH,
        lambda m: m["pledge_ratio"] > 0.80,
        "质押率 > 80%", "年报股东情况 / 质押公告",
        ("pledge_ratio",),
    ),
    SignalRule(  # :90 🟡 中
        "GOV-03", "governance-fraud-risk.md:90", Strength.MID,
        lambda m: bool(m["controller_changed_within_3y"]),
        "实控人变更", "年度报告 / 权益变动公告",
        ("controller_changed_within_3y",),
    ),
    SignalRule(  # :97 🔴 强
        "GOV-04", "governance-fraud-risk.md:97", Strength.HIGH,
        lambda m: m["cfo_changes_3y"] >= 2,
        "管理层频繁变动（CFO）", "年报 / 高管变动公告",
        ("cfo_changes_3y",),
    ),
    SignalRule(  # :99 🔴 强
        "GOV-05", "governance-fraud-risk.md:99", Strength.HIGH,
        lambda m: m["core_exec_departures"] >= 3,
        "核心管理层集体离职", "临时公告",
        ("core_exec_departures",),
    ),
    SignalRule(  # :100 🟡 中
        "GOV-06", "governance-fraud-risk.md:100", Strength.MID,
        _check_gov06,
        "总经理任期异常短", "年报高管变动历史",
        ("gm_recent_tenure_years",),
    ),
    SignalRule(  # :108 🔴 强
        "GOV-07", "governance-fraud-risk.md:108", Strength.HIGH,
        _check_gov07,
        "独立董事占比不足", "年报董事会构成",
        ("independent_directors", "board_size"),
    ),
    SignalRule(  # :112 🟡 中
        "GOV-08", "governance-fraud-risk.md:112", Strength.MID,
        _check_gov08,
        "再融资频率异常", "公告 / 年报",
        ("refinancing_3y_total", "market_cap"),
    ),
    SignalRule(  # :123 🔴 强
        "GOV-09", "governance-fraud-risk.md:123", Strength.HIGH,
        lambda m: bool(m["disclosure_violation_within_3y"]),
        "信息披露违规记录", "证监会/交易所公告",
        ("disclosure_violation_within_3y",),
    ),
    SignalRule(  # :124 🟡 中
        "GOV-10", "governance-fraud-risk.md:124", Strength.MID,
        _check_gov10,
        "重大诉讼/仲裁", "年报重大诉讼仲裁章节",
        ("litigation_amount", "net_assets"),
    ),
    # ---- §3 关联交易异常（9 条；关联收入/担保两档独立成条） ----
    SignalRule(  # :140 🔴 强（20% 档）
        "REL-01", "governance-fraud-risk.md:140", Strength.HIGH,
        lambda m: m["related_txn_to_revenue"] > 0.20,
        "关联交易/收入 > 20%", "年报关联交易汇总表",
        ("related_txn_to_revenue",),
    ),
    SignalRule(  # :141 🔴 强（50% 档，依赖关联方）
        "REL-02", "governance-fraud-risk.md:141", Strength.HIGH,
        lambda m: m["related_txn_to_revenue"] > 0.50,
        "关联交易/收入 > 50%", "年报关联交易汇总表",
        ("related_txn_to_revenue",),
    ),
    SignalRule(  # :142 🔴 强
        "REL-03", "governance-fraud-risk.md:142", Strength.HIGH,
        _check_rel03,
        "关联交易毛利率异常", "年报分部报告 / 关联交易明细",
        ("related_gross_margin", "non_related_gross_margin"),
    ),
    SignalRule(  # :143 🟡 中
        "REL-04", "governance-fraud-risk.md:143", Strength.MID,
        lambda m: m["related_sales_growth"] > 3 * m["total_revenue_growth"],
        "关联销售快速增长", "年报 / 季报",
        ("related_sales_growth", "total_revenue_growth"),
    ),
    SignalRule(  # :144 🟡 中
        "REL-05", "governance-fraud-risk.md:144", Strength.MID,
        lambda m: m["related_top5_supplier_share"] > 0.80,
        "关联采购集中度高", "年报供应商披露",
        ("related_top5_supplier_share",),
    ),
    SignalRule(  # :150 🔴 强
        "REL-06", "governance-fraud-risk.md:150", Strength.HIGH,
        _check_rel06,
        "“其他应收款”中的关联方款项", "年报其他应收款附注",
        ("related_other_receivables", "total_assets"),
    ),
    SignalRule(  # :151 🔴 强；值为 bool 或账龄 >1 年的金额（>0 即占用）
        "REL-07", "governance-fraud-risk.md:151", Strength.HIGH,
        lambda m: bool(m["related_prepayment_aged_over_1y"]),
        "“预付账款”中的关联方款项", "年报预付款项附注",
        ("related_prepayment_aged_over_1y",),
    ),
    SignalRule(  # :159 🔴 强（50% 档）
        "REL-08", "governance-fraud-risk.md:159", Strength.HIGH,
        lambda m: m["guarantee_to_net_assets"] > 0.50,
        "对外担保/净资产 > 50%", "年报对外担保情况",
        ("guarantee_to_net_assets",),
    ),
    SignalRule(  # :161 🔴 强（100% 档，担保风险实质性暴露）
        "REL-09", "governance-fraud-risk.md:161", Strength.HIGH,
        lambda m: m["guarantee_to_net_assets"] > 1.00,
        "担保余额超过净资产", "年报对外担保情况",
        ("guarantee_to_net_assets",),
    ),
    # ---- §4 逃废债机械项（2 条） ----
    SignalRule(  # :209 🔴 强（逃废债三件套之一；三件套齐发的一票否决判定在 T2 events 层）
        "DEBT-01", "governance-fraud-risk.md:209", Strength.HIGH,
        lambda m: m["parent_debt_ratio"] > 0.90,
        "母公司负债率 > 90%（逃废债三件套之一）", "年报 / 公告",
        ("parent_debt_ratio",),
    ),
    SignalRule(  # :212 🟡 中
        "DEBT-02", "governance-fraud-risk.md:212", Strength.MID,
        lambda m: m["annual_report_delay_days"] > 30,
        "年报延迟披露", "年报 / 公告",
        ("annual_report_delay_days",),
    ),
)


def evaluate_signals(measured: dict) -> list[RedFlag]:
    """逐条评估规则库 → 命中 RedFlag 列表。

    缺输入（required 键缺失或值为 None）的规则跳过并留 data_note 条目
    （note 以 DATA_NOTE_PREFIX 开头、strength=LOW 占位）——不静默按 0 处理，
    缺失可观测。命中条目 evidence 为输入键值留痕。
    """
    flags = []
    for rule in RULES:
        missing = [k for k in rule.required if k not in measured or measured[k] is None]
        if missing:
            flags.append(RedFlag(
                name=rule.name,
                strength=Strength.LOW,
                evidence="",
                source=rule.source,
                note=(
                    f"{DATA_NOTE_PREFIX}规则 {rule.id} 缺输入指标 {missing}，"
                    "跳过（不静默按 0 处理）"
                ),
            ))
            continue
        if rule.check(measured):
            evidence = "; ".join(f"{k}={measured[k]!r}" for k in rule.required)
            flags.append(RedFlag(
                name=rule.name,
                strength=rule.strength,
                evidence=evidence,
                source=rule.source,
                note=f"{rule.id} 命中（{rule.doc_anchor}）",
            ))
    return flags


# --------------------------------------------------------------------------
# 辅助检测公式（§1.5 :73-:76）
# --------------------------------------------------------------------------

def beneish_m(dsri, gmi, aqi, sgi, depi, sgai, tata, lvgi) -> float:
    """Beneish M-Score（8 变量经典系数；:73「简化版」操纵嫌疑线 > -2.22）。

    文档仅给输出阈值未给系数——采用 Beneish (1999) 原始 8 变量系数
    （参数出处注释，非文档阈值故不属 D6 约束）。
    """
    return (
        -4.84
        + 0.92 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )


def altman_z(x1, x2, x3, x4, x5) -> float:
    """Altman Z-Score（中国版，:74）：1.2X1+1.4X2+3.3X3+0.6X4+1.0X5。

    Z < 1.81 为高风险区（ALTMAN_Z_HIGH_RISK_THRESHOLD）。
    """
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def core_earnings(cfo, non_recurring, net_profit) -> float:
    """Core Earnings Ratio（:76）：（经营现金流 - 非经常性费用）/ 净利润。

    持续 < 0.5 盈利能力可疑（CORE_EARNINGS_SUSPICION_THRESHOLD）；
    > 0.8 正常。净利润为 0 无法计算 → raise（失败可观测，不静默返回）。
    """
    if net_profit == 0:
        raise ValueError("core_earnings：净利润为 0，比率不可计算")
    return (cfo - non_recurring) / net_profit


# --------------------------------------------------------------------------
# §4.3 还款意愿评分（:219-232）
# --------------------------------------------------------------------------

# :221-224 四项信号扣分（信号存在即扣全额；权重 30%/25%/25%/20%）。
_WILLINGNESS_DEDUCTIONS = (30, 25, 25, 20)  # 划转 / 政府支持 / 空壳化 / 历史记录


def repayment_willingness(
    transfer: int, gov_support: int, hollowing: int, history: int,
) -> tuple:
    """§4.3 还款意愿评分：四项 0/1 信号 → (得分, 档位标签)。

    档位（:228-231，左闭右开沿分值轴）：
      -80~-100 🔴 高度逃废债嫌疑；-50~-79 🟠 中高度嫌疑；
      -20~-49 🟡 有风险点；0~-19 🟢 还款意愿正常。
    输入非 0/1 → raise（不静默截断）。
    """
    inputs = (transfer, gov_support, hollowing, history)
    illegal = [v for v in inputs if v not in (0, 1)]
    if illegal:
        raise ValueError(
            f"还款意愿信号须为 0/1（存在与否），实际 {inputs!r}"
        )
    score = -sum(w * v for w, v in zip(_WILLINGNESS_DEDUCTIONS, inputs))
    if score <= -80:
        label = "🔴 高度逃废债嫌疑"
    elif score <= -50:
        label = "🟠 中高度嫌疑"
    elif score <= -20:
        label = "🟡 有风险点"
    else:
        label = "🟢 还款意愿正常"
    return score, label


# --------------------------------------------------------------------------
# T2：一票否决规则库（§6.3 :344-349 / §2.4 :128 / §10.3 :714-717）
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class VetoRule:
    """一票否决规则：触发后综合评级上限锁定 CCC（§6.2 :323 / §6.3 :342）。

    双轨判定（取并集，任一轨命中即触发）：
    - 事件轨：events[event_key] 为 truthy（布尔或文本证据）——11 条全有，
      不可机械判定项（立案调查/失联/灾难中断等）仅此轨；
    - 机械轨：check 非空且 measured 输入齐备时按阈值判定（v5/v7 两条；
      required 键缺失或 None 时跳过并留 notes，不静默按 0 处理）。
    """

    id: str
    doc_anchor: str          # "governance-fraud-risk.md:<行号>"（parity 锚点）
    name: str
    event_key: str           # events 输入键（布尔/文本证据）
    check: object = None     # callable[[dict], bool] | None（机械轨，可空）
    required: tuple = ()


def _check_v5(m: dict) -> bool:
    # :348 关联方资金占用金额超过净资产 30%（"超过"→ 严格大于）
    return m["related_funds_occupation"] > 0.30 * m["net_assets"]


def _check_v7(m: dict) -> bool:
    # :128 年报净资产为负（事实上的 D 级状态）
    return m["net_assets"] < 0


VETO_RULES: tuple = (
    VetoRule(  # §6.3-1 :344
        "v1", "governance-fraud-risk.md:344",
        "被证监会/监管机构立案调查且涉及财务造假",
        "v1_csrc_fraud_investigation",
    ),
    VetoRule(  # §6.3-2 :345
        "v2", "governance-fraud-risk.md:345",
        "审计机构对持续经营能力出具否定意见或无法表示意见",
        "v2_going_concern_adverse",
    ),
    VetoRule(  # §6.3-3 :346
        "v3", "governance-fraud-risk.md:346",
        "实控人高比例质押 + 股价持续跌破平仓线且无补充质押物",
        "v3_pledge_liquidation_no_supplement",
    ),
    VetoRule(  # §6.3-4 :347
        "v4", "governance-fraud-risk.md:347",
        "核心资产剥离已实质性启动且无合理解释",
        "v4_core_asset_divestiture",
    ),
    VetoRule(  # §6.3-5 :348（机械轨 + 事件轨）
        "v5", "governance-fraud-risk.md:348",
        "关联方资金占用金额超过净资产 30%",
        "v5_related_funds_occupation",
        _check_v5, ("related_funds_occupation", "net_assets"),
    ),
    VetoRule(  # §6.3-6 :349（三件套由调用方聚合确认后布尔输入；
        # 其中"母公司负债率>90%"机械项见 DEBT-01 :209，单中不构成否决）
        "v6", "governance-fraud-risk.md:349",
        "逃废债三件套全部确认同时出现（AAA + 负债率>90% + 核心主体切割）",
        "v6_debt_evasion_trio",
    ),
    VetoRule(  # §2.4 :128（机械轨 + 事件轨）
        "v7", "governance-fraud-risk.md:128",
        "净资产为负/资不抵债",
        "v7_negative_net_assets",
        _check_v7, ("net_assets",),
    ),
    VetoRule(  # §10.3-7 :714
        "v8", "governance-fraud-risk.md:714",
        "实控人失联/被调查/被采取强制措施",
        "v8_controller_missing_or_investigated",
    ),
    VetoRule(  # §10.3-8 :715
        "v9", "governance-fraud-risk.md:715",
        "核心系统灾难性故障致核心业务完全中断超过 72 小时",
        "v9_core_system_outage_over_72h",
    ),
    VetoRule(  # §10.3-9 :716
        "v10", "governance-fraud-risk.md:716",
        "被网信办认定严重数据安全风险并责令业务整改",
        "v10_cac_data_security_rectification",
    ),
    VetoRule(  # §10.3-10 :717
        "v11", "governance-fraud-risk.md:717",
        "反垄断处罚致核心业务被迫拆分或结构性调整",
        "v11_antitrust_business_split",
    ),
)


# --------------------------------------------------------------------------
# T2：D6 判断型事件（无阈值不新造——LLM 判断输入 + 注记，🟠 关注 → LOW_MID）
# --------------------------------------------------------------------------

# (event_key, 名称, doc_anchor)；🟠 关注介于 🟡 中与低强度之间 → LOW_MID，
# 计入 red_flags 但不计入通用红旗面数（面数口径 strength≥MID，见 §6.2 :338）。
JUDGMENT_EVENTS: tuple = (
    ("exchange_inquiry", "交易所问询函/监管关注", "governance-fraud-risk.md:126"),
    ("litigation_surge", "被申请仲裁/诉讼频率骤增", "governance-fraud-risk.md:127"),
)


# --------------------------------------------------------------------------
# T2：§10.4 数据可得性参数表（:723-731）
# --------------------------------------------------------------------------

DATA_DENSITY: dict = {
    "财务欺诈": "60-70%",    # :725
    "管理层治理": "60-70%",  # :726
    "关联交易": "50-60%",    # :727
    "逃废债": "60-70%",      # :728
    "系统故障": "30-40%",    # :729
    "合规违规": "70-80%",    # :730
    "关键人员": "50-60%",    # :731
}


# --------------------------------------------------------------------------
# T2：叠加合成（§6.2 矩阵 :318-323 + 通用红旗计数叠加 :325-338，D5 取最严）
# --------------------------------------------------------------------------

_GRADES = ("正常", "关注", "高", "严重")  # §6.2 :320-323 四档有序


@dataclass(frozen=True)
class StackResult:
    """stack_severity 输出。

    l4_cap：L4 财务层评分上限（10 无影响 / 7 关注档 / 4 高档）；否决时
    「所有层评分上限锁定」（:323），单一 L4 上限不适用 → None。
    """

    risk_grade: str          # 正常 / 关注 / 高 / 严重
    rating_cap: object       # None | "B" | "CCC"
    l4_cap: object           # int | None（否决锁定）
    outlook_flag: bool       # 关注档「评级前置减半档」（:321，D4 → flag）
    counted_flags: int       # 通用红旗面数（strength≥MID，data_note 已过滤）
    mid_count: int
    high_count: int
    severity_upgraded: bool  # 计数叠加 ≥2 面升一级（:328）
    veto_triggered: bool
    notes: tuple = ()


def stack_severity(flags: list) -> StackResult:
    """D5 合成顺序（§6.2 :338 双口径并行适用 + §10.3 :719 取最严）：

    ① 通用红旗计数（strength≥MID 计 1 面，:328-329）：≥3 → rating_cap=B；
      ≥2 → 严重度升一级（非否决路径上限为「高」——「严重」仅由否决触发，:323）；
    ② §6.2 矩阵（:320-323）：MID 计数 2-3 → 关注（l4_cap=7 + outlook_flag）；
      MID>3 或 HIGH≥1 → 高（l4_cap=4 + cap B）；
    ③ 一票否决（VETO 强度旗）→ 严重 + cap CCC + 全层锁定（l4_cap=None）。

    T1 带入项：note 以 DATA_NOTE_PREFIX 开头的占位条目一律过滤，
    不计入任何计数/分级。
    """
    effective = [f for f in flags if not f.note.startswith(DATA_NOTE_PREFIX)]
    vetoes = [f for f in effective if f.strength >= Strength.VETO]
    counted = [f for f in effective if Strength.MID <= f.strength < Strength.VETO]
    mid_n = sum(1 for f in counted if f.strength == Strength.MID)
    high_n = sum(1 for f in counted if f.strength >= Strength.HIGH)
    n = len(counted)

    # ③ 否决优先判定（:323 🔴 严重 → CCC + 所有层评分上限锁定）
    if vetoes:
        return StackResult(
            risk_grade="严重",
            rating_cap="CCC",
            l4_cap=None,
            outlook_flag=False,
            counted_flags=n,
            mid_count=mid_n,
            high_count=high_n,
            severity_upgraded=False,
            veto_triggered=True,
            notes=(
                f"一票否决触发（{len(vetoes)} 条，§6.2 :323）→ 综合评级上限锁定 "
                "CCC，所有层评分上限锁定（l4_cap 不适用）",
            ),
        )

    # ② §6.2 矩阵（取最严：高档条件优先于关注档）
    if mid_n > 3 or high_n >= 1:
        grade, l4_cap, cap, outlook = "高", 4, "B", False
        matrix_note = "§6.2 高档（:322）：中强度 >3 或高强度 ≥1 → L4 上限 4 + 评级上限 B"
    elif 2 <= mid_n <= 3:
        grade, l4_cap, cap, outlook = "关注", 7, None, True
        matrix_note = "§6.2 关注档（:321）：2-3 个中强度信号 → L4 上限 7 + 评级前置减半档"
    else:
        grade, l4_cap, cap, outlook = "正常", 10, None, False
        matrix_note = "§6.2 正常档（:320）：无红旗或仅个别低强度信号 → 无影响"

    # ① 通用红旗计数叠加（与矩阵并行适用，:338；效果取最严）
    upgraded = n >= 2
    if n >= 3:
        cap = "B"
    if n >= 2 and grade != "高":
        grade = _GRADES[_GRADES.index(grade) + 1]  # 升一级；高档已为非否决上限
    overlay_note = (
        f"通用红旗 {n} 面（:328-329）："
        + ("≥3 → 评级上限 B；" if n >= 3 else "")
        + ("≥2 → 严重度升一级" if n >= 2 else "未达升级线")
    )

    return StackResult(
        risk_grade=grade,
        rating_cap=cap,
        l4_cap=l4_cap,
        outlook_flag=outlook,
        counted_flags=n,
        mid_count=mid_n,
        high_count=high_n,
        severity_upgraded=upgraded,
        veto_triggered=False,
        notes=(matrix_note, overlay_note),
    )


# --------------------------------------------------------------------------
# T2：合成入口
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceResult:
    """compute_governance 输出（字段口径见 stack_severity/compute docstring）。"""

    risk_grade: str
    rating_cap: object           # None | "B" | "CCC"
    l4_cap: object               # int | None
    outlook_flag: bool
    red_flags: list              # evaluate_signals 全部条目 + 否决/判断事件旗
    veto_triggers: list          # 触发的否决规则 id（"v1"-"v11"）
    repayment_willingness: object  # (score, label) | None（未提供信号时）
    data_density: dict           # §10.4 可观测比例参数表（DATA_DENSITY）
    notes: list


def compute_governance(measured: dict, events: dict) -> GovernanceResult:
    """合成入口：信号评估 → 否决检测 → D6 判断事件 → 叠加合成。

    measured 契约：机械指标的预聚合单值字典——"连续 8 季""且持续"等
    持续性修饰语由调用方预聚合为单值输入（T4 适配器 docstring 引用本口径）。

    events 契约：事件型输入——
    - 否决证据：VETO_RULES 各 event_key → 布尔或文本证据（truthy 触发）；
      v5/v7 另有机械轨，与事件轨并行取并集；
    - D6 判断项：JUDGMENT_EVENTS 各键 → LLM 判断输入（truthy 计入
      red_flags 并带注记，不计入通用红旗面数）；
    - willingness（可选）：§4.3 四项 0/1 信号子 dict
      {"transfer","gov_support","hollowing","history"}——四键缺一即
      raise（失败可观测）；整体缺省 → repayment_willingness=None + 注记。
    """
    notes = []
    flags = list(evaluate_signals(measured))
    missing_n = sum(1 for f in flags if f.note.startswith(DATA_NOTE_PREFIX))
    if missing_n:
        notes.append(
            f"{missing_n} 条信号规则缺输入留 data_note（前缀过滤，不计入计数/分级）"
        )

    # 否决检测：事件轨 ∪ 机械轨
    veto_triggers = []
    for rule in VETO_RULES:
        evidences = []
        event_val = events.get(rule.event_key)
        if event_val:
            evidences.append(f"{rule.event_key}={event_val!r}")
        if rule.check is not None:
            missing = [
                k for k in rule.required
                if k not in measured or measured[k] is None
            ]
            if missing:
                notes.append(
                    f"否决规则 {rule.id} 机械轨缺输入 {missing}，"
                    f"仅依 events[{rule.event_key!r}] 判定（不静默按 0 处理）"
                )
            elif rule.check(measured):
                evidences.append(
                    "; ".join(f"{k}={measured[k]!r}" for k in rule.required)
                )
        if evidences:
            veto_triggers.append(rule.id)
            flags.append(RedFlag(
                name=rule.name,
                strength=Strength.VETO,
                evidence=" | ".join(evidences),
                source="events/measured（一票否决）",
                note=f"{rule.id} 一票否决命中（{rule.doc_anchor}）",
            ))

    # D6 判断型事件：LLM 判断输入计入 red_flags + 注记（不计入面数）
    for key, name, anchor in JUDGMENT_EVENTS:
        val = events.get(key)
        if val:
            flags.append(RedFlag(
                name=name,
                strength=Strength.LOW_MID,  # 🟠 关注（介于中与低之间）
                evidence=f"{key}={val!r}",
                source="LLM 判断输入（events）",
                note=(
                    f"{key} 判断事件计入（{anchor}）——D6 注记：无阈值不新造，"
                    "LLM 判断输入按事件计入，不计入通用红旗面数"
                ),
            ))

    # §4.3 还款意愿（可选子 dict；四键缺一即 raise）
    w = events.get("willingness")
    if w is None:
        willingness = None
        notes.append("未提供还款意愿信号（§4.3），repayment_willingness=None")
    else:
        required_w = ("transfer", "gov_support", "hollowing", "history")
        missing_w = [k for k in required_w if k not in w]
        if missing_w:
            raise ValueError(
                f"willingness 子 dict 缺键 {missing_w}（§4.3 四项信号须齐备，"
                "不静默按 0 处理）"
            )
        willingness = repayment_willingness(*(w[k] for k in required_w))

    stack = stack_severity(flags)
    notes.extend(stack.notes)

    return GovernanceResult(
        risk_grade=stack.risk_grade,
        rating_cap=stack.rating_cap,
        l4_cap=stack.l4_cap,
        outlook_flag=stack.outlook_flag,
        red_flags=flags,
        veto_triggers=veto_triggers,
        repayment_willingness=willingness,
        data_density=DATA_DENSITY,
        notes=notes,
    )

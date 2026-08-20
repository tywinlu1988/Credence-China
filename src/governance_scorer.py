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

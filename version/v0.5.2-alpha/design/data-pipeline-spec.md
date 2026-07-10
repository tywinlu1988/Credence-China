# 数据管道接口规范 · 固收信用分析引擎 Mode A 马赛克引擎

**版本**: v0.1 | **日期**: 2026-07-09
**性质**: 接口契约文档 — 定义数据采集层、信号提取层、报告生成层的标准化接口
**状态**: 初稿 — 已有方法论文档支撑的部分已标注

---

## 目录

1. [总体架构](#一总体架构)
2. [数据采集层（Input Adapter）](#二数据采集层input-adapter)
3. [信号提取层（Signal Extractor）](#三信号提取层signal-extractor)
4. [报告生成层（Report Generator）](#四报告生成层report-generator)
5. [数据流时序](#五数据流时序)
6. [公开数据源清单](#六公开数据源清单)
7. [优先级和依赖](#七优先级和依赖)
8. [错误处理与边界条件](#八错误处理与边界条件)
9. [附录：与现有设计文档的映射关系](#九附录与现有设计文档的映射关系)

---

## 一、总体架构

### 1.1 五层管道

```
                +------------+
                │  用户输入   │
                │ 行业+企业名 │
                +------+-----+
                       │
                       ▼
          ┌──────────────────────┐
          │  ① 数据采集层        │  ← 新工程化
          │  Input Adapter       │
          │  Mode A: WebSearch   │
          │  Mode B: 外部数据源  │  (接口已定义，未来实现)
          └──────────┬───────────┘
                     │ RawData[]
                     ▼
          ┌──────────────────────┐
          │  ② 信号提取层        │  ← 新工程化
          │  Signal Extractor    │
          │  非结构化 → 结构化   │
          └──────────┬───────────┘
                     │ Signal[]
                     ▼
          ┌──────────────────────┐
          │  ③ 马赛克拼图层      │  ← 已有设计
          │  Mosaic Engine       │  (mosaic-engine.md §四)
          │  信号叠加/交叉验证   │
          │  完备性评估          │
          └──────────┬───────────┘
                     │ MosaicResult
                     ▼
          ┌──────────────────────┐
          │  ④ 分析引擎层        │  ← 已有设计
          │  Analysis Engine     │  (analysis-engine-methodology.md)
          │  金字塔评分/评级映射 │
          └──────────┬───────────┘
                     │ AnalysisResult
                     ▼
          ┌──────────────────────┐
          │  ⑤ 报告生成层        │  ← 新工程化
          │  Report Generator    │
          │  结果 → HTML报告     │
          └──────────────────────┘
```

### 1.2 分层职责

| 层 | 职责 | 输入 | 输出 | 当前状态 |
|---|---|---|---|---|
| ① 数据采集层 | 从多源获取原始数据 | `(industry, company)` | `RawData[]` | **纯空白** — 当前依赖手工WebSearch |
| ② 信号提取层 | 非结构化→结构化信号转换 | `RawData[]` | `Signal[]` | **纯空白** — 当前依赖LLM临时提示词 |
| ③ 马赛克拼图层 | 信号聚合/交叉验证/完备性 | `Signal[]` | `MosaicResult` | **已有完整设计** — mosaic-engine.md §三-五 |
| ④ 分析引擎层 | 金字塔评分/评级映射 | `MosaicResult` | `AnalysisResult` | **已有完整设计** — analysis-engine-methodology.md §四-六 |
| ⑤ 报告生成层 | 结果→HTML渲染 | `AnalysisResult` | `HTML file` | **部分空白** — 模板已设计，渲染逻辑未工程化 |

### 1.3 关键设计原则

1. **数据层无判断**：数据采集层只做拉取和结构化，不做信用判断
2. **接口契约优先**：每层定义严格的输入/输出接口，支持独立开发
3. **并行拉取**：数据采集层同时向多个数据源发起请求，聚合后统一交付
4. **诚实标记**：任何时候不得篡改或编造数据，缺失信息必须显式标记
5. **向后兼容**：新增数据源类型不破环已有管道

---

## 二、数据采集层（Input Adapter）

### 2.1 概述

**当前状态**: **纯空白**。所有数据采集当前通过手工WebSearch完成，无标准化接口。

**职责**:
- 接收 `(industry, company)` 输入
- 根据输入自动确定需要采集的数据层级（policy/enterprise/industry/market）
- 按层级并行发起多个数据采集任务
- 聚合原始数据并传递给信号提取层

**核心接口**:

```yaml
InputAdapter:
  # ── 入口 ──
  collect(industry: string, company: string, options?: CollectOptions):
    # 主入口：并行采集所有数据源
    # 返回: CollectResult

  # ── 内部接口（可独立调用）──
  collect_policy(industry: string): PolicyDoc[]
    # 采集产业政策数据

  collect_enterprise(company: string): EnterpriseProfile
    # 采集企业公开数据

  collect_industry_data(industry: string): IndustryData[]
    # 采集行业/市场数据

  collect_market_pricing(company: string): MarketData[]
    # 采集市场定价数据

  # ── 生命周期 ──
  validate_source(name: string): SourceStatus
    # 检查某个数据源是否可达

  # ── 事件 ──
  on_source_complete(source_name: string): void
    # 单个数据源采集完成时触发
  on_all_complete(): void
    # 全部数据源采集完成时触发
  on_source_error(source_name: string, error: Error): void
    # 单个数据源采集失败时触发
```

**错误处理**:

```yaml
CollectError:
  type: "source_unreachable" | "parse_failed" | "rate_limited" | "timeout" | "empty_result"
  source: string          # 出问题的数据源名称
  detail: string          # 错误详情
  recoverable: boolean    # 是否可重试
  retry_after?: int       # 建议重试等待时间（秒）

  # 错误处理策略：
  # - 非关键源（如某个行业数据源）失败 → 记录错误，继续其他源
  # - 关键源（如企业工商信息）失败 → 整个采集失败，向上层返回错误
  # - 所有源都为空 → 返回 "no_data" 错误
```

### 2.2 Mode A: 公开数据源适配器（当前实现）

```yaml
PublicDataSource:
  # ═══════════════════════════════════════════
  # A1 — 政策数据源适配器
  # ═══════════════════════════════════════════
  - name: "web_search_policy"
    description: "关键字搜索 → 搜索策略模板 → 结果列表"
    method: >
      1. 根据行业加载搜索关键词模板
      2. 并行向多个搜索策略发起查询
      3. 过滤出.gov/.org等高可信来源
      4. 按相关度和时间排序
    input:
      industry: string        # 如 "光伏"
      keywords: string[]       # 自动生成的关键词列表
      time_range: string       # "1y" | "2y" | "all"
    output: SearchResult[]
    output_structure:
      SearchResult:
        url: string
        title: string
        snippet: string
        source: string         # 域名
        publish_date: datetime
        relevance_score: 0-1
        content_type: "policy_document" | "regulation" | "notice" | "industry_plan"
    error:
      - "no_results": 搜索无结果 → 标记为数据缺口
      - "rate_limited": 搜索限流 → 等待后重试（最多3次）
    # 已有方法论文档支撑: data-architecture.md L1层, mosaic-engine.md §七

  # ═══════════════════════════════════════════
  # A2 — 企业数据源适配器
  # ═══════════════════════════════════════════
  - name: "web_search_enterprise"
    description: "企业名称 → 工商/司法/执行/招投标多源聚合"
    method: >
      1. 按企业全称+别名发起搜索
      2. 识别并分类结果类型（工商/司法/招投标/新闻）
      3. 从GSXT/wenshu/zxgk等目标站提取结构化信息
      4. 多源去重、合并
    input:
      company: string          # 企业全称
      aliases?: string[]       # 曾用名/简称
    output: EnterpriseProfile
    output_structure:
      EnterpriseProfile:
        basic:
          name: string
          unified_social_credit_code: string
          registered_capital: string
          legal_representative: string
          establishment_date: datetime
          status: "active" | "revoked" | "cancelled" | "bankruptcy"
        risk_records:
          enforcement_records: EnforcementRecord[]
          dishonest_persons: DishonestPerson[]
          litigation_records: LitigationRecord[]
          admin_penalties: AdminPenalty[]
          bankruptcy_info?: BankruptcyInfo
        bidding_records:
          won_bids: BidRecord[]
          win_rate: float
          major_customers: string[]
        news_and_events:
          news: NewsItem[]
          financing_events: FinancingEvent[]
          major_announcements: Announcement[]
    error:
      - "company_not_found": 企业名称无法匹配 → 返回搜索建议
      - "partial_data": 部分数据源不可用 → 返回可用数据+标注缺口
    # 已有方法论文档支撑: data-architecture.md L4-L5层

  # ═══════════════════════════════════════════
  # A3 — 行业数据源适配器
  # ═══════════════════════════════════════════
  - name: "web_search_industry"
    description: "行业名称 → 行业统计/价格/报告多源聚合"
    method: >
      1. 按行业加载数据模板（价格指数、产量、装机量等）
      2. 从CPIA/SEMI/券商报告等来源搜索
      3. 识别数据点的时间戳和单位
      4. 同指标多源数据对齐
    input:
      industry: string         # 如 "光伏"
      data_categories: string[]  # ["price", "capacity", "demand", "policy_impact"]
      time_range: string       # "6m" | "1y" | "3y"
    output: IndustryData[]
    output_structure:
      IndustryData:
        category: string       # "price_index" | "capacity" | "shipment" | "utilization_rate"
        series_name: string    # "TOPCon电池价格" | "硅料产量"
        data_points: DataPoint[]
          - date: datetime
            value: float
            unit: string
            source: string
            data_quality: "official" | "estimated" | "inferred"
    error:
      - "insufficient_data": 该行业公开数据不足 → 返回所有可用数据+缺口标记
    # 已有方法论文档支撑: data-architecture.md L2-L3层, 四类数据验证

  # ═══════════════════════════════════════════
  # A4 — 市场定价数据源适配器
  # ═══════════════════════════════════════════
  - name: "web_search_market"
    description: "企业/行业 → 公开市场定价信号"
    method: >
      1. 搜索企业债券/股票公开交易信息
      2. 从中国货币网/交易所/中债估值获取利率和信用利差数据
      3. 聚合搜索结果为结构化信号
    input:
      company: string
      bond_codes?: string[]    # 已知的债券代码
      market_type: "bond" | "stock" | "both"
    output: MarketData[]
    output_structure:
      MarketData:
        instrument_type: "bond" | "stock"
        code?: string
        name: string
        data_type: "ytm" | "spread" | "volume" | "rating"
        data_points: DataPoint[]
          - date: datetime
            value: float
            source: string
        # 注意: 中国市场bid-ask spread不披露 → 标注为"结构性缺失"
    error:
      - "no_public_pricing": 非上市公司或债券无公开报价 → 属正常缺口
    # 已有方法论文档支撑: data-architecture.md §四, mosaic-engine.md §五.2
```

### 2.3 Mode B: 外部数据源适配器（未来实现）

```yaml
ExternalDataSource:
  description: >
    模式B是马赛克引擎的可扩展数据适配层，允许用户接入付费数据终端或内部数据源来填补模式A的缺口。
    接口定义已完成（详见 mosaic-engine.md §六 和 data-architecture.md §六），此处仅为概要引用。

  # ── 适配器契约（完整版见 mosaic-engine.md §六.1）──
  DataSourceAdapter:
    # 生命周期
    init(config):
      # config.auth_type: "api_key" | "oauth" | "basic"
      # config.rate_limit: requests/minute
      # config.cache_ttl: seconds

    health_check():
      # 返回: { status: "ok" | "degraded" | "down", latency_ms: int }

    # 核心查询
    query_bond_analytics(bond_code, fields):
      # fields: ["ytm","duration","convexity","z_spread","oas","bid_ask"]
      # 返回: { field: value, data_timestamp: string }

    query_market_data(instrument_code, data_type, date_range):
      # data_type: "price_history" | "volume" | "volatility" | "fund_flow"

    query_industry_benchmark(industry, metric, date):
      # metric: "credit_spread" | "default_rate" | "rating_migration"

    to_signals():
      # 将外部数据转换为统一的信号对象格式

  # ── 支持的接入方式（规划）──
  connection_methods:
    - type: "csv_upload"
      priority: P1
      scenario: "一次性分析，用户手动导出数据"

    - type: "rest_api"
      priority: P1
      scenario: "Wind/Choice/同花顺等金融终端API"
      examples:
        - "Wind API"
        - "Choice API"
        - "中债估值API"

    - type: "mcp_server"
      priority: P2
      scenario: "用户自建的数据服务"
      protocol: "MCP (Model Context Protocol)"

    - type: "database"
      priority: P3
      scenario: "用户内部数据仓库"

  # 当前状态: 接口已定义（契约完成），但无实现
```

### 2.4 数据采集策略

```yaml
CollectStrategy:
  # ── 搜索关键词模板（按行业加载）──
  keyword_templates:
    policy:
      industry: "industry"     # 替换为实际行业名
      templates:
        - "{industry} 政策 {year}"
        - "{industry} 发改委 最新规定"
        - "{industry} 产业指导目录"
        - "{industry} 补贴 退坡"
    enterprise:
      company: "company"       # 替换为实际企业名
      templates:
        - "{company} 工商信息"
        - "{company} 被执行人"
        - "{company} 裁判文书"
        - "{company} 招标"
        - "{company} 公告"
    industry:
      - "{industry} 产量 {year}"
      - "{industry} 价格 最新"
      - "{industry} 市场规模"
      - "{industry} 装机量"

  # ── 并行策略 ──
  concurrency:
    max_parallel_sources: 4       # 最多同时查询4个数据源
    source_timeout: 30000          # 单源超时30秒
    total_timeout: 120000          # 总超时120秒
    retry_count: 3                 # 失败重试次数
    retry_backoff: "exponential"   # 指数退避

  # ── 缓存策略 ──
  cache:
    policy_data: 86400             # 政策数据缓存24小时
    enterprise_data: 3600          # 企业数据缓存1小时
    market_data: 300               # 市场数据缓存5分钟
    industry_data: 86400           # 行业数据缓存24小时

  # ── 数据质量标注 ──
  DataQuality:
    - level: "official"
      description: "官方发布，精确数据"
      examples: ["政府公告", "交易所数据", "法院判决书"]
      confidence_modifier: 0       # 对信号置信度无影响

    - level: "reported"
      description: "可靠媒体报道或摘要"
      examples: ["券商研报摘要", "行业媒体报道"]
      confidence_modifier: -1      # 信号置信度降一级

    - level: "estimated"
      description: "估算或推断数据"
      examples: ["行业估算值", "从多源推断"]
      confidence_modifier: -2      # 信号置信度降二级

    - level: "inferred"
      description: "从碎片数据推导"
      examples: ["从招标结果推断产量", "从价格趋势推断供需"]
      confidence_modifier: -3      # 信号置信度降三级
```

---

## 三、信号提取层（Signal Extractor）

### 3.1 概述

**当前状态**: **纯空白**。当前信号提取通过临时LLM提示词完成，无标准化接口、无缓存、无质量监控。

**职责**:
- 将数据采集层返回的非结构化/半结构化数据转换为统一的信号对象
- 每条信号标注源URL、时间戳、所属维度、方向、强度、置信度
- 不做判断，只做结构化（见 mosaic-engine.md §三.3）
- 每条原始数据最多提取3条信号（避免LLM过度生成）

**核心接口**:

```yaml
SignalExtractor:
  # ── 主入口 ──
  extract(raw_data: RawData[], industry: string, company: string):
    # 将一批原始数据转换为结构化信号
    # 返回: ExtractResult

  # ── 类型专用提取器 ──
  extract_from_search_results(results: SearchResult[]): Signal[]
    # 从搜索结果（标题+摘要+URL）提取信号

  extract_from_policy_doc(doc: PolicyDoc): Signal[]
    # 从完整政策文本提取信号（需要LLM全文理解）

  extract_from_enterprise_profile(profile: EnterpriseProfile): Signal[]
    # 从企业画像提取信号（工商/司法/招投标结构化数据→信号）

  extract_from_industry_data(data: IndustryData[]): Signal[]
    # 从行业数据序列提取趋势信号

  extract_from_market_data(data: MarketData[]): Signal[]
    # 从市场定价数据提取信号

  # ── 元数据 ──
  get_extraction_stats(session_id: string): ExtractionStats
    # 获取提取统计信息（信号数/源数/平均置信度/耗时）

  # ── 事件 ──
  on_signal_extracted(signal: Signal): void
  on_extraction_complete(result: ExtractResult): void
  on_extraction_error(source_id: string, error: Error): void
```

### 3.2 信号对象数据结构

```yaml
Signal:
  # ── 标识字段 ──
  id: string                     # 格式: "sig_{timestamp}_{uuid_short}"
  session_id: string             # 所属采集会话ID
  source_url: string             # 具体数据来源URL
  source_type: string            # "policy_document" | "court_record" | "bidding_result"
                                 # | "industry_report" | "news" | "enterprise_db"
                                 # | "financial_statement" | "market_data" | "rating_event"
  source_data_quality: string    # "official" | "reported" | "estimated" | "inferred"

  # ── 时间字段 ──
  published_at: datetime         # 信息来源发布时间（非采集时间）
  extracted_at: datetime         # 信号提取时间
  effective_at: datetime         # 信号有效时间（数据点对应的时间）

  # ── 内容字段 ──
  dimension: string              # "L1_policy" | "L2_technology" | "L3_supply_chain"
                                 # | "L4_financial" | "track_b"
  sub_dimension: string          # 维度内的子类目（按行业金字塔结构对应）
  content: string                # 信号文本（中文，简洁，事实性）
  summary: string                # 一句话摘要（用于报告展示）

  # ── 信号强度 ──
  direction: string              # "positive" | "negative" | "neutral"
  strength: int                  # 1-5
  # 1 = 方向性弱信号（只有方向，无量级）
  # 2 = 方向性中信号（有方向+定性描述）
  # 3 = 方向性强信号（有方向+粗略量级）
  # 4 = 量化信号（精确数值对比）
  # 5 = 确定性信号（精确数值+权威来源）

  # ── 置信度（初始值，进入拼图层后可能升级）──
  confidence: string             # "L5_cross_validated" | "L4_direct"
                                 # | "L3_inferred" | "L2_weak" | "L1_gap"
  # L5 = 多源交叉验证（≥2独立来源确认同一事实）
  # L4 = 单源直接信号（一个可靠来源明确陈述）
  # L3 = 衍生推断（从多片碎片组合推理得出）
  # L2 = 方向性弱信号（只有方向，无量级）
  # L1 = 缺失信号（缺口）

  # ── 关联字段 ──
  related_signals: string[]      # 关联信号ID列表（用于马赛克关联）
  tags: string[]                 # 自由标签（便于筛选聚合）

  # ── 验证字段 ──
  extraction_method: string      # "llm_extract" | "rule_parse" | "direct_transform"
  human_verified: boolean        # 是否经过人工验证（默认为false）

  # ── 冲突管理 ──
  conflicts_with: string[]       # 如果与其他信号矛盾，记录矛盾信号ID
  is_contradicted: boolean       # 是否被其他信号矛盾
```

### 3.3 提取规则

```yaml
ExtractionRules:
  # ── 数量限制 ──
  max_signals_per_source: 3     # 每条源数据最多提取3条信号
  max_signals_per_session: 200  # 每轮分析最多提取200条信号
  min_content_length: 10        # 信号文本至少10个汉字
  max_content_length: 200       # 信号文本最多200个汉字

  # ── 质量规则 ──
  rules:
    - name: "fact_only"
      description: "只提取事实性内容，不做判断"
      example:
        - NOT_OK: "隆基绿能技术领先"  # 这是判断，不是事实
        - OK: "隆基BC电池量产效率达24.8%"  # 这是事实

    - name: "source_required"
      description: "必须链接到具体数据来源URL"
      example:
        - NOT_OK: "行业竞争加剧"  # 无来源
        - OK: "组件价格从0.38元/W降至0.24元/W（来源: PVInfoLink 2026年7月第1周周报）"

    - name: "time_required"
      description: "必须标注数据时间点"
      example:
        - NOT_OK: "企业被执行记录"  # 无时间
        - OK: "2026年6月新增被执行记录，标的额1.2亿"

    - name: "no_duplicate"
      description: "同一来源的同一事实只提取一次"
      dedup_window: 3600  # 1小时内同源同内容去重

  # ── 维度映射规则 ──
  dimension_mapping:
    # 从 source_type 到 dimension 的默认映射（可被行业模板覆盖）
    policy_document: "L1_policy"
    court_record: "L4_financial"  # 司法记录映射到财务风险
    bidding_result: "L2_technology"  # 招投标映射到竞争位势
    industry_report: "L2_technology"
    news: "L1_policy" | "L3_supply_chain"  # 视内容而定
    financial_statement: "L4_financial"
    market_data: "track_b"
    rating_event: "track_b"

  # ── 强度映射规则 ──
  strength_mapping:
    - condition: "包含精确数值+比较关系"
      examples: ["效率差距1.5pct", "负债率86.89%", "涨幅13%"]
      strength: 5

    - condition: "包含精确数值"
      examples: ["电池效率24.8%", "中标52GW", "亏损95亿"]
      strength: 4

    - condition: "包含定性描述+对比"
      examples: ["大幅领先同行", "显著恶化", "高于行业平均"]
      strength: 3

    - condition: "包含定性描述"
      examples: ["产能不足", "技术路线存在分歧", "市场份额下降"]
      strength: 2

    - condition: "仅说明方向"
      examples: ["政策支持", "竞争激烈", "风险加剧"]
      strength: 1
```

### 3.4 LLM提取提示词框架

```yaml
LLMPromptFramework:
  description: >
    信号提取层依赖LLM进行非结构化文本的结构化转换。
    以下定义标准化提示词模板，确保各提取节点输出格式一致。

  system_prompt_template: |
    你是一个信用分析引擎的信号提取器。你的任务是从给定的文本中提取结构化的信用信号。

    规则：
    1. 只提取事实——不做判断，不做推测
    2. 每条信号必须有明确的数据来源
    3. 每条信号必须有时间信息（如无具体日期则使用文档日期）
    4. 每条信号标注所属维度（L1政策/L2技术/L3供应链/L4财务/track_b市场）
    5. 数量限制：每条源数据最多提取3条信号
    6. 如果文本中无可用的信用信号，返回空列表
    7. 不要编造——只有当文本明确包含时才提取
    8. 对非结构化文本中的数值、时间、实体进行标准化

    输出格式：
    [
      {
        "content": "信号文本（中文，简洁，200字以内）",
        "summary": "一句话摘要（30字以内）",
        "dimension": "L1_policy",
        "sub_dimension": "电价政策",
        "direction": "positive" | "negative" | "neutral",
        "strength": 1-5,
        "published_at": "YYYY-MM-DD",
        "source_url": "URL",
        "source_type": "policy_document" | "court_record" | "bidding_result" | "industry_report" | "news"
      }
    ]

  context_template: |
    行业: {industry}
    企业: {company}
    分析日期: {analysis_date}
    上下文: {additional_context}

    原始文本：
    {raw_text}

    请提取结构化信号。
```

### 3.5 错误处理

```yaml
SignalExtractorError:
  type: "llm_failure" | "parse_failure" | "empty_result" | "quality_check_failed"
  source_id: string          # 出问题的源数据ID
  detail: string
  recoverable: boolean

  # 错误处理策略：
  # - llm_failure（LLM调用失败）→ 重试2次，指数退避
  # - parse_failure（LLM返回格式无法解析）→ 重试1次，添加格式约束
  # - empty_result（LLM返回空信号列表）→ 正常，记录"该源未提取到信号"
  # - quality_check_failed（提取结果不满足质量规则）→ 丢弃，记录原因
  # - 单个源提取失败 → 不影响其他源
```

### 3.6 提取结果聚合

```yaml
ExtractResult:
  session_id: string
  signals: Signal[]
  stats: ExtractionStats
  errors: SignalExtractorError[]

ExtractionStats:
  total_raw_sources: int         # 输入的原始数据源数量
  total_signals: int             # 提取的信号总数
  avg_confidence: string         # 平均置信度
  distribution:
    L1_gap: int                  # 各置信级别的信号数
    L2_weak: int
    L3_inferred: int
    L4_direct: int
    L5_cross_validated: int
  by_dimension:
    L1_policy: int
    L2_technology: int
    L3_supply_chain: int
    L4_financial: int
    track_b: int
  extraction_duration_ms: int    # 提取耗时
  failed_sources: int            # 失败的源数量

  # 统计输出示例：
  # total_signals: 37
  # avg_confidence: "L3_inferred"
  # distribution: { L1: 2, L2: 8, L3: 15, L4: 10, L5: 2 }
  # by_dimension: { L1: 12, L2: 8, L3: 5, L4: 7, track_b: 5 }
```

---

## 四、报告生成层（Report Generator）

### 4.1 概述

**当前状态**: **部分空白**。12种报告模板的HTML/CSS设计已完成（`report-style-system.md`），但分析结果到HTML的系统化渲染逻辑未实现。当前报告的生成方式为手动编写HTML。

**职责**:
- 接收分析引擎输出的结构化结果
- 根据指定的报告类型选择对应模板
- 将数据注入模板并渲染为完整HTML文件
- 处理报告页眉/页脚/元信息等固定结构
- 处理多语言（中文为主）和数字格式化

**核心接口**:

```yaml
ReportGenerator:
  # ── 主入口 ──
  render(result: AnalysisResult, options: RenderOptions):
    # 将分析结果渲染为HTML
    # 返回: RenderResult（包含渲染后的HTML内容和元数据）

  # ── 独立渲染方法 ──
  render_hero(result: AnalysisResult): string
    # 渲染HERO区域（标题+元信息）

  render_strip(result: AnalysisResult): string
    # 渲染顶栏数字条

  render_section(layer_score: LayerScore, signals: Signal[]): string
    # 渲染单个层级的分析区块

  render_signal_table(signals: Signal[]): string
    # 渲染信号列表表格

  render_completeness(mosaic_result: MosaicResult): string
    # 渲染完备性报告

  render_risk_signals(risk_signals: RiskSignal[]): string
    # 渲染风险信号清单

  # ── 辅助方法 ──
  format_value(value: float, format_spec: string): string
    # 格式化数值（千分位、小数位数、百分比等）
  format_date(date: datetime, format_spec: string): string
    # 格式化日期
  resolve_template_path(template_type: string): string
    # 解析模板文件路径

  # ── 事件 ──
  on_before_render(result: AnalysisResult, options: RenderOptions): void
  on_after_render(html: string, file_path: string): void
  on_render_error(error: RenderError): void
```

### 4.2 渲染选项

```yaml
RenderOptions:
  # ── 报告类型（从12种中选择）──
  template_type: string
  # "type1" — 单标的深度分析（P0）
  # "type2" — 双标的前瞻对比（P1+）
  # "type3" — 黑天鹅回溯验证（P1+）
  # "type4" — 多身份并行评估（P1+）
  # "type5" — 债券投资仪表盘（P0）
  # "type6" — 马赛克完备性报告（P0）
  # "type7" — 行业方法论页（P1+）
  # "type8" — 债项LGD评估（P1+）
  # "type9" — 外部支持专项评估（P1+）
  # "type10" — ESG+治理风险扫描（P1+）
  # "type11" — 压力测试报告（P1+）
  # "type12" — 引擎验证统计（P2+）

  # ── 报告信息 ──
  report_title: string          # 报告标题（如"隆基绿能信用分析报告"）
  report_subtitle?: string      # 副标题
  analyst?: string              # 分析人员（可省略）
  analysis_date: datetime       # 分析日期

  # ── 显示选项 ──
  language: string              # "zh" | "en"（默认为zh）
  show_completeness: boolean    # 是否显示完备性报告（默认true）
  show_signals: boolean         # 是否显示完整信号列表（默认false）
  show_gaps: boolean            # 是否显示数据缺口（默认true）
  compact_mode: boolean         # 紧凑模式（适用于打印，默认false）

  # ── 输出 ──
  output_path?: string          # 输出文件路径（不指定则返回HTML字符串）
  include_css: boolean          # 是否内联CSS（默认true，独立文件时设为false）
  minify: boolean               # 是否压缩HTML（默认false）

  # ── 高级选项 ──
  custom_css_path?: string      # 自定义CSS覆盖
  custom_header?: string        # 自定义页眉HTML
  custom_footer?: string        # 自定义页脚HTML
  watermark_text?: string       # 水印文字（如"草稿"）
```

### 4.3 分析结果数据结构

```yaml
AnalysisResult:
  description: >
    分析引擎的最终输出。包含评分、信号、完备性、交叉对比等信息。
    这是报告生成层的输入。

  # ── 标识 ──
  industry: string              # 行业名称
  company: string               # 企业名称
  analysis_date: datetime       # 分析日期
  engine_version: string        # 引擎版本号

  # ── 综合评分 ──
  scores:                       # 各层级评分
    L1_policy: float            # 政策环境（0-10）
    L2_technology: float        # 技术/竞争（0-10）
    L3_supply_chain: float      # 供应链（0-10）
    L4_financial: float         # 财务/偿债（0-10）
    track_b: float              # 市场定价（0-10，可选）

  composite_score: float        # 综合评分（0-10）
  rating: string                # 评级（AAA/AA/A/BBB/BB/B/CCC/D）
  outlook: string               # "positive" | "stable" | "negative" | "developing"
  veto_triggered: boolean       # 是否触发了否决条件
  veto_detail?: string          # 否决详情

  # ── 信号 ──
  signals: Signal[]             # 所有信号
  key_signals: Signal[]         # 关键信号（精选展示用，≤10条）

  # ── 完备性 ──
  completeness:
    density:
      L1_policy: number         # 信号密度 0-100%
      L2_technology: number
      L3_supply_chain: number
      L4_financial: number
      track_b: number
    overall_density: number     # 总信号密度
    confidence_level: string    # "high" | "medium" | "low"

  # ── 缺口 ──
  gaps: Gap[]
    Gap:
      dimension: string         # 缺口所在的维度
      missing_data: string      # 具体缺失的数据
      impact: string            # 对分析结论的影响
      substitute?: string       # 替代信号（如有）
      substitute_effectiveness: string  # "high" | "medium" | "low"

  # ── 交叉对比 ──
  cross_comparison:
    track_a_b_consensus: boolean
    track_a_score: float
    track_b_score: float
    quadrant: string            # "consensus_good" | "consensus_poor"
                                # | "divergence_market_panic"
                                # | "divergence_market_ignoring"
    divergence_analysis?: string

  # ── 利益相关者视角 ──
  stakeholder_views:
    credit_approval: string     # 信贷审批视角
    bond_investment?: string    # 债券投资视角（M1）
    bond_underwriting?: string  # 债券承销视角（M2）
    market_trading?: string     # 市场交易视角（M3）
    portfolio_risk?: string     # 组合风险视角（M4）
    corporate_finance?: string  # 企业融资视角（M5）

  # ── 一票否决 ──
  vetos:
    triggered: boolean
    items: VetoItem[]
      VetoItem:
        layer: string
        condition: string
        consequence: string
        evidence: string

  # ── 风险信号清单 ──
  risk_signals: RiskSignal[]
    RiskSignal:
      priority: "critical" | "high" | "medium" | "low"
      signal: Signal
      description: string
      recommended_action: string

  # ── 信贷建议（仅Type1包含）──
  credit_suggestion?:
    facility_amount: string
    term: string
    collateral: string
    conditions: string[]
    monitoring_focus: string[]
```

### 4.4 模板系统

```yaml
TemplateSystem:
  description: >
    报告模板基于 report-style-system.md §五 中定义的12种报告类型。
    每种类型对应一个HTML模板文件和一个Hero渐变配置。

  # ── 模板目录结构（已有设计）──
  directory: "design/templates/"
  files:
    base: "template-base.css"         # 14KB，所有类型共享的基础样式
    components: "components/components.css"  # 组件样式（未创建）
    types:
      - "template-type1.html"         # 单标的深度分析（当前缺失）
      - "template-type2.html"         # 双标的前瞻对比
      - "template-type3.html"         # 黑天鹅回溯验证
      - "template-type4.html"         # 多身份并行评估
      - "template-type5.html"         # 债券投资仪表盘
      - "template-type6.html"         # 马赛克完备性报告
      - "template-type7.html"         # 行业方法论页
      - "template-type8.html"         # 债项LGD评估
      - "template-type9.html"         # 外部支持专项评估
      - "template-type10.html"        # ESG+治理风险扫描
      - "template-type11.html"        # 压力测试报告
      - "template-type12.html"        # 引擎验证统计

  # ── 当前模板状态 ──
  template_status:
    template-base.css: "已创建"       # v1.0, 2026-07-08
    components.css: "未创建"          # 样式已定义在report-style-system.md §四
    template-type1.html: "未创建"     # 当前报告的HTML为手动编写
    template-type2.html: "已创建"
    template-type3.html: "已创建"
    template-type4.html: "已创建"
    template-type5.html: "已创建"
    template-type6.html: "已创建"
    template-type7.html: "已创建"
    template-type8.html: "已创建"
    template-type9.html: "已创建"
    template-type10.html: "已创建"
    template-type11.html: "已创建"
    template-type12.html: "已创建"

  # ── 渲染策略 ──
  rendering_strategy:
    method: "jinja2" | "mustache" | "ejs" | "string_replace"
    # 建议使用模板引擎（如Jinja2 for Python或模板字符串替换），
    # 将 AnalysisResult 的数据注入预定义的HTML模板。

    injection_points:
      # 模板中需要注入数据的标记点（以Mustache语法为例）：
      hero: >
        {{report_title}}
        {{industry}} · {{company}}
        {{analysis_date}}
        {{rating}} | {{composite_score}}
        {{outlook}}

      strip_items: >
        {{#strip_items}}
        {{label}}: {{value}}
        {{/strip_items}}

      pyramid_layers: >
        {{#layers}}
        {{name}}: {{score}}/10
        {{#signals}}
        - {{content}}
        {{/signals}}
        {{/layers}}

      completeness: >
        {{#completeness}}
        {{dimension}}: {{density}}%
        {{/completeness}}
```

### 4.5 渲染结果

```yaml
RenderResult:
  html: string                  # 渲染完成的HTML字符串
  file_path?: string            # 输出文件路径（如指定）
  file_size: int                # 文件大小（bytes）
  render_duration_ms: int       # 渲染耗时
  template_used: string         # 使用的模板ID
  included_sections: string[]   # 包含的章节列表
  warnings: string[]            # 渲染警告（如数据缺失导致的占位符）

  # 示例
  # file_size: 48500
  # render_duration_ms: 320
  # template_used: "type1"
  # included_sections: ["hero", "strip", "pyramid", "risk_signals", "credit_suggestion"]
  # warnings: ["市场定价数据缺失 → track_b区块留空"]
```

### 4.6 错误处理

```yaml
RenderError:
  type: "template_not_found" | "data_mismatch" | "css_load_failed"
        | "output_write_failed" | "data_incomplete"
  detail: string
  recoverable: boolean

  # 错误处理策略：
  # - template_not_found: 模板不存在 → 回退到type1模板
  # - data_mismatch: 数据字段与模板不匹配 → 跳过不匹配字段，记录警告
  # - css_load_failed: CSS文件无法加载 → 使用内联样式保底
  # - output_write_failed: 文件写入失败 → 返回HTML字符串
  # - data_incomplete: 数据不完整 → 渲染部分区块，标注"数据不足"
```

---

## 五、数据流时序

### 5.1 完整时序（同步视图）

```
用户输入(行业, 企业名称, 分析日期)
  │
  ├── [Step 1] 行业识别（已有）
  │     加载行业十维评分 → 确定行业类型 → 加载权重模板
  │     输入: (行业名称)
  │     输出: (行业类型, 权重模板, 分析框架配置)
  │     已有方法论文档支撑: analysis-engine-methodology.md §二
  │
  ├── [Step 2] 数据采集（新）
  │  ┌─ 并行─────────────────────────────────────┐
  │  │ A1. web_search_policy(industry)             │
  │  │     → 搜索策略关键词 → LLM解析 → PolicyDoc[] │
  │  │ A2. web_search_enterprise(company)           │
  │  │     → 多源聚合 → EnterpriseProfile            │
  │  │ A3. web_search_industry(industry)             │
  │  │     → 数据模板 → IndustryData[]               │
  │  │ A4. web_search_market(company)                │
  │  │     → 搜索 → MarketData[]                    │
  │  └─────────────────────────────────────────────┘
  │     输入: (行业, 企业)
  │     输出: RawData[] (聚合多源原始数据)
  │     当前状态: 纯空白
  │
  ├── [Step 3] 信号提取（新）
  │     extract_from_* → Signal[]
  │     输入: RawData[]
  │     输出: Signal[] (结构化信号)
  │     每条信号: {源, 时间, 维度, 方向, 强度, 置信度, 内容}
  │     当前状态: 纯空白
  │
  ├── [Step 4] 马赛克拼图（已有设计）
  │     信号叠加 → 交叉验证 → 信号密度计算 → 完备性评估
  │     输入: Signal[]
  │     输出: MosaicResult { 聚合信号, 信号密度, 缺口清单, 置信度 }
  │     已有方法论文档支撑: mosaic-engine.md §四-五
  │
  ├── [Step 5] 分析评分（已有设计）
  │     逐层评分 → 综合加权 → 评级映射 → 否决检查
  │     输入: MosaicResult + 行业权重模板
  │     输出: AnalysisResult { 评分, 评级, 展望, 风险信号, 信贷建议 }
  │     已有方法论文档支撑: analysis-engine-methodology.md §四-六
  │
  └── [Step 6] 报告生成（新）
        render(result, type1) → HTML文件
        输入: AnalysisResult + 模板ID
        输出: HTML文件（完整报告）
        模板已有: report-style-system.md
        渲染逻辑: 纯空白
```

### 5.2 异步并行视图

```
时间线 →
─────────────────────────────────────────────────────

Step 2 (数据采集)        ████████████████████░░░░  ~120s
  A1 web_search_policy   ████████░░░░░░░░░░░░░░░   ~30s
  A2 web_search_enterp.  ██████████████░░░░░░░░░░   ~60s
  A3 web_search_industry ████████░░░░░░░░░░░░░░░   ~30s
  A4 web_search_market   ████████░░░░░░░░░░░░░░░   ~30s

Step 3 (信号提取)        ░░░░████████████░░░░░░░░  ~60s
  LLM提取 × 4源类型     ░░░░████████████░░░░░░░░

Step 4 (马赛克拼图)      ░░░░░░░░████░░░░░░░░░░░░  ~15s
  信号叠加+交叉验证      ░░░░░░░░████░░░░░░░░░░░░

Step 5 (分析评分)        ░░░░░░░░░░████░░░░░░░░░░  ~15s
  评分+评级+否决         ░░░░░░░░░░████░░░░░░░░░░

Step 6 (报告生成)        ░░░░░░░░░░░░████████░░░░  ~30s
  HTML渲染+文件写入      ░░░░░░░░░░░░████████░░░░

总计: ~240s (4分钟)
```

### 5.3 缓存策略

```yaml
CacheStrategy:
  # ── 数据采集缓存（Input Adapter 内部）──
  data_cache:
    - key: "policy_{industry}_{date}"
      ttl: 86400       # 政策数据24小时
    - key: "industry_{industry}_{date}"
      ttl: 86400       # 行业数据24小时
    - key: "enterprise_{company}"
      ttl: 3600        # 企业数据1小时
    - key: "market_{company}"
      ttl: 300         # 市场数据5分钟

  # ── 信号提取缓存（Signal Extractor 内部）──
  signal_cache:
    - key: "signals_{source_hash}"
      ttl: 3600        # 同一源数据的信号提取结果缓存1小时

  # ── 报告缓存（Report Generator 内部）──
  report_cache:
    - key: "report_{company}_{analysis_date}_{template_type}"
      ttl: 3600        # 同一企业同日报告缓存1小时

  # ── 缓存失效条件 ──
  invalidation:
    - 用户主动刷新
    - 数据源返回"有新数据"
    - 分析起始日期变更
```

---

## 六、公开数据源清单

### 6.1 已验证可用的公开数据源

以下数据源已在POC阶段实测，覆盖六层数据架构：

```yaml
VerifiedPublicSources:
  # ═══════════════════════════════════════
  # L1 宏观政策
  # ═══════════════════════════════════════
  policy_sources:
    - name: "国务院"
      url: "https://www.gov.cn"
      type: "policy_document"
      coverage: "国务院令、国务院文件、政策解读"
      verified: true
      verified_case: "光伏出口退税取消公告"

    - name: "国家发改委"
      url: "https://www.ndrc.gov.cn"
      type: "policy_document"
      coverage: "产业政策、价格政策、投资审批"
      verified: true
      verified_case: "136号电价市场化文件"

    - name: "工业和信息化部"
      url: "https://www.miit.gov.cn"
      type: "policy_document"
      coverage: "行业管理、技术标准、产能调控"
      verified: true
      verified_case: "光伏行业规范条件"

    - name: "国家能源局"
      url: "https://www.nea.gov.cn"
      type: "policy_document"
      coverage: "绿电、电价、并网政策"
      verified: true
      verified_case: "688号绿电直连通知"

    - name: "财政部"
      url: "https://www.mof.gov.cn"
      type: "policy_document"
      coverage: "财政政策、出口退税"
      verified: true
      verified_case: "光伏出口退税取消公告"

    - name: "商务部"
      url: "https://www.mofcom.gov.cn"
      type: "policy_document"
      coverage: "贸易政策、反倾销"
      verified: true
      verified_case: "光伏贸易摩擦数据"

    - name: "人民银行"
      url: "https://www.pbc.gov.cn"
      type: "policy_document"
      coverage: "货币政策、LPR/MLF"
      verified: true
      verified_case: "公开市场操作数据"

  # ═══════════════════════════════════════
  # L2 行业数据
  # ═══════════════════════════════════════
  industry_sources:
    - name: "CPIA (中国光伏行业协会)"
      url: "https://www.chinapv.org.cn"
      type: "industry_statistics"
      coverage: "光伏产能产量、出口数据、市场份额"
      verified: true
      verified_case: "光伏行业2025年装机量数据"

    - name: "SEMI (国际半导体产业协会)"
      url: "https://www.semi.org"
      type: "industry_statistics"
      coverage: "半导体设备出货量、材料市场"
      verified: false
      note: "依赖公开报告搜索"

    - name: "CAAM (中国汽车工业协会)"
      url: "https://www.caam.org.cn"
      type: "industry_statistics"
      coverage: "汽车产销、新能源车数据"
      verified: false

    - name: "巨潮资讯网"
      url: "https://www.cninfo.com.cn"
      type: "public_company_filing"
      coverage: "上市公司年报/季报、募集说明书、公告"
      verified: true
      verified_case: "隆基绿能2025年年报数据提取"

  # ═══════════════════════════════════════
  # L3 产业链价格
  # ═══════════════════════════════════════
  pricing_sources:
    - name: "PVInfoLink"
      url: "https://www.pvinfolink.com"
      type: "price_index"
      coverage: "光伏产业链周度报价（免费版延迟1-2周）"
      verified: true
      verified_case: "TOPCon电池0.275元/W，周跌5.17%"

    - name: "TrendForce"
      url: "https://www.trendforce.com"
      type: "price_index"
      coverage: "存储芯片/面板价格"
      verified: false
      note: "免费版数据有限"

    - name: "SMM (上海有色网)"
      url: "https://www.smm.cn"
      type: "price_index"
      coverage: "金属/锂/钴/镍价格"
      verified: true
      verified_case: "硅料价格数据"

  # ═══════════════════════════════════════
  # L4 企业公开信息
  # ═══════════════════════════════════════
  enterprise_sources:
    - name: "国家企业信用信息公示系统"
      url: "https://www.gsxt.gov.cn"
      type: "enterprise_basic"
      coverage: "工商信息、股东、变更、行政处罚"
      verified: true
      verified_case: "一道新能工商信息查询"

    - name: "中国裁判文书网"
      url: "https://wenshu.court.gov.cn"
      type: "judicial_record"
      coverage: "诉讼、判决、裁定文书"
      verified: true
      verified_case: "光伏企业诉讼记录"

    - name: "中国执行信息公开网"
      url: "https://zxgk.court.gov.cn"
      type: "enforcement_record"
      coverage: "被执行人、失信被执行人、限制高消费"
      verified: true
      verified_case: "爱康科技被执行>5.8亿"

    - name: "全国企业破产重整案件信息网"
      url: "https://pccz.court.gov.cn"
      type: "bankruptcy_record"
      coverage: "破产申请、管理人指定、债权人会议"
      verified: true
      verified_case: "泉为科技预重整信息"

    - name: "巨潮资讯网"
      url: "https://www.cninfo.com.cn"
      type: "public_company_filing"
      coverage: "年报/季报、重大事项、募集说明书"
      verified: true

  # ═══════════════════════════════════════
  # L5 招投标
  # ═══════════════════════════════════════
  bidding_sources:
    - name: "央企电子采购平台"
      url: "各央企平台"
      type: "bidding_result"
      coverage: "华能/华电/国家电投/三峡/中核/中广核/国能/中煤等"
      verified: true
      verified_case: "三峡2026年集采10GW+，隆基入围50.3GW"

    - name: "中国招标投标公共服务平台"
      url: "https://www.cebpubservice.com"
      type: "bidding_result"
      coverage: "各类招标结果"
      verified: false

  # ═══════════════════════════════════════
  # L6 区域经济
  # ═══════════════════════════════════════
  regional_sources:
    - name: "各省市统计局"
      url: "各省市网站"
      type: "regional_economy"
      coverage: "区域GDP、产业结构、财政收支"
      verified: false

  # ═══════════════════════════════════════
  # 市场数据
  # ═══════════════════════════════════════
  market_sources:
    - name: "中国货币网"
      url: "https://www.chinamoney.com.cn"
      type: "bond_market_data"
      coverage: "债券发行利率、收益率曲线、信用利差"
      verified: true
      verified_case: "中债估值收益率曲线"

    - name: "上海证券交易所"
      url: "https://www.sse.com.cn"
      type: "exchange_data"
      coverage: "债券行情、交易量、公告"
      verified: true

    - name: "深圳证券交易所"
      url: "https://www.szse.cn"
      type: "exchange_data"
      coverage: "债券行情、交易量、公告"
      verified: true
```

### 6.2 数据源可达性速查表

| 行业 | 政策数据 | 企业风险 | 行业数据 | 招投标 | 市场数据 | 数据充裕度 |
|---|---|---|---|---|---|---|
| 光伏 | ✅ 高 | ✅ 高 | ✅ 高 | ✅ 高 | ✅ 中 | ★★★★★ |
| 半导体 | ✅ 高 | ✅ 中 | ✅ 中 | ⚠️ 低 | ✅ 中 | ★★★★ |
| 新能源车 | ✅ 高 | ✅ 高 | ✅ 高 | ⚠️ 低 | ✅ 高 | ★★★★ |
| 生物医药 | ✅ 中 | ✅ 中 | ✅ 中 | ⚠️ 低 | ✅ 中 | ★★★ |
| 高端装备 | ✅ 中 | ✅ 中 | ⚠️ 低 | ✅ 中 | ⚠️ 低 | ★★★ |
| 数据中心 | ✅ 中 | ⚠️ 低 | ⚠️ 低 | ⚠️ 低 | ✅ 高 | ★★ |
| 医疗器械 | ✅ 中 | ✅ 中 | ✅ 中 | ✅ 中 | ✅ 中 | ★★★★ |

> 注：以上速查表基于现有POC经验，部分行业尚未实际验证。标志为"⚠️ 低"不代表数据不存在，仅代表通过WebSearch获取的难度较高或数据密度较低。

---

## 七、优先级和依赖

### 7.1 组件优先矩阵

```yaml
PriorityMatrix:
  # ── P0：核心管道必须运转 ──
  P0:
    - component: "Input Adapter (Mode A)"
      description: "公开数据采集—至少实现A1(政策)+A2(企业)双源并行"
      depends_on: ["LLM搜索能力", "搜索关键词模板"]
      estimated_effort: "5-7天（含关键词模板工程）"
      validation: "对已有POC案例（隆基/一道新能）运行管道，输出与原手工搜索结果对比"
      current_status: "纯空白"

    - component: "Signal Extractor"
      description: "从采集数据中提取结构化信号"
      depends_on: ["Input Adapter (Mode A)"]
      estimated_effort: "3-5天（含LLM提示词体系）"
      validation: "对同一组原始数据，手工提取 vs 管道提取的信号对比"
      current_status: "纯空白"

  # ── P1：报告产出 ──
  P1:
    - component: "Report Generator (Type 1)"
      description: "单标的深度分析—最常用的报告类型"
      depends_on: ["Analysis Engine (已有)", "template-type1.html (未创建)"]
      estimated_effort: "3-4天（含模板创建+渲染逻辑）"
      validation: "输入已有分析结果，输出符合report-style-system.md Type 1规格的HTML"
      current_status: "模板未创建，渲染逻辑空白"

    - component: "Report Generator (Type 5 + Type 6)"
      description: "债券投资仪表盘 + 马赛克完备性报告"
      depends_on: ["Analysis Engine (已有)"]
      estimated_effort: "2-3天"
      current_status: "模板已创建，渲染逻辑空白"

  # ── P2：完整报告体系 ──
  P2:
    - component: "Report Generator (Type 2-4, 7-12)"
      description: "其余9种报告类型"
      depends_on: ["Report Generator (Type 1)"]
      estimated_effort: "5-7天（复用Type 1的渲染框架）"
      current_status: "模板已创建（除Type1），渲染逻辑空白"

    - component: "Input Adapter (Mode A3 + A4)"
      description: "新增行业数据+市场定价数据源"
      depends_on: ["Input Adapter (Mode A1+A2)"]
      estimated_effort: "2-3天"
      current_status: "纯空白"

  # ── P3：外部数据源 ──
  P3:
    - component: "Input Adapter (Mode B - CSV Upload)"
      description: "CSV/Excel上传适配器"
      depends_on: ["Signal Extractor (new → existing)", "Mosaic Engine (existing)"]
      estimated_effort: "3-5天"
      current_status: "接口已定义，无实现"

    - component: "Input Adapter (Mode B - REST API)"
      description: "Wind/Choice等金融终端API"
      depends_on: ["外部数据源接入许可"]
      estimated_effort: "5-8天"
      current_status: "接口已定义，无实现"

    - component: "Input Adapter (Mode B - MCP)"
      description: "MCP数据服务适配器"
      depends_on: ["MCP协议栈"]
      estimated_effort: "8-10天"
      current_status: "接口已定义，无实现"
```

### 7.2 依赖图（DAG）

```
P0 ─────────────────────────────────────────────────
  InputAdapter(Mode A1+A2)
       │
       ▼
  SignalExtractor
       │
       ▼
  MosaicEngine (已有) ──┬── AnalysisEngine (已有)
       │
       ▼
  [已有管道完成]

P1 ─────────────────────────────────────────────────
  AnalysisEngine (已有)
       │
       ▼
  ReportGenerator(Type1)


P2 ─────────────────────────────────────────────────
  InputAdapter(Mode A3+A4)         ReportGenerator(Type1)
       │                                  │
       ▼                                  ▼
  SignalExtractor(增强)          ReportGenerator(Type2-12)

P3 ─────────────────────────────────────────────────
  InputAdapter(Mode B)
       │
       ▼
  SignalExtractor(增强)
```

### 7.3 实施路径建议

```yaml
ImplementationPath:
  Phase1: "P0核心管道（2周）"
    steps:
      - "完成InputAdapter Mode A1(政策)+A2(企业)"
      - "完成SignalExtractor核心逻辑"
      - "连接已有MosaicEngine和AnalysisEngine"
      - "以隆基/一道新能为验证案例"

  Phase2: "P0报告产出（1周）"
    steps:
      - "创建template-type1.html"
      - "完成ReportGenerator Type1渲染逻辑"
      - "验证：已有分析结果 → 自动生成符合规范的HTML报告"

  Phase3: "P1-P2扩展（2周）"
    steps:
      - "InputAdapter扩展A3(行业)+A4(市场)"
      - "ReportGenerator扩展Type5+Type6"
      - "ReportGenerator扩展其余Type"

  Phase4: "P3外部数据源（视条件）"
    steps:
      - "实现CSV Upload适配器"
      - "实现REST API适配器（需Wind/Choice许可）"
```

---

## 八、错误处理与边界条件

### 8.1 全局错误分类

```yaml
ErrorClassification:
  # ── 输入层错误 ──
  input_errors:
    - error: "empty_company_name"
      handling: "返回验证错误：企业名称不能为空"
    - error: "invalid_industry"
      handling: "返回验证错误：未支持的行业"
    - error: "ambiguous_company_name"
      handling: "返回企业名称候选列表，要求用户确认"

  # ── 数据采集层错误 ──
  collection_errors:
    - error: "source_unreachable"
      handling: "标记该源为不可用，继续其他源"
    - error: "all_sources_failed"
      handling: "返回数据采集失败错误，建议用户检查网络或稍后重试"
    - error: "rate_limited"
      handling: "指数退避重试（最多3次），仍失败则跳过该源"
    - error: "timeout"
      handling: "单源超时30s → 跳过该源；整体超时120s → 使用已采集数据"

  # ── 信号提取层错误 ──
  extraction_errors:
    - error: "llm_failure"
      handling: "重试2次，失败后跳过该源"
    - error: "parse_failure"
      handling: "重试1次（添加格式约束），失败后跳过该源"
    - error: "empty_extraction"
      handling: "正常处理——记录'该源未提取到信号'"
    - error: "quality_check_failed"
      handling: "丢弃该信号，记录原因"

  # ── 分析引擎层错误（已有）──
  engine_errors:
    - error: "veto_triggered"
      handling: "终止分析，直接输出上限评级"
    - error: "insufficient_data"
      handling: "标注为'数据不足无法评分'，输出方向判断"
    - error: "score_out_of_range"
      handling: "截断到0-10范围"

  # ── 报告生成层错误 ──
  render_errors:
    - error: "template_not_found"
      handling: "回退到type1模板"
    - error: "data_mismatch"
      handling: "跳过不匹配字段，记录警告"
    - error: "output_write_failed"
      handling: "返回HTML字符串作为备用"
```

### 8.2 边界条件

```yaml
EdgeCases:
  # ── 企业维度 ──
  - scenario: "企业有多家同名公司"
    handling: "使用统一社会信用代码+注册地+注册时间进行消歧"
    fallback: "返回候选列表，要求用户选择"

  - scenario: "企业名称变更"
    handling: "搜索时同时使用新名称和曾用名"
    fallback: "仅使用当前注册名称"

  - scenario: "集团/母公司 vs 发债主体"
    handling: "明确区分分析主体（如'华晨汽车集团' vs '华晨中国'）"
    fallback: "标注分析主体范围"

  # ── 数据维度 ──
  - scenario: "数据时间不一致"
    handling: "每条信号标注发布时间，分析引擎使用加权时间轴"
    fallback: "对于无时间数据，标注为'时间未知'"

  - scenario: "数据完全为空"
    handling: "信号提取层返回空信号列表 → 马赛克引擎标注为'数据严重不足'"
    fallback: "综合评分基于可用信号"

  - scenario: "搜索结果为0"
    handling: "所有搜索策略返回空 → 标记为'公开数据覆盖不足'"
    fallback: "提示用户：该企业可能无公开信用数据"

  - scenario: "单一数据源返回大量结果"
    handling: "最多取前50条结果用于信号提取"
    fallback: "基于摘要信号密度采样"

  # ── 报告维度 ──
  - scenario: "评分等于边界值"
    handling: "优先归属较高区间（如7.50归为AA而非BBB）"
    fallback: "标注接近边界"

  - scenario: "不同维度信号矛盾"
    handling: "马赛克拼图层处理（mosaic-engine.md §四.1）"
    fallback: "标注为分歧信号，降低相关维度置信度"

  - scenario: "跨行业企业（集团）"
    handling: "按主营业务行业分类，附属业务在分析中标注"
    fallback: "使用主营业务对应的分析框架"
```

### 8.3 数据完备性分级响应

```yaml
DataCompletenessResponse:
  # 基于 mosaic-engine.md §五.4 的信号密度响应规则：
  
  density_gt_80:
    response: "高置信度"
    scoring: "直接输出精确评分"
    report_note: "无"

  density_50_to_80:
    response: "中置信度"
    scoring: "输出评分 ±1 区间"
    report_note: "标注'数据基础中等，评分存在±1误差区间'"

  density_20_to_50:
    response: "低置信度"
    scoring: "仅输出方向性判断（正面/负面/中性），不输出精确评分"
    report_note: "标注'信息不足，仅给出方向判断'，建议补充数据"

  density_lt_20:
    response: "无法评估"
    scoring: "不给出该维度评分"
    report_note: "标注'信息不足无法评估'，提示用户补充数据源"
```

---

## 九、附录：与现有设计文档的映射关系

### 9.1 本规范与已有文档的对应

| 本规范章节 | 对应已有文档 | 关系 |
|---|---|---|
| §一 总体架构 | `mosaic-engine.md` §二、`analysis-engine-methodology.md` §一 | 扩展已有架构，新增数据采集层和报告生成层 |
| §二 数据采集层 | `data-architecture.md` §二、`mosaic-engine.md` §六 | 将"手动验证"的数据源工程化为标准化接口 |
| §三 信号提取层 | `mosaic-engine.md` §三 | 将"信号数据结构定义"扩展为完整的提取接口 |
| §四 报告生成层 | `report-style-system.md` §一-六 | 将"设计规格"中的模板规格转化为渲染接口 |
| §五 数据流时序 | `analysis-engine-methodology.md` §五.1 | 从单步骤扩展为完整的管道时序 |
| §六 公开数据源清单 | `data-architecture.md` §二、`analysis-engine-methodology.md` §三 | 基于已有POC验证数据整理 |
| §七 优先级和依赖 | `mosaic-engine.md` §八、`2026-07-08-full-chain-design-plan.md` §二-四 | 衔接已有优先级体系 |

### 9.2 当前实现状态总览

```
Legend:
  ▓ 已有完整设计（方法论文档）
  ▒ 部分完成（接口已定义/模板已创建）
  ░ 纯空白（需从零开发）

组件                          状态    上下文
──────────────────────────────────────────────────
行业分类（十维评分）           ▓▓▓▓▓  analysis-engine-methodology.md §二
行业金字塔权重模板             ▓▓▓▓▓  industry-pyramids.md
轨道A：基本面分析              ▓▓▓▓▓  analysis-engine-methodology.md §四
轨道B：市场定价                ▓▓▓▓▓  mosaic-engine.md, dual-track-methodology.md
交叉对撞（四象限）            ▓▓▓▓▓  dual-track-methodology.md
一票否决条件库                 ▓▓▓▓▓  analysis-engine-methodology.md §六
马赛克拼图层（信号叠加/交叉）  ▓▓▓▓▓  mosaic-engine.md §四
马赛克完备性评估层             ▓▓▓▓▓  mosaic-engine.md §五
数据缺口→风险映射              ▓▓▓▓▓  mosaic-engine.md §五.2
Mode B接口契约                 ▓▓▓▓▓  mosaic-engine.md §六, data-architecture.md §六
模板基础CSS                    ▓▓▓▓  report-style-system.md, template-base.css
报告模板（Type2-12）          ▓▓▓▓  report-style-system.md, template-type*.html
报告模板（Type1）             ░░░░░  未创建
──────────────────────────────────────────────────
Input Adapter（数据采集）      ░░░░░  本规范 §二
Signal Extractor（信号提取）   ░░░░░  本规范 §三
Report Generator（报告渲染）  ░░░░░  本规范 §四
LLM提示词体系                 ░░░░░  本规范 §三.4（框架层定义）
搜索关键词模板                ░░░░░  本规范 §二.4（框架层定义）
```

### 9.3 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-07-09 | 初始草稿：定义Input Adapter/Signal Extractor/Report Generator三层的标准化接口，整理数据源清单，标注优先级和依赖关系 |

---

*本文档定义了固收信用分析引擎Mode A马赛克引擎的数据管道接口规范。各层接口的详细实现需对应开发独立的技术设计文档。*

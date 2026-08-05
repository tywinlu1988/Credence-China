# Credence 报告模板导航

> 本目录是报告模板的**单一事实源**（`template-base.css` + Type 1–19，共 17 份（Type 9/12 已归档至 archive/）+ 1 份共享样式）。
> 路径 → 模板映射以 `dev/engine/work-path-registry.md` 的 `templates` 字段为唯一权威；本页只做导航与契约说明，不复制模板内容。

## 模板总表

| Type | 名称/用途 | 适用工作路径 | 文件 |
|---|---|---|---|
| 1 | L2 深度信用报告（主模板） | WP-M0-01 信贷审批单标的评级 | [template-type1.html](template-type1.html) |
| 2 | 双标的前瞻对比 | WP-M1-02 双标的前瞻对比 | [template-type2.html](template-type2.html) |
| 3 | 黑天鹅回溯验证 | WP-X-01 黑天鹅回溯验证 | [template-type3.html](template-type3.html) |
| 4 | 多身份并行评估 | WP-X-02 多身份并行评估 | [template-type4.html](template-type4.html) |
| 5 | 债券投资仪表盘 | WP-M1-01 债券投资仪表盘 | [template-type5.html](template-type5.html) |
| 6 | 马赛克完备性报告 | WP-M0-01（配套） | [template-type6.html](template-type6.html) |
| 7 | 行业分析框架建设 | WP-X-03 行业分析框架建设 | [template-type7.html](template-type7.html) |
| 8 | 审贷专项附加包（LGD+外部支持） | WP-M0-02 审贷专项附加包 | [template-type8.html](template-type8.html) |
| 10 | ESG/治理风险扫描 | WP-X-04 ESG/治理风险扫描 | [template-type10.html](template-type10.html) |
| 11 | 组合压力测试 | WP-M4-04 组合压力测试 | [template-type11.html](template-type11.html) |
| 13 | 跨行业传染分析 | WP-M4-02 跨行业传染分析 | [template-type13.html](template-type13.html) |
| 14 | 组合集中度评估 | WP-M4-01 组合集中度评估 | [template-type14.html](template-type14.html) |
| 15 | 系统性风险警报 | WP-M4-03 系统性风险读数 | [template-type15.html](template-type15.html) |
| 16 | 承销可行性报告 | WP-M2-01 承销可行性评估 | [template-type16.html](template-type16.html) |
| 17 | 融资顾问报告 | WP-M5-01 企业融资顾问 | [template-type17.html](template-type17.html) |
| 18 | 展望与持续监控 | WP-X-05 展望与持续监控 | [template-type18.html](template-type18.html) |
| 19 | L0 交易盯市信号卡 | WP-M3-01 交易盯市信号卡 | [template-type19.html](template-type19.html) |

## 模板契约（自制/填充前必读）

1. **模板自包含（CSS 构建期注入）**：dev 源模板首段为 `<!-- @inject-css: template-base.css -->` 标记，`scripts/build_dist.py` 装配发行包时注入 `template-base.css` 全文——修改基础样式只改这一个文件，无需同步任何模板。发行包内模板完全自包含，禁止外部 `<link>` 引用样式。
2. **戳记不可删**：文件头注释 `<!-- @template: dev/templates/template-typeN.html -->` 与 `<!-- @engine-version: vX.Y.Z-release -->`（晋升时由 promote.py 统一改写，勿手改）。
3. **三段式结构**：`hero`（类型徽章+标题+主体/评级/日期）→ 编号 `<section>` 内容区 → `<footer>`（报告编号 + 版本 + 生成日期 + "仅供内部风险评估使用 / 不构成投资建议"两行）。
4. **占位符约定**：全角花括号 `{占位名}`（如 `{主体名称}`、`{当前评级}`），填充时整体替换，保留未覆盖项为占位符原文，不得改写为半角或删减。
5. **内容区卡片样式**：沿用模板自带 class（如 `signal-card`/`metric-box`），新增小节复用既有 class，不引入新色系。
6. **防幻觉铁律**：模板一律不含真实/示例项目数据；装配时无对应数据的占位符必须保留为 `{占位符}` 或显式标注"数据缺口"，禁止以模板自带示例值顶替——数据缺口按引擎纪律即风险信号处理。（方法论案例库引用除外：永煤/紫光等历史回测案例仅可出现在"案例库/回测"标题语境中。）

## 防崩指南（常见错误）

- ❌ 交付报告含外部 `<link>` 样式引用 → 转发后格式崩溃；✅ 报告完全自包含，CSS 已内联。
- ❌ 删除/覆盖内联 base.css `<style>` 块 → 样式基线丢失；✅ 追加样式在同一 `<style>` 块之后或模板自有 `<style>` 块内。
- ❌ 删除/修改头部戳记 → 版本追踪失效（consistency 门会拦）。
- ❌ 占位符改半角 `{}` 或翻译占位名 → 装配映射失配。
- ❌ footer 缺版本/日期/免责声明行 → 不合规交付。
- ❌ 节标题跳级（h2 直接跳 h4）或乱改节序 → 报告结构失真。

## 如何选择模板

- **按工作路径选（默认）**：先确定 path_id，按注册表 `templates` 字段取（上表已列映射）。
- **按报告形态选**：深度叙事（Type 1/2/4/5/7/8/11）、专项卡片/警报（Type 13/14/15/18/19）、验证留档（Type 3）、附加模块（Type 6/10）。

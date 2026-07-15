# 报告风格与布局系统 · 设计规格

**版本**: v1.0
**日期**: 2026-07-08
**状态**: 设计审批中

---

## 一、色彩体系

### 基础色板（所有报告通用）

```css
:root {
  /* 背景层 */
  --bg-primary:    #0f1117;
  --bg-secondary:  #1a1d28;
  --bg-tertiary:   #212433;
  --bg-hover:      #252b38;

  /* 文字层 */
  --text-primary:   #e2e4ea;
  --text-secondary: #9398a9;
  --text-tertiary:  #5d6270;

  /* 边框层 */
  --border-default: #2a2e3c;
  --border-strong:  #3d4250;
}
```

### 语义色板（所有报告通用）

```css
  /* 红：风险/警告/下跌/否决 */
  --red:       #ef4444;
  --red-bg:    rgba(239,68,68,0.08);

  /* 琥珀：关注/待定/波动/缓和 */
  --amber:     #f59e0b;
  --amber-bg:  rgba(245,158,11,0.08);

  /* 绿：安全/通过/上涨/正面 */
  --green:     #22c55e;
  --green-bg:  rgba(34,197,94,0.08);

  /* 蓝：信息/链接/中性/数据 */
  --blue:      #6366f1;
  --blue-bg:   rgba(99,102,241,0.08);

  /* 紫：方法论/元分析/系统/版本 */
  --purple:    #a855f7;
  --purple-bg: rgba(168,85,247,0.08);
```

### 使用规则

| 颜色 | 文本着色 | 背景着色 | 色条/边框 | 禁止使用 |
|---|---|---|---|---|
| 红 | `.text-red` | `.bg-red` | `.border-red` | 装饰性大面积使用 |
| 琥珀 | `.text-amber` | `.bg-amber` | `.border-amber` | 标题（易与红混淆） |
| 绿 | `.text-green` | `.bg-green` | `.border-green` | 警告/风险标注 |
| 蓝 | `.text-blue` | `.bg-blue` | `.border-blue` | 正面/负面信号 |
| 紫 | `.text-purple` | `.bg-purple` | `.border-purple` | 数据展示 |

---

## 二、字体与排版

### 字体栈

```css
--font-body: -apple-system, BlinkMacSystemFont, "Segoe UI",
             "PingFang SC", "Microsoft YaHei", sans-serif;
--font-mono: "SF Mono", "Cascadia Code", "Consolas", monospace;
```

### 字号层级（16px根）

| 级别 | 选择器 | 字号 | 粗细 | 用途 |
|---|---|---|---|---|
| H1 | `.report-title` | 30px | 800 | 页面主标题 |
| H2 | `.section-title` | 19px | 700 | 区块标题 |
| H3 | `.card-title` | 15px | 600 | 卡片内标题 |
| H4 | `.sub-title` | 14px | 600 | 子标题 |
| Body | `body, p, li` | 14px | 400 | 正文 |
| Caption | `.caption` | 12px | 400 | 辅助说明 |
| Micro | `.micro` | 10px | 400 | 脚注/水印 |
| Table Head | `thead th` | 11px | 600 | 表头 |
| Table Body | `tbody td` | 13px | 400 | 表体 |
| Num Large | `.num-lg` | 26px | 800 | 评分/金额 |
| Num XLarge | `.num-xl` | 36px | 800 | 核心结论数字 |

### 排版规则

- 行高：body 1.6、长文本 1.8、heading 1.3
- 段间距：1em
- 容器最大宽度：960px（页级）
- 全局padding：24px（桌面）/ 16px（移动端）
- 数字列右对齐，文本列左对齐

---

## 三、布局骨架

```
┌──────────────────────────────────────────────┐
│  HERO 区（全宽，渐变背景）                      │
│  .hero                                          │
│  ├── .hero-chip  类型标签（圆角chip）            │
│  ├── h1          主标题                          │
│  ├── p           副标题/说明                     │
│  └── .hero-meta  元信息标签行                    │
├──────────────────────────────────────────────┤
│  CONTENT 区（居中 max-width: 960px）            │
│  .container                                     │
│  ├── .strip      顶栏数字条（4-6列）             │
│  ├── .section    内容区块                        │
│  │   ├── .section-title  区块标题                │
│  │   ├── .card    卡片组件                       │
│  │   ├── table    表格组件                       │
│  │   ├── .metric-grid  指标网格（2-4列）          │
│  │   └── .timeline    时间线组件                  │
│  └── ...                                        │
├──────────────────────────────────────────────┤
│  FOOTER（全宽，单线分割）                        │
│  .footer                                        │
└──────────────────────────────────────────────┘
```

### 响应式断点

| 断点 | 调整 |
|---|---|
| ≤768px | 网格降为1列 · Hero标题24px · strip降为2列 · 全局padding 16px |
| ≤480px | strip降为1列 · 字号等比缩小10% · 表格横向滚动 |

---

## 四、组件库

### 4.1 Card

```css
.card {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 20px 24px;
  border: 1px solid var(--border-default);
}
.card-red   { border-left: 4px solid var(--red); }
.card-amber { border-left: 4px solid var(--amber); }
.card-green { border-left: 4px solid var(--green); }
.card-blue  { border-left: 4px solid var(--blue); }
.card-purple{ border-left: 4px solid var(--purple); }
```

### 4.2 Strip（顶栏数字条）

```css
.strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);  /* 或2/3/5/6列 */
  gap: 1px;
  background: var(--border-default);
  border-radius: 10px;
  overflow: hidden;
}
.strip-item {
  background: var(--bg-secondary);
  padding: 20px 16px;
  text-align: center;
}
```

### 4.3 Table

```css
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--bg-secondary);
  border-radius: 6px;
  overflow: hidden;
}
thead th {
  background: var(--bg-tertiary);
  padding: 9px 13px;
  font-weight: 600;
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 2px solid var(--border-default);
}
tbody td {
  padding: 9px 13px;
  border-bottom: 1px solid var(--border-default);
}
tbody tr:hover { background: var(--bg-hover); }
```

### 4.4 Metric Grid

```css
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.metric {
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 16px 18px;
  text-align: center;
  border: 1px solid var(--border-default);
}
.metric .m-num  { font-size: 28px; font-weight: 800; }
.metric .m-label{ font-size: 12px; color: var(--text-secondary); }
```

### 4.5 Timeline

```css
.timeline {
  position: relative;
  padding-left: 28px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 4px; bottom: 4px;
  width: 2px;
  background: var(--border-default);
}
.timeline-item {
  position: relative;
  padding: 10px 0 10px 20px;
  font-size: 13px;
}
.timeline-item::before {
  content: '';
  position: absolute;
  left: -20px; top: 14px;
  width: 12px; height: 12px;
  border-radius: 50%;
}
.timeline-item.red::before   { background: var(--red); }
.timeline-item.amber::before { background: var(--amber); }
.timeline-item.green::before { background: var(--green); }
```

### 4.6 评分配色

| 分值区间 | 颜色 | 类名 |
|---|---|---|
| ≥7.5 | 绿 | `.score-good` |
| 5.0-7.4 | 蓝 | `.score-ok` |
| 3.0-4.9 | 琥珀 | `.score-warn` |
| <3.0 | 红 | `.score-bad` |

### 4.7 信号指示灯

```css
.signal { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.signal-red   { background: var(--red); }
.signal-amber { background: var(--amber); }
.signal-green { background: var(--green); }
```

### 4.8 Tab导航（多行业总览页专用）

```css
.tab-bar {
  display: flex;
  gap: 0;
  overflow-x: auto;
  border-bottom: 1px solid var(--border-default);
}
.tab-label {
  flex-shrink: 0;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.tab-label.active {
  color: var(--blue);
  border-bottom-color: var(--blue);
}
```

---

## 五、12种报告类型

| # | 类型 | Hero渐变方向 | 典型Strip列数 | 核心组件 |
|---|---|---|---|---|
| 1 | 单标的深度分析 | 135deg, #0f172a, #1e3a5f | 4列 | 金字塔+交叉对撞+风险清单+完备性 |
| 2 | 双标的前瞻对比 | 135deg, #0f172a, #1e3a5f, #065f46 | 2×4列 | 逐层对比表+分差分析+框架改进 |
| 3 | 黑天鹅回溯验证 | 135deg, #0f172a, #4a1a1a, #7c2d12 | 4列 | 时间线+双时点+叙事拆解+评级分析 |
| 4 | 多身份并行评估 | 135deg, #0f172a, #1e3a5f, #4a1a1a | 3列 | 身份卡片+交叉矩阵+共识分歧 |
| 5 | 债券投资仪表盘 | 135deg, #0f172a, #1e3a5f, #1a3a2a | 4列 | 四维分析+排名表+事件日历+缺口 |
| 6 | 马赛克完备性报告 | 135deg, #0f172a, #312e81 | 4列 | 信号密度条+信号清单+缺口映射 |
| 7 | 行业方法论页 | 135deg, #0f172a, #1e3a5f, #312e81 | 6列 | 金字塔图+指标清单+一票否决+同业对标 |
| 8 | 债项LGD评估 | 135deg, #0f172a, #5b21b6 | 5列 | LGD分级+抵押物估值+回收路径 |
| 9 | 外部支持专项评估 | 135deg, #0f172a, #0e7490 | 4列 | 支持能力vs意愿+上调规则+陷阱信号 |
| 10 | ESG+治理风险扫描 | 135deg, #0f172a, #065f46 | 4列 | E/S/G三维+欺诈信号+操作风险 |
| 11 | 压力测试报告 | 135deg, #0f172a, #991b1b | 4列 | Severe场景+临界点+二阶效应 |
| 12 | 引擎验证统计 | 135deg, #0f172a, #6366f1 | 6列 | 混淆矩阵+FNR/FPR+迁移矩阵+置信度 |

---

## 六、代码组织

> v0.7.1 起，模板作为单一事实源集中存放于顶层 `dev/templates/`；`design/` 仅保留本设计规格。

```
dev/
├── design/
│   └── report-style-system.md   ← 本文件（设计规格）
└── templates/                   ← 模板单一事实源（v0.7.1 起）
    ├── template-base.css        基础色板+字体+布局（15种类型共享）
    ├── template-type1.html      单标的深度分析
    ├── template-type2.html      双标的前瞻对比
    ├── template-type3.html      黑天鹅回溯验证
    ├── template-type4.html      多身份并行评估
    ├── template-type5.html      债券投资仪表盘
    ├── template-type6.html      马赛克完备性报告
    ├── template-type7.html      行业方法论页
    ├── template-type8.html      债项LGD评估
    ├── template-type9.html      外部支持专项评估
    ├── template-type10.html     ESG+治理风险扫描
    ├── template-type11.html     压力测试报告
    ├── template-type12.html     引擎验证统计
    ├── template-type13.html     传染分析报告
    ├── template-type14.html     组合集中度报告
    └── template-type15.html     系统性风险警报
```

### 文件使用方式

- `template-base.css` 被各模板引用（`<link rel="stylesheet">`，同目录相对路径 `template-base.css`）
- 每个 `.html` 模板仅包含：特定于此类型的Hero渐变+Strip列数调整+特定内容结构
- 实例报告位于 `dev/reports/<子目录>/`，通过 `../../templates/template-base.css` 引用样式
- 语义色变量和字体变量继承自 `template-base.css`

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-08 | 初始设计：色彩体系、字体排版、布局骨架、6组件、12报告类型 |
| v1.1 | 2026-07-15 | 代码组织章节同步 v0.7.1 结构：模板迁至 `dev/templates/`（15 种类型），移除不存在的 components/ 目录 |

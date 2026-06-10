# 智能投资评分 / 定投系统 — 项目总计划

> 本文档汇总前期讨论结论，作为开发与验收的单一事实来源（SSOT）。

---

## 1. 项目目标

构建一套 **Python** 驱动的投资分析系统，实现：

1. **多市场综合评分（S）**：纳斯达克100（重点）、标普500、日经225、德国 DAX、国内主动基金；指标可开关、按市场差异化。
2. **智能定投建议**：用户输入计划金额 P，根据 S 与激进倍数（1.5× / 2.0×）输出实际建议金额，并支持现金池与平滑。
3. **数据管道**：免费 API 为主，稳定拉取 → 校验 → 入库；技术指标由库内重算，保证可复现。
4. **AI 解读**：DeepSeek Pro，**仅中文解读**，不篡改系统计算的 S 与定投金额。
5. **专业界面**：现代 Web UI，仪表盘、评分、定投、回测、配置管理。

---

## 2. 需求摘要（来自讨论）

### 2.1 标的与市场

| 优先级 | 标的 | 资产类型 | 说明 |
|--------|------|----------|------|
| P0 | 纳斯达克100 | 美国成长指数 | 重点；代理 QQQ / ^NDX |
| P0 | 标普500 | 美国宽基 | 与纳指共用 `index_us` 模板，权重微调 |
| P1 | 日经225 | 日本指数 | `index_jp`；汇率、日股估值 |
| P1 | 德国 DAX | 欧洲指数 | `index_de`；VDAX、欧元 |
| P2 | 国内主动基金 | 公募基金 | `cn_active_fund`；净值、超额、回撤、申购状态 |

每个标的一套 **`InstrumentProfile`**（行情源、日历、指标集、维度权重、采集 cron）。

### 2.2 评估指标

- **维度统一**：趋势 | 动量 | 波动/情绪 | 估值 | 宏观 | （广度可选）| 基金质量/执行
- **来源分三类**：
  - **爬/API 入库**：OHLCV、净值、VIX、VDAX、美债、汇率、指数 PE-TTM、基金申购状态
  - **库内计算**：MA、RSI、MACD、回撤、波动率、PE 历史分位、基金超额/夏普/最大回撤
  - **AI**：自然语言报告（输入结构化分数，输出 schema 校验后的中文）

详见 `config/metric_catalog.yaml`。

### 2.3 定投

| 配置项 | 选项 |
|--------|------|
| 频率 | 每天、每周、双周、每月、每两月 |
| 计划金额 | 用户输入 P（如 500） |
| 激进倍数 M | **1.5** 或 **2.0**（低估时最大加仓倍数） |
| 低估下限 | 默认 0.4×P（如 200）；高估侧随 S 升高而减少 |
| 平滑 | 相邻定投日建议变化 ≤30%（可配置） |
| 现金池 | 少投累积，低估日优先投出 |

**评分 S**：0–100，越高越偏贵/偏热/偏谨慎。定投仅在 **定投日** 生成正式建议；非定投日可预览。

### 2.4 数据采集频率（准确性优先）

| 数据 | 策略 |
|------|------|
| 美股/欧日指数日线 | 每交易日 **1 次 official**（北京时间清晨主任务 + 失败重试） |
| 国内基金净值 | **22:30 partial** + **次日 02:00 official** 补全 |
| 宏观/估值（VIX、10Y、PE） | 每交易日 1 次，与行情任务捆绑 |
| 基金档案/申购 | 每周 + 每个定投日前校验 |
| 技术指标 | 爬数成功后 **批处理重算**，不单独爬 |

写入策略：`provisional` 不覆盖 `official`；异常跳变拒绝入库并告警。

### 2.5 AI

- 模型：**DeepSeek Pro**（具体 model id 以控制台为准，如 `deepseek-chat`）
- 语言：仅中文
- 职责：解读 S、维度驱动因素、风险与注意事项；**禁止**模型直接决定定投数字

---

## 3. 技术栈（拟定）

| 层级 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 生态成熟 |
| Web API | FastAPI | 类型友好、OpenAPI |
| 前端 | **Next.js 14 + Tailwind + shadcn/ui** | 专业仪表盘观感 |
| 图表 | ECharts 或 Lightweight Charts | K 线、评分历史、回测曲线 |
| 数据库 | PostgreSQL（生产）/ SQLite（本地 MVP） | 关系型 + 时序友好 |
| ORM | SQLAlchemy 2 + Alembic | 迁移 |
| 任务调度 | APScheduler（MVP）→ Celery + Redis（扩展） |
| 行情/宏观 | yfinance、FRED、东方财富 JSON、Tushare 免费档 | 见 DATA_SOURCES.md |
| 指标计算 | pandas, pandas-ta | 可复现 |
| AI | DeepSeek HTTP API | 中文解读 |
| 部署 | Docker Compose | 一键本地/小服务器 |

---

## 4. 系统模块

```
invest/
├── config/              # YAML：标的、指标、权重、DCA
├── data/
│   ├── providers/       # 各免费 API 适配器
│   ├── validators/      # 入库校验
│   └── repository/      # DB 读写
├── core/
│   ├── calendar.py      # 各市场交易日、定投日判定
│   ├── indicators.py    # 由 OHLCV/净值计算
│   ├── scoring.py       # 维度分 → S
│   └── dca.py           # f(S), M, 平滑, 现金池
├── jobs/                # 定时：爬取 → 指标 → 评分 → 定投日 AI
├── ai/                  # DeepSeek + prompt + schema
├── api/                 # FastAPI 路由
└── web/                 # Next.js 前端
```

数据流：

```
免费 API → 校验 → DB(原始) → 计算指标 → DB(指标) → S → DB(评分)
                                              ↓
                                    定投日 → 建议金额 → DeepSeek 报告 → DB + UI
```

---

## 5. 分期与里程碑

### M0 — 规划与草案（当前）✓

- [x] 总计划、架构、数据源、UI 规范
- [x] `instruments.yaml`、`metric_catalog.yaml`、权重与 DCA 草案

### M1 — 数据基础（约 2 周）

- [x] DB Schema（ohlcv, macro, valuation, fund_nav, indicators, scores, crawl_audit）
- [x] yfinance：QQQ、^GSPC、^N225、^GDAXI、^VIX、汇率
- [x] FRED：US10Y、DXY（需 `FRED_API_KEY`）
- [x] 校验 + official 写入
- [x] CLI：`python -m invest.jobs.daily_crawl`
- [ ] APScheduler 定时（可选，M1 末尾）

### M2 — 评分引擎（约 1.5 周）

- [x] `metric_catalog` 驱动指标计算
- [x] 纳指 + 标普 scoring（`index_us`）
- [x] 单元测试：指标与评分
- [x] Docker Python 3.12 + `recompute_scores` / `pipeline` CLI

### M3 — 定投 + 回测（约 1.5 周）

- [x] 五档频率、M=1.5/2.0、f(S) 与平滑、现金池
- [x] 固定 P vs 动态定投回测 API
- [x] FastAPI 基础路由
- [x] 修复 score 宏观序列读取 bug

### M4 — 日经 + DAX（约 1 周）

- [ ] `index_jp` / `index_de` Profile
- [ ] 汇率、VDAX（或 ATR 降级）

### M5 — 国内主动基金（约 2 周）

- [ ] 净值双次采集、申购状态
- [ ] 相对基准超额、回撤、夏普
- [ ] 可选：沪深300 PE 作环境分

### M6 — AI + 专业 UI（约 2 周）

- [ ] DeepSeek 中文报告 + JSON schema
- [x] Next.js 仪表盘 MVP：总览、标的详情、定投、回测、设置
- [x] 深色主题、响应式侧栏/底栏
- [ ] 定投日历、AI 报告页

### M7 — 加固（持续）

- [ ] 双源比对、监控告警、配置热更新
- [ ] PE 源升级路径（付费 API 可选）

---

## 6. 验收标准（摘要）

| 项 | 标准 |
|----|------|
| 数据 | 每标的每个交易日至多一条 `official` 日线/净值；失败有重试与 stale 标记 |
| 评分 | 同输入数据重复计算 S 一致；维度可开关 |
| 定投 | P=500、M=2、S=0 时建议≈1000；S=100 时建议≈200（在配置范围内） |
| AI | 输出含 summary/risk_level/drivers；失败降级为无 AI 模板 |
| UI | 首屏展示最新 S、建议定投、数据 as-of；移动端可用 |

---

## 7. 风险与合规

- 所有页面与报告固定 **免责声明**
- API Key 仅环境变量；日志脱敏
- 爬虫遵守 robots、限速（≥1s/请求）
- 不承诺收益；回测标注假设（费率、滑点）

---

## 8. 相关文件

- 架构细节 → [ARCHITECTURE.md](./ARCHITECTURE.md)
- 数据源 → [DATA_SOURCES.md](./DATA_SOURCES.md)
- 界面 → [UI_DESIGN.md](./UI_DESIGN.md)
- 配置草案 → `../config/`

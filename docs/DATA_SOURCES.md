# 免费数据源方案（稳定性优先）

> 原则：**行情/宏观用成熟 API；估值用单一主源 + 可选备用；国内基金用公开 JSON 接口并双源校验；技术指标一律库内重算。**

---

## 1. 数据源总表

| 数据 | 主源（免费） | 备用 | 频率 | 备注 |
|------|--------------|------|------|------|
| 美股/ETF OHLCV | **yfinance** | Stooq（可选） | 1×/交易日 | QQQ, ^GSPC, ^VIX |
| 日经 / DAX | **yfinance** | — | 1×/交易日 | ^N225, ^GDAXI |
| VIX | yfinance `^VIX` | FRED `VIXCLS` | 1×/交易日 | 二选一主源即可 |
| 美债10Y | **FRED** `DGS10` | yfinance `^TNX` 近似 | 1×/交易日 | 需免费 API Key |
| 美元指数 | FRED `DTWEXBGS` 或 yfinance `DX-Y.NYB` | — | 1×/交易日 | |
| USD/JPY | yfinance `JPY=X` | — | 1×/交易日 | 日经宏观 |
| EUR/USD | yfinance `EURUSD=X` | — | 1×/交易日 | DAX 宏观 |
| VDAX | yfinance 或爬取（见下） | **ATR 实现波动** 降级 | 1×/交易日 | 无稳定免费流时用 ATR |
| 指数 PE-TTM | **见 §2** | 价格5年分位 | 1×/交易日 | 估值维降级策略 |
| 国内基金净值（含 QDII） | **东方财富 f10/lsjz**（每页 20 条） | pingzhongdata.js | 手动/定时 | pageSize>20 会返回空；概况 404 时走备用 |
| 基金经理 ID / 档案 | **FundMNMangerList** + **FundMSNMangerInfo**（fundmobapi） | — | 录入解析 + 爬取时 | 需 `manager_ids`；档案缓存表 `fund_manager_profiles` |
| 基金申购状态 | 东方财富 / 天天基金 | — | 周 + 定投日前 | |
| 沪深300 PE（环境分） | **Tushare 免费** | 中证/爬取 | 1×/日 | 需注册 token |
| 国内指数行情 | Tushare / yfinance | — | 1×/日 | 基准用 000300.SH |

---

## 2. 估值数据（PE-TTM）免费策略

指数 PE 无法从 OHLCV 推导，免费方案按优先级：

### 方案 A（推荐 MVP）：价格分位 + 盈利收益率 proxy

- **不爬 PE**，估值维用：
  - `price_percentile_5y`（库内算）
  - 可选 `cape` / Shiller 数据（FRED 或 multpl，更新慢）
- UI 标注：「估值维度基于价格历史分位，非财报 PE」

### 方案 B：爬取稳定网页序列（需维护）

| 指数 | 来源示例 | 风险 |
|------|----------|------|
| 标普500 | multpl.com/shiller-pe | 页面结构变更 |
| 纳斯达克 | 部分财经站指数估值页 | 需维护 parser |
| 日经 | 日经指数公司 / 财经 API | 英文/日文页面 |

**入库**：`valuation_series`；**分位数在库内算**。

### 方案 C：Tushare 免费档（国内环境友好）

- `index_dailybasic` 等接口可拿 A 股指数 PE；对 **沪深300 环境分** 很实用
- 美股指数 PE 覆盖有限，仍建议方案 A + 后期付费 Wind

**项目默认**：M1–M2 用 **方案 A**；M4 起为标普/纳指尝试 **方案 B 单一主源**；国内基金环境分用 **Tushare 沪深300 PE**。

---

## 3. Provider 适配器约定

```text
providers/
  base.py          # fetch(series_id, start, end) -> DataFrame
  yfinance_provider.py
  fred_provider.py
  eastmoney_fund.py
  tushare_provider.py   # 可选，环境变量 TUSHARE_TOKEN
```

统一返回列：`trade_date, value, source, raw_meta`

重试：3 次，间隔 20s；超时 30s；User-Agent 固定。

---

## 4. 校验规则（入库前）

```python
# 伪代码
def validate_ohlcv(row):
    assert row.low <= row.open <= row.high
    assert row.low <= row.close <= row.high
    assert row.volume >= 0

def validate_jump(prev_close, close, threshold=0.15):
    if abs(close/prev_close - 1) > threshold:
        raise ValidationError("abnormal jump")

def should_write(new_status, existing_status):
    if existing_status == "official" and new_status == "provisional":
        return False
    return True
```

双源：净值偏差 >0.5% 标 `conflict`，不更新评分直至人工或主源确认。

---

## 5. 环境变量

```bash
# .env.example
DATABASE_URL=postgresql://user:pass@localhost:5432/invest
FRED_API_KEY=your_fred_key          # https://fred.stlouisfed.org/docs/api/api_key.html
TUSHARE_TOKEN=optional              # https://tushare.pro
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat        # 或 Pro 对应 id
CRAWL_USER_AGENT=InvestAnalyzer/1.0
```

---

## 6. 稳定性实践

| 实践 | 说明 |
|------|------|
| 单主源 | 每 series 只一个 primary，避免混用 |
| 幂等写入 | UNIQUE(instrument_id, trade_date) |
| 审计表 | 每次 job 记 success/fail/rows |
| 数据新鲜度 API | `health` 返回 last_official_date |
| 降级 | VDAX/PE 缺失时维度权重重分配或 ATR/分位替代 |
| 限速 | 东方财富 1–2s/基金；Tushare 遵守积分 |

---

## 7. 法律与合规

- FRED、yfinance：遵守使用条款；yfinance 非官方 API，生产需监控失效
- 东方财富/天天基金：仅个人研究频率；不商用大规模爬取
- 文档与 UI 固定免责声明

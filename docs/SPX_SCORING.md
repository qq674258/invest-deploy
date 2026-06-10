# 标普500（SPX）综合评分

SPX 与 NDX、国内基金 **完全独立**：专用指标集、`macro:spx:*` 数据序列、`profiles.spx` 权重。

## 维度与权重

| 维度 | 权重 |
|------|------|
| valuation | 26% |
| sentiment | 17% |
| drawdown | 12% |
| breadth | 12% |
| macro | 21% |
| trend | 12% |

## 指标（与 NDX 同结构、不同序列）

| 维度 | 指标 | 宏观序列 ID |
|------|------|-------------|
| 估值 | pe_ttm, shiller_cape, erp_spread, pb, forward_pe_12m | `macro:spx:pe_ttm` 等 |
| 情绪 | vix, cnn_fear_greed, put_call_ratio | `macro:spx:vix` 等 |
| 回撤 | drawdown_6m_high | 由 ^GSPC 行情计算 |
| 广度 | spx_pct_above_ma200 | `macro:spx:breadth_ma200` |
| 宏观 | us10y, yield_curve_2s10s, fed_funds, dxy, fed_balance_sheet | `macro:spx:us10y` 等 |
| 趋势 | price_vs_ma200, ma50_ma200_cross | 由 ^GSPC 行情计算 |

**PE-TTM** 历史为 multpl 标普月度；**最新值**为 **SPY trailingPE** 日频（与 ETF 口径一致，通常低于指数聚合 PE）。前瞻 PE 来自 SPY 快照。广度见 `config/spx_constituents.yaml`。  
PUT/CALL 与 NDX 相同：Cboe CDN 历史 CSV + 每日快照（详见 [CRAWL_CONFIG.md](CRAWL_CONFIG.md)）。

## 计算方式

与 NDX 相同：5 年历史分位 → 谨慎分 → 维度均分 → 加权 S。详见 [DATA_ISOLATION.md](DATA_ISOLATION.md)。

## 采集

```powershell
docker compose -p invest-analyzer run --rm api python -m invest.jobs.daily_crawl --job crawl_spx --years 10
docker compose -p invest-analyzer run --rm api python -m invest.jobs.recompute_scores --instrument SPX
```

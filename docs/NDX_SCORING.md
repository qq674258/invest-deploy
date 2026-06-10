# 纳斯达克100（NDX）综合评分

NDX 与 SPX、国内基金 **完全独立**：专用指标集、`macro:ndx:*` 数据序列、`profiles.ndx` 权重。

## 维度与权重

| 维度 | 权重 |
|------|------|
| valuation | 28% |
| sentiment | 18% |
| drawdown | 10% |
| breadth | 10% |
| macro | 20% |
| trend | 14% |

## 指标与数据序列

| 维度 | 指标 | 宏观序列 ID |
|------|------|-------------|
| 估值 | pe_ttm, shiller_cape, erp_spread, pb, forward_pe_12m | `macro:ndx:pe_ttm` 等 |
| 情绪 | vix, cnn_fear_greed, put_call_ratio | `macro:ndx:vix` 等 |
| 回撤 | drawdown_6m_high | 由 QQQ 行情计算 |
| 广度 | ndx_pct_above_ma200 | `macro:ndx:breadth_ma200` |
| 宏观 | us10y, yield_curve_2s10s, fed_funds, dxy, fed_balance_sheet | `macro:ndx:us10y` 等 |
| 趋势 | price_vs_ma200, ma50_ma200_cross | 由 QQQ 行情计算 |

股债收益差：`macro:ndx:earnings_yield − macro:ndx:us10y`（盈利收益率为 multpl 月度，对齐后前向填充）。

**PE-TTM** 历史为 multpl 标普月度（长期参考）；**最新值**为 **QQQ trailingPE** 日频（与行情软件纳指 ETF 口径一致，约 35–37×）。前瞻 PE 亦来自 QQQ 快照。广度见 `config/ndx_constituents.yaml`。  
PUT/CALL 来自 **Cboe**：CDN 历史 CSV（约 1995–2019）+ 每日统计页快照；非 Yahoo `^CPC`。2019-10 之后依赖每日采集累积。P/B 为 multpl **年度**序列，评分时按日向前填充。

## 计算方式

1. 单指标谨慎分：在**可选 1 / 5 / 10 / 20 年**滚动窗口内做历史分位（前端侧栏切换，API 参数 `lookback_years`）；默认 5 年，与采集 `lookback_years: 20` **无关**。
2. 维度分：维度内指标等权平均。
3. 综合分 S：维度加权，缺失维度权重重分配；可选 `defaults.scoring.cautious_bias`（默认 +6）整体上调谨慎度。
4. 智能定投：`config/dca_defaults.yaml` 中 `s_mid`、`high_side_scale` 控制 S 高时减投力度；牛市里智能总收益可能低于固定定投，见回测页说明。

## 采集与重算

```powershell
docker compose -p invest-analyzer run --rm api python -m invest.jobs.daily_crawl --job crawl_ndx --years 10
docker compose -p invest-analyzer run --rm api python -m invest.jobs.recompute_scores --instrument NDX
```

## 说明

- multpl 估值序列在库内以 `macro:ndx:*` / `macro:spx:*` **分别存储**，即使同源网页也是两套独立时间序列。
- 与 SPX 的完整隔离说明：[DATA_ISOLATION.md](DATA_ISOLATION.md)

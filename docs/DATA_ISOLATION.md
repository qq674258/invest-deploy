# 数据与评分隔离说明

## 三条独立链路

| 类型 | 标的示例 | 行情表 | 宏观/估值序列 | 综合分 S |
|------|----------|--------|---------------|----------|
| **纳指100** | NDX | `ohlcv`（QQQ） | `macro:ndx:*` | ✅ `profiles.ndx` |
| **标普500** | SPX | `ohlcv`（^GSPC） | `macro:spx:*` | ✅ `profiles.spx` |
| **国内基金** | FUND_* | `fund_nav` | 无综合 S 序列 | ❌ `scoring.enabled: false` |

NDX 与 SPX **不共用**任何 `macro_series` 行、指标权重或采集任务；基金 **不参与** `recompute_scores` 的综合评分。

## 采集任务

| Job | 写入 OHLCV | 写入宏观序列 |
|-----|------------|--------------|
| `crawl_ndx` | 仅 `crawl.job=crawl_ndx` 的标的（NDX） | 仅 `macro:ndx:*` |
| `crawl_spx` | 仅 SPX | 仅 `macro:spx:*` |
| `crawl_us` | 兼容：NDX+SPX 行情 | 兼容：两套序列都拉 |
| 基金爬取 | `fund_nav` + 持仓等 | 无 |

```powershell
docker compose -p invest-analyzer run --rm api python -m invest.jobs.daily_crawl --job crawl_ndx --years 10
docker compose -p invest-analyzer run --rm api python -m invest.jobs.daily_crawl --job crawl_spx --years 10
docker compose -p invest-analyzer run --rm api python -m invest.jobs.recompute_scores --instrument NDX
docker compose -p invest-analyzer run --rm api python -m invest.jobs.recompute_scores --instrument SPX
```

## 配置入口

- 各标的 `macro_series`：`config/instruments.yaml`
- NDX 指标与权重：[NDX_SCORING.md](NDX_SCORING.md)
- SPX 指标与权重：[SPX_SCORING.md](SPX_SCORING.md)
- 基金：详情页 `/funds/{id}`，不走综合 S

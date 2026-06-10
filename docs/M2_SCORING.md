# M2 评分引擎

## 功能

- 从 `ohlcv` / `macro_series` 计算技术指标（见 `config/metric_catalog.yaml`）
- 滚动历史分位 → 各指标「谨慎分」0–100
- 维度加权 → 综合分 **S**（越高越谨慎/偏贵/偏热）
- 写入 `indicator_values`、`composite_scores`

## 命令

```bash
# 本地（需已有 M1 数据）
python -m invest.jobs.recompute_scores --all
python -m invest.jobs.recompute_scores --instrument NDX

# Docker（推荐 Python 3.12）
docker compose build
docker compose run --rm crawl          # 先采集
docker compose run --rm score          # 再评分
docker compose up invest               # 或一键 pipeline
```

## 权重

| 标的 | 配置 profile |
|------|----------------|
| NDX | `nasdaq` |
| SPX | `sp500` |

见 `config/scoring_weights.yaml`。

## MVP 说明

- `pe_ttm_percentile_5y` 暂无 PE 序列时，用 **价格 5 年分位** 代理
- 缺宏观序列（如未配 FRED）时，该维度权重按比例分给其余维度

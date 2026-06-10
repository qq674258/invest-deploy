# M3 智能定投

## 修复说明（M2 评分报错）

若 `score` 报错 `Length of values (0) does not match length of index`：已修复宏观数据读取（SQLAlchemy 结果集不可二次遍历）。请重新构建镜像后执行 `score`。

## 功能

- `f(S)` 映射：计划金额 P × 因子，上限 M（1.5 / 2.0），下限 0.4×P
- 五档频率：DAILY / WEEKLY / BIWEEKLY / MONTHLY / BIMONTHLY
- 相邻定投平滑（默认 ±30%）
- 现金池：少投部分累积入账
- 回测：固定定投 vs 动态定投
- FastAPI：`/api/v1/dca/preview`、`/backtest/{id}` 等

## CLI

```powershell
docker compose -p invest-analyzer run --rm score
docker compose -p invest-analyzer run --rm dca

# 或本地
python -m invest.jobs.recompute_scores --all
python -m invest.jobs.dca_suggest --all
python -m invest.jobs.dca_suggest --instrument NDX --force
```

## API

```powershell
uvicorn invest.api.main:app --reload --host 0.0.0.0 --port 8000
```

- `GET /api/v1/health`
- `GET /api/v1/scores/{id}/latest`
- `POST /api/v1/dca/preview` body: `{"instrument_id":"NDX","planned_amount":500,"multiplier_max":1.5}`
- `GET /api/v1/backtest/NDX?planned_amount=500&multiplier_max=1.5`（按行情自动重算历史 S，无需逐日入库）
- `GET /api/v1/market/NDX/return-stats`（复利计算器默认年化收益）

# 采集配置说明

## 配置文件

| 文件 | 说明 |
|------|------|
| `config/crawl_sources.yaml` | 基线配置（可提交 Git；Docker 内只读） |
| `data/crawl_config.override.yaml` | 运行覆盖（管理后台保存或手工编辑；优先于基线合并） |

## 可配置项

- **defaults**：回溯年数、评分分位年数、重试次数、广度爬取间隔等
- **endpoints**：FRED、multpl、Cboe、CNN、Stooq、Yahoo、东方财富等接口地址
- **multpl_slugs**：`macro:ndx:*` / `macro:spx:*` 与 multpl 路径映射
- **providers**：如 Cboe Put/Call 使用的比率名称
- **jobs**：各 `crawl_ndx` / `crawl_spx` 任务的宏观序列列表

## 修改方式

### 1. 直接改 YAML（推荐运维）

编辑 `config/crawl_sources.yaml` 或 `data/crawl_config.override.yaml` 后，重启 API 或触发一次采集即可（配置有内存缓存，保存覆盖文件会自动刷新）。

### 2. 管理后台

访问 **管理后台 → 采集配置**（`/admin/settings`）。

- 数值参数可直接改后点「保存配置」
- **接口地址**变更时，系统返回 409，需在页面确认框中点「确认并保存」
- 「恢复基线」会删除 `data/crawl_config.override.yaml`

## 环境变量

`.env` 中 `OHLCV_LOOKBACK_DAYS` 若大于 0，仍优先于配置文件中的 `lookback_years`（单次 CLI 的 `--years` 参数优先级最高）。

## Put/Call 历史

`cboe_putcall` 会按 `lookback_days` 合并以下 Cboe CDN CSV（可在 `endpoints` 中改 URL）：

| 配置键 | 覆盖区间（约） |
|--------|----------------|
| `cboe_pc_ratio_archive` | 1995-09 — 2003-12 |
| `cboe_totalpc_archive` | 2003-10 — 2012-06 |
| `cboe_totalpc_csv` | 2006-11 — 2019-10 |

同日数据以后者为准；再与 **每日统计页** 当日 `TOTAL PUT/CALL RATIO` 快照合并。

**说明**：Cboe 官方 CSV 止于 2019-10-04，2019-10-05 至昨日仅能通过每日采集快照逐步补齐（无免费日频全量源）。设置 `lookback_years: 20` 时，Put/Call 可回填约 20 年官方历史。

## 性能说明

- 库体积通常不大（约 20MB 级）；页面慢多因 **NDX/SPX 实时重算评分**（需合并多年宏观序列），与库“过大”无直接关系。
- 前端切换 1/5/10/20 年分位时，后端会缓存约 2 分钟；首页优先展示总览，评分走势图稍后加载。
- 回测默认不再计算四种定投频率对比（需时在 API 加 `include_frequency_compare=true`）。

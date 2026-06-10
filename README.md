# 智能投资评分与定投系统 / Smart Investment Scoring & DCA System

[![Dashboard](webimage/dashboard.png)](webimage/dashboard.png)

基于量化指标的综合评分（S）、智能定投建议与 DeepSeek 中文解读的投资分析平台。
An investment analysis platform with quantitative scoring (S), smart DCA suggestions, and DeepSeek-powered Chinese analysis.

---

## 功能预览 / Feature Overview

| 截图 Screenshot | 说明 Description |
|---|---|
| ![dashboard](webimage/dashboard.png) | **首页仪表盘** — 指数评分总览与市场健康度 / Dashboard with index scores & market health |
| ![data-crawl](webimage/data-crawl.png) | **数据抓取** — 一键拉取行情、宏观指标 / One-click data crawl for prices & macro indicators |
| ![fund-custom-entry](webimage/fund-custom-entry.png) | **自定义录入与管理** — 手动录入基金信息 / Custom fund entry & management |
| ![fund-detail](webimage/fund-detail.png) | **基金详情** — 业绩、净值、持仓、经理档案 / Fund detail with performance, NAV, holdings, manager |
| ![calculator](webimage/calculator.png) | **计算器** — 一次投入与复利计算 / Lump-sum & compound interest calculator |
| ![lump-sum-calc](webimage/lump-sum-calc.png) | **一次投入产出计算** — 按日/周/月测算收益 / Invest & return projection by day/week/month |
| ![compound-interest](webimage/compound-interest.png) | **复利计算** — 定投复利增长模拟 / DCA compound growth simulation |
| ![multi-user](webimage/multi-user.png) | **多用户** — 多账户支持与权限管理 / Multi-user support & access control |
| ![drawdown-alert-config](webimage/drawdown-alert-config.png) | **回撤提醒配置** — 自定义回撤阈值告警 / Custom drawdown threshold alerts |
| ![auto-crawl-config](webimage/auto-crawl-config.png) | **自动采集配置** — 定时任务与采集参数 / Scheduled crawl & automation settings |

---

## 文档索引 / Document Index

| 文档 Document | 说明 Description |
|---|---|
| [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | **总计划**：需求摘要、分期、里程碑 / Roadmap, milestones |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 技术架构、模块、数据流 / Architecture, modules, data flow |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | 免费稳定数据源与采集策略 / Free data sources & crawl strategy |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | 界面与交互规范 / UI & interaction spec |
| [config/instruments.yaml](config/instruments.yaml) | 标的 InstrumentProfile 草案 / Instrument profiles |
| [config/metric_catalog.yaml](config/metric_catalog.yaml) | 指标目录（爬取 vs 计算）/ Metric catalog |
| [config/scoring_weights.yaml](config/scoring_weights.yaml) | 各市场维度权重 / Scoring weights by market |
| [config/dca_defaults.yaml](config/dca_defaults.yaml) | 定投与倍数默认配置 / DCA defaults |

---

## 当前阶段 / Current Phase

**M6 前端 MVP** — 专业深色仪表盘（纳指 / 标普）。推荐 **Docker** 启动 API + Web。
**M6 Frontend MVP** — Professional dark dashboard (NDX / SPX). Docker recommended for API + Web.

### Docker 一键启动（推荐）/ One-Click Docker Setup (Recommended)

在项目根目录执行（PowerShell）：
Run from project root (PowerShell):

```powershell
cd "d:\桌面\投资分析"

# 1. 环境配置（首次使用）/ Environment setup (first time)
copy .env.docker.example .env
# 编辑 .env：ADMIN_USERNAME / ADMIN_PASSWORD、FRED_API_KEY、代理等
# Edit .env: ADMIN_USERNAME / ADMIN_PASSWORD, FRED_API_KEY, proxy, etc.

# 2. 构建镜像（首次或依赖变更后）/ Build images (first time or after dependency changes)
.\scripts\docker-build.ps1

# 3. 写入行情与评分（首次或需重拉数据时，约数分钟）
# Seed market data & scores (first time or data refresh, takes a few minutes)
.\scripts\bootstrap-data.ps1

# 4. 后台启动 API + 前端 / Start API + frontend in background
docker compose -p invest-analyzer up -d api web
```

| 地址 URL | 说明 Description |
|---|---|
| http://localhost:3009 | 前端仪表盘 / Frontend Dashboard |
| http://localhost:3009/admin/login | 管理后台（`.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）/ Admin Panel |
| http://localhost:18001/docs | API 文档（Swagger）/ API Docs |

**日常一键启动**（已构建过、只需开服务）/ **Daily quick start** (already built, just start services):

```powershell
cd "d:\桌面\投资分析"
docker compose -p invest-analyzer up -d api web
```

若浏览器出现 **Application error**，多半是 Web 镜像过旧或未重建，见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。
If you see **Application error**, the web image is likely stale — see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

**停止服务 / Stop services**:

```powershell
docker compose -p invest-analyzer down
```

### 重启前端/后端 / Restart Frontend / Backend

| 场景 Scenario | 命令 Command |
|---|---|
| 只重启后端 API / Restart API only | `docker compose -p invest-analyzer restart api` |
| 只重启前端 Web / Restart Web only | `docker compose -p invest-analyzer restart web` |
| 同时重启前后端 / Restart both | `docker compose -p invest-analyzer restart api web` |
| 改了 `.env` 或环境变量 / Changed `.env` | 先 `restart api` |
| 改了 `invest/` Python 代码 / Changed Python code | API 已挂载卷带 `--reload`，一般自动生效 / Auto-reload mounted; if not, `restart api` |
| 改了 `web/` 前端代码 / Changed frontend code | **必须** `build web` 后再 `up -d web` / **Must** rebuild, restart won't update image |
| 页面 Application error / Page error | 同上重建 `web`，确认已跑 `bootstrap-data.ps1` / Rebuild web, ensure bootstrap ran |
| 改了 `requirements.txt` 或 Dockerfile | `.\scripts\docker-build.ps1` 或 `build api web`，再 `up -d api web` |

查看运行日志 / View logs:

```powershell
docker compose -p invest-analyzer logs -f api web
```

镜像加速、Web 构建慢等问题见 [docs/DOCKER.md](docs/DOCKER.md)。

### 管理后台 / Admin Panel (M5)

![data-crawl](webimage/data-crawl.png)

- 指数分键拉取：纳斯达克100 / 标普500 / 日经 / DAX / Index crawl: NDX / SPX / N225 / DAX
- 国内主动基金：录入前 **「解析基金信息」**；爬取含净值/持仓/交易规则/经理档案 / China active funds: parse, crawl NAV, holdings, manager profiles
- 历史数据：查看、按日期去重、删除、重新爬取 / History: view, deduplicate, delete, re-crawl
- 首页总览展示已启用的指数与国内基金 / Dashboard shows enabled indices & funds

![fund-custom-entry](webimage/fund-custom-entry.png) | ![fund-detail](webimage/fund-detail.png)
---|---

本地仅跑前端 / Run frontend locally:

```powershell
cd web && npm install && npm run dev
```

（Web 默认 3009，需 API 在 18001）/ (Web defaults to port 3009, requires API on 18001)

- 前端 / Frontend: [docs/FRONTEND.md](docs/FRONTEND.md)
- 评分 / Scoring: [docs/M2_SCORING.md](docs/M2_SCORING.md)
- 采集配置 / Crawl config: [docs/CRAWL_CONFIG.md](docs/CRAWL_CONFIG.md)
- 数据隔离 / Data isolation: [docs/DATA_ISOLATION.md](docs/DATA_ISOLATION.md)
- NDX 评分 / NDX scoring: [docs/NDX_SCORING.md](docs/NDX_SCORING.md)
- SPX 评分 / SPX scoring: [docs/SPX_SCORING.md](docs/SPX_SCORING.md)
- 定投 / DCA: [docs/M3_DCA.md](docs/M3_DCA.md)

### 本地 Python（3.8 兼容）/ Local Python (Python 3.8+)

若 pip 报 `ProxyError`（系统代理 127.0.0.1:10808 未启动）：先关系统代理，或启动 Clash/V2Ray；也可用项目内 `pip.conf`：
If pip shows `ProxyError`: disable system proxy or start Clash/V2Ray; alternatively use the bundled `pip.conf`:

```powershell
cd 投资分析
$env:PIP_CONFIG_FILE = "$PWD\pip.conf"
.\scripts\install.ps1
```

手动安装 / Manual install:

```powershell
cd 投资分析
$env:PIP_CONFIG_FILE = "$PWD\pip.conf"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt pytest

# 初始化数据库 / Init database
.\.venv\Scripts\python -m invest.jobs.daily_crawl --init-db

# 采集美股任务 / Crawl US market data
python -m invest.jobs.daily_crawl --job crawl_ndx
python -m invest.jobs.daily_crawl --job crawl_spx

# 日经 + DAX + 汇率 / Nikkei + DAX + FX
python -m invest.jobs.daily_crawl --job crawl_jp_de

# 全部 + 数据新鲜度 / All + data health check
python -m invest.jobs.daily_crawl --job all

# M2：重算评分（需先有 OHLCV 数据）/ Recompute scores (requires OHLCV data)
python -m invest.jobs.recompute_scores --all

# 仅查看库内最新日期 / Check latest data dates
python -m invest.jobs.daily_crawl --health
```

可选 `.env` 配置 / Optional `.env` config:

- `FRED_API_KEY` — [免费申请 / Free sign-up](https://fred.stlouisfed.org/docs/api/api_key.html)，采集美债10Y、美元指数 / for US 10Y yield & DXY
- `HTTP_PROXY=http://127.0.0.1:10808` — 开启 Clash 等代理后，用于 Yahoo/Stooq 行情（国内通常需要）/ Proxy for Yahoo/Stooq (needed in China)

故障排查见 / Troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 免责声明 / Disclaimer

本系统输出仅供研究与个人参考，不构成投资建议。历史回测不代表未来收益。
This system is for research and personal reference only. It does not constitute investment advice. Past performance does not guarantee future results.

---

## 版权与许可 / Copyright & License

**Copyright © 2026 多点互动 (MoreTouch). All rights reserved.**

**官网 / Website:** [www.moretouch.com.cn](https://www.moretouch.com.cn)

本项目基于 **MIT 许可证** 开源 —— 您可以自由使用、修改和分发，但须保留上述版权声明。
This project is open-sourced under the **MIT License** — you are free to use, modify, and distribute, provided that the above copyright notice is retained.

```
MIT License

Copyright (c) 2026 多点互动 (MoreTouch) — www.moretouch.com.cn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

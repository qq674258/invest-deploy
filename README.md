# 智能投资评分与定投系统

基于量化指标的综合评分（S）、智能定投建议与 DeepSeek 中文解读的投资分析平台。

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | **总计划**：需求摘要、分期、里程碑 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 技术架构、模块、数据流 |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | 免费稳定数据源与采集策略 |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | 界面与交互规范 |
| [config/instruments.yaml](config/instruments.yaml) | 标的 InstrumentProfile 草案 |
| [config/metric_catalog.yaml](config/metric_catalog.yaml) | 指标目录（爬取 vs 计算） |
| [config/scoring_weights.yaml](config/scoring_weights.yaml) | 各市场维度权重 |
| [config/dca_defaults.yaml](config/dca_defaults.yaml) | 定投与倍数默认配置 |

## 当前阶段

**M6 前端 MVP** — 专业深色仪表盘（纳指 / 标普）。推荐 **Docker** 启动 API + Web。

### Docker 一键启动（推荐）

在项目根目录执行（PowerShell）：

```powershell
cd "d:\桌面\投资分析"

# 1. 环境（首次）
copy .env.docker.example .env
# 编辑 .env：ADMIN_USERNAME / ADMIN_PASSWORD、FRED_API_KEY、代理等

# 2. 构建镜像（首次或依赖变更后）
.\scripts\docker-build.ps1

# 3. 写入行情与评分（首次或需重拉数据时，约数分钟）
.\scripts\bootstrap-data.ps1

# 4. 后台启动 API + 前端
docker compose -p invest-analyzer up -d api web
```

| 地址 | 说明 |
|------|------|
| http://localhost:3009 | 前端仪表盘 |
| http://localhost:3009/admin/login | 管理后台（`.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD`） |
| http://localhost:18001/docs | API 文档（Swagger） |

**日常一键启动**（已构建过、只需开服务）：

```powershell
cd "d:\桌面\投资分析"
docker compose -p invest-analyzer up -d api web
```

若浏览器出现 **Application error（client-side exception）**，多半是 Web 镜像过旧或未重建，见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md#打开-httplocalhost3000-显示-application-errorclient-side-exception)。

**停止服务**：

```powershell
docker compose -p invest-analyzer down
```

### 重启前端 / 后端

| 场景 | 命令 |
|------|------|
| 只重启后端 API | `docker compose -p invest-analyzer restart api` |
| 只重启前端 Web | `docker compose -p invest-analyzer restart web` |
| 同时重启前后端 | `docker compose -p invest-analyzer restart api web` |
| 改了 `.env` 或环境变量 | 先 `restart api`（管理登录、FRED Key 等） |
| 改了 `invest/` Python 代码 | API 已挂载卷且带 `--reload`，保存后一般自动生效；不生效则 `restart api` |
| 改了 `web/` 前端代码 | **必须** `build web` 后再 `up -d web`（仅 `restart` 不会更新镜像内代码；可用 `.\scripts\build-web-local.ps1`） |
| 页面 Application error | 同上重建 `web`；并确认已 `bootstrap-data.ps1` |
| 改了 `requirements.txt` 或 Dockerfile | `.\scripts\docker-build.ps1` 或 `build api web`，再 `up -d api web` |

查看运行日志：

```powershell
docker compose -p invest-analyzer logs -f api web
```

镜像加速、Web 构建慢等问题见 [docs/DOCKER.md](docs/DOCKER.md)。



请重建并重启前端（改 web/ 必须 build，不能只 restart）：

cd "d:\桌面\投资分析"
docker compose -p invest-analyzer build web
docker compose -p invest-analyzer up -d web

### 管理后台（M5 简易版）

- 指数分键拉取：纳斯达克100 / 标普500 / 日经 / DAX
- 国内主动基金：录入前 **「解析基金信息」**；爬取含净值/持仓/交易规则/经理档案；前台 **基金详情页** `/funds/FUND_xxxxx`（业绩、历史业绩、净值、持仓、经理、规则）
- 历史数据：查看、按日期去重、删除、重新爬取
- 首页总览会展示已启用的指数与国内基金（基金评分需后续接入 `cn_fund` 算分）

本地仅跑前端：`cd web && npm install && npm run dev`（Web 默认 3009，需 API 在 8001）

若报错 **`hub-mirror.c.163.com`**：见 [docs/DOCKER.md](docs/DOCKER.md)

- 前端：[docs/FRONTEND.md](docs/FRONTEND.md)
- 评分：[docs/M2_SCORING.md](docs/M2_SCORING.md)
- **采集配置**（接口地址、回溯年数）：[docs/CRAWL_CONFIG.md](docs/CRAWL_CONFIG.md) · 管理后台 `/admin/settings`
- **数据隔离**（NDX / SPX / 基金）：[docs/DATA_ISOLATION.md](docs/DATA_ISOLATION.md)
- **NDX 评分**：[docs/NDX_SCORING.md](docs/NDX_SCORING.md) · **SPX 评分**：[docs/SPX_SCORING.md](docs/SPX_SCORING.md)
- 定投：[docs/M3_DCA.md](docs/M3_DCA.md)

### 本地 Python（3.8 兼容）

**若 pip 报 `ProxyError`（系统代理 127.0.0.1:10808 未启动）**：先关 Windows「设置 → 网络 → 代理」，或启动 Clash/V2Ray；也可用项目内 `pip.conf`：

```powershell
cd 投资分析
$env:PIP_CONFIG_FILE = "$PWD\pip.conf"
.\scripts\install.ps1
```

手动安装：

```powershell
cd 投资分析
$env:PIP_CONFIG_FILE = "$PWD\pip.conf"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt pytest

# 初始化数据库
.\.venv\Scripts\python -m invest.jobs.daily_crawl --init-db

# 采集（美股任务：QQQ/GSPC + VIX；无 FRED Key 时跳过美债/美元）
python -m invest.jobs.daily_crawl --job crawl_ndx
python -m invest.jobs.daily_crawl --job crawl_spx

# 日经 + DAX + 汇率
python -m invest.jobs.daily_crawl --job crawl_jp_de

# 全部 + 数据新鲜度
python -m invest.jobs.daily_crawl --job all

# M2：重算评分（需先有 OHLCV 数据）
python -m invest.jobs.recompute_scores --all

# 仅查看库内最新日期
python -m invest.jobs.daily_crawl --health
```

可选 `.env` 配置：

- `FRED_API_KEY` — [免费申请](https://fred.stlouisfed.org/docs/api/api_key.html)，采集美债10Y、美元指数
- `HTTP_PROXY=http://127.0.0.1:10808` — 开启 Clash 等代理后，用于 Yahoo/Stooq 行情（国内通常需要）

故障排查见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 免责声明

本系统输出仅供研究与个人参考，不构成投资建议。历史回测不代表未来收益。

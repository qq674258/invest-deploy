# 常见问题

## 管理后台登录后立刻退出

**原因**：Next.js 代理未把浏览器的 `Authorization: Bearer …` 转发给 FastAPI，登录成功但后续 `/api/v1/admin/*` 全部 401，前端会清空 token 并跳回登录页。

**处理**：更新代码后 **重建 web**（见下），无需改 API。

## K 线页 `Cannot read properties of undefined (reading 'type')`

**原因**：K 线图把 **grid 下标** 误当成 **yAxis 下标**（叠加「综合评分 S」右轴时成交量绑错轴）。

**处理**：同上，重建 `web` 镜像。

## 打开 http://localhost:3000 显示 Application error（client-side exception）

**现象**：`docker compose up -d api web` 后浏览器提示 *Application error: a client-side exception has occurred*。

**常见原因**：

1. **Web 镜像是旧代码**，与当前 API/页面不匹配 → 需重建前端。
2. **ECharts 图表模块**在生产包中加载失败（首页评分曲线、K 线、回测图等）。
3. **从未写入评分/行情**，个别页面访问无数据字段（已在新版前端加固）。

**处理（按顺序）**：

```powershell
cd "d:\桌面\投资分析"
docker compose -p invest-analyzer ps
# 确认 api、web 均为 Up

# 1. 重建并重启前端（改 web/ 代码后必做）
docker compose -p invest-analyzer build web
docker compose -p invest-analyzer up -d api web

# 或本机 npm 构建后打镜像（更快）
.\scripts\build-web-local.ps1
docker compose -p invest-analyzer up -d web

# 2. 若无数据，补全库
.\scripts\bootstrap-data.ps1

# 3. 看日志
docker compose -p invest-analyzer logs -f web api
```

浏览器按 **F12 → Console** 查看红色报错；把首条 `Error:` 信息便于定位。

**仅重启、未改代码时**一般不需要 `build web`，只需：

```powershell
docker compose -p invest-analyzer restart api web
```

## Web 镜像构建卡在 `npm run build` / `Creating an optimized production build`

**现象**：`docker compose build web` 十多分钟无新输出，像卡死。

**原因**：Next.js 正在编译 **ECharts** 等大包，内存不足时极慢；并非一定失败。

**处理（任选）**：

1. Docker Desktop → **Resources**：内存 **≥4GB**，CPU ≥2 核。
2. 打开详细日志后重试：
   ```powershell
   $env:DOCKER_BUILDKIT=1
   docker compose -p invest-analyzer build web --progress=plain
   ```
   首次常见 **5～15 分钟**；第二次有缓存会快很多。
3. **推荐：本机构建 + Docker 只打包**（约 1 分钟出镜像）：
   ```powershell
   cd "d:\桌面\投资分析"
   .\scripts\build-web-local.ps1
   ```
   完成后将 `docker-compose.yml` 里 `web` 的 `build:` 改为 `image: invest-analyzer-web:latest` 再 `docker compose up web -d`。

## Docker build：`hub-mirror.c.163.com: no such host`

网易等旧镜像站已失效，但 Docker Desktop 仍指向它们。

**处理**：见 [DOCKER.md](./DOCKER.md)（删 163 镜像 + 用 `scripts/docker-build.ps1` 或项目默认 DaoCloud 基础镜像）。

## pip ProxyError（Cannot connect to proxy 127.0.0.1:10808）

**原因**：Windows 系统代理已开启，但本机 Clash/V2Ray 未运行。

**方案（三选一）**：

1. **启动代理软件**，确保 `127.0.0.1:10808` 可连。
2. **关闭系统代理**：设置 → 网络和 Internet → 代理 →「使用代理服务器」关闭。
3. **使用项目 `pip.conf`**（安装时）：
   ```powershell
   $env:PIP_CONFIG_FILE = "$PWD\pip.conf"
   pip install -r requirements.txt
   ```

## yfinance 无数据 / 403 Forbidden

**原因**：Yahoo Finance 在国内常不可用。

**方案**：

1. **启动 Clash/V2Ray**，在 `.env` 中设置：
   ```env
   HTTP_PROXY=http://127.0.0.1:10808
   ```
2. 重新执行：`python -m invest.jobs.daily_crawl --job all`

采集顺序：yfinance → Yahoo Chart API → Stooq.pl（均会走上述代理）。

## pandas>=2.2 安装失败

**原因**：当前为 Python 3.8，最高支持 pandas 2.0.x。

**方案**：使用仓库内 `requirements.txt`（已适配 3.8），或安装 [Python 3.11+](https://www.python.org/downloads/)。

## FRED 宏观数据跳过

在 `.env` 中设置：

```env
FRED_API_KEY=你的密钥
```

免费申请：https://fred.stlouisfed.org/docs/api/api_key.html

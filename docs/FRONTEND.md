# 前端（M6 MVP）

## 技术栈

- Next.js 14 · Tailwind · ECharts · React Query
- 深色金融仪表盘风格（见 `UI_DESIGN.md`）

## 页面

| 路径 | 功能 |
|------|------|
| `/` | 总览：评分卡片、历史曲线、数据状态 |
| `/instruments/NDX` | 详情：雷达图、指标表、评分走势 |
| `/dca` | 定投计算器 |
| `/backtest` | 固定 vs 智能回测 |
| `/settings` | 数据健康度 |

当前仅展示 **纳指 NDX、标普 SPX**（`index_us`）。

## 本地开发

```powershell
# 终端 1：API
docker compose -p invest-analyzer up api
# 或: .\.venv\Scripts\uvicorn invest.api.main:app --reload --port 8000

# 终端 2：前端
cd web
copy .env.local.example .env.local
npm install
npm run dev
```

浏览器打开 http://localhost:3000

## Docker 一键

```powershell
# 无缓存重建 web（依赖在镜像构建时 npm install，不会出现在宿主机 web/node_modules）
docker compose -p invest-analyzer build web --no-cache
docker compose -p invest-analyzer up api web
```

说明：依赖安装在 **Docker 构建阶段** 的容器内，本地 `web/` 目录不会出现 `node_modules`，这是正常现象。

- 前端 http://localhost:3000
- API 文档 http://localhost:8000/docs

## 说明

- 浏览器请求 `/api/v1/*` 由 Next **运行时** 代理到后端（`src/app/api/v1/[...path]/route.ts`）
- Docker 内必须使用 `API_INTERNAL_URL=http://api:8000`（**不能** 用 `127.0.0.1`）
- 本地 `npm run dev` 使用 `web/.env.local` 中的 `http://127.0.0.1:8000`

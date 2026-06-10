# Docker 构建与运行

## 你遇到的错误

```
lookup hub-mirror.c.163.com: no such host
```

**原因**：Docker Desktop 里配置了已失效的 **网易镜像加速器**（`hub-mirror.c.163.com`），拉取 `python:3.12-slim-bookworm` 时 DNS 失败。

---

## 解决步骤（推荐按顺序）

### 1. 修改 Docker Desktop 镜像加速

1. 打开 **Docker Desktop** → **Settings** → **Docker Engine**
2. 在 JSON 中找到 `registry-mirrors`，**删除**含 `163.com` 的地址，例如：

```json
"registry-mirrors": [
  "https://hub-mirror.c.163.com"
]
```

3. 可改为目前仍常用的镜像（任选 1～2 个），或 **整段删除** 直连 Docker Hub：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
```

4. 点击 **Apply & Restart**

### 2. 使用项目默认配置构建（已绕过失效镜像）

项目 `docker-compose.yml` 默认从 **DaoCloud** 拉基础镜像，不依赖 163：

```powershell
cd "d:\桌面\投资分析"
copy .env.docker.example .env
docker compose -p invest-analyzer build
```

### 3. 若仍失败，手动指定镜像

```powershell
docker compose -p invest-analyzer build --build-arg PYTHON_IMAGE=docker.1ms.run/library/python:3.12-slim-bookworm
```

或先单独拉取再构建：

```powershell
docker pull docker.m.daocloud.io/library/python:3.12-slim-bookworm
docker tag docker.m.daocloud.io/library/python:3.12-slim-bookworm python:3.12-slim-bookworm
docker compose -p invest-analyzer build --build-arg PYTHON_IMAGE=python:3.12-slim-bookworm
```

---

## Web 前端构建慢 / 卡住

见 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md#web-镜像构建卡在-npm-run-build--creating-an-optimized-production-build)。

快捷：`.\scripts\build-web-local.ps1`（本机 `npm run build` 后打镜像）。

---

## 一键启动（API + 前端）

```powershell
cd "d:\桌面\投资分析"

# 首次
copy .env.docker.example .env
.\scripts\docker-build.ps1
.\scripts\bootstrap-data.ps1

# 启动（后台）
docker compose -p invest-analyzer up -d api web
```

- 前端：http://localhost:3000  
- API：http://localhost:8000/docs  

**日常**（已构建过）只需：

```powershell
docker compose -p invest-analyzer up -d api web
```

**停止**：

```powershell
docker compose -p invest-analyzer down
```

---

## 重启前端 / 后端

```powershell
# 仅后端（FastAPI / 评分 / 回测 API）
docker compose -p invest-analyzer restart api

# 仅前端（Next.js）
docker compose -p invest-analyzer restart web

# 前后端一起
docker compose -p invest-analyzer restart api web
```

| 修改内容 | 建议操作 |
|----------|----------|
| `.env`（管理账号、代理、Key） | `restart api` |
| `invest/` 下 Python | 卷已挂载 + `--reload`，多数情况保存即生效；否则 `restart api` |
| `web/` 下前端 | `build web` → `restart web`，或 `.\scripts\build-web-local.ps1` |
| `requirements.txt` / Dockerfile | `.\scripts\docker-build.ps1` → `up -d api web` |

```powershell
# 查看日志
docker compose -p invest-analyzer logs -f api web
```

---

## 数据与构建（常用）

```powershell
docker compose -p invest-analyzer build
docker compose -p invest-analyzer run --rm crawl
docker compose -p invest-analyzer run --rm score
.\scripts\bootstrap-data.ps1
```

## 代理（采集 Yahoo 行情）

宿主开启 Clash（10808）时，在 `.env` 添加：

```env
HTTP_PROXY=http://host.docker.internal:10808
HTTPS_PROXY=http://host.docker.internal:10808
```

**注意**：每日自动采集在 **`api` 容器**内执行（非 `crawl` 一次性容器），代理必须写在 `.env` 里并 `restart api`。

## 每日自动采集

内置定时器随 **`api` 容器**启动，默认每天 **07:30（Asia/Shanghai）** 增量采集指数 + 基金。

| 检查项 | 说明 |
|--------|------|
| 管理后台 → **告警与定时** | 勾选「启用每日自动采集」并保存（写入 `data/crawl_config.override.yaml`） |
| `GET /api/v1/admin/scheduler/status` | `running: true` 且 `next_run` 有值 |
| `api` 容器需 **7×24 运行** | `docker compose up -d api web`，勿只部署 web |
| 采集审计 | 管理后台「采集控制」底部应有 `crawl_ndx` 等记录 |

若服务器未上传 `data/crawl_config.override.yaml`，以 `config/crawl_sources.yaml` 为准（**现已默认 `auto_crawl_enabled: true`**）。

**Linux 宿主机 cron 备用方案**（不依赖 api 内置定时器）：

```bash
30 7 * * * cd /path/to/投资分析 && docker compose -p invest-analyzer run --rm crawl python -m invest.jobs.daily_crawl --job all --incremental --funds >> /var/log/invest-crawl.log 2>&1
```

## 不用 Docker

本地已有 `.venv` 时：

```powershell
$env:PIP_CONFIG_FILE = "$PWD\pip.conf"
.\.venv\Scripts\python -m invest.jobs.daily_crawl --job all
.\.venv\Scripts\python -m invest.jobs.recompute_scores --all
```

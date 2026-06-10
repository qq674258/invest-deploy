# 在 Windows 本机构建 Next.js，再用 Dockerfile.prebuilt 打镜像（避免 Docker 内 next build 卡住）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "web"
Set-Location $Web

Write-Host "=== 1/2 本机 npm ci + next build（首次约 3～8 分钟，请耐心等待）===" -ForegroundColor Cyan
if (-not (Test-Path "node_modules")) {
    npm ci --registry=https://registry.npmmirror.com --legacy-peer-deps
}
$env:NODE_OPTIONS = "--max-old-space-size=4096"
$env:NEXT_TELEMETRY_DISABLED = "1"
npm run build

if (-not (Test-Path ".next/standalone/server.js")) {
    Write-Error "构建失败：未找到 .next/standalone/server.js"
}

Write-Host "=== 2/2 Docker 打包预构建产物（通常 <1 分钟）===" -ForegroundColor Cyan
Set-Location $Root
docker build -f web/Dockerfile.prebuilt -t invest-analyzer-web:latest web

Write-Host ""
Write-Host "完成。启动: docker compose -p invest-analyzer up api -d" -ForegroundColor Green
Write-Host "      docker run --rm -p 3009:3000 --network invest-analyzer_default -e API_INTERNAL_URL=http://api:8001 invest-analyzer-web:latest"
Write-Host "或在 compose 中为 web 指定 image: invest-analyzer-web:latest" -ForegroundColor Yellow

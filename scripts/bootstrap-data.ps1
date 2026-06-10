# 一键：采集 -> 评分 -> 定投（Docker）
param(
    [int]$Years = 10
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== 1/3 采集行情（近 $Years 年）===" -ForegroundColor Cyan
docker compose -p invest-analyzer run --rm crawl `
  python -m invest.jobs.daily_crawl --job all --years $Years
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/3 计算评分 ===" -ForegroundColor Cyan
docker compose -p invest-analyzer run --rm score
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/3 定投建议 ===" -ForegroundColor Cyan
docker compose -p invest-analyzer run --rm dca
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n完成。可访问 http://localhost:8001/api/v1/version 检查 API 版本" -ForegroundColor Green

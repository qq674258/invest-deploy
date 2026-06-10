# Docker build script (DaoCloud base image + Tsinghua pip mirror)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.docker.example" ".env"
    Write-Host "[info] Created .env from .env.docker.example" -ForegroundColor Yellow
}

if (-not $env:PYTHON_IMAGE) {
    $env:PYTHON_IMAGE = "docker.m.daocloud.io/library/python:3.12-slim-bookworm"
}

if (-not $env:PIP_INDEX_URL) {
    $env:PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
}

Write-Host "PYTHON_IMAGE=$($env:PYTHON_IMAGE)"
Write-Host "If you see hub-mirror.c.163.com errors, edit Docker Desktop registry-mirrors (see docs/DOCKER.md)"
Write-Host ""

docker compose -p invest-analyzer build @args

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Build OK. Next:" -ForegroundColor Green
Write-Host "  docker compose -p invest-analyzer run --rm crawl"
Write-Host "  docker compose -p invest-analyzer run --rm score"

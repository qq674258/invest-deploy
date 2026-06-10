# Install dependencies (fixes Windows system proxy 127.0.0.1:10808 when VPN is off)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:PIP_CONFIG_FILE = Join-Path $Root "pip.conf"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
# If pip still uses system proxy, disable: Settings -> Network -> Proxy -> Off
# Or start VPN on 127.0.0.1:10808

Write-Host "PIP_CONFIG_FILE = $env:PIP_CONFIG_FILE"
Write-Host ""

# Prefer Python 3.11+
$py = $null
foreach ($candidate in @("py -3.12", "py -3.11", "python")) {
    try {
        $ver = Invoke-Expression "$candidate -c `"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')`"" 2>$null
        if ($ver -and ([version]$ver -ge [version]"3.11")) {
            $py = $candidate
            break
        }
    } catch {}
}

if (-not $py) {
    Write-Host "ERROR: Python 3.11+ required. Install from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Current venv may be 3.8 - delete .venv and re-run this script after installing 3.11+"
    exit 1
}

Write-Host "Using: $py ($ver)"

if (-not (Test-Path ".venv")) {
    Invoke-Expression "$py -m venv .venv"
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt pytest

Write-Host ""
Write-Host "Done. Next:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m invest.jobs.daily_crawl --init-db"
Write-Host "  .\.venv\Scripts\python.exe -m invest.jobs.daily_crawl --job all"

param(
    [switch]$DnsWorkaround,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)" }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed. Install and open Docker Desktop first."
}
Invoke-Docker info --format '{{.ServerVersion}}'
Invoke-Docker compose -f docker-compose.setup.yml run --rm setup
$composeArgs = @('-f', 'docker-compose.yml')
if ($DnsWorkaround) {
    Invoke-Docker compose -f docker-compose.setup.yml run --rm setup python scripts/build_dns_override.py
    $composeArgs += @('-f', 'runtime/compose.build-dns.yml')
}
Invoke-Docker compose @composeArgs up --build -d --wait --wait-timeout 600
Invoke-Docker compose @composeArgs ps -a
$webBinding = Invoke-Docker compose @composeArgs port frontend 80
$webPort = ([string]($webBinding | Select-Object -First 1)).Trim().Split(':')[-1]
$webUrl = "http://localhost:$webPort"
Write-Host "LabChain ready: $webUrl"
Write-Host "API: http://localhost:8000/docs"
if ($OpenBrowser) { Start-Process $webUrl }

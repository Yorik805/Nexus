$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot '..\nexus.config.json'
$config = Get-Content $configPath -Raw | ConvertFrom-Json

$env:NEXUS_URL = "$($config.protocol)://$($config.host):$($config.runtime_port)"
$env:NEXUS_HOST = [string]$config.host
$env:NEXUS_RUNTIME_URL = $env:NEXUS_URL
$env:NEXUS_DASHBOARD_PORT = [string]$config.dashboard_port
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://$($config.host):$($config.dashboard_port)"

Write-Host "Nexus host: $($config.host)"
Write-Host "Runtime URL: $env:NEXUS_RUNTIME_URL"
Write-Host "Dashboard backend: $env:NEXUS_DASHBOARD_BACKEND_URL"
Write-Host "Dashboard port: $env:NEXUS_DASHBOARD_PORT"
Write-Host "Environment applied to this PowerShell session."

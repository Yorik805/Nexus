$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot '..\nexus.config.json'
$config = Get-Content $configPath -Raw | ConvertFrom-Json

$env:NEXUS_URL = "$($config.protocol)://$($config.host):$($config.runtime_port)"
$env:NEXUS_HOST = [string]$config.host
$env:NEXUS_RUNTIME_URL = $env:NEXUS_URL
$env:NEXUS_DASHBOARD_PORT = [string]$config.dashboard_port
$env:NEXUS_DASHBOARD_BACKEND_URL = "http://$($config.host):$($config.dashboard_port)"

$envPath = Join-Path $PSScriptRoot '..\.env'
if (Test-Path $envPath) {
	Get-Content $envPath | ForEach-Object {
		$line = $_.Trim()
		if ($line -and !$line.StartsWith('#') -and $line -match '^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
			[Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), 'Process')
		}
	}
	Write-Host "Loaded private provider settings from .env."
} else {
	Write-Host "No .env found; provider settings were not loaded."
}

Write-Host "Nexus host: $($config.host)"
Write-Host "Runtime URL: $env:NEXUS_RUNTIME_URL"
Write-Host "Dashboard backend: $env:NEXUS_DASHBOARD_BACKEND_URL"
Write-Host "Dashboard port: $env:NEXUS_DASHBOARD_PORT"
Write-Host "Environment applied to this PowerShell session."

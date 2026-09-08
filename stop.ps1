# Nexus Unified Windows Service Stopper
Write-Host "Stopping all Nexus processes..." -ForegroundColor Yellow

$killed = 0
Get-CimInstance Win32_Process | Where-Object { 
  $cmd = $_.CommandLine
  $name = $_.Name
  if ($cmd) {
    return ($cmd -like "*nexus_server.py*" -or 
            $cmd -like "*nexus_dashboard_server.py*" -or 
            ($cmd -like "*nexus-voice-console*" -and $name -like "*node*"))
  }
  return $false
} | ForEach-Object {
  Write-Host "Stopping process $($_.Name) (PID: $($_.ProcessId))..." -ForegroundColor DarkGray
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  $killed++
}

Write-Host "[OK] Stopped $killed Nexus processes." -ForegroundColor Green
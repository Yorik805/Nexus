# Nexus Unified Windows Service Runner
$rootDir = $PSScriptRoot
Set-Location $rootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       NEXUS WINDOWS LOCAL DEV & SERVICE RUNNER           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Detect Python
$python = "$rootDir\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
    Write-Host "[INFO] .venv not found, using system python." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Using Python virtual environment (.venv)" -ForegroundColor Green
}

# 2. Check and install Python dependencies if needed
Write-Host "[1/3] Checking Python dependencies..." -ForegroundColor Cyan
& $python -m pip install -r requirements.txt --quiet

# 3. Check and install Voice Console web dependencies
Write-Host "[2/3] Checking Voice Console dependencies..." -ForegroundColor Cyan
$clientDir = "$rootDir\assets\web_client\nexus-voice-console"
if (-not (Test-Path "$clientDir\node_modules")) {
    Write-Host "[INFO] Installing npm packages in $clientDir..." -ForegroundColor Yellow
    Push-Location $clientDir
    npm install --no-audit --no-fund
    Pop-Location
} else {
    Write-Host "[OK] Voice Console node_modules ready." -ForegroundColor Green
}

# 4. Launch 3 Services
Write-Host "[3/3] Starting Nexus services in separate terminal windows..." -ForegroundColor Cyan

# Launch Core Server
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Nexus Core Runtime (Port 8765)'; Set-Location '$rootDir'; Write-Host '=== Nexus Core Runtime ===' -ForegroundColor Green; & '$python' nexus_server.py"

# Launch Dashboard Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Nexus Dashboard Server (Port 11882)'; Set-Location '$rootDir'; Write-Host '=== Nexus Dashboard Server ===' -ForegroundColor Magenta; & '$python' nexus_dashboard_server.py"

# Launch Voice Console
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'Nexus Voice Console (Port 3001)'; Set-Location '$clientDir'; Write-Host '=== Nexus Voice Console ===' -ForegroundColor Yellow; npm run dev -- -p 3001"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "               ALL 3 SERVICES LAUNCHED                    " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  1. Nexus Main Core:        http://127.0.0.1:8765" -ForegroundColor White
Write-Host "  2. Debugging Dashboard:    http://127.0.0.1:11882" -ForegroundColor White
Write-Host "  3. Voice Console:          http://localhost:3001" -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "To stop all services at once, run: .\stop.ps1" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
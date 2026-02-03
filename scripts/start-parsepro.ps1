# =============================================================================
# Parse Pro AI - Windows 11 Startup Script
# =============================================================================
# Usage:
#   .\scripts\start-parsepro.ps1                    # Start with defaults
#   .\scripts\start-parsepro.ps1 -Workers 2        # Start with 2 workers
#   .\scripts\start-parsepro.ps1 -Pool solo        # Use solo pool (fallback)
#   .\scripts\start-parsepro.ps1 -SkipRedisCheck   # Skip Redis check
# =============================================================================

param(
    [int]$Workers = 1,
    [int]$Concurrency = 8,
    [ValidateSet("eventlet", "solo", "threads")]
    [string]$Pool = "eventlet",
    [switch]$SkipRedisCheck,
    [switch]$SkipDjango
)

$ErrorActionPreference = "Stop"

# Get project paths
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
$venvActivate = Join-Path $projectPath ".venv\Scripts\Activate.ps1"
$envFile = Join-Path $projectPath ".env"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Parse Pro AI - Windows 11 Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor White
Write-Host "  Workers:     $Workers" -ForegroundColor Gray
Write-Host "  Concurrency: $Concurrency" -ForegroundColor Gray
Write-Host "  Pool:        $Pool" -ForegroundColor Gray
Write-Host ""

# Check virtual environment
if (-not (Test-Path $venvActivate)) {
    Write-Host "[ERROR] Virtual environment not found at: $venvActivate" -ForegroundColor Red
    Write-Host "        Run: uv venv && uv sync" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Virtual environment found" -ForegroundColor Green

# Check .env file
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env file not found" -ForegroundColor Red
    Write-Host "        Create .env with OPENROUTER_API_KEY" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] .env file found" -ForegroundColor Green

# Check Redis/Memurai
if (-not $SkipRedisCheck) {
    $redis = Get-Process | Where-Object { 
        $_.ProcessName -like "*memurai*" -or 
        $_.ProcessName -like "*redis*" 
    }
    if (-not $redis) {
        Write-Host "[WARNING] Redis/Memurai not detected" -ForegroundColor Yellow
        Write-Host "          Start Redis first: memurai-server" -ForegroundColor Yellow
        Write-Host "          Or use -SkipRedisCheck to bypass" -ForegroundColor Yellow
        
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    } else {
        Write-Host "[OK] Redis/Memurai is running" -ForegroundColor Green
    }
}

Write-Host ""

# Start Django server
if (-not $SkipDjango) {
    Write-Host "Starting Django server..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit", 
        "-Command",
        "Set-Location '$projectPath'; & '$venvActivate'; Write-Host 'Django Server' -ForegroundColor Cyan; python manage.py runserver"
    ) -WindowStyle Normal
    Write-Host "  Django server starting..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

# Start Celery worker(s)
Write-Host "Starting $Workers Celery worker(s) with $Pool pool..." -ForegroundColor Cyan

for ($i = 1; $i -le $Workers; $i++) {
    $workerName = "worker$i"
    
    if ($Pool -eq "solo") {
        # Solo pool - no concurrency setting
        $celeryCmd = "celery -A config worker -l info -P solo -n $workerName@%COMPUTERNAME% -Q resume_parse"
    } else {
        # Eventlet or threads pool with concurrency
        $celeryCmd = "celery -A config worker -l info -P $Pool -c $Concurrency -n $workerName@%COMPUTERNAME% -Q resume_parse"
    }
    
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$projectPath'; & '$venvActivate'; Write-Host 'Celery Worker: $workerName ($Pool pool)' -ForegroundColor Cyan; $celeryCmd"
    ) -WindowStyle Normal
    
    Write-Host "  Started $workerName ($Pool pool, concurrency=$Concurrency)" -ForegroundColor Gray
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Parse Pro AI is running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor White
Write-Host "  Django:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API:      http://localhost:8000/api/v1/" -ForegroundColor Cyan
Write-Host "  Swagger:  http://localhost:8000/api/docs/" -ForegroundColor Cyan
Write-Host "  Admin:    http://localhost:8000/admin/" -ForegroundColor Cyan
Write-Host ""
Write-Host "FREE TIER NOTE:" -ForegroundColor Yellow
Write-Host "  You have limited daily API requests on the free tier." -ForegroundColor Yellow
Write-Host "  Model fallbacks are enabled for rate limit resilience." -ForegroundColor Yellow
Write-Host ""

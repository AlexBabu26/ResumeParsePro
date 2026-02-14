# =============================================================================
# Parse Pro AI - Status Check Script
# =============================================================================
# Usage:
#   .\scripts\status-parsepro.ps1
# =============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Parse Pro AI - Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Redis/Memurai
Write-Host "Redis/Memurai:" -ForegroundColor White
$redis = Get-Process | Where-Object { 
    $_.ProcessName -like "*memurai*" -or 
    $_.ProcessName -like "*redis*" 
}
if ($redis) {
    Write-Host "  [RUNNING]" -ForegroundColor Green
    $redis | Format-Table Id, ProcessName, CPU -AutoSize
} else {
    Write-Host "  [NOT RUNNING]" -ForegroundColor Red
}

# Check Django
Write-Host "Django Server:" -ForegroundColor White
$django = Get-Process | Where-Object {
    $_.ProcessName -eq "python" -and $_.CommandLine -like "*runserver*"
}
if ($django) {
    Write-Host "  [RUNNING] http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "  [NOT RUNNING]" -ForegroundColor Yellow
}

# Check Celery workers
Write-Host ""
Write-Host "Celery Workers:" -ForegroundColor White
$celery = Get-Process | Where-Object { 
    $_.ProcessName -like "*celery*" -or 
    ($_.ProcessName -eq "python" -and $_.CommandLine -like "*celery*")
}
if ($celery) {
    Write-Host "  [RUNNING] $($celery.Count) worker(s)" -ForegroundColor Green
    $celery | Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize
} else {
    Write-Host "  [NOT RUNNING]" -ForegroundColor Yellow
}

# Check API endpoint
Write-Host "API Health Check:" -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/schema/" -Method GET -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] API responding" -ForegroundColor Green
    }
} catch {
    Write-Host "  [ERROR] API not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

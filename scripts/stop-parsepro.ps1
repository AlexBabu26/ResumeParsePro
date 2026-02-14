# =============================================================================
# Parse Pro AI - Stop All Workers Script
# =============================================================================
# Usage:
#   .\scripts\stop-parsepro.ps1           # Stop all workers
#   .\scripts\stop-parsepro.ps1 -Force    # Force stop without confirmation
# =============================================================================

param(
    [switch]$Force
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  Parse Pro AI - Stop Workers" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Find Celery processes
$celeryProcesses = Get-Process | Where-Object { 
    $_.ProcessName -like "*celery*" -or 
    ($_.ProcessName -eq "python" -and $_.CommandLine -like "*celery*")
}

if ($celeryProcesses) {
    Write-Host "Found Celery processes:" -ForegroundColor White
    $celeryProcesses | Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize
    
    if (-not $Force) {
        $confirm = Read-Host "Stop all Celery workers? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Gray
            exit 0
        }
    }
    
    Write-Host "Stopping Celery workers..." -ForegroundColor Yellow
    $celeryProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Celery workers stopped" -ForegroundColor Green
} else {
    Write-Host "No Celery workers found running." -ForegroundColor Gray
}

# Optional: Stop Django server
$djangoProcesses = Get-Process | Where-Object {
    $_.ProcessName -eq "python" -and $_.CommandLine -like "*runserver*"
}

if ($djangoProcesses) {
    Write-Host ""
    Write-Host "Found Django server processes:" -ForegroundColor White
    $djangoProcesses | Format-Table Id, ProcessName -AutoSize
    
    if (-not $Force) {
        $confirm = Read-Host "Stop Django server too? (y/N)"
        if ($confirm -eq "y" -or $confirm -eq "Y") {
            $djangoProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Django server stopped" -ForegroundColor Green
        }
    } else {
        $djangoProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Django server stopped" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green

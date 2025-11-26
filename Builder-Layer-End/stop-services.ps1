# Stop Docker Services Script

Write-Host "`n[INFO] Stopping Docker Compose services...`n" -ForegroundColor Cyan

# Stop and remove containers, networks, and volumes
docker-compose -f docker-compose.test.yml down -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Services stopped and cleaned up!`n" -ForegroundColor Green
    
    # Show disk usage
    Write-Host "[INFO] Current Docker disk usage:" -ForegroundColor Cyan
    docker system df
    Write-Host ""
} else {
    Write-Host "`n[ERROR] Failed to stop services!`n" -ForegroundColor Red
    exit 1
}

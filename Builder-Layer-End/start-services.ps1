# Start Docker Services Script

Write-Host "`n[INFO] Starting Docker Compose services...`n" -ForegroundColor Cyan

# Start all services in detached mode
docker-compose -f docker-compose.test.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Services started!`n" -ForegroundColor Green
    
    # Wait a bit for services to initialize
    Write-Host "[INFO] Waiting 30 seconds for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Show service status
    Write-Host "`n[INFO] Service status:" -ForegroundColor Cyan
    docker-compose -f docker-compose.test.yml ps
    
    Write-Host "`n[NEXT] To run tests:" -ForegroundColor Cyan
    Write-Host "  docker-compose -f docker-compose.test.yml run --rm test-runner`n" -ForegroundColor White
    
    Write-Host "[NEXT] To view logs:" -ForegroundColor Cyan
    Write-Host "  docker-compose -f docker-compose.test.yml logs -f`n" -ForegroundColor White
    
    Write-Host "[NEXT] To stop services:" -ForegroundColor Cyan
    Write-Host "  docker-compose -f docker-compose.test.yml down -v`n" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] Failed to start services!`n" -ForegroundColor Red
    exit 1
}

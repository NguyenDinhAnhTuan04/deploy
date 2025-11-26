# Quick Docker Build Script - Simple and Fast

Write-Host "`n[INFO] Starting optimized Docker build...`n" -ForegroundColor Cyan

# Enable BuildKit
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

# Build test-runner
Write-Host "[BUILD] Building test-runner with Dockerfile.test.optimized..." -ForegroundColor Yellow
docker-compose -f docker-compose.test.yml build test-runner

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Build successful!`n" -ForegroundColor Green
    
    # Show image size
    Write-Host "[INFO] Image size:" -ForegroundColor Cyan
    docker images builder-layer-end-test-runner --format "table {{.Repository}}\t{{.Size}}"
    
    Write-Host "`n[NEXT] To start services, run:" -ForegroundColor Cyan
    Write-Host "  docker-compose -f docker-compose.test.yml up -d`n" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] Build failed!`n" -ForegroundColor Red
    exit 1
}

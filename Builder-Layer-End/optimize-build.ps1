# Docker Cleanup and Optimized Build Script
# Cleans up Docker resources and rebuilds with optimizations

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   Docker Build Optimization & Cleanup Script" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Enable Docker BuildKit for faster builds
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

Write-Host "[OK] Docker BuildKit enabled" -ForegroundColor Green
Write-Host ""

# Step 1: Stop existing containers
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 1: Stopping existing containers..." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose -f docker-compose.test.yml down -v 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Containers stopped and volumes removed" -ForegroundColor Green
} else {
    Write-Host "[WARN] No containers to stop" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Show Docker disk usage
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 2: Current Docker disk usage" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker system df
Write-Host ""

# Step 3: Clean up Docker resources
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 3: Cleaning up Docker resources..." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Removing dangling images..." -ForegroundColor Cyan
docker image prune -f 2>&1 | Out-Null
Write-Host "[OK] Dangling images removed" -ForegroundColor Green

Write-Host "Removing build cache..." -ForegroundColor Cyan
docker builder prune -f 2>&1 | Out-Null
Write-Host "[OK] Build cache cleared" -ForegroundColor Green
Write-Host ""

# Step 4: Build optimized image
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 4: Building optimized test-runner image..." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

$startTime = Get-Date

docker-compose -f docker-compose.test.yml build test-runner

$endTime = Get-Date
$buildDuration = $endTime - $startTime

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Test-runner image built successfully" -ForegroundColor Green
    Write-Host "Build time: $($buildDuration.TotalSeconds.ToString('0.0')) seconds" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] Build failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Show new disk usage
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 5: Docker disk usage after optimization" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker system df
Write-Host ""

# Step 6: Show image size
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 6: Test-runner image details" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker images builder-layer-end-test-runner --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
Write-Host ""

# Step 7: Pull service images
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "Step 7: Pulling service images..." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose -f docker-compose.test.yml pull --ignore-pull-failures

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   [OK] Optimization Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start services:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.test.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run tests:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.test.yml run --rm test-runner" -ForegroundColor Gray
Write-Host ""
Write-Host "3. View logs:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.test.yml logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Stop services:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.test.yml down -v" -ForegroundColor Gray
Write-Host ""

# Docker Image Size Comparison Script
# Compares original vs optimized Dockerfile sizes

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Docker Image Size Comparison                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$env:DOCKER_BUILDKIT = 1

# Build original Dockerfile
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Building ORIGINAL Dockerfile.test..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

$start1 = Get-Date
docker build -f Dockerfile.test -t test-runner:original . 2>&1 | Out-Null
$end1 = Get-Date
$duration1 = ($end1 - $start1).TotalSeconds

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Original build completed in $($duration1.ToString('0.0'))s" -ForegroundColor Green
} else {
    Write-Host "✗ Original build failed" -ForegroundColor Red
}
Write-Host ""

# Build optimized Dockerfile
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Building OPTIMIZED Dockerfile.test.optimized..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

$start2 = Get-Date
docker build -f Dockerfile.test.optimized -t test-runner:optimized . 2>&1 | Out-Null
$end2 = Get-Date
$duration2 = ($end2 - $start2).TotalSeconds

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Optimized build completed in $($duration2.ToString('0.0'))s" -ForegroundColor Green
} else {
    Write-Host "✗ Optimized build failed" -ForegroundColor Red
}
Write-Host ""

# Get image sizes
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Image Size Comparison" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

# Get sizes
$originalSize = docker images test-runner:original --format "{{.Size}}"
$optimizedSize = docker images test-runner:optimized --format "{{.Size}}"

# Display comparison table
Write-Host "┌─────────────────┬──────────────┬──────────────┐" -ForegroundColor White
Write-Host "│ Metric          │ Original     │ Optimized    │" -ForegroundColor White
Write-Host "├─────────────────┼──────────────┼──────────────┤" -ForegroundColor White
Write-Host ("│ Image Size      │ {0,-12} │ {1,-12} │" -f $originalSize, $optimizedSize) -ForegroundColor Cyan
Write-Host ("│ Build Time      │ {0,9:0.0}s   │ {1,9:0.0}s   │" -f $duration1, $duration2) -ForegroundColor Cyan
Write-Host "└─────────────────┴──────────────┴──────────────┘" -ForegroundColor White
Write-Host ""

# Calculate savings
if ($originalSize -match '(\d+\.?\d*)([A-Z]+)') {
    $originalValue = [float]$matches[1]
    $originalUnit = $matches[2]
    
    if ($optimizedSize -match '(\d+\.?\d*)([A-Z]+)') {
        $optimizedValue = [float]$matches[1]
        $optimizedUnit = $matches[2]
        
        # Convert to MB for comparison
        $originalMB = if ($originalUnit -eq "GB") { $originalValue * 1024 } else { $originalValue }
        $optimizedMB = if ($optimizedUnit -eq "GB") { $optimizedValue * 1024 } else { $optimizedValue }
        
        $savedMB = $originalMB - $optimizedMB
        $savedPercent = ($savedMB / $originalMB) * 100
        
        Write-Host "💾 Space Saved:" -ForegroundColor Green
        Write-Host "   - Size reduction: $($savedMB.ToString('0.0'))MB" -ForegroundColor White
        Write-Host "   - Percentage: $($savedPercent.ToString('0.0'))%" -ForegroundColor White
        Write-Host ""
    }
}

# Build time comparison
$timeSaved = $duration1 - $duration2
$timeSavedPercent = ($timeSaved / $duration1) * 100

Write-Host "⏱ Build Time:" -ForegroundColor Green
if ($timeSaved -gt 0) {
    Write-Host "   - Time saved: $($timeSaved.ToString('0.0'))s" -ForegroundColor White
    Write-Host "   - Percentage: $($timeSavedPercent.ToString('0.0'))% faster" -ForegroundColor White
} else {
    Write-Host "   - Time difference: $([Math]::Abs($timeSaved).ToString('0.0'))s slower" -ForegroundColor Yellow
    Write-Host "   - Note: First build may be slower due to layer caching" -ForegroundColor Yellow
}
Write-Host ""

# Layer comparison
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Layer Analysis" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

Write-Host "Original Image Layers:" -ForegroundColor Cyan
docker history test-runner:original --format "{{.Size}}`t{{.CreatedBy}}" --no-trunc=false | Select-Object -First 10
Write-Host ""

Write-Host "Optimized Image Layers:" -ForegroundColor Cyan
docker history test-runner:optimized --format "{{.Size}}`t{{.CreatedBy}}" --no-trunc=false | Select-Object -First 10
Write-Host ""

# Recommendations
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "Recommendations" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

if ($savedPercent -gt 40) {
    Write-Host "✓ Excellent optimization! (>40% size reduction)" -ForegroundColor Green
    Write-Host "  → Use Dockerfile.test.optimized for production" -ForegroundColor White
} elseif ($savedPercent -gt 20) {
    Write-Host "✓ Good optimization (20-40% size reduction)" -ForegroundColor Green
    Write-Host "  → Consider using Dockerfile.test.optimized" -ForegroundColor White
} else {
    Write-Host "⚠ Modest optimization (<20% size reduction)" -ForegroundColor Yellow
    Write-Host "  → May need further optimization" -ForegroundColor White
}
Write-Host ""

# Cleanup option
$response = Read-Host "Remove test images? (y/N)"
if ($response -eq 'y' -or $response -eq 'Y') {
    docker rmi test-runner:original test-runner:optimized
    Write-Host "✓ Test images removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✓ Comparison Complete!                                 ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green

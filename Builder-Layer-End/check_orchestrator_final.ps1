# Final Orchestrator Analysis - Check for 100% Success
# No Warnings, No Errors, No Skipping

$logFile = "logs/orchestrator_final.log"

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     FINAL ORCHESTRATOR ANALYSIS - 100% SUCCESS CHECK       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Wait for file to exist
$maxWait = 30
$waited = 0
while (-not (Test-Path $logFile) -and $waited -lt $maxWait) {
    Write-Host "⏳ Waiting for log file... ($waited/$maxWait seconds)" -ForegroundColor Yellow
    Start-Sleep -Seconds 1
    $waited++
}

if (-not (Test-Path $logFile)) {
    Write-Host "❌ Log file not found: $logFile" -ForegroundColor Red
    exit 1
}

# Wait for workflow to complete (check every 10 seconds)
Write-Host "⏳ Waiting for workflow completion..." -ForegroundColor Yellow
$completed = $false
$maxIterations = 60  # 10 minutes max
$iteration = 0

while (-not $completed -and $iteration -lt $maxIterations) {
    Start-Sleep -Seconds 10
    $iteration++
    
    $content = Get-Content $logFile -ErrorAction SilentlyContinue
    if ($content -match "WORKFLOW COMPLETED") {
        $completed = $true
        break
    }
    
    # Show progress
    $latestPhase = $content | Select-String -Pattern "PHASE:" | Select-Object -Last 1
    if ($latestPhase) {
        Write-Host "  📍 Current: $($latestPhase.Line)" -ForegroundColor Cyan
    }
}

if (-not $completed) {
    Write-Host "⏱️  Workflow still running after $($iteration * 10) seconds..." -ForegroundColor Yellow
    Write-Host "Please check logs/orchestrator_final.log manually" -ForegroundColor Yellow
    exit 0
}

# Analyze results
$content = Get-Content $logFile

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 WORKFLOW STATUS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$status = $content | Select-String -Pattern "WORKFLOW COMPLETED:" | Select-Object -Last 1
if ($status) {
    Write-Host $status.Line -ForegroundColor Green
}

$summary = $content | Select-String -Pattern "Status:|Duration:|Total Agents:|Successful:|Failed:" | Select-Object -Last 5
$summary | ForEach-Object { Write-Host $_.Line }

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "⚠️  ERROR COUNT" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$errors = $content | Select-String -Pattern "ERROR|agent failed" -CaseSensitive:$false
$errorCount = ($errors | Measure-Object).Count
if ($errorCount -eq 0) {
    Write-Host "✅ ZERO ERRORS!" -ForegroundColor Green
} else {
    Write-Host "❌ Found $errorCount errors:" -ForegroundColor Red
    $errors | Select-Object -First 20 | ForEach-Object { Write-Host $_.Line -ForegroundColor Red }
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "⚠️  WARNING COUNT" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$warnings = $content | Select-String -Pattern "WARNING|Input file not found|Empty entity" -CaseSensitive:$false
$warningCount = ($warnings | Measure-Object).Count
if ($warningCount -eq 0) {
    Write-Host "✅ ZERO WARNINGS!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Found $warningCount warnings:" -ForegroundColor Yellow
    
    # Group warnings by type
    $fileNotFound = $warnings | Where-Object { $_.Line -match "Input file not found" }
    $emptyEntity = $warnings | Where-Object { $_.Line -match "Empty entity|No entities" }
    $skipping = $warnings | Where-Object { $_.Line -match "skipping|skip" }
    
    if ($fileNotFound) {
        Write-Host "`n  📁 File Not Found: $(($fileNotFound | Measure-Object).Count)" -ForegroundColor Magenta
        $fileNotFound | Select-Object -First 5 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
    }
    
    if ($emptyEntity) {
        Write-Host "`n  📄 Empty Entity List: $(($emptyEntity | Measure-Object).Count)" -ForegroundColor Magenta
        $emptyEntity | Select-Object -First 5 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
    }
    
    if ($skipping) {
        Write-Host "`n  ⏭️  Skipping: $(($skipping | Measure-Object).Count)" -ForegroundColor Magenta
        $skipping | Select-Object -First 5 | ForEach-Object { Write-Host "    $($_.Line)" -ForegroundColor Gray }
    }
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📁 OUTPUT FILES STATUS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$files = @(
    @{Name="observations.json"; Path="data/observations.json"},
    @{Name="accidents.json"; Path="data/accidents.json"},
    @{Name="congestion.json"; Path="data/congestion.json"},
    @{Name="patterns.json"; Path="data/patterns.json"},
    @{Name="cameras_enriched.json"; Path="data/cameras_enriched.json"},
    @{Name="validated_observations.json"; Path="data/validated_observations.json"},
    @{Name="validated_accidents.json"; Path="data/validated_accidents.json"},
    @{Name="validated_patterns.json"; Path="data/validated_patterns.json"}
)

foreach ($file in $files) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        $jsonContent = Get-Content $file.Path | ConvertFrom-Json
        
        if ($jsonContent -is [Array]) {
            $count = $jsonContent.Count
            Write-Host "  ✅ $($file.Name) - $count entities ($size bytes)" -ForegroundColor Green
        } else {
            Write-Host "  ✅ $($file.Name) - Object ($size bytes)" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ $($file.Name) - NOT CREATED" -ForegroundColor Red
    }
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🏁 FINAL VERDICT" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

if ($errorCount -eq 0 -and $warningCount -eq 0) {
    Write-Host "`n🎉 PERFECT! 100% SUCCESS!" -ForegroundColor Green
    Write-Host "✅ Zero Errors" -ForegroundColor Green
    Write-Host "✅ Zero Warnings" -ForegroundColor Green
    Write-Host "✅ Zero Skipping" -ForegroundColor Green
} elseif ($errorCount -eq 0) {
    Write-Host "`n⚠️  SUCCESS WITH WARNINGS" -ForegroundColor Yellow
    Write-Host "✅ Zero Errors" -ForegroundColor Green
    Write-Host "⚠️  $warningCount Warnings (check above)" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ FAILED - ERRORS DETECTED" -ForegroundColor Red
    Write-Host "❌ $errorCount Errors" -ForegroundColor Red
    Write-Host "⚠️  $warningCount Warnings" -ForegroundColor Yellow
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

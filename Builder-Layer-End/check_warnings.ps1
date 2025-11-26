# Check Orchestrator Log for Warnings
# Monitors orchestrator_analysis.log for any warnings/errors/skipping

param(
    [int]$WaitSeconds = 180  # Wait up to 3 minutes
)

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          ORCHESTRATOR WARNING CHECKER                        ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$logFile = "logs/orchestrator_analysis.log"
$startTime = Get-Date

Write-Host "Waiting for orchestrator to complete (max $WaitSeconds seconds)...`n" -ForegroundColor Yellow

while (((Get-Date) - $startTime).TotalSeconds -lt $WaitSeconds) {
    Start-Sleep -Seconds 5
    
    if (Test-Path $logFile) {
        $content = Get-Content $logFile -Raw
        
        # Check if workflow completed
        if ($content -match "WORKFLOW COMPLETED") {
            Write-Host "✅ Workflow completed! Analyzing results...`n" -ForegroundColor Green
            break
        }
    }
}

if (!(Test-Path $logFile)) {
    Write-Host "❌ Log file not found: $logFile" -ForegroundColor Red
    exit 1
}

$content = Get-Content $logFile

# Count warnings by type
Write-Host "━━━ WARNING SUMMARY ━━━`n" -ForegroundColor Yellow

$inputFileWarnings = ($content | Select-String -Pattern "Input file not found" | Measure-Object).Count
$rdfDirWarnings = ($content | Select-String -Pattern "RDF directory not found" | Measure-Object).Count
$noEntitiesWarnings = ($content | Select-String -Pattern "No entities to publish|No entities to convert|Empty entity list" | Measure-Object).Count
$skippingWarnings = ($content | Select-String -Pattern "skipping" -CaseSensitive:$false | Measure-Object).Count
$errors = ($content | Select-String -Pattern " ERROR " | Measure-Object).Count
$failures = ($content | Select-String -Pattern "failed:" -CaseSensitive:$false | Measure-Object).Count

Write-Host "Input File Not Found:    $inputFileWarnings" -ForegroundColor $(if ($inputFileWarnings -eq 0) { "Green" } else { "Red" })
Write-Host "RDF Directory Not Found: $rdfDirWarnings" -ForegroundColor $(if ($rdfDirWarnings -eq 0) { "Green" } else { "Red" })
Write-Host "No Entities Warnings:    $noEntitiesWarnings" -ForegroundColor $(if ($noEntitiesWarnings -eq 0) { "Green" } else { "Red" })
Write-Host "Skipping Messages:       $skippingWarnings" -ForegroundColor $(if ($skippingWarnings -eq 0) { "Green" } else { "Red" })
Write-Host "Errors:                  $errors" -ForegroundColor $(if ($errors -eq 0) { "Green" } else { "Red" })
Write-Host "Failures:                $failures" -ForegroundColor $(if ($failures -eq 0) { "Green" } else { "Red" })

$totalIssues = $inputFileWarnings + $rdfDirWarnings + $noEntitiesWarnings + $skippingWarnings + $errors + $failures

Write-Host "`n━━━ FILE STATUS CHECK ━━━`n" -ForegroundColor Yellow

# Check if critical output files exist
$files = @(
    "data/validated_observations.json",
    "data/validated_accidents.json",
    "data/validated_patterns.json"
)

$allFilesExist = $true
foreach ($file in $files) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        $entities = (Get-Content $file | ConvertFrom-Json).Count
        Write-Host "✅ $file - $entities entities ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "❌ $file - NOT FOUND" -ForegroundColor Red
        $allFilesExist = $false
    }
}

Write-Host "`n━━━ FINAL RESULT ━━━`n" -ForegroundColor Cyan

if ($totalIssues -eq 0 -and $allFilesExist) {
    Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅ 100% SUCCESS - NO WARNINGS!      ║" -ForegroundColor Green
    Write-Host "║  ✅ All output files created!        ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Green
    exit 0
} else {
    Write-Host "╔═══════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║  ❌ ISSUES DETECTED                   ║" -ForegroundColor Red
    Write-Host "║  Total Issues: $totalIssues                    ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════╝" -ForegroundColor Red
    
    Write-Host "`n━━━ DETAILED WARNINGS ━━━`n" -ForegroundColor Yellow
    
    if ($inputFileWarnings -gt 0) {
        Write-Host "Input File Warnings:" -ForegroundColor Red
        $content | Select-String -Pattern "Input file not found" | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
    }
    
    if ($rdfDirWarnings -gt 0) {
        Write-Host "`nRDF Directory Warnings:" -ForegroundColor Red
        $content | Select-String -Pattern "RDF directory not found" | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
    }
    
    if ($errors -gt 0) {
        Write-Host "`nErrors:" -ForegroundColor Red
        $content | Select-String -Pattern " ERROR " | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
    }
    
    exit 1
}

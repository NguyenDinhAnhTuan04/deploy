# ==========================================
# KIỂM TRA DATA COMPLETENESS TRONG TẤT CẢ STORAGE
# ==========================================

Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "1. STELLIO (NGSI-LD Context Broker)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/ngsi-ld/v1/entities?limit=200" -Method Get -ContentType "application/ld+json"
    $entities = $response
    
    # Count by type
    $cameras = ($entities | Where-Object { $_.type -eq "Camera" }).Count
    $weather = ($entities | Where-Object { $_.type -eq "WeatherObserved" }).Count
    $airquality = ($entities | Where-Object { $_.type -eq "AirQualityObserved" }).Count
    $total = $entities.Count
    
    Write-Host " Total Entities: $total" -ForegroundColor Green
    Write-Host "  - Camera: $cameras" -ForegroundColor White
    Write-Host "  - WeatherObserved: $weather" -ForegroundColor White
    Write-Host "  - AirQualityObserved: $airquality" -ForegroundColor White
    Write-Host "  - Other: $($total - $cameras - $weather - $airquality)" -ForegroundColor White
} catch {
    Write-Host " Stellio Error: $_" -ForegroundColor Red
}

Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "2. FUSEKI (RDF Triplestore)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    # Check dataset exists
    $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:test_admin"))
    $headers = @{Authorization="Basic $auth"}
    $datasets = Invoke-RestMethod -Uri "http://localhost:3030/$/datasets" -Headers $headers -Method Get
    
    if ($datasets.datasets | Where-Object { $_.'ds.name' -eq '/lod-dataset' }) {
        Write-Host " Dataset 'lod-dataset' exists" -ForegroundColor Green
        
        # Count triples
        $sparql = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        $query = [System.Web.HttpUtility]::UrlEncode($sparql)
        $response = Invoke-RestMethod -Uri "http://localhost:3030/lod-dataset/sparql?query=$query" -Headers $headers
        $triples = $response.results.bindings[0].count.value
        
        Write-Host "  - Total Triples: $triples" -ForegroundColor White
        
        # Count graphs
        $sparql2 = "SELECT (COUNT(DISTINCT ?g) as ?count) WHERE { GRAPH ?g { ?s ?p ?o } }"
        $query2 = [System.Web.HttpUtility]::UrlEncode($sparql2)
        $response2 = Invoke-RestMethod -Uri "http://localhost:3030/lod-dataset/sparql?query=$query2" -Headers $headers
        $graphs = $response2.results.bindings[0].count.value
        
        Write-Host "  - Named Graphs: $graphs" -ForegroundColor White
    } else {
        Write-Host " Dataset 'lod-dataset' NOT FOUND" -ForegroundColor Red
    }
} catch {
    Write-Host " Fuseki Error: $_" -ForegroundColor Red
}

Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "3. NEO4J (Property Graph)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

try {
    $neo4jAuth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("neo4j:test_neo4j"))
    $neo4jHeaders = @{
        Authorization="Basic $neo4jAuth"
        "Content-Type"="application/json"
    }
    
    # Count all nodes
    $cypher = @{
        statements = @(
            @{statement="MATCH (n) RETURN count(n) as total"}
        )
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "http://localhost:7474/db/neo4j/tx/commit" -Method Post -Headers $neo4jHeaders -Body $cypher
    $total = $response.results[0].data[0].row[0]
    
    Write-Host " Total Nodes: $total" -ForegroundColor Green
    
    # Count by label
    $cypher2 = @{
        statements = @(
            @{statement="MATCH (n:Camera) RETURN count(n) as count"},
            @{statement="MATCH (n:WeatherObserved) RETURN count(n) as count"},
            @{statement="MATCH (n:AirQualityObserved) RETURN count(n) as count"}
        )
    } | ConvertTo-Json
    
    $response2 = Invoke-RestMethod -Uri "http://localhost:7474/db/neo4j/tx/commit" -Method Post -Headers $neo4jHeaders -Body $cypher2
    
    $cameras = $response2.results[0].data[0].row[0]
    $weather = $response2.results[1].data[0].row[0]
    $airquality = $response2.results[2].data[0].row[0]
    
    Write-Host "  - Camera: $cameras" -ForegroundColor White
    Write-Host "  - WeatherObserved: $weather" -ForegroundColor White
    Write-Host "  - AirQualityObserved: $airquality" -ForegroundColor White
} catch {
    Write-Host " Neo4j Error: $_" -ForegroundColor Red
}

Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "4. LOCAL FILES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check RDF files
$rdfFiles = Get-ChildItem -Path "data\rdf" -Filter "*.ttl" -ErrorAction SilentlyContinue
if ($rdfFiles) {
    Write-Host " RDF Files: $($rdfFiles.Count) Turtle files" -ForegroundColor Green
    
    # Count Camera vs ObservableProperty files
    $cameraFiles = ($rdfFiles | Where-Object { $_.Name -like "Camera_*" }).Count
    $propertyFiles = ($rdfFiles | Where-Object { $_.Name -like "ObservableProperty_*" }).Count
    
    Write-Host "  - Camera_*.ttl: $cameraFiles" -ForegroundColor White
    Write-Host "  - ObservableProperty_*.ttl: $propertyFiles" -ForegroundColor White
} else {
    Write-Host " No RDF files found" -ForegroundColor Red
}

# Check JSON files
$jsonFiles = @(
    "data\cameras_updated.json",
    "data\cameras_enriched.json",
    "data\ngsi_ld_entities.json",
    "data\observations.json"
)

foreach ($file in $jsonFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw | ConvertFrom-Json
        if ($content -is [Array]) {
            $count = $content.Count
        } else {
            $count = 1
        }
        Write-Host " $file: $count entities" -ForegroundColor Green
    } else {
        Write-Host " $file: NOT FOUND" -ForegroundColor Red
    }
}

Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Data storage verified across 4 systems" -ForegroundColor White

# GITHUB COPILOT PROMPTS - STELLIO MULTI-AGENT SYSTEM

## PROMPT 0: PROJECT STRUCTURE

```markdown
# Create Project Structure (Empty Files/Folders Only)

Create the following directory structure with EMPTY files and folders:

```

 config/
├── data_sources.yaml
├── stellio.yaml
├── fuseki.yaml
└── agents.yaml
agents/
├── data_collection/
│   ├── image_refresh_agent.py
│   └── external_data_collector_agent.py
├── transformation/
│   ├── ngsi_ld_transformer_agent.py
│   └── sosa_ssn_mapper_agent.py
├── analytics/
│   ├── cv_analysis_agent.py
│   ├── congestion_detection_agent.py
│   ├── accident_detection_agent.py
│   └── pattern_recognition_agent.py
├── context_management/
│   ├── entity_publisher_agent.py
│   ├── state_updater_agent.py
│   └── temporal_data_manager_agent.py
├── rdf_linked_data/
│   ├── smart_data_models_validation_agent.py
│   ├── ngsi_ld_to_rdf_agent.py
│   ├── triplestore_loader_agent.py
│   └── content_negotiation_agent.py
├── notification/
│   ├── subscription_manager_agent.py
│   ├── alert_dispatcher_agent.py
│   └── incident_report_generator_agent.py
├── monitoring/
│   ├── health_check_agent.py
│   ├── data_quality_validator_agent.py
│   └── performance_monitor_agent.py
└── integration/
    ├── api_gateway_agent.py
    └── cache_manager_agent.py
shared/
├── __init__.py
├── config_loader.py
├── logger.py
└── utils.py
tests/
└── (mirror agents/ structure)
docker-compose.yml
requirements.txt
README.md
```

DO NOT add any code content. Just create the folder structure and empty files.
```

---

## PROMPT 1: IMAGE REFRESH AGENT

```markdown
# Build Image Refresh Agent

## WORKFLOW
```
┌─────────────────────────────────────────────┐
│      IMAGE REFRESH AGENT WORKFLOW           │
└─────────────────────────────────────────────┘

[Config File: data_sources.yaml]
         ↓
    Read camera endpoints
         ↓
┌─────────────────────┐
│  Scheduler (30-60s) │
└──────────┬──────────┘
           ↓
    ┌──────────────┐
    │ For each URL │
    └──────┬───────┘
           ↓
    Parse image_url_x4
           ↓
    Extract: id, zoom
           ↓
    Generate new timestamp
           ↓
    Build new URL: ?id=X&zoom=Y&t=NEW_TS
           ↓
    HTTP HEAD check (verify accessible)
           ↓
    ┌──────────────┐
    │ Valid?       │
    └──┬────────┬──┘
      YES      NO
       ↓        ↓
    Update   Log error
       ↓
    [Output: cameras_updated.json]
```

## IMPLEMENTATION

Create `agents/data_collection/image_refresh_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read camera endpoints from `config/data_sources.yaml`
- Parse `image_url_x4` field: extract `id`, `zoom` parameters
- Generate fresh timestamp in milliseconds
- Rebuild URL with new `&t=` parameter
- Async HTTP HEAD requests to verify accessibility
- Handle 722 cameras in parallel (batch size: 50)
- Output updated JSON to `data/cameras_updated.json`
- Logging: INFO for updates, ERROR for failures
- Retry logic: 3 attempts with exponential backoff
- Graceful shutdown on SIGTERM

### Config Schema (data_sources.yaml):
```yaml
cameras:
  source_file: "data/cameras_raw.json"
  output_file: "data/cameras_updated.json"
  refresh_interval: 30  # seconds
  batch_size: 50
  url_template: "https://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx"
  params:
    - id
    - zoom
    - t  # timestamp to refresh
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Test URL parsing with valid/invalid formats
   - Test timestamp generation
   - Test URL reconstruction
   - Test batch processing logic

2. **Integration Tests:**
   - Load config from YAML
   - Process sample 10 cameras
   - Verify output JSON structure
   - Test error handling (404, timeout)

3. **Performance Tests:**
   - Process 722 cameras < 5 seconds
   - Memory usage < 100MB
   - No memory leaks after 1000 iterations

4. **Edge Cases:**
   - Empty input file
   - Malformed URLs
   - Network failures
   - Concurrent executions

Write comprehensive tests in `tests/data_collection/test_image_refresh_agent.py`.

Run tests with: `pytest tests/data_collection/test_image_refresh_agent.py -v --cov=agents/data_collection/image_refresh_agent --cov-report=term-missing`

Must achieve 100% code coverage.
```

---

## PROMPT 2: EXTERNAL DATA COLLECTOR AGENT

```markdown
# Build External Data Collector Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│   EXTERNAL DATA COLLECTOR AGENT WORKFLOW     │
└──────────────────────────────────────────────┘

[Config: data_sources.yaml]
         ↓
    API keys & endpoints
         ↓
┌─────────────────────┐
│  Scheduler (10 min) │
└──────────┬──────────┘
           ↓
    ┌──────────────────┐
    │ Fetch Weather    │ → OpenWeatherMap API
    │ (by coordinates) │
    └────────┬─────────┘
             ↓
    ┌──────────────────┐
    │ Fetch AQI        │ → OpenAQ API
    │ (by location)    │
    └────────┬─────────┘
             ↓
    Match data to cameras (geo-radius)
             ↓
    Enrich camera data with context
             ↓
    [Output: external_data.json]
```

## IMPLEMENTATION

Create `agents/data_collection/external_data_collector_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read API configs from `config/data_sources.yaml`
- Fetch OpenWeatherMap API (current weather by lat/lng)
- Fetch OpenAQ API (air quality by coordinates)
- Match external data to cameras within 5km radius
- Rate limiting: max 60 req/min per API
- Cache responses (TTL: 10 minutes)
- Output to `data/external_data.json`
- Async HTTP requests with aiohttp
- Retry on failures (3 attempts)
- Comprehensive error logging

### Config Schema:
```yaml
external_apis:
  openweathermap:
    base_url: "https://api.openweathermap.org/data/2.5/weather"
    api_key: "5d43c8c74f6a4b9f3cfdc3aaf1e5a015"
    rate_limit: 60  # req/min
    timeout: 5
  openaq:
    base_url: "https://api.openaq.org/v2/latest"
    api_key: "1268dbec69a5c8dd637f4a0616a7338d1f320ae966721abdc18e94a2b20b0675"
    rate_limit: 60
    timeout: 5
  geo_match_radius: 5000  # meters
```

### Output Format:
```json
{
  "camera_id": "TTH406",
  "weather": {
    "temperature": 28.5,
    "humidity": 75,
    "description": "scattered clouds"
  },
  "air_quality": {
    "aqi": 102,
    "pm25": 45.2,
    "category": "Moderate"
  },
  "timestamp": "2025-11-01T10:30:00Z"
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - API response parsing
   - Geo-matching algorithm
   - Rate limiter logic
   - Cache hit/miss scenarios

2. **Integration Tests:**
   - Mock API responses
   - Test full data collection cycle
   - Verify output JSON structure

3. **Performance Tests:**
   - Handle 722 cameras < 2 minutes
   - Respect rate limits
   - Cache effectiveness

4. **Edge Cases:**
   - API failures (500, timeout)
   - Invalid API keys
   - Missing coordinates
   - No nearby data

Write tests in `tests/data_collection/test_external_data_collector_agent.py`.

Achieve 100% coverage: `pytest tests/data_collection/test_external_data_collector_agent.py -v --cov --cov-report=html`
```

---

## PROMPT 3: NGSI-LD TRANSFORMER AGENT

```markdown
# Build NGSI-LD Transformer Agent

## WORKFLOW
```
┌─────────────────────────────────────────────┐
│      NGSI-LD TRANSFORMER AGENT WORKFLOW     │
└─────────────────────────────────────────────┘

[Input: cameras_updated.json]
         ↓
    Read raw JSON (722 cameras)
         ↓
    ┌────────────────────┐
    │ For each camera    │
    └─────────┬──────────┘
              ↓
    ┌─────────────────────────┐
    │ Mapping Rules Engine    │
    │ • code → urn:ngsi-ld:..│
    │ • ptz → cameraType      │
    │ • lat/lng → GeoProperty │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────┐
    │ Build NGSI-LD JSON  │
    │ • Add @context      │
    │ • Property format   │
    │ • Relationship fmt  │
    └──────────┬──────────┘
               ↓
    Validate NGSI-LD structure
               ↓
    [Output: ngsi_ld_entities.json]
```

## IMPLEMENTATION

Create `agents/transformation/ngsi_ld_transformer_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read `cameras_updated.json`
- Transform to NGSI-LD format per Smart Data Models
- Mapping rules from `config/ngsi_ld_mappings.yaml`
- Generate URI: `urn:ngsi-ld:Camera:{code}`
- Add @context from smartdatamodels.org
- Handle Property vs Relationship types
- GeoProperty for location (GeoJSON Point)
- Temporal properties: observedAt
- Output to `data/ngsi_ld_entities.json`
- Batch processing: 100 entities at a time
- Validation against NGSI-LD core schema
- Logging: transform stats (success/fail counts)

### Mapping Config (ngsi_ld_mappings.yaml):
```yaml
entity_type: "Camera"
uri_prefix: "urn:ngsi-ld:Camera:"
id_field: "code"

property_mappings:
  name: "cameraName"
  code: "cameraNum"
  ptz:
    target: "cameraType"
    transform: "boolean_to_ptz"  # True→PTZ, False→Fixed
  cam_type:
    target: "cameraUsage"
    transform: "uppercase"  # tth→TRAFFIC

geo_property:
  source: ["latitude", "longitude"]
  target: "location"
  format: "Point"

context_urls:
  - "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
  - "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld"
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - URI generation
   - Property type detection
   - GeoJSON formatting
   - Transform functions (boolean_to_ptz, etc.)

2. **Integration Tests:**
   - Full 722 camera transformation
   - Verify NGSI-LD structure
   - @context resolution

3. **Validation Tests:**
   - Schema compliance
   - Required fields present
   - Valid coordinates

4. **Performance Tests:**
   - Transform 722 cameras < 10 seconds
   - Memory efficient streaming

Write tests in `tests/transformation/test_ngsi_ld_transformer_agent.py`.

Coverage: `pytest tests/transformation/ -v --cov=agents/transformation/ngsi_ld_transformer_agent --cov-report=term-missing`
```

---

## PROMPT 4: SOSA/SSN MAPPER AGENT

```markdown
# Build SOSA/SSN Mapper Agent

## WORKFLOW
```
┌─────────────────────────────────────────────┐
│        SOSA/SSN MAPPER AGENT WORKFLOW       │
└─────────────────────────────────────────────┘

[Input: ngsi_ld_entities.json]
         ↓
    Read NGSI-LD entities
         ↓
    ┌────────────────────────┐
    │ Load SOSA ontology     │
    │ definitions            │
    └──────────┬─────────────┘
               ↓
    ┌─────────────────────────────┐
    │ For each Camera entity      │
    └──────────┬──────────────────┘
               ↓
    ┌─────────────────────────────┐
    │ Add SOSA properties:        │
    │ • type: sosa:Sensor         │
    │ • sosa:observes →           │
    │   ObservableProperty        │
    │ • sosa:isHostedBy →         │
    │   Platform                  │
    │ • sosa:madeObservation      │
    └──────────┬──────────────────┘
               ↓
    Create ObservableProperty entity
               ↓
    Create Platform entity
               ↓
    [Output: sosa_enhanced_entities.json]
```

## IMPLEMENTATION

Create `agents/transformation/sosa_ssn_mapper_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read NGSI-LD entities from previous step
- Add SOSA/SSN ontology properties
- Map Camera → sosa:Sensor
- Create sosa:observes relationships
- Generate ObservableProperty entities
- Generate Platform entity (HCMC Traffic System)
- Output enhanced NGSI-LD with SOSA
- Preserve all original properties
- Add SOSA context to @context array

### SOSA Mapping Config (sosa_mappings.yaml):
```yaml
sensor_type: "sosa:Sensor"
observable_property_type: "TrafficFlow"
platform:
  id: "urn:ngsi-ld:Platform:HCMCTrafficSystem"
  name: "Ho Chi Minh City Traffic Monitoring System"

relationships:
  observes:
    type: "Relationship"
    target_type: "ObservableProperty"
  isHostedBy:
    type: "Relationship"
    target_type: "Platform"
  madeObservation:
    type: "Relationship"
    target_type: "Observation"
    dynamic: true  # timestamp-based

sosa_context: "https://www.w3.org/ns/sosa/"
```

### Output Structure:
```json
{
  "id": "urn:ngsi-ld:Camera:TTH406",
  "type": ["Camera", "sosa:Sensor"],
  "sosa:observes": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:ObservableProperty:TrafficFlow"
  },
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://www.w3.org/ns/sosa/"
  ]
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - SOSA property addition
   - Relationship creation
   - URI generation for ObservableProperty
   - Context merging

2. **Integration Tests:**
   - Process all 722 cameras
   - Verify SOSA-compliant output
   - Check relationship integrity

3. **Ontology Validation:**
   - Validate against SOSA/SSN schema
   - Required SOSA properties present
   - Relationship types correct

4. **Performance:**
   - Enhance 722 entities < 5 seconds

Write tests in `tests/transformation/test_sosa_ssn_mapper_agent.py`.

Run: `pytest tests/transformation/test_sosa_ssn_mapper_agent.py -v --cov --cov-report=html`
```

---

## PROMPT 5: SMART DATA MODELS VALIDATION AGENT

```markdown
# Build Smart Data Models Validation Agent

## WORKFLOW
```
┌──────────────────────────────────────────────────┐
│  SMART DATA MODELS VALIDATION AGENT WORKFLOW     │
└──────────────────────────────────────────────────┘

[Input: sosa_enhanced_entities.json]
         ↓
    Load Smart Data Models schema
         ↓
    ┌──────────────────────┐
    │ For each entity      │
    └─────────┬────────────┘
              ↓
    ┌─────────────────────────────┐
    │ JSON Schema Validation      │
    │ • Check required fields     │
    │ • Validate data types       │
    │ • Check @context            │
    └──────────┬──────────────────┘
               ↓
    ┌─────────────────────────────┐
    │ LOD 5-Star Rating           │
    │ ★ Open License              │
    │ ★★ Machine Readable         │
    │ ★★★ Open Format             │
    │ ★★★★ URI Identifiers        │
    │ ★★★★★ Linked Data           │
    └──────────┬──────────────────┘
               ↓
    Generate validation report
               ↓
    ┌──────────────────┐
    │ Valid?           │
    └────┬────────┬────┘
        YES      NO
         ↓        ↓
    Accept   Reject + Log errors
         ↓
    [Output: validated_entities.json + report.json]
```

## IMPLEMENTATION

Create `agents/rdf_linked_data/smart_data_models_validation_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Download Smart Data Models schemas from smartdatamodels.org
- JSON Schema validation (jsonschema library)
- Validate: id, type, @context, required properties
- Calculate LOD 5-star rating per entity
- Generate detailed validation report
- Filter valid entities to output
- Log all validation errors
- Support multiple entity types (Camera, Observation, etc.)

### LOD Rating Criteria: ( config/validation.yaml )
```yaml
lod_criteria:
  star_1:
    name: "Open License"
    check: "license field present (CC-BY, ODbL, etc.)"
  star_2:
    name: "Machine Readable"
    check: "Valid JSON structure"
  star_3:
    name: "Open Format"
    check: "JSON-LD format with @context"
  star_4:
    name: "URI Identifiers"
    check: "id starts with urn: or http://"
  star_5:
    name: "Linked Data"
    check: "Contains Relationship types linking to external URIs"
```

### Validation Report Format:
```json
{
  "summary": {
    "total_entities": 722,
    "valid": 720,
    "invalid": 2,
    "average_lod_stars": 4.99
  },
  "lod_distribution": {
    "5_stars": 720,
    "4_stars": 2,
    "3_stars": 0
  },
  "errors": [
    {
      "entity_id": "urn:ngsi-ld:Camera:TTH999",
      "errors": ["Missing required field: location"]
    }
  ]
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Schema loading
   - Individual LOD criteria checks
   - Rating calculation
   - Error message formatting

2. **Validation Tests:**
   - Valid entity (5 stars)
   - Missing required field
   - Invalid @context
   - Malformed URI

3. **Integration Tests:**
   - Validate 722 cameras
   - Generate report
   - Filter invalid entities

4. **Performance:**
   - Validate 722 entities < 15 seconds

Write tests in `tests/rdf_linked_data/test_smart_data_models_validation_agent.py`.

Coverage: `pytest tests/rdf_linked_data/test_smart_data_models_validation_agent.py -v --cov --cov-report=term-missing`
```

---

## PROMPT 6: ENTITY PUBLISHER AGENT

```markdown
# Build Entity Publisher Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│       ENTITY PUBLISHER AGENT WORKFLOW        │
└──────────────────────────────────────────────┘

[Input: validated_entities.json]
         ↓
    Read validated NGSI-LD entities
         ↓
    Load Stellio config (URL, auth)
         ↓
    ┌────────────────────────┐
    │ Batch entities (50)    │
    └──────────┬─────────────┘
               ↓
    ┌─────────────────────────────────┐
    │ POST /ngsi-ld/v1/entities       │
    │ Content-Type: application/ld+json│
    └──────────┬──────────────────────┘
               ↓
    ┌──────────────────┐
    │ Response OK?     │
    └────┬────────┬────┘
        200      409/500
         ↓        ↓
    Success   ┌──────────────────┐
              │ Entity exists?   │
              └────┬────────┬────┘
                  409      500
                   ↓        ↓
              PATCH    Retry (3x)
              update   exponential
                       backoff
         ↓
    [Neo4j: Cameras stored as graph nodes]
```

## IMPLEMENTATION

Create `agents/context_management/entity_publisher_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read validated entities from input
- POST to Stellio Context Broker: `http://stellio:8080/ngsi-ld/v1/entities`
- Batch operations: 50 entities per request
- Handle 409 Conflict → PATCH update instead
- Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
- Track success/failure counts
- Output publish report
- Support auth tokens (optional)

### Stellio Config (stellio.yaml):
```yaml
stellio:
  base_url: "http://localhost:8080"
  api_version: "ngsi-ld/v1"
  endpoints:
    entities: "/entities"
    batch: "/entityOperations/upsert"
  auth:
    enabled: false
    token: "${STELLIO_AUTH_TOKEN}"
  batch_size: 50
  timeout: 30
  retry:
    max_attempts: 3
    backoff_factor: 2
```

### API Call Example:
```python
POST http://stellio:8080/ngsi-ld/v1/entities
Content-Type: application/ld+json

{
  "id": "urn:ngsi-ld:Camera:TTH406",
  "type": "Camera",
  ...
}

# Batch upsert
POST http://stellio:8080/ngsi-ld/v1/entityOperations/upsert
Content-Type: application/ld+json

[
  { entity1 },
  { entity2 },
  ...
]
```

### Publish Report:
```json
{
  "timestamp": "2025-11-01T10:00:00Z",
  "total_entities": 722,
  "successful": 720,
  "failed": 2,
  "duration_seconds": 12.5,
  "errors": [
    {
      "entity_id": "urn:ngsi-ld:Camera:TTH999",
      "status_code": 500,
      "error": "Internal Server Error"
    }
  ]
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Batch splitting logic
   - Retry mechanism
   - Error handling (409, 500)
   - Report generation

2. **Integration Tests (Mock Stellio):**
   - POST entities (200 OK)
   - Handle conflicts (409)
   - Timeout scenarios
   - Auth token injection

3. **Performance:**
   - Publish 722 entities < 30 secondsf
   - Parallel batch requests

4. **Edge Cases:**
   - Empty input
   - All entities fail
   - Network interruption

Write tests in `tests/context_management/test_entity_publisher_agent.py`.

Mock Stellio with responses library: `pytest tests/context_management/ -v --cov --cov-report=html`
```

---

## PROMPT 7: NGSI-LD TO RDF AGENT

```markdown
# Build NGSI-LD to RDF Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│       NGSI-LD TO RDF AGENT WORKFLOW          │
└──────────────────────────────────────────────┘

[Input: validated_entities.json]
         ↓
    Read NGSI-LD JSON-LD
         ↓
    ┌─────────────────────────┐
    │ Parse @context          │
    │ Resolve URIs            │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────────┐
    │ rdflib: Expand JSON-LD      │
    │ to RDF triples              │
    │ (subject-predicate-object)  │
    └──────────┬──────────────────┘
               ↓
    ┌─────────────────────────┐
    │ Serialize RDF:          │
    │ • Turtle (.ttl)         │
    │ • N-Triples (.nt)       │
    │ • RDF/XML (.rdf)        │
    └──────────┬──────────────┘
               ↓
    [Output: cameras.ttl, cameras.nt, cameras.rdf]
```

## IMPLEMENTATION

Create `agents/rdf_linked_data/ngsi_ld_to_rdf_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read validated NGSI-LD entities
- Use rdflib to parse JSON-LD
- Expand to RDF triples
- Serialize to multiple formats:
  - Turtle (human-readable)
  - N-Triples (simple)
  - RDF/XML (standard)
- Namespace management (sosa:, geo:, ngsi-ld:, camera:)
- Output files to `data/rdf/`
- Streaming for large datasets
- Validate RDF syntax

### Namespace Config (namespaces.yaml):
```yaml
namespaces:
  sosa: "http://www.w3.org/ns/sosa/"
  ssn: "http://www.w3.org/ns/ssn/"
  geo: "http://www.w3.org/2003/01/geo/wgs84_pos#"
  schema: "https://schema.org/"
  ngsi-ld: "https://uri.etsi.org/ngsi-ld/"
  camera: "https://smartdatamodels.org/dataModel.Device/Camera/"

output_formats:
  - format: "turtle"
    extension: ".ttl"
  - format: "nt"
    extension: ".nt"
  - format: "xml"
    extension: ".rdf"
```

### Example RDF Output (Turtle):
```turtle
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix camera: <https://smartdatamodels.org/dataModel.Device/Camera/> .

<urn:ngsi-ld:Camera:TTH406> 
    a sosa:Sensor, camera:Camera ;
    camera:cameraName "Trần Quang Khải - Trần Khắc Chân" ;
    camera:cameraType "PTZ" ;
    geo:lat "10.791890"^^xsd:decimal ;
    geo:long "106.691054"^^xsd:decimal ;
    sosa:observes <urn:ngsi-ld:ObservableProperty:TrafficFlow> .
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - JSON-LD parsing
   - Triple generation
   - Namespace resolution
   - Serialization to each format

2. **Validation Tests:**
   - RDF syntax validation
   - Namespace correctness
   - Triple count verification

3. **Integration Tests:**
   - Convert 722 cameras
   - Verify output files exist
   - Parse generated RDF back

4. **Performance:**
   - Convert 722 entities < 20 seconds
   - Memory efficient streaming

Write tests in `tests/rdf_linked_data/test_ngsi_ld_to_rdf_agent.py`.

Run: `pytest tests/rdf_linked_data/test_ngsi_ld_to_rdf_agent.py -v --cov --cov-report=term-missing`
```

---

## PROMPT 8: TRIPLESTORE LOADER AGENT

```markdown
# Build Triplestore Loader Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│      TRIPLESTORE LOADER AGENT WORKFLOW       │
└──────────────────────────────────────────────┘

[Input: cameras.ttl]
         ↓
    Read RDF files (Turtle/N-Triples/RDF-XML)
         ↓
    Load Fuseki config
         ↓
    ┌─────────────────────────┐
    │ Validate RDF syntax     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────────────────┐
    │ POST to Fuseki                      │
    │ http://fuseki:3030/{dataset}/data   │
    │ Content-Type: text/turtle           │
    └──────────┬──────────────────────────┘
               ↓
    ┌─────────────────────────┐
    │ Create named graphs     │
    │ • camera-data           │
    │ • observations          │
    │ • accidents             │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Test SPARQL endpoint    │
    │ SELECT COUNT(*)         │
    └──────────┬──────────────┘
               ↓
    [Fuseki: RDF triples loaded, SPARQL ready]
```

## IMPLEMENTATION

Create `agents/rdf_linked_data/triplestore_loader_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Must work with ANY LOD domain (healthcare, geography, commerce, etc.) without code changes
2. CONFIG-DRIVEN: All endpoint configs in YAML file (config/data_sources.yaml)
3. INDEPENDENT: No dependencies on other agents, standalone executable

### Requirements:
- Read RDF files from `data/rdf/`
- Validate RDF syntax before upload
- POST to Fuseki: `http://fuseki:3030/traffic-cameras/data`
- Support multiple RDF formats (auto-detect)
- Create named graphs for organization
- Configure SPARQL endpoint
- Test endpoint after load
- Retry on failures (3 attempts)
- Generate load report

### Fuseki Config (fuseki.yaml):
```yaml
fuseki:
  base_url: "http://localhost:3030"
  dataset: "traffic-cameras"
  auth:
    username: "admin"
    password: "${FUSEKI_PASSWORD}"
  endpoints:
    data: "/{dataset}/data"
    sparql: "/{dataset}/sparql"
    update: "/{dataset}/update"
  named_graphs:
    - "http://hcmc-traffic/cameras"
    - "http://hcmc-traffic/observations"
    - "http://hcmc-traffic/accidents"
  batch_size: 1000  # triples per request
  timeout: 60
```

### API Calls:
```python
# Load RDF data
POST http://fuseki:3030/traffic-cameras/data
Content-Type: text/turtle

<turtle RDF content>

# Named graph
POST http://fuseki:3030/traffic-cameras/data?graph=http://hcmc-traffic/cameras
Content-Type: text/turtle

# Test SPARQL
POST http://fuseki:3030/traffic-cameras/sparql
Content-Type: application/sparql-query

SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }
```

### Load Report:
```json
{
  "timestamp": "2025-11-01T10:30:00Z",
  "dataset": "traffic-cameras",
  "files_loaded": ["cameras.ttl", "observations.ttl"],
  "total_triples": 8640,
  "named_graphs": [
    "http://hcmc-traffic/cameras"
  ],
  "sparql_endpoint": "http://fuseki:3030/traffic-cameras/sparql",
  "duration_seconds": 5.2,
  "status": "success"
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - RDF syntax validation
   - Graph URI generation
   - Request building

2. **Integration Tests (Mock Fuseki):**
   - Load valid RDF
   - Handle upload errors
   - Test SPARQL queries
   - Auth handling

3. **SPARQL Tests:**
   - Count query
   - Basic SELECT
   - Named graph queries

4. **Performance:**
   - Load 8640 triples < 10 seconds

Write tests in `tests/rdf_linked_data/test_triplestore_loader_agent.py`.

Mock Fuseki: `pytest tests/rdf_linked_data/test_triplestore_loader_agent.py -v --cov --cov-report=html`
```

---

## PROMPT 9: OVERALL WORKFLOW ORCHESTRATION

```markdown
# Overall Multi-Agent Workflow

## COMPLETE SYSTEM WORKFLOW
```
┌─────────────────────────────────────────────────────────────────────┐
│                       MULTI-AGENT SYSTEM                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  PHASE 1: DATA COLLECTION (Layer 1)     │
└──────────────────────────────────────────┘
[cameras_raw.json] (722 cameras)
         ↓
    Image Refresh Agent (30-60s cycle)
         ↓ 
    [cameras_updated.json] + [external_data.json]
         ↓
┌──────────────────────────────────────────┐
│  PHASE 2: TRANSFORMATION (Layer 2)      │
└──────────────────────────────────────────┘
    NGSI-LD Transformer Agent
         ↓
    [ngsi_ld_entities.json]
         ↓
    SOSA/SSN Mapper Agent
         ↓
    [sosa_enhanced_entities.json]
         ↓
┌──────────────────────────────────────────┐
│  PHASE 3: VALIDATION (Layer 5)          │
└──────────────────────────────────────────┘
    Smart Data Models Validation Agent
         ↓
    [validated_entities.json] (LOD ★★★★★)
         ↓
         ├─────────────────────────┬─────────────────────┐
         ↓                         ↓                     ↓
┌─────────────────┐    ┌───────────────────┐  ┌──────────────────┐
│ PHASE 4:        │    │ PHASE 5:          │  │ PHASE 6:         │
│ STELLIO         │    │ RDF CONVERSION    │  │ ANALYTICS        │
│ (Layer 4)       │    │ (Layer 5)         │  │ (Layer 3)        │
└─────────────────┘    └───────────────────┘  └──────────────────┘
Entity Publisher       NGSI-LD to RDF         CV Analysis
     ↓                      ↓                       ↓
Stellio Context      [cameras.ttl/.nt/.rdf]   Traffic Metrics
Broker :8080              ↓                         ↓
     ↓                Triplestore Loader       ItemFlowObserved
Neo4j Graph          Agent                          ↓
Database                  ↓                    Accident Detection
     ↓                Fuseki :3030                   ↓
Temporal Manager          ↓                    RoadAccident
     ↓                SPARQL Endpoint                ↓
Subscriptions             ↓                    Pattern Recognition
     ↓                    ↓                          ↓
     └────────────────────┴──────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│  PHASE 7: INTEGRATION & ACCESS (Layers 6,8)        │
└─────────────────────────────────────────────────────┘
    API Gateway (Kong)
         ↓
    ┌────────────────────────┬────────────────────┐
    ↓                        ↓                    ↓
Stellio NGSI-LD API    Fuseki SPARQL      Alert Dispatcher
(Operational)          (Semantic)          (WebSocket/FCM)
    ↓                        ↓                    ↓
Neo4j Graph Queries    Linked Data         Notifications
                       Queries
         ↓                   ↓                    ↓
         └───────────────────┴────────────────────┘
                          ↓
                    [Web/Mobile Apps]
```

## ORCHESTRATION IMPLEMENTATION

Create `orchestrator.py`:

### Requirements:
- Sequential agent execution with dependency management
- Each phase waits for previous completion
- Error handling: retry failed agents
- Progress tracking and logging
- Parallel execution where possible (Phase 4-6)
- Health checks between phases
- Configuration-driven workflow
- Generate final system report

### Execution Flow:
```python
# Phase 1: Data Collection
run_agent("image_refresh_agent")
run_agent("external_data_collector_agent")

# Phase 2: Transformation
run_agent("ngsi_ld_transformer_agent")
run_agent("sosa_ssn_mapper_agent")

# Phase 3: Validation
run_agent("smart_data_models_validation_agent")

# Phase 4-6: Parallel execution
parallel_run([
    "entity_publisher_agent",
    "ngsi_ld_to_rdf_agent",
    "cv_analysis_agent"
])

# Phase 5 continued:
run_agent("triplestore_loader_agent")

# Phase 7: Integration ready
verify_endpoints([
    "http://stellio:8080/ngsi-ld/v1/entities",
    "http://fuseki:3030/traffic-cameras/sparql"
])
```

### Workflow Config (workflow.yaml):
```yaml
workflow:
  phases:
    - name: "Data Collection"
      agents:
        - image_refresh_agent
        - external_data_collector_agent
      parallel: true
      
    - name: "Transformation"
      agents:
        - ngsi_ld_transformer_agent
        - sosa_ssn_mapper_agent
      parallel: false
      
    - name: "Validation"
      agents:
        - smart_data_models_validation_agent
      parallel: false
      
    - name: "Publishing"
      agents:
        - entity_publisher_agent
        - ngsi_ld_to_rdf_agent
        - cv_analysis_agent
      parallel: true
      
    - name: "RDF Loading"
      agents:
        - triplestore_loader_agent
      parallel: false

  retry_policy:
    max_attempts: 3
    backoff: exponential
    
  health_checks:
    - endpoint: "http://stellio:8080/health"
    - endpoint: "http://fuseki:3030/$/ping"
```

### System Report:
```json
{
  "execution_time": "2025-11-01T10:00:00Z",
  "total_duration_seconds": 120,
  "phases": [
    {
      "name": "Data Collection",
      "status": "success",
      "duration": 35.2,
      "agents": [
        {"name": "image_refresh_agent", "status": "success"},
        {"name": "external_data_collector_agent", "status": "success"}
      ]
    }
  ],
  "endpoints": {
    "stellio_ngsi_ld": "http://stellio:8080/ngsi-ld/v1/entities",
    "neo4j_browser": "http://neo4j:7474",
    "fuseki_sparql": "http://fuseki:3030/traffic-cameras/sparql"
  },
  "statistics": {
    "cameras_processed": 722,
    "ngsi_ld_entities": 722,
    "rdf_triples": 8640,
    "lod_rating_average": 5.0
  }
}
```

### Testing Requirements:
1. **Integration Tests:**
   - Full workflow execution (mock all services)
   - Phase dependency validation
   - Error recovery

2. **E2E Tests:**
   - Run against real Stellio + Fuseki
   - Verify data in Neo4j
   - Query SPARQL endpoint

3. **Performance:**
   - Complete workflow < 3 minutes

Write tests in `tests/test_orchestrator.py`.

Run: `pytest tests/test_orchestrator.py -v --cov=orchestrator --cov-report=html`
```

---

**NOTES:**
- Remaining agents (CV Analysis, Congestion Detection, Accident Detection, Temporal Manager, etc.) follow similar patterns
- Focus on the core data pipeline first (Prompts 1-9)
- Analytics agents can be built incrementally after core is stable
- All agents must be independently testable with 100% coverage
- Config-driven design allows easy adaptation to other LOD domains



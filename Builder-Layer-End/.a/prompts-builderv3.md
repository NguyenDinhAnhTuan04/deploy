# GITHUB COPILOT PROMPTS - REMAINING AGENTS (10-25)
Stellio 2.26.1 KHÔNG HỖ TRỢ Neo4j natively! Stellio chỉ dùng PostgreSQL. Tôi cần tạo một connector agent mới để sync data từ Stellio PostgreSQL sang Neo4j:
---

## PROMPT 10: CV ANALYSIS AGENT

```markdown
# Build CV Analysis Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│       CV ANALYSIS AGENT WORKFLOW             │
└──────────────────────────────────────────────┘

[Input: cameras_updated.json + image URLs]
         ↓
    Scheduler (fetch every 60s)
         ↓
    ┌─────────────────────────┐
    │ Download camera images  │
    │ (async, batch=20)       │
    └──────────┬────────────┬─┘
               ↓            ↓
         Valid image    Failed
               ↓            ↓
    ┌─────────────────┐  Log error
    │ YOLOv8 detect   │
    │ - cars          │
    │ - motorbikes    │
    │ - buses         │
    │ - trucks        │
    └──────────┬──────┘
               ↓
    Calculate metrics:
    - vehicleCount
    - intensity (vehicles/frame)
    - occupancy (0.0-1.0)
    - averageSpeed (estimated)
               ↓
    Create ItemFlowObserved entity
               ↓
    [Output: observations.json]
```

## IMPLEMENTATION

Create `agents/analytics/cv_analysis_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Works with any image source
2. CONFIG-DRIVEN: All CV model configs in YAML
3. INDEPENDENT: Standalone execution

### Requirements:
- Download images from `imageSnapshot` URLs
- YOLOv8 object detection (pretrained COCO)
- Vehicle classification: car, motorbike, bus, truck, person
- Calculate traffic metrics per camera
- Generate NGSI-LD ItemFlowObserved entities
- Batch inference: 20 images parallel
- Model caching (avoid reload)
- Output observations with temporal data

### Config Schema (cv_config.yaml):
```yaml
cv_analysis:
  model:
    type: "yolov8"
    weights: "yolov8n.pt"  # nano for speed
    confidence: 0.5
    device: "cpu"  # or "cuda"
  
  vehicle_classes:
    - car
    - motorbike
    - bus
    - truck
  
  metrics:
    intensity_threshold: 0.7  # >70% = congested
    speed_estimation: "optical_flow"  # or "distance_based"
  
  batch_size: 20
  timeout: 10
  output_file: "data/observations.json"
```

### ItemFlowObserved Entity Format:
```json
{
  "id": "urn:ngsi-ld:ItemFlowObserved:TTH406-{timestamp}",
  "type": "ItemFlowObserved",
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH406"
  },
  "location": {
    "type": "GeoProperty",
    "value": {"type": "Point", "coordinates": [106.691, 10.791]}
  },
  "intensity": {
    "type": "Property",
    "value": 0.75,
    "observedAt": "2025-11-01T10:00:00Z"
  },
  "occupancy": {
    "type": "Property",
    "value": 0.82
  },
  "averageSpeed": {
    "type": "Property",
    "value": 15.5,
    "unitCode": "KMH"
  },
  "vehicleCount": {
    "type": "Property",
    "value": 45
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Image download
   - YOLO inference mock
   - Metric calculation
   - Entity generation

2. **Integration Tests:**
   - Process 10 camera images
   - Verify observation format
   - Handle download failures

3. **Performance:**
   - Process 722 cameras < 2 minutes
   - GPU acceleration if available

Write tests in `tests/analytics/test_cv_analysis_agent.py`.
```

---

## PROMPT 11: CONGESTION DETECTION AGENT

```markdown
# Build Congestion Detection Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│     CONGESTION DETECTION AGENT WORKFLOW      │
└──────────────────────────────────────────────┘

[Input: observations.json]
         ↓
    Read ItemFlowObserved entities
         ↓
    For each observation:
         ↓
    ┌─────────────────────────┐
    │ Check thresholds:       │
    │ - occupancy > 0.7       │
    │ - averageSpeed < 15 km/h│
    │ - intensity > 0.75      │
    └──────────┬──────────────┘
               ↓
    ┌──────────────────┐
    │ Congested?       │
    └───┬──────────┬───┘
       YES        NO
        ↓          ↓
    Update      Skip
    Camera
    entity
        ↓
    POST/PATCH to Stellio:
    {congested: true}
        ↓
    [Neo4j: Camera.congested updated]
```

## IMPLEMENTATION

Create `agents/analytics/congestion_detection_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Threshold-based logic adaptable
2. CONFIG-DRIVEN: Thresholds in YAML
3. INDEPENDENT: Standalone execution

### Requirements:
- Read observations from CV Analysis output
- Apply congestion detection rules
- Update Camera entities in Stellio
- PATCH only changed attributes
- Track congestion state changes
- Alert on new congestion events
- Historical trend analysis (optional)

### Config Schema (congestion_config.yaml):
```yaml
congestion_detection:
  thresholds:
    occupancy: 0.7
    average_speed: 15  # km/h
    intensity: 0.75
  
  rules:
    logic: "AND"  # occupancy > 0.7 AND speed < 15
    min_duration: 120  # seconds (ignore transient)
  
  stellio:
    update_endpoint: "/ngsi-ld/v1/entities/{id}/attrs"
    batch_updates: true
  
  alert:
    enabled: true
    notify_on_change: true  # only when false→true
```

### PATCH Request Example:
```bash
PATCH http://stellio:8080/ngsi-ld/v1/entities/urn:ngsi-ld:Camera:TTH406/attrs
Content-Type: application/ld+json

{
  "congested": {
    "type": "Property",
    "value": true,
    "observedAt": "2025-11-01T10:00:00Z"
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Threshold evaluation
   - State change detection
   - PATCH request building

2. **Integration Tests:**
   - Mock Stellio responses
   - Process 722 observations
   - Verify updates

3. **Edge Cases:**
   - Missing observation fields
   - Stellio connection failures
   - Rapid state changes

Write tests in `tests/analytics/test_congestion_detection_agent.py`.
```

---

## PROMPT 12: ACCIDENT DETECTION AGENT

```markdown
# Build Accident Detection Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│      ACCIDENT DETECTION AGENT WORKFLOW       │
└──────────────────────────────────────────────┘

[Input: camera images + observations]
         ↓
    Analyze anomalies:
         ↓
    ┌─────────────────────────┐
    │ Methods:                │
    │ 1. Sudden stop          │
    │ 2. Object on road       │
    │ 3. Speed variance spike │
    │ 4. Unusual patterns     │
    └──────────┬──────────────┘
               ↓
    ┌──────────────────┐
    │ Accident likely? │
    └───┬──────────┬───┘
       YES        NO
        ↓          ↓
    Create    Continue
    RoadAccident
    entity
        ↓
    POST to Stellio
        ↓
    Trigger alert
        ↓
    [Neo4j: RoadAccident node + relationships]
```

## IMPLEMENTATION

Create `agents/analytics/accident_detection_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Anomaly detection framework
2. CONFIG-DRIVEN: Detection parameters in YAML
3. INDEPENDENT: Standalone execution

### Requirements:
- Anomaly detection from observations
- Multiple detection methods:
  - Statistical (speed variance)
  - Rule-based (occupancy spike)
  - Optional: ML model (future)
- Create RoadAccident NGSI-LD entities
- Link to Camera via Relationship
- Severity classification (minor/moderate/severe)
- False positive filtering

### Config Schema (accident_config.yaml):
```yaml
accident_detection:
  methods:
    - name: "speed_variance"
      enabled: true
      threshold: 3.0  # std deviations
    
    - name: "occupancy_spike"
      enabled: true
      spike_factor: 2.0  # 2x normal
    
    - name: "sudden_stop"
      enabled: false  # requires video analysis
  
  severity_thresholds:
    minor: 0.3
    moderate: 0.6
    severe: 0.9
  
  filtering:
    min_confidence: 0.5
    cooldown_period: 300  # seconds between same-camera alerts
```

### RoadAccident Entity:
```json
{
  "id": "urn:ngsi-ld:RoadAccident:TTH406-{timestamp}",
  "type": "RoadAccident",
  "location": {
    "type": "GeoProperty",
    "value": {"type": "Point", "coordinates": [106.691, 10.791]}
  },
  "refCamera": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH406"
  },
  "accidentDate": {
    "type": "Property",
    "value": {"@type": "DateTime", "@value": "2025-11-01T10:00:00Z"}
  },
  "severity": {
    "type": "Property",
    "value": "moderate"
  },
  "detectionMethod": {
    "type": "Property",
    "value": "speed_variance"
  },
  "confidence": {
    "type": "Property",
    "value": 0.75
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Each detection method
   - Severity classification
   - Cooldown logic

2. **Integration Tests:**
   - Process anomaly scenarios
   - Entity creation
   - Mock Stellio POST

3. **False Positive Tests:**
   - Rush hour patterns (not accidents)
   - Camera angle changes
   - Weather conditions

Write tests in `tests/analytics/test_accident_detection_agent.py`.
```

---

## PROMPT 13: PATTERN RECOGNITION AGENT

```markdown
# Build Pattern Recognition Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│     PATTERN RECOGNITION AGENT WORKFLOW       │
└──────────────────────────────────────────────┘

[Input: observations.json (time-series)]
         ↓
    Load historical data from Neo4j
         ↓
    ┌─────────────────────────┐
    │ Pattern Analysis:       │
    │ - Daily rush hours      │
    │ - Weekly trends         │
    │ - Seasonal patterns     │
    │ - Anomaly detection     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Predictions:            │
    │ - Next hour forecast    │
    │ - Peak time estimates   │
    └──────────┬──────────────┘
               ↓
    Create TrafficPattern entities
               ↓
    Update Camera with predictions
               ↓
    [Output: patterns.json + Neo4j graph]
```

## IMPLEMENTATION

Create `agents/analytics/pattern_recognition_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Time-series analysis framework
2. CONFIG-DRIVEN: Analysis parameters in YAML
3. INDEPENDENT: Standalone execution

### Requirements:
- Query Neo4j temporal data (Cypher)
- Time-series analysis (pandas, statsmodels)
- Pattern detection:
  - Hourly patterns (0-23h)
  - Day-of-week patterns
  - Holiday vs normal day
- Simple forecasting (moving average, ARIMA)
- Visualization data generation (optional)

### Config Schema (pattern_config.yaml):
```yaml
pattern_recognition:
  neo4j:
    uri: "bolt://neo4j:7687"
    auth:
      username: "neo4j"
      password: "${NEO4J_PASSWORD}"
  
  analysis:
    time_windows:
      - "1_hour"
      - "1_day"
      - "7_days"
    
    metrics:
      - intensity
      - occupancy
      - congested_count
  
  patterns:
    rush_hours:
      morning: [7, 9]  # 7am-9am
      evening: [17, 19]
    
    anomaly_detection:
      method: "zscore"
      threshold: 2.5
  
  forecasting:
    enabled: true
    method: "moving_average"
    window: 7  # days
```

### Cypher Query Example:
```cypher
MATCH (c:Camera {id: 'urn:ngsi-ld:Camera:TTH406'})
      -[:HAS_OBSERVATION]->(o:Observation)
WHERE o.observedAt >= datetime() - duration('P7D')
RETURN o.observedAt, o.intensity, o.occupancy
ORDER BY o.observedAt
```

### TrafficPattern Entity:
```json
{
  "id": "urn:ngsi-ld:TrafficPattern:TTH406-weekly",
  "type": "TrafficPattern",
  "refCamera": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH406"
  },
  "patternType": {
    "type": "Property",
    "value": "weekly"
  },
  "rushHours": {
    "type": "Property",
    "value": [
      {"hour": 7, "intensity": 0.8},
      {"hour": 17, "intensity": 0.9}
    ]
  },
  "forecast": {
    "type": "Property",
    "value": {
      "nextHour": 0.65,
      "confidence": 0.75
    }
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Time window calculations
   - Pattern detection algorithms
   - Forecast generation

2. **Integration Tests:**
   - Mock Neo4j responses
   - Process 7-day data
   - Entity creation

3. **Statistical Tests:**
   - Verify rush hour detection
   - Anomaly identification accuracy

Write tests in `tests/analytics/test_pattern_recognition_agent.py`.
```

---

## PROMPT 14: STATE UPDATER AGENT

```markdown
# Build State Updater Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│        STATE UPDATER AGENT WORKFLOW          │
└──────────────────────────────────────────────┘

[Input: Real-time events from queue/webhook]
         ↓
    Listen to event stream
         ↓
    ┌─────────────────────────┐
    │ Event types:            │
    │ - Image refresh         │
    │ - Congestion change     │
    │ - Observation update    │
    └──────────┬──────────────┘
               ↓
    Parse entity ID + attributes
               ↓
    ┌─────────────────────────┐
    │ PATCH Stellio entity    │
    │ - Atomic updates        │
    │ - Preserve history      │
    └──────────┬──────────────┘
               ↓
    Verify update success
               ↓
    [Neo4j: Entity state updated]
```

## IMPLEMENTATION

Create `agents/context_management/state_updater_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic entity updater
2. CONFIG-DRIVEN: Event mappings in YAML
3. INDEPENDENT: Standalone event listener

### Requirements:
- Subscribe to event sources (Kafka/WebSocket/HTTP)
- Parse update events
- PATCH Stellio entities atomically
- Handle concurrent updates (retry with backoff)
- Track update statistics
- Rollback on failures (optional)

### Config Schema (state_updater_config.yaml):
```yaml
state_updater:
  event_sources:
    - type: "kafka"
      topic: "camera-updates"
      bootstrap_servers: "kafka:9092"
    
    - type: "webhook"
      endpoint: "/updates"
      port: 8081
  
  stellio:
    base_url: "http://stellio:8080"
    timeout: 10
    retry:
      max_attempts: 3
      backoff_factor: 2
  
  update_rules:
    imageSnapshot:
      method: "PATCH"
      attrs: ["imageSnapshot", "observedAt"]
    
    congested:
      method: "PATCH"
      attrs: ["congested"]
      notify: true
```

### Event Format:
```json
{
  "entity_id": "urn:ngsi-ld:Camera:TTH406",
  "updates": {
    "imageSnapshot": {
      "type": "Property",
      "value": "https://...",
      "observedAt": "2025-11-01T10:00:00Z"
    }
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Event parsing
   - PATCH request building
   - Retry logic

2. **Integration Tests:**
   - Mock Kafka consumer
   - Mock Stellio endpoint
   - Concurrent updates

3. **Stress Tests:**
   - 100 updates/second
   - Network failures
   - Duplicate events

Write tests in `tests/context_management/test_state_updater_agent.py`.
```

---

## PROMPT 15: TEMPORAL DATA MANAGER AGENT

```markdown
# Build Temporal Data Manager Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│     TEMPORAL DATA MANAGER AGENT WORKFLOW     │
└──────────────────────────────────────────────┘

[Input: Observations with timestamps]
         ↓
    For each observation:
         ↓
    ┌─────────────────────────┐
    │ Store temporal instance │
    │ POST /temporal/entities │
    │ /{id}/attrs             │
    └──────────┬──────────────┘
               ↓
    Neo4j creates time-indexed node
               ↓
    ┌─────────────────────────┐
    │ Retention policy:       │
    │ - Keep 30 days detailed │
    │ - Aggregate 30-90 days  │
    │ - Archive >90 days      │
    └──────────┬──────────────┘
               ↓
    Periodic cleanup job
               ↓
    [Neo4j: Optimized temporal storage]
```

## IMPLEMENTATION

Create `agents/context_management/temporal_data_manager_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic temporal storage
2. CONFIG-DRIVEN: Retention policies in YAML
3. INDEPENDENT: Standalone cron-like execution

### Requirements:
- POST temporal instances to Stellio
- Implement data retention policies
- Aggregate old data (hourly → daily averages)
- Archive to cold storage (S3/filesystem)
- Query optimization (Neo4j indexes)
- Cleanup expired data

### Config Schema (temporal_config.yaml):
```yaml
temporal_data_manager:
  stellio:
    temporal_endpoint: "/ngsi-ld/v1/temporal/entities"
  
  retention:
    detailed:
      period: 30  # days
      resolution: "full"  # every observation
    
    aggregated:
      period: 60  # days 30-90
      resolution: "hourly"  # avg per hour
    
    archived:
      period: 365  # days
      storage: "s3"
      bucket: "traffic-archive"
  
  cleanup:
    schedule: "0 2 * * *"  # 2am daily
    batch_size: 1000
  
  aggregation:
    metrics:
      - name: "intensity"
        method: "mean"
      - name: "occupancy"
        method: "max"
```

### Temporal POST Example:
```bash
POST http://stellio:8080/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:Camera:TTH406/attrs
Content-Type: application/ld+json

{
  "intensity": [
    {
      "type": "Property",
      "value": 0.75,
      "observedAt": "2025-11-01T10:00:00Z"
    },
    {
      "type": "Property",
      "value": 0.78,
      "observedAt": "2025-11-01T10:01:00Z"
    }
  ]
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Retention logic
   - Aggregation calculations
   - Archive path generation

2. **Integration Tests:**
   - Mock Stellio temporal API
   - Cleanup simulation
   - Query optimization

3. **Data Integrity:**
   - Verify no data loss
   - Aggregation accuracy
   - Archive retrieval

Write tests in `tests/context_management/test_temporal_data_manager_agent.py`.
```

---

## PROMPT 16: SUBSCRIPTION MANAGER AGENT

```markdown
# Build Subscription Manager Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│     SUBSCRIPTION MANAGER AGENT WORKFLOW      │
└──────────────────────────────────────────────┘

[Config: subscriptions.yaml]
         ↓
    Load subscription definitions
         ↓
    ┌─────────────────────────┐
    │ For each subscription:  │
    │ - Entity type filter    │
    │ - Attribute watchlist   │
    │ - Notification endpoint │
    └──────────┬──────────────┘
               ↓
    POST to Stellio /subscriptions
               ↓
    ┌─────────────────────────┐
    │ Monitor subscription:   │
    │ - Status check          │
    │ - Renewal before expiry │
    │ - Error handling        │
    └──────────┬──────────────┘
               ↓
    [Stellio: Active subscriptions]
```

## IMPLEMENTATION

Create `agents/notification/subscription_manager_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic subscription framework
2. CONFIG-DRIVEN: Subscriptions in YAML
3. INDEPENDENT: Standalone manager

### Requirements:
- Create NGSI-LD subscriptions via Stellio API
- Monitor subscription health
- Auto-renew expiring subscriptions
- Handle subscription failures
- CRUD operations (Create, Read, Update, Delete)
- Subscription templates

### Config Schema (subscriptions.yaml):
```yaml
subscriptions:
  - name: "congestion-alerts"
    description: "Notify when congestion detected"
    entities:
      - type: "Camera"
    watched_attributes:
      - "congested"
    notification:
      endpoint:
        uri: "http://alert-dispatcher:8080/notify"
        accept: "application/json"
    q: "congested==true"  # NGSI-LD query
    throttling: 60  # seconds
    expires_at: "2026-11-01T00:00:00Z"
  
  - name: "accident-alerts"
    entities:
      - type: "RoadAccident"
    notification:
      endpoint:
        uri: "http://alert-dispatcher:8080/accident"
    throttling: 0  # immediate
```

### Stellio Subscription API:
```bash
POST http://stellio:8080/ngsi-ld/v1/subscriptions
Content-Type: application/ld+json

{
  "type": "Subscription",
  "entities": [{"type": "Camera"}],
  "watchedAttributes": ["congested"],
  "q": "congested==true",
  "notification": {
    "endpoint": {
      "uri": "http://alert-dispatcher:8080/notify",
      "accept": "application/json"
    }
  },
  "throttling": 60,
  "expiresAt": "2026-11-01T00:00:00Z"
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Subscription creation
   - Expiry checking
   - Renewal logic

2. **Integration Tests:**
   - Mock Stellio subscription API
   - Create/delete operations
   - Health monitoring

3. **Edge Cases:**
   - Invalid endpoints
   - Network failures
   - Duplicate subscriptions

Write tests in `tests/notification/test_subscription_manager_agent.py`.
```

---

## PROMPT 17: ALERT DISPATCHER AGENT

```markdown
# Build Alert Dispatcher Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│       ALERT DISPATCHER AGENT WORKFLOW        │
└──────────────────────────────────────────────┘

[Input: Webhook from Stellio subscriptions]
         ↓
    HTTP server listening on :8080
         ↓
    ┌─────────────────────────┐
    │ Parse notification:     │
    │ - Entity ID             │
    │ - Changed attributes    │
    │ - Timestamp             │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Route by alert type:    │
    │ - Congestion → SMS      │
    │ - Accident → Push       │
    │ - Pattern → Email       │
    └──────────┬──────────────┘
               ↓
    Send via channels:
    - WebSocket (realtime)
    - Firebase (mobile push)
    - Email (SMTP)
    - SMS (Twilio)
               ↓
    Log delivery status
               ↓
    [Users notified]
```

## IMPLEMENTATION

Create `agents/notification/alert_dispatcher_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Multi-channel notification system
2. CONFIG-DRIVEN: Channels and routing in YAML
3. INDEPENDENT: Standalone HTTP server

### Requirements:
- HTTP server for Stellio webhooks
- Multi-channel delivery:
  - WebSocket (Socket.IO)
  - Firebase Cloud Messaging (FCM)
  - Email (SMTP)
  - SMS (Twilio API)
- Priority-based routing
- Retry failed deliveries
- Rate limiting per user
- Template engine for messages

### Config Schema (alert_dispatcher_config.yaml):
```yaml
alert_dispatcher:
  server:
    host: "0.0.0.0"
    port: 8080
  
  channels:
    websocket:
      enabled: true
      url: "ws://alert-dispatcher:8080/ws"
    
    fcm:
      enabled: true
      server_key: "${FCM_SERVER_KEY}"
      priority: "high"
    
    email:
      enabled: true
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      from_addr: "traffic@hcmc.gov.vn"
    
    sms:
      enabled: false
      provider: "twilio"
      account_sid: "${TWILIO_SID}"
  
  routing_rules:
    congestion:
      channels: ["websocket", "fcm"]
      priority: "medium"
    
    accident:
      channels: ["websocket", "fcm", "sms"]
      priority: "high"
    
    pattern:
      channels: ["email"]
      priority: "low"
  
  rate_limiting:
    max_per_user: 10  # alerts per hour
```

### Message Template:
```yaml
templates:
  congestion:
    title: "Traffic Congestion Alert"
    body: "Heavy traffic detected at {{camera_name}}. Average speed: {{speed}} km/h."
  
  accident:
    title: "⚠️ Traffic Accident"
    body: "Possible accident at {{location}}. Severity: {{severity}}. Time: {{time}}."
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Webhook parsing
   - Routing logic
   - Template rendering

2. **Integration Tests:**
   - Mock FCM/SMTP/Twilio
   - WebSocket connections
   - Delivery retries

3. **Load Tests:**
   - 100 concurrent notifications
   - Rate limiter effectiveness

Write tests in `tests/notification/test_alert_dispatcher_agent.py`.
```

---

## PROMPT 18: INCIDENT REPORT GENERATOR AGENT

```markdown
# Build Incident Report Generator Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│   INCIDENT REPORT GENERATOR AGENT WORKFLOW   │
└──────────────────────────────────────────────┘

[Trigger: RoadAccident entity created]
         ↓
    Query related data:
    - Camera details
    - Recent observations
    - Weather conditions
    - Historical patterns
         ↓
    ┌─────────────────────────┐
    │ Generate report:        │
    │ - Summary               │
    │ - Timeline              │
    │ - Impact analysis       │
    │ - Recommendations       │
    └──────────┬──────────────┘
               ↓
    Render formats:
    - PDF (ReportLab)
    - JSON (API)
    - HTML (web view)
               ↓
    Store in filesystem/S3
               ↓
    Notify stakeholders
               ↓
    [Output: incident_reports/]
```

## IMPLEMENTATION

Create `agents/notification/incident_report_generator_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Template-based reporting
2. CONFIG-DRIVEN: Report formats in YAML
3. INDEPENDENT: Standalone generator

### Requirements:
- Subscribe to RoadAccident entities
- Query Neo4j for context data
- Generate multi-format reports
- Include visualizations (charts, maps)
- Store reports persistently
- Email reports to admins
- API endpoint for report retrieval

### Config Schema (incident_report_config.yaml):
```yaml
incident_report_generator:
  triggers:
    - entity_type: "RoadAccident"
      severity: ["moderate", "severe"]  # skip minor
  
  data_sources:
    neo4j:
      uri: "bolt://neo4j:7687"
      queries:
        context: |
          MATCH (a:RoadAccident)-[:DETECTED_BY]->(c:Camera)
          WHERE a.id = $accident_id
          RETURN c, a
        
        timeline: |
          MATCH (c:Camera)-[:HAS_OBSERVATION]->(o:Observation)
          WHERE c.id = $camera_id
            AND o.observedAt >= $start_time
            AND o.observedAt <= $end_time
          RETURN o
  
  report_formats:
    - type: "pdf"
      template: "templates/incident_report.html"
      engine: "weasyprint"
    
    - type: "json"
      fields: ["summary", "timeline", "impact"]
    
    - type: "html"
      template: "templates/incident_web.html"
  
  storage:
    path: "data/incident_reports/"
    naming: "incident_{accident_id}_{timestamp}"
  
  notifications:
    email_to: ["admin@hcmc.gov.vn"]
    subject: "Incident Report: {{accident_id}}"
```

### Report Structure:
```json
{
  "report_id": "RPT-2025-11-01-001",
  "accident_id": "urn:ngsi-ld:RoadAccident:TTH406-1730448000",
  "generated_at": "2025-11-01T10:05:00Z",
  "summary": {
    "location": "Trần Quang Khải - Trần Khắc Chân",
    "severity": "moderate",
    "detection_time": "2025-11-01T10:00:00Z",
    "estimated_clearance": "2025-11-01T10:30:00Z"
  },
  "timeline": [
    {"time": "09:55", "event": "Normal traffic flow"},
    {"time": "10:00", "event": "Speed variance spike detected"},
    {"time": "10:01", "event": "Accident confirmed"}
  ],
  "impact": {
    "affected_cameras": ["TTH406", "TTH407"],
    "avg_speed_drop": "45%",
    "congestion_duration": "30 minutes"
  },
  "recommendations": [
    "Deploy traffic police to scene",
    "Activate alternate routes via GPS apps"
  ]
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Query building
   - Template rendering
   - Format conversion (JSON→PDF)

2. **Integration Tests:**
   - Mock Neo4j data
   - Generate sample reports
   - Email delivery

3. **PDF Tests:**
   - Valid PDF structure
   - Embedded images
   - Multi-page layout

Write tests in `tests/notification/test_incident_report_generator_agent.py`.
```

---

## PROMPT 19: HEALTH CHECK AGENT

```markdown
# Build Health Check Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│        HEALTH CHECK AGENT WORKFLOW           │
└──────────────────────────────────────────────┘

[Scheduler: every 5 minutes]
         ↓
    ┌─────────────────────────┐
    │ Check services:         │
    │ - Stellio API           │
    │ - Neo4j                 │
    │ - Fuseki SPARQL         │
    │ - Kafka                 │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Check data quality:     │
    │ - 722 cameras online?   │
    │ - Recent observations?  │
    │ - Image URLs valid?     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Health status:          │
    │ - GREEN: all OK         │
    │ - YELLOW: degraded      │
    │ - RED: critical failure │
    └──────────┬──────────────┘
               ↓
    Update health dashboard
               ↓
    Alert if status changes
               ↓
    [Metrics exported to Prometheus]
```

## IMPLEMENTATION

Create `agents/monitoring/health_check_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic health check framework
2. CONFIG-DRIVEN: Check definitions in YAML
3. INDEPENDENT: Standalone monitoring

### Requirements:
- Periodic health checks (cron-like)
- Service availability tests (HTTP/TCP)
- Data quality validation
- Performance metrics collection
- Prometheus metrics export
- Alert on status changes
- Health dashboard endpoint

### Config Schema (health_check_config.yaml):
```yaml
health_check:
  interval: 300  # seconds (5 min)
  
  checks:
    - name: "stellio_api"
      type: "http"
      url: "http://stellio:8080/health"
      timeout: 5
      expected_status: 200
    
    - name: "neo4j"
      type: "cypher"
      uri: "bolt://neo4j:7687"
      query: "RETURN 1"
      timeout: 5
    
    - name: "fuseki_sparql"
      type: "sparql"
      url: "http://fuseki:3030/traffic-cameras/sparql"
      query: "ASK { ?s ?p ?o }"
      timeout: 10
    
    - name: "cameras_online"
      type: "data_quality"
      check: "count_cameras"
      threshold:
        min: 700  # at least 700/722 cameras
    
    - name: "recent_observations"
      type: "data_quality"
      check: "latest_observation_age"
      threshold:
        max: 300  # less than 5 min old
  
  alerting:
    on_state_change: true
    webhook: "http://alert-dispatcher:8080/health-alert"
  
  prometheus:
    enabled: true
    port: 9090
    metrics:
      - health_status{service="stellio"}
      - cameras_online_count
      - observation_age_seconds
```

### Health Status Response:
```json
{
  "status": "GREEN",
  "timestamp": "2025-11-01T10:00:00Z",
  "checks": [
    {
      "name": "stellio_api",
      "status": "OK",
      "response_time_ms": 45
    },
    {
      "name": "neo4j",
      "status": "OK",
      "response_time_ms": 12
    },
    {
      "name": "cameras_online",
      "status": "OK",
      "value": 720,
      "threshold": 700
    }
  ],
  "uptime_percent": 99.8
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Each check type
   - Status aggregation
   - Threshold evaluation

2. **Integration Tests:**
   - Mock service endpoints
   - Simulate failures
   - Alert triggering

3. **Prometheus Tests:**
   - Metrics format
   - Scrape endpoint

Write tests in `tests/monitoring/test_health_check_agent.py`.
```

---

## PROMPT 20: DATA QUALITY VALIDATOR AGENT

```markdown
# Build Data Quality Validator Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│    DATA QUALITY VALIDATOR AGENT WORKFLOW     │
└──────────────────────────────────────────────┘

[Input: Any NGSI-LD entity before publishing]
         ↓
    ┌─────────────────────────┐
    │ Schema validation:      │
    │ - Required fields       │
    │ - Data types            │
    │ - @context validity     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Business rules:         │
    │ - Lat/lng ranges        │
    │ - Speed realistic?      │
    │ - Timestamps ordered?   │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Quality score:          │
    │ 0.0 - 1.0               │
    │ (weighted criteria)     │
    └──────────┬──────────────┘
               ↓
    ┌──────────────────┐
    │ Quality OK?      │
    └───┬──────────┬───┘
       YES        NO
        ↓          ↓
    Accept    Reject + Log
        ↓
    [Output: quality_report.json]
```

## IMPLEMENTATION

Create `agents/monitoring/data_quality_validator_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Rule engine adaptable
2. CONFIG-DRIVEN: Validation rules in YAML
3. INDEPENDENT: Standalone validator

### Requirements:
- Pre-publish validation hook
- JSON Schema validation
- Custom business rules engine
- Quality score calculation
- Detailed error reporting
- Automatic data cleaning (optional)
- Integration with Entity Publisher

### Config Schema (data_quality_config.yaml):
```yaml
data_quality_validator:
  schema_validation:
    enabled: true
    strict_mode: false  # allow extra fields
  
  business_rules:
    - name: "valid_coordinates"
      field: "location.value.coordinates"
      rules:
        - "longitude >= 106.5 AND longitude <= 107.0"
        - "latitude >= 10.5 AND latitude <= 11.0"
      weight: 1.0
    
    - name: "realistic_speed"
      field: "averageSpeed.value"
      rules:
        - "speed >= 0 AND speed <= 120"  # km/h
      weight: 0.8
    
    - name: "timestamp_order"
      field: "observedAt"
      rules:
        - "observedAt <= now()"
        - "observedAt >= now() - 24h"
      weight: 0.5
    
    - name: "image_url_accessible"
      field: "imageSnapshot.value"
      rules:
        - "http_head(url) == 200"
      weight: 0.6
  
  quality_thresholds:
    accept: 0.7  # score >= 0.7 passes
    warn: 0.5    # 0.5-0.7 warns
    reject: 0.5  # score < 0.5 rejects
  
  data_cleaning:
    enabled: true
    rules:
      - fix_timezone  # convert to UTC
      - trim_whitespace
      - normalize_case
```

### Validation Result:
```json
{
  "entity_id": "urn:ngsi-ld:Camera:TTH406",
  "validation_timestamp": "2025-11-01T10:00:00Z",
  "quality_score": 0.85,
  "status": "PASS",
  "checks": [
    {
      "rule": "valid_coordinates",
      "passed": true,
      "weight": 1.0
    },
    {
      "rule": "realistic_speed",
      "passed": true,
      "weight": 0.8
    },
    {
      "rule": "image_url_accessible",
      "passed": false,
      "error": "HTTP 404",
      "weight": 0.6
    }
  ],
  "errors": [
    "imageSnapshot URL returned 404"
  ],
  "warnings": []
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Each business rule
   - Score calculation
   - Error message formatting

2. **Integration Tests:**
   - Valid/invalid entities
   - Edge cases (missing fields)
   - Data cleaning

3. **Performance:**
   - Validate 722 entities < 10 seconds

Write tests in `tests/monitoring/test_data_quality_validator_agent.py`.
```

---

## PROMPT 21: PERFORMANCE MONITOR AGENT

```markdown
# Build Performance Monitor Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│     PERFORMANCE MONITOR AGENT WORKFLOW       │
└──────────────────────────────────────────────┘

[Collect metrics every 30s]
         ↓
    ┌─────────────────────────┐
    │ System metrics:         │
    │ - CPU usage             │
    │ - Memory usage          │
    │ - Disk I/O              │
    │ - Network throughput    │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Application metrics:    │
    │ - Agent execution time  │
    │ - API response times    │
    │ - Queue lengths         │
    │ - Error rates           │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Neo4j metrics:          │
    │ - Query performance     │
    │ - DB size               │
    │ - Connection pool       │
    └──────────┬──────────────┘
               ↓
    Export to Prometheus
               ↓
    [Grafana dashboards]
```

## IMPLEMENTATION

Create `agents/monitoring/performance_monitor_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic metrics collector
2. CONFIG-DRIVEN: Metrics definitions in YAML
3. INDEPENDENT: Standalone monitoring

### Requirements:
- Collect system metrics (psutil)
- Application-level metrics
- Neo4j performance monitoring
- Prometheus metrics export
- Grafana dashboard definitions
- Alert on thresholds exceeded
- Historical trend analysis

### Config Schema (performance_monitor_config.yaml):
```yaml
performance_monitor:
  collection_interval: 30  # seconds
  
  system_metrics:
    - cpu_percent
    - memory_percent
    - disk_io_read_bytes
    - disk_io_write_bytes
    - network_bytes_sent
    - network_bytes_recv
  
  application_metrics:
    - name: "agent_execution_time"
      type: "histogram"
      labels: ["agent_name"]
    
    - name: "api_request_duration"
      type: "histogram"
      labels: ["endpoint", "method", "status"]
    
    - name: "queue_length"
      type: "gauge"
      labels: ["queue_name"]
    
    - name: "error_count"
      type: "counter"
      labels: ["agent_name", "error_type"]
  
  neo4j_metrics:
    uri: "bolt://neo4j:7687"
    queries:
      - name: "query_duration_p95"
        query: "CALL dbms.queryJmx('org.neo4j:*') YIELD name, attributes"
      
      - name: "database_size_bytes"
        query: "CALL dbms.queryJmx('org.neo4j:name=Store file sizes') YIELD attributes"
  
  prometheus:
    port: 9091
    path: "/metrics"
  
  alerting:
    rules:
      - metric: "memory_percent"
        threshold: 85
        duration: 300  # 5 minutes
        severity: "warning"
      
      - metric: "api_request_duration"
        percentile: 95
        threshold: 1000  # ms
        severity: "critical"
```

### Prometheus Metrics Format:
```
# HELP agent_execution_time Agent execution duration in seconds
# TYPE agent_execution_time histogram
agent_execution_time_bucket{agent_name="image_refresh_agent",le="1.0"} 100
agent_execution_time_bucket{agent_name="image_refresh_agent",le="5.0"} 120
agent_execution_time_sum{agent_name="image_refresh_agent"} 450.2
agent_execution_time_count{agent_name="image_refresh_agent"} 122

# HELP cameras_processed_total Total cameras processed
# TYPE cameras_processed_total counter
cameras_processed_total{agent_name="cv_analysis_agent"} 72200
```

### Grafana Dashboard JSON:
```json
{
  "dashboard": {
    "title": "Multi-Agent System Performance",
    "panels": [
      {
        "title": "Agent Execution Times",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_execution_time_sum[5m]) / rate(agent_execution_time_count[5m])"
          }
        ]
      },
      {
        "title": "Neo4j Query Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "neo4j_query_duration_p95"
          }
        ]
      }
    ]
  }
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Metric collection
   - Prometheus format generation
   - Alert evaluation

2. **Integration Tests:**
   - Mock psutil
   - Mock Neo4j metrics
   - Prometheus scraping

3. **Load Tests:**
   - High metric volume
   - Continuous collection

Write tests in `tests/monitoring/test_performance_monitor_agent.py`.
```

---

## PROMPT 22: API GATEWAY AGENT

```markdown
# Build API Gateway Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│        API GATEWAY AGENT WORKFLOW            │
└──────────────────────────────────────────────┘

[Client Request]
         ↓
    ┌─────────────────────────┐
    │ Authentication:         │
    │ - API key validation    │
    │ - JWT verification      │
    │ - OAuth2 (optional)     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Rate limiting:          │
    │ - 100 req/min per key   │
    │ - Token bucket algo     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Route to backend:       │
    │ /ngsi-ld/* → Stellio    │
    │ /sparql → Fuseki        │
    │ /health → Health Agent  │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Response transformation │
    │ - Add CORS headers      │
    │ - Compress (gzip)       │
    │ - Cache control         │
    └──────────┬──────────────┘
               ↓
    [Client Response]
```

## IMPLEMENTATION

Create `agents/integration/api_gateway_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic API gateway
2. CONFIG-DRIVEN: Routes and policies in YAML
3. INDEPENDENT: Standalone HTTP server

### Requirements:
- HTTP server (FastAPI/Flask)
- Authentication middleware
- Rate limiting per API key
- Request routing and proxying
- Response caching (Redis integration)
- CORS handling
- Request/response logging
- OpenAPI documentation

### Config Schema (api_gateway_config.yaml):
```yaml
api_gateway:
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4
  
  authentication:
    enabled: true
    methods:
      - type: "api_key"
        header: "X-API-Key"
        keys:
          - key: "dev-key-123"
            owner: "development"
            rate_limit: 1000
      
      - type: "jwt"
        secret: "${JWT_SECRET}"
        algorithm: "HS256"
  
  rate_limiting:
    enabled: true
    default_limit: 100  # requests per minute
    storage: "redis"
    redis_url: "redis://redis:6379"
  
  routes:
    - path: "/ngsi-ld/*"
      backend: "http://stellio:8080/ngsi-ld"
      methods: ["GET", "POST", "PATCH", "DELETE"]
      auth_required: true
      cache: false
    
    - path: "/sparql"
      backend: "http://fuseki:3030/traffic-cameras/sparql"
      methods: ["GET", "POST"]
      auth_required: false
      cache:
        ttl: 300  # 5 minutes
    
    - path: "/health"
      backend: "http://health-check-agent:9090/health"
      methods: ["GET"]
      auth_required: false
  
  cors:
    enabled: true
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST", "PATCH", "DELETE"]
    allowed_headers: ["*"]
  
  logging:
    level: "INFO"
    format: "json"
    include_request_body: false
```

### Middleware Stack:
```python
# Execution order (request):
1. CORS preflight
2. Authentication
3. Rate limiting
4. Request logging
5. Route to backend
6. Response caching
7. Response compression
8. Response logging
```

### Rate Limiting Response:
```json
HTTP 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1730448120

{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Authentication logic
   - Rate limiter
   - Route matching

2. **Integration Tests:**
   - Full request lifecycle
   - Backend proxying
   - Cache behavior

3. **Load Tests:**
   - 1000 requests/second
   - Rate limiter under load

Write tests in `tests/integration/test_api_gateway_agent.py`.
```

---

## PROMPT 23: CACHE MANAGER AGENT

```markdown
# Build Cache Manager Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│        CACHE MANAGER AGENT WORKFLOW          │
└──────────────────────────────────────────────┘

[API Gateway makes request]
         ↓
    ┌─────────────────────────┐
    │ Check cache:            │
    │ key = hash(url+params)  │
    └──────────┬──────────────┘
               ↓
    ┌──────────────────┐
    │ Cache hit?       │
    └───┬──────────┬───┘
       YES        NO
        ↓          ↓
    Return    Fetch from backend
    cached         ↓
    data      Store in cache (TTL)
        ↓          ↓
    [Response]
         ↓
    Cache warming (preload popular)
         ↓
    Cache invalidation on entity updates
         ↓
    [Redis: Cached responses]
```

## IMPLEMENTATION

Create `agents/integration/cache_manager_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: Generic caching layer
2. CONFIG-DRIVEN: Cache policies in YAML
3. INDEPENDENT: Standalone Redis wrapper

### Requirements:
- Redis client wrapper
- Cache key generation (URL + params)
- TTL management per resource type
- Cache warming (preload hot data)
- Cache invalidation (on updates)
- Cache statistics (hit rate)
- Memory management (LRU eviction)

### Config Schema (cache_config.yaml):
```yaml
cache_manager:
  redis:
    host: "redis"
    port: 6379
    db: 0
    password: "${REDIS_PASSWORD}"
    max_connections: 50
  
  policies:
    - pattern: "/ngsi-ld/v1/entities/{id}"
      ttl: 300  # 5 minutes
      invalidate_on:
        - "entity_update"
        - "entity_delete"
    
    - pattern: "/sparql?query=*"
      ttl: 600  # 10 minutes
      max_size: "10MB"
    
    - pattern: "/ngsi-ld/v1/entities?type=Camera"
      ttl: 60  # 1 minute
      warming:
        enabled: true
        schedule: "*/5 * * * *"  # every 5 min
  
  warming:
    enabled: true
    urls:
      - "/ngsi-ld/v1/entities?type=Camera&limit=100"
      - "/sparql?query=SELECT+*+WHERE+{+?s+a+sosa:Sensor+}+LIMIT+100"
  
  invalidation:
    strategies:
      - trigger: "stellio_webhook"
        endpoint: "/cache/invalidate"
      
      - trigger: "time_based"
        check_interval: 60  # seconds
  
  monitoring:
    enabled: true
    metrics:
      - hit_rate
      - miss_rate
      - memory_usage
      - eviction_count
```

### Cache Key Generation:
```python
def generate_cache_key(url: str, params: dict, headers: dict) -> str:
    # Include relevant factors
    factors = [
        url,
        sorted(params.items()),
        headers.get('Accept', ''),
        headers.get('Accept-Language', '')
    ]
    return hashlib.sha256(str(factors).encode()).hexdigest()
```

### Cache Warming:
```python
async def warm_cache():
    """Preload frequently accessed data"""
    urls = [
        "/ngsi-ld/v1/entities?type=Camera&limit=100",
        "/sparql?query=SELECT+*+WHERE+{+?s+a+sosa:Sensor+}+LIMIT+100"
    ]
    for url in urls:
        response = await fetch_and_cache(url)
        logger.info(f"Warmed cache for {url}")
```

### Cache Statistics:
```json
{
  "timestamp": "2025-11-01T10:00:00Z",
  "hit_rate": 0.85,
  "miss_rate": 0.15,
  "total_requests": 10000,
  "hits": 8500,
  "misses": 1500,
  "memory_usage_mb": 245,
  "keys_count": 1523,
  "evictions": 42
}
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Key generation
   - TTL expiration
   - Invalidation logic

2. **Integration Tests:**
   - Mock Redis
   - Cache warming
   - Eviction behavior

3. **Performance:**
   - 10,000 gets/second
   - Cache hit latency < 1ms

Write tests in `tests/integration/test_cache_manager_agent.py`.
```

---

## PROMPT 24: CONTENT NEGOTIATION AGENT

```markdown
# Build Content Negotiation Agent

## WORKFLOW
```
┌──────────────────────────────────────────────┐
│    CONTENT NEGOTIATION AGENT WORKFLOW        │
└──────────────────────────────────────────────┘

[HTTP Request with Accept header]
         ↓
    Parse Accept header:
    - application/ld+json
    - text/turtle
    - application/rdf+xml
    - text/html
         ↓
    ┌─────────────────────────┐
    │ Fetch entity from:      │
    │ - Stellio (JSON-LD)     │
    │ - Fuseki (RDF)          │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Convert to requested:   │
    │ - JSON-LD (default)     │
    │ - Turtle (rdflib)       │
    │ - RDF/XML (rdflib)      │
    │ - HTML (Jinja2)         │
    └──────────┬──────────────┘
               ↓
    Set Content-Type header
               ↓
    [Response in negotiated format]
```

## IMPLEMENTATION

Create `agents/rdf_linked_data/content_negotiation_agent.py`:

CRITICAL REQUIREMENTS:
1. DOMAIN-AGNOSTIC: LOD best practice implementation
2. CONFIG-DRIVEN: Format mappings in YAML
3. INDEPENDENT: Standalone HTTP server

### Requirements:
- HTTP server with content negotiation
- Accept header parsing (quality values)
- Multi-format conversion (rdflib)
- HTML representation (human-readable)
- 303 redirects for non-information resources
- Link headers for alternate formats
- Cache-friendly responses

### Config Schema (content_negotiation_config.yaml):
```yaml
content_negotiation:
  server:
    host: "0.0.0.0"
    port: 8082
  
  formats:
    - mime_type: "application/ld+json"
      extension: ".jsonld"
      priority: 1.0
      source: "stellio"
    
    - mime_type: "text/turtle"
      extension: ".ttl"
      priority: 0.9
      source: "fuseki"
    
    - mime_type: "application/rdf+xml"
      extension: ".rdf"
      priority: 0.8
      source: "convert"
    
    - mime_type: "text/html"
      extension: ".html"
      priority: 0.7
      template: "templates/entity.html"
  
  backends:
    stellio:
      url: "http://stellio:8080/ngsi-ld/v1/entities/{id}"
      default_format: "application/ld+json"
    
    fuseki:
      url: "http://fuseki:3030/traffic-cameras/data?graph=default"
      query: "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o . FILTER(?s = <{uri}>) }"
  
  redirects:
    enabled: true
    information_resource_suffix: "/data"
    # /id/Camera/TTH406 → 303 → /id/Camera/TTH406/data
  
  link_headers:
    enabled: true
    # Link: <...>;rel="alternate";type="text/turtle"
```

### Accept Header Parsing:
```python
def parse_accept_header(accept: str) -> List[Tuple[str, float]]:
    """
    Parse: Accept: application/ld+json, text/turtle;q=0.9, */*;q=0.1
    Returns: [('application/ld+json', 1.0), ('text/turtle', 0.9), ...]
    """
    formats = []
    for part in accept.split(','):
        mime, *params = part.split(';')
        q = 1.0
        for param in params:
            if param.strip().startswith('q='):
                q = float(param.split('=')[1])
        formats.append((mime.strip(), q))
    return sorted(formats, key=lambda x: x[1], reverse=True)
```

### 303 Redirect Example:
```http
GET /id/Camera/TTH406 HTTP/1.1
Accept: text/turtle

HTTP/1.1 303 See Other
Location: /id/Camera/TTH406/data
Vary: Accept
```

### HTML Template (Jinja2):
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ entity.id }}</title>
</head>
<body>
    <h1>{{ entity.type }}: {{ entity.cameraName.value }}</h1>
    <dl>
        <dt>Location:</dt>
        <dd>{{ entity.location.value.coordinates }}</dd>
        <dt>Camera Type:</dt>
        <dd>{{ entity.cameraType.value }}</dd>
    </dl>
    <footer>
        <p>Available formats: 
            <a href="?format=jsonld">JSON-LD</a> | 
            <a href="?format=turtle">Turtle</a> | 
            <a href="?format=rdfxml">RDF/XML</a>
        </p>
    </footer>
</body>
</html>
```

### Testing Requirements (100% Coverage):
1. **Unit Tests:**
   - Accept header parsing
   - Format conversion
   - Redirect logic

2. **Integration Tests:**
   - Mock Stellio/Fuseki
   - Request with different Accept headers
   - Verify Content-Type

3. **LOD Compliance:**
   - Cool URIs
   - 303 redirects
   - Link headers

Write tests in `tests/rdf_linked_data/test_content_negotiation_agent.py`.
```

---

## PROMPT 25: COMPLETE INTEGRATION TEST SUITE

```markdown
# Build Complete Integration Test Suite

## TEST WORKFLOW
```
┌──────────────────────────────────────────────┐
│      COMPLETE INTEGRATION TEST SUITE         │
└──────────────────────────────────────────────┘

[Start Docker Compose stack]
         ↓
    ┌─────────────────────────┐
    │ Wait for services:      │
    │ - Stellio ready         │
    │ - Neo4j ready           │
    │ - Fuseki ready          │
    │ - Redis ready           │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Run agent pipeline:     │
    │ Phase 1-7 sequentially  │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ Verify outputs:         │
    │ - Neo4j: 722 cameras    │
    │ - Fuseki: RDF triples   │
    │ - Alerts sent           │
    │ - Reports generated     │
    └──────────┬──────────────┘
               ↓
    ┌─────────────────────────┐
    │ End-to-end tests:       │
    │ - API queries           │
    │ - SPARQL queries        │
    │ - Subscription triggers │
    └──────────┬──────────────┘
               ↓
    [Test report + coverage]
```

## IMPLEMENTATION

Create `tests/integration/test_complete_system.py`:

### Requirements:
- Docker Compose orchestration
- Service readiness checks
- Full pipeline execution
- Data verification in all stores
- API endpoint testing
- Performance benchmarking
- Test data cleanup

### Test Scenarios:
```yaml
integration_tests:
  - name: "full_pipeline_722_cameras"
    steps:
      - load_raw_data: "data/cameras_raw.json"
      - run_agent: "image_refresh_agent"
      - run_agent: "ngsi_ld_transformer_agent"
      - run_agent: "sosa_ssn_mapper_agent"
      - run_agent: "smart_data_models_validation_agent"
      - run_agent: "entity_publisher_agent"
      - run_agent: "ngsi_ld_to_rdf_agent"
      - run_agent: "triplestore_loader_agent"
      - verify_neo4j_count: 722
      - verify_fuseki_triples: 8640
      - verify_lod_rating: 5.0
  
  - name: "realtime_updates"
    steps:
      - simulate_image_refresh
      - verify_stellio_update_received
      - verify_subscription_notification
      - verify_alert_dispatched
  
  - name: "accident_detection_workflow"
    steps:
      - inject_anomaly_observation
      - run_agent: "accident_detection_agent"
      - verify_road_accident_created
      - verify_incident_report_generated
      - verify_alert_sent
  
  - name: "api_gateway_e2e"
    steps:
      - request: "GET /ngsi-ld/v1/entities?type=Camera"
        expect: 200
        verify_count: 722
      - request: "POST /sparql"
        body: "SELECT * WHERE { ?s a sosa:Sensor } LIMIT 10"
        expect: 200
        verify_results: 10
  
  - name: "performance_benchmark"
    metrics:
      - pipeline_duration: "< 180s"  # 3 minutes
      - api_response_p95: "< 500ms"
      - sparql_query_p95: "< 1000ms"
```

### Docker Compose Test Stack:
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  # Inherit from main docker-compose.yml
  stellio:
    extends:
      file: docker-compose.yml
      service: stellio-api-gateway
  
  neo4j:
    extends:
      file: docker-compose.yml
      service: neo4j
  
  fuseki:
    extends:
      file: docker-compose.yml
      service: fuseki
  
  # Test runner
  test-runner:
    build: .
    command: pytest tests/integration/ -v --cov --cov-report=html
    depends_on:
      - stellio
      - neo4j
      - fuseki
    volumes:
      - ./tests:/app/tests
      - ./htmlcov:/app/htmlcov
    environment:
      - STELLIO_URL=http://stellio:8080
      - NEO4J_URI=bolt://neo4j:7687
      - FUSEKI_URL=http://fuseki:3030
```

### Pytest Fixture:
```python
@pytest.fixture(scope="session")
def docker_stack():
    """Start Docker Compose stack for tests"""
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"])
    
    # Wait for services
    wait_for_service("http://stellio:8080/health", timeout=60)
    wait_for_service("bolt://neo4j:7687", timeout=60)
    wait_for_service("http://fuseki:3030/$/ping", timeout=60)
    
    yield
    
    # Cleanup
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"])
```

### Test Execution:
```bash
# Run integration tests
pytest tests/integration/test_complete_system.py -v \
    --cov=agents \
    --cov-report=html \
    --cov-report=term-missing \
    --duration=10

# Expected output:
# ✓ full_pipeline_722_cameras: PASSED (152.3s)
# ✓ realtime_updates: PASSED (5.2s)
# ✓ accident_detection_workflow: PASSED (8.7s)
# ✓ api_gateway_e2e: PASSED (2.1s)
# ✓ performance_benchmark: PASSED (3.5s)
# 
# Coverage: 95%
```

### CI/CD Integration (GitHub Actions):
```yaml
# .github/workflows/test.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Compose
        run: docker-compose -f docker-compose.test.yml up -d
      
      - name: Run Integration Tests
        run: |
          docker-compose -f docker-compose.test.yml run test-runner
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./htmlcov/coverage.xml
```

Write comprehensive tests covering all 24 agents and their interactions.
```

---

**NOTES:**
- All 25 prompts maintain consistent structure
- Each agent is domain-agnostic and config-driven
- 100% test coverage required for each
- Integration with existing core pipeline (Prompts 1-9)
- Ready for GitHub Copilot code generation
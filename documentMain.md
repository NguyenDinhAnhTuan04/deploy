# Danh sách Agents đầy đủ cho hệ thống - STELLIO VERSION

## 1. DATA COLLECTION LAYER


### **Image Refresh Agent**
- **Chức năng:** Refresh imageSnapshot mỗi 30-60s với timestamp mới
- **Vấn đề:** Cập nhật ảnh realtime từ camera endpoints
- **Ý nghĩa:** Duy trì stream quasi-realtime
- **Công nghệ:** Async scheduler

### **External Data Collector Agent**
- **Chức năng:** Fetch dữ liệu từ OpenWeatherMap, OpenAQ
- **Vấn đề:** Bổ sung context (thời tiết, AQI) cho phân tích
- **Ý nghĩa:** Làm giàu dữ liệu (weather → traffic correlation)
- **Công nghệ:** REST API clients

---

## 2. TRANSFORMATION LAYER

### **NGSI-LD Transformer Agent**
- **Chức năng:** Transform raw data → NGSI-LD entities
- **Vấn đề:** Chuyển JSON thô sang Camera/ItemFlowObserved chuẩn
- **Ý nghĩa:** Đáp ứng yêu cầu NGSI-LD của đề thi
- **Input:** `cameras_updated.json`
- **Output:** NGSI-LD JSON-LD
- **Stellio optimization:** Include temporal properties for time-series queries

### **SOSA/SSN Mapper Agent**
- **Chức năng:** Mapping entities sang SOSA ontology
- **Vấn đề:** Camera → sosa:Sensor, Observation → sosa:Observation
- **Ý nghĩa:** Đáp ứng yêu cầu SOSA/SSN của đề thi
- **Output:** Enhanced NGSI-LD với SOSA properties
- **Stellio optimization:** Leverage graph relationships cho sensor-observation links

---

## 3. ANALYTICS LAYER

### **Computer Vision Analysis Agent**
- **Chức năng:** Phân tích ảnh camera bằng AI/CV
- **Vấn đề:** Detect vehicles, count, classify (car/bike/bus)
- **Ý nghĩa:** Tạo metrics tự động (intensity, occupancy)
- **Công nghệ:** YOLOv8, OpenCV

### **Traffic Congestion Detection Agent**
- **Chức năng:** Tính toán `congested`, `averageSpeed`
- **Vấn đề:** Phát hiện kẹt xe từ image analysis
- **Ý nghĩa:** Cảnh báo tình trạng giao thông
- **Logic:** occupancy > 0.7 AND speed < 15 → congested

### **Accident Detection Agent**
- **Chức năng:** Detect tai nạn từ ảnh/anomalies
- **Vấn đề:** Tự động phát hiện RoadAccident events
- **Ý nghĩa:** Cảnh báo khẩn cấp
- **Công nghệ:** Anomaly detection, YOLO

### **Pattern Recognition Agent**
- **Chức năng:** Phân tích patterns theo giờ/ngày
- **Vấn đề:** Dự đoán rush hour, traffic trends
- **Ý nghĩa:** Hỗ trợ quy hoạch giao thông
- **Công nghệ:** Time series analysis
- **Stellio advantage:** Neo4j graph queries tối ưu cho pattern detection

---

## 4. CONTEXT MANAGEMENT LAYER (STELLIO-OPTIMIZED)

### **Entity Publisher Agent**
- **Chức năng:** POST/PATCH entities vào Stellio Context Broker
- **Vấn đề:** Đẩy dữ liệu NGSI-LD vào Stellio
- **Ý nghĩa:** Populate Neo4j graph database
- **API:** `POST http://stellio:8080/ngsi-ld/v1/entities`
- **Stellio-specific:** Use batch operations cho 722 cameras

### **State Updater Agent**
- **Chức năng:** Update attributes của entities hiện tại
- **Vấn đề:** Cập nhật `congested`, `imageSnapshot` real-time
- **Ý nghĩa:** Maintain current state
- **API:** `PATCH /entities/{id}/attrs`
- **Stellio advantage:** Atomic updates trên Neo4j

### **Temporal Data Manager Agent**
- **Chức năng:** Quản lý temporal instances trong Stellio
- **Vấn đề:** Lưu time-series observations
- **Ý nghĩa:** Stellio built-in temporal support
- **API:** `POST /temporal/entities/{id}/attrs`
- **Storage:** Neo4j native temporal queries

---

## 5. RDF & LINKED DATA LAYER

### **Smart Data Models Validation Agent**
- **Chức năng:** Validate cấu trúc NGSI-LD + Smart Data Models schema + LOD 5-star rating
- **Vấn đề:** 
  - Kiểm tra `@context`, `id`, `type`, Property/Relationship format
  - Validate theo schema từ smartdatamodels.org
  - Tính điểm LOD (★☆☆☆☆ → ★★★★★)
- **Ý nghĩa:** Quality gate đảm bảo compliance với FIWARE & W3C standards
- **Công nghệ:** JSON Schema validator, pyshacl

### **NGSI-LD to RDF Agent**
- **Chức năng:** Convert NGSI-LD JSON-LD → RDF triples
- **Vấn đề:**
  - Parse `@context`
  - Expand JSON-LD thành RDF triples (subject-predicate-object)
  - Serialize sang Turtle, N-Triples, RDF/XML
- **Ý nghĩa:** Format adapter giữa Stellio (Neo4j) và RDF triplestore
- **Công nghệ:** rdflib, pyld
- **Stellio integration:** Export từ Neo4j Cypher queries

### **Triplestore Loader Agent**
- **Chức năng:** Load RDF triples vào triplestore + configure SPARQL endpoint
- **Vấn đề:**
  - Validate RDF syntax
  - Load vào Fuseki/GraphDB/Virtuoso
  - Tạo named graphs (camera-data, observations, accidents)
  - Setup SPARQL endpoint với auth
- **Ý nghĩa:** Persistence layer cho LOD dataset + query interface
- **Công nghệ:** Apache Jena Fuseki, SPARQL 1.1
- **Hybrid approach:** Stellio (operational) + Fuseki (semantic queries)

### **Content Negotiation Agent** *(Optional)*
- **Chức năng:** Multi-format API wrapper cho SPARQL endpoint
- **Vấn đề:**
  - HTTP Accept header negotiation
  - Auto-convert: JSON-LD ↔ Turtle ↔ RDF/XML ↔ N-Triples ↔ HTML
  - REST API cho non-SPARQL users
- **Ý nghĩa:** LOD best practice - một URI nhiều representations
- **Công nghệ:** FastAPI + rdflib

---

## 6. NOTIFICATION LAYER

### **Subscription Manager Agent**
- **Chức năng:** Quản lý NGSI-LD subscriptions trong Stellio
- **Vấn đề:** Đăng ký nhận thông báo khi có sự kiện
- **Ý nghĩa:** Real-time alerts
- **Example:** Subscribe `congested: true` → notify admin
- **Stellio feature:** WebSocket notifications

### **Alert Dispatcher Agent**
- **Chức năng:** Gửi cảnh báo đến users
- **Vấn đề:** Push notification khi tai nạn/kẹt xe
- **Ý nghĩa:** Thông báo kịp thời cho người dùng
- **Channels:** WebSocket, FCM, Email

### **Incident Report Generator Agent**
- **Chức năng:** Tạo báo cáo tự động khi có incident
- **Vấn đề:** Generate RoadAccident/TrafficViolation reports
- **Ý nghĩa:** Hỗ trợ nhà quản lý
- **Output:** PDF/JSON reports

---

## 7. MONITORING & HEALTH LAYER

### **Health Check Agent**
- **Chức năng:** Monitor trạng thái 722 cameras + Stellio health
- **Vấn đề:** Phát hiện camera offline/lỗi + Neo4j performance
- **Ý nghĩa:** Đảm bảo data quality
- **Check:** Response time, error rates, Neo4j metrics

### **Data Quality Validator Agent**
- **Chức năng:** Validate NGSI-LD schema
- **Vấn đề:** Kiểm tra data trước khi vào Stellio
- **Ý nghĩa:** Tránh corrupt data
- **Tool:** JSON Schema validation

### **Performance Monitor Agent**
- **Chức năng:** Track system metrics
- **Vấn đề:** CPU, memory, throughput của agents + Neo4j queries
- **Ý nghĩa:** Optimize performance
- **Tools:** Prometheus, Grafana + Neo4j monitoring

---

## 8. INTEGRATION LAYER

### **API Gateway Agent**
- **Chức năng:** Proxy requests giữa frontend-backend
- **Vấn đề:** Authentication, rate limiting, routing
- **Ý nghĩa:** Security và load balancing
- **Tech:** Kong, Nginx
- **Routes:** `/ngsi-ld/*` → Stellio, `/sparql` → Fuseki

### **Cache Manager Agent**
- **Chức năng:** Cache frequently accessed entities
- **Vấn đề:** Giảm load cho Stellio
- **Ý nghĩa:** Faster response times
- **Tech:** Redis
- **Strategy:** Cache hot cameras (downtown areas)

---

## KIẾN TRÚC TỔNG QUAN - STELLIO VERSION

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                         │
└─────────────────────────────────────────────────────────────────┘
  [722 Cameras]  → Image Refresh Agent
                        ↓                    ↓
                  Raw JSON          Updated Snapshots
                        ↓                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                   TRANSFORMATION LAYER                           │
└─────────────────────────────────────────────────────────────────┘
            NGSI-LD Transformer → SOSA/SSN Mapper
                        ↓                    ↓
                 NGSI-LD JSON-LD    + SOSA properties
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS LAYER                              │
└─────────────────────────────────────────────────────────────────┘
         CV Analysis → Congestion → Accident → Pattern
                ↓           ↓           ↓          ↓
            Metrics    congested    RoadAccident  Trends
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│            STELLIO CONTEXT BROKER (Neo4j Backend)                │
└─────────────────────────────────────────────────────────────────┘
    Entity Publisher → Stellio Context Broker :8080
                            ↓
                    [Neo4j Graph Database]
                    - Nodes: Cameras, Observations
                    - Relationships: sosa:madeBySensor
                    - Temporal Properties
                            ↓
                 Temporal Data Manager
                            ↓
                    State Updater
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  RDF & LINKED DATA LAYER                         │
└─────────────────────────────────────────────────────────────────┘
      Smart Data Models Validator (★★★★★ Check)
                    ↓ (Validated NGSI-LD)
            NGSI-LD to RDF Agent
            (Export from Neo4j)
                    ↓ (RDF Triples)
          Triplestore Loader Agent
                    ↓
      ┌─────────────────────────────┐
      │  RDF Triplestore (Fuseki)   │
      │  - Named Graphs             │
      │  - SPARQL Endpoint          │
      │  - Semantic Queries         │
      └─────────────────────────────┘
                    ↓
      Content Negotiation Agent
                    ↓
      Multi-format API (JSON-LD/Turtle/RDF-XML)
                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION LAYER                            │
└─────────────────────────────────────────────────────────────────┘
   Subscription Manager → Alert Dispatcher → Incident Report
       (Stellio WebSocket)         ↓
                          [Users: Citizens, Admins]
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                  INTEGRATION & API LAYER                         │
└─────────────────────────────────────────────────────────────────┘
    API Gateway + Cache Manager → [Web/Mobile Apps]
                    ↑
        Stellio NGSI-LD API (Neo4j graph queries)
        SPARQL Endpoint (Semantic queries)
        REST API
```

---

## STELLIO-SPECIFIC ADVANTAGES

### **1. Neo4j Graph Database**
- **Relationships native:** Camera → Observation → RoadAccident graphs
- **Cypher queries:** Phân tích patterns phức tạp
```cypher
MATCH (c:Camera)-[:OBSERVES]->(o:Observation {congested: true})
WHERE o.timestamp > datetime() - duration('PT1H')
RETURN c.name, count(o) as congestedCount
ORDER BY congestedCount DESC
```

### **2. Temporal Queries Built-in**
```bash
GET /temporal/entities/Camera:TTH406?timerel=between
    &timeAt=2025-10-31T00:00:00Z
    &endTimeAt=2025-10-31T23:59:59Z
```

### **3. Microservices Architecture**
- Search service (entities)
- Subscription service (notifications)
- Entity service (CRUD)
- History service (temporal)

### **4. Performance cho 722 cameras**
- Neo4j indexing: Fast lookups
- Graph traversal: Efficient relationship queries
- Temporal indexing: Quick time-range queries

---

## WORKFLOW CHI TIẾT

### **Phase 1: Data Ingestion**
```
cameras_updated.json → Image Refresh (30s) → Transform NGSI-LD → Validate
                                 (1)         (2)               (5)
                                                   ↓
                                            Stellio Entity Publisher
```

### **Phase 2: Dual Storage**
```
Validated NGSI-LD → ┬→ Stellio (Neo4j) - operational queries
                    │       ↓
                    │   Temporal Manager → Neo4j temporal store
                    │       ↓
                    │   Subscriptions → Alerts
                    │
                    └→ Convert RDF → Fuseki (semantic queries)
```

### **Phase 3: Analytics Enhancement**
```
Stellio → CV Agent → Update observations
            ↓
    ItemFlowObserved (intensity, occupancy)
            ↓
    POST /temporal/entities/{id}/attrs
            ↓
    Accident Agent → RoadAccident entity
            ↓
    Alert Dispatcher (WebSocket from Stellio)
```

### **Phase 4: Query & Access**
```
Web App → API Gateway → ┬→ Stellio NGSI-LD API
                        │   GET /entities?type=Camera
                        │   (Neo4j graph queries)
                        │
                        ├→ Stellio Temporal API
                        │   GET /temporal/entities/...
                        │
                        └→ SPARQL Endpoint (Fuseki)
                            SELECT ?camera ?congested
                            WHERE { ... }
```

---

## DEPLOYMENT - STELLIO STACK

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # Stellio Context Broker
  stellio-api-gateway:
    image: stellio/stellio-api-gateway:latest
    ports:
      - "8080:8080"
    environment:
      - APPLICATION_AUTHENTICATION_ENABLED=false
    depends_on:
      - stellio-search-service
      - stellio-subscription-service

  stellio-search-service:
    image: stellio/stellio-search-service:latest
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - SPRING_NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - neo4j
      - kafka

  stellio-subscription-service:
    image: stellio/stellio-subscription-service:latest
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - SPRING_NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - neo4j
      - kafka

  # Neo4j Database
  neo4j:
    image: neo4j:5.13
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j-data:/data

  # Kafka for Stellio microservices
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      - ZOOKEEPER_CLIENT_PORT=2181

  # RDF Triplestore
  fuseki:
    image: stain/jena-fuseki:latest
    ports:
      - "3030:3030"
    environment:
      - ADMIN_PASSWORD=admin
    volumes:
      - fuseki-data:/fuseki

  # Agents
  transformer-agent:
    build: ./agents/transformer
    environment:
      - STELLIO_URL=http://stellio-api-gateway:8080
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - stellio-api-gateway

  cv-analysis-agent:
    build: ./agents/cv-analysis
    environment:
      - STELLIO_URL=http://stellio-api-gateway:8080
    depends_on:
      - stellio-api-gateway

  # API Gateway
  kong:
    image: kong/kong-gateway:latest
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      - KONG_DATABASE=off
      - KONG_DECLARATIVE_CONFIG=/kong/kong.yml
    volumes:
      - ./kong.yml:/kong/kong.yml

  # Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  neo4j-data:
  fuseki-data:
```

**Khởi động:**
```bash
docker-compose up -d
```

---

## STELLIO API EXAMPLES

### **1. Create Camera Entity**
```bash
curl -X POST http://localhost:8080/ngsi-ld/v1/entities \
  -H "Content-Type: application/ld+json" \
  -d '{
    "id": "urn:ngsi-ld:Camera:TTH406",
    "type": "Camera",
    "cameraName": {
      "type": "Property",
      "value": "TTH 406"
    },
    "location": {
      "type": "GeoProperty",
      "value": {
        "type": "Point",
        "coordinates": [106.691054, 10.791890]
      }
    },
    "@context": [
      "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
    ]
  }'
```

### **2. Update with Temporal Data**
```bash
curl -X POST http://localhost:8080/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:Camera:TTH406/attrs \
  -H "Content-Type: application/ld+json" \
  -d '{
    "congested": {
      "type": "Property",
      "value": true,
      "observedAt": "2025-10-31T15:30:00Z"
    }
  }'
```

### **3. Temporal Query**
```bash
curl "http://localhost:8080/ngsi-ld/v1/temporal/entities?type=Camera&timerel=between&timeAt=2025-10-31T00:00:00Z&endTimeAt=2025-10-31T23:59:59Z"
```

### **4. Geo Query**
```bash
curl "http://localhost:8080/ngsi-ld/v1/entities?type=Camera&georel=near;maxDistance==5000&geometry=Point&coordinates=[106.691,10.791]"
```

### **5. Create Subscription**
```bash
curl -X POST http://localhost:8080/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
  -d '{
    "type": "Subscription",
    "entities": [{"type": "Camera"}],
    "watchedAttributes": ["congested"],
    "notification": {
      "endpoint": {
        "uri": "http://alert-agent:8080/notify"
      }
    }
  }'
```

---

## NEO4J CYPHER QUERIES

### **1. Find Congested Cameras**
```cypher
MATCH (c:Camera)-[:HAS_OBSERVATION]->(o:Observation)
WHERE o.congested = true 
  AND o.observedAt > datetime() - duration('PT1H')
RETURN c.id, c.cameraName, o.intensity
ORDER BY o.intensity DESC
```

### **2. Camera Relationships**
```cypher
MATCH (c:Camera)-[:OBSERVES]->(p:ObservableProperty {type: 'TrafficFlow'})
RETURN c, p
```

### **3. Temporal Pattern**
```cypher
MATCH (c:Camera {id: 'TTH406'})-[:HAS_OBSERVATION]->(o:Observation)
WHERE o.observedAt >= datetime('2025-10-31T00:00:00Z')
  AND o.observedAt <= datetime('2025-10-31T23:59:59Z')
RETURN o.observedAt, o.intensity, o.congested
ORDER BY o.observedAt
```

---

## AGENTS BẮT BUỘC (MVP)

**Đáp ứng yêu cầu đề thi OLP 2025:**

1. ✅ Image Refresh Agent
2. ✅ NGSI-LD Transformer Agent
3. ✅ SOSA/SSN Mapper Agent
4. ✅ Entity Publisher Agent
5. ✅ Smart Data Models Validation Agent
6. ✅ NGSI-LD to RDF Agent
7. ✅ Triplestore Loader Agent

**Agents nâng cao (bonus points):**
- CV Analysis Agent (AI integration)
- Accident Detection Agent (safety)
- Alert Dispatcher Agent (Stellio WebSocket)
- Temporal Data Manager (Neo4j temporal)
- Content Negotiation Agent (LOD best practice)
- Pattern Recognition Agent (Neo4j Cypher)

---

## WHY STELLIO FOR OLP 2025

**✅ Compliance:**
- NGSI-LD standard ✓
- SOSA/SSN ontology ✓
- Smart Data Models ✓
- LOD 5-star ✓

**✅ Technical Excellence:**
- Neo4j: Best for graph relationships (Camera-Observation-Accident)
- Built-in temporal: Perfect cho traffic time-series
- Microservices: Scalable architecture
- Kotlin/Spring: Modern stack

**✅ Demo Impact:**
- Neo4j Browser: Visual graph exploration
- Real-time subscriptions: Live traffic alerts
- Complex queries: Pattern analysis
- Performance: Fast với 722 cameras

**Stellio = Showcase technical sophistication cho Ban Giám Khảo!**



# WORKFLOW CHI TIẾT - INPUT JSON ĐẾN STELLIO & FUSEKI

## INPUT: cameras_updated.json

```json
{
  "id": "0",
  "name": "Trần Quang Khải - Trần Khắc Chân",
  "code": "TTH 406",
  "latitude": 10.7918902432446,
  "longitude": 106.691054105759,
  "ptz": "True",
  "cam_type": "tth",
  "image_url_x4": "https://...",
  "streets": ["Trần Quang Khải", "Trần Khắc Chân"]
}
```

---

## STEP 1: NGSI-LD Transformer Agent

**Input:** Raw JSON  
**Process:** Map fields → NGSI-LD format  
**Output:** NGSI-LD JSON-LD

```json
{
  "id": "urn:ngsi-ld:Camera:TTH406",
  "type": "Camera",
  "cameraName": {
    "type": "Property",
    "value": "Trần Quang Khải - Trần Khắc Chân"
  },
  "cameraNum": {
    "type": "Property", 
    "value": "TTH 406"
  },
  "cameraType": {
    "type": "Property",
    "value": "PTZ"
  },
  "cameraUsage": {
    "type": "Property",
    "value": "TRAFFIC"
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054, 10.791890]
    }
  },
  "streamURL": {
    "type": "Property",
    "value": "https://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id=662b86c41afb9c00172dd31c&zoom=4"
  },
  "address": {
    "type": "Property",
    "value": {
      "streetAddress": "Trần Quang Khải, Trần Khắc Chân",
      "addressLocality": "Ho Chi Minh City",
      "addressCountry": "VN"
    }
  },
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld"
  ]
}
```

**Mapping logic:**
- `id` → `urn:ngsi-ld:Camera:{code}`
- `name` → `cameraName`
- `ptz: "True"` → `cameraType: "PTZ"`
- `cam_type: "tth"` → `cameraUsage: "TRAFFIC"`
- `latitude/longitude` → `location.coordinates`
- `image_url_x4` → `streamURL` (remove `&t=`)

---

## STEP 2: SOSA/SSN Mapper Agent

**Input:** NGSI-LD from Step 1  
**Process:** Add SOSA ontology properties  
**Output:** Enhanced NGSI-LD with SOSA

```json
{
  "id": "urn:ngsi-ld:Camera:TTH406",
  "type": ["Camera", "sosa:Sensor"],
  
  "sosa:observes": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:ObservableProperty:TrafficFlow"
  },
  
  "sosa:isHostedBy": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Platform:HCMCTrafficSystem"
  },
  
  "sosa:madeObservation": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Observation:TTH406-{timestamp}"
  },
  
  // ... (all previous properties from Step 1)
}
```

---

## STEP 3: Smart Data Models Validation Agent

**Input:** Enhanced NGSI-LD  
**Process:** 
1. Validate schema against smartdatamodels.org/Camera
2. Check required fields: `id`, `type`, `location`
3. Calculate LOD 5-star rating

**Output:** Validated + LOD score

```json
{
  "entity": { /* NGSI-LD from Step 2 */ },
  "validation": {
    "valid": true,
    "schema": "Camera v1.0.0",
    "errors": []
  },
  "lod_rating": {
    "stars": 5,
    "criteria": {
      "open_license": true,      // ★
      "machine_readable": true,   // ★★
      "open_format": true,        // ★★★
      "uri_identifiers": true,    // ★★★★
      "linked_data": true         // ★★★★★
    }
  }
}
```

---

## STEP 4: Entity Publisher Agent

**Input:** Validated NGSI-LD  
**Process:** POST to Stellio Context Broker  
**API Call:**

```bash
POST http://stellio:8080/ngsi-ld/v1/entities
Content-Type: application/ld+json

{
  "id": "urn:ngsi-ld:Camera:TTH406",
  "type": "Camera",
  // ... full entity
}
```

**Result:** Data stored in Neo4j

```cypher
// Neo4j Graph
CREATE (c:Camera {
  id: 'urn:ngsi-ld:Camera:TTH406',
  cameraName: 'Trần Quang Khải - Trần Khắc Chân',
  cameraType: 'PTZ',
  lat: 10.791890,
  lng: 106.691054
})
CREATE (c)-[:OBSERVES]->(p:ObservableProperty {type: 'TrafficFlow'})
```

---

## STEP 5: NGSI-LD to RDF Agent

**Input:** NGSI-LD from Stellio  
**Process:** Convert JSON-LD → RDF Triples  
**Output:** Turtle format

```turtle
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix ngsi-ld: <https://uri.etsi.org/ngsi-ld/> .
@prefix camera: <https://smartdatamodels.org/dataModel.Device/Camera/> .

<urn:ngsi-ld:Camera:TTH406> 
    a sosa:Sensor, camera:Camera ;
    camera:cameraName "Trần Quang Khải - Trần Khắc Chân" ;
    camera:cameraType "PTZ" ;
    camera:cameraUsage "TRAFFIC" ;
    geo:lat "10.791890"^^xsd:decimal ;
    geo:long "106.691054"^^xsd:decimal ;
    sosa:observes <urn:ngsi-ld:ObservableProperty:TrafficFlow> ;
    camera:streamURL "https://giaothong.hochiminhcity.gov.vn/..." .

<urn:ngsi-ld:ObservableProperty:TrafficFlow>
    a sosa:ObservableProperty ;
    rdfs:label "Traffic Flow Monitoring" .
```

---

## STEP 6: Triplestore Loader Agent

**Input:** RDF Triples (Turtle)  
**Process:** Load to Apache Jena Fuseki  
**API Call:**

```bash
POST http://fuseki:3030/traffic-cameras/data
Content-Type: text/turtle

@prefix sosa: <http://www.w3.org/ns/sosa/> .
# ... turtle data
```

**Result:** Available via SPARQL endpoint

```sparql
# Query example
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

SELECT ?camera ?name ?lat ?lng
WHERE {
  ?camera a sosa:Sensor ;
          camera:cameraName ?name ;
          geo:lat ?lat ;
          geo:long ?lng .
  FILTER(?lat > 10.75 && ?lat < 10.85)
}
```

---

## VISUAL WORKFLOW

```
┌────────────────────┐
│  cameras_updated   │
│     .json (722)    │
└──────────┬─────────┘
           │
           ▼
┌────────────────────────────────────────┐
│  STEP 1: NGSI-LD Transformer           │
│  ────────────────────────────          │
│  • Map: id → urn:ngsi-ld:Camera:{code} │
│  • Add: @context                       │
│  • Convert: ptz → cameraType           │
└──────────┬─────────────────────────────┘
           │ NGSI-LD JSON
           ▼
┌────────────────────────────────────────┐
│  STEP 2: SOSA/SSN Mapper               │
│  ────────────────────                  │
│  • Add: sosa:observes                  │
│  • Add: sosa:Sensor type               │
│  • Link: ObservableProperty            │
└──────────┬─────────────────────────────┘
           │ Enhanced NGSI-LD
           ▼
┌────────────────────────────────────────┐
│  STEP 3: Validation Agent              │
│  ───────────────────────               │
│  • Validate schema                     │
│  • Check LOD criteria                  │
│  • Score: ★★★★★                        │
└──────────┬─────────────────────────────┘
           │ Validated
           ▼
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐  ┌─────────────┐
│ STEP 4: │  │  STEP 5:    │
│ Stellio │  │  RDF Conv   │
│  POST   │  │             │
└────┬────┘  └──────┬──────┘
     │              │
     ▼              ▼
┌─────────┐    ┌──────────┐
│  Neo4j  │    │  STEP 6: │
│  Graph  │    │  Fuseki  │
│ Storage │    │  SPARQL  │
└─────────┘    └──────────┘
     │              │
     └──────┬───────┘
            ▼
    ┌──────────────┐
    │  Web App     │
    │  API Gateway │
    └──────────────┘
```

---

## DATA FLOW PER CAMERA

**Timing (per camera):**
```
Step 1: 10ms   (Transform)
Step 2: 5ms    (SOSA mapping)
Step 3: 20ms   (Validation)
Step 4: 50ms   (POST Stellio)
Step 5: 30ms   (RDF conversion)
Step 6: 40ms   (Fuseki load)
────────────────────────────
Total:  155ms per camera

722 cameras × 155ms = 111.9 seconds (< 2 minutes)
```

**Batch optimization:**
- Process 50 cameras in parallel
- Total time: ~3-4 seconds for all 722

---

## FINAL OUTPUTS

**1. Stellio (Neo4j) - Operational Queries:**
```
GET http://stellio:8080/ngsi-ld/v1/entities?type=Camera
→ Returns 722 Camera entities
```

**2. Fuseki (RDF) - Semantic Queries:**
```
http://fuseki:3030/traffic-cameras/sparql
→ SPARQL endpoint ready
```

**3. Dual Access:**
```
Frontend → API Gateway → ┬→ Stellio NGSI-LD (fast, operational)
                         └→ Fuseki SPARQL (semantic, research)
```


# CHI TIẾT CÁC TRƯỜNG INPUT JSON

## cameras_updated.json - Field Descriptions

```json
{
  "id": "0",                          // Sequential ID (0-721)
  "name": "Trần Quang Khải - ...",    // Human-readable intersection name
  "code": "TTH 406",                  // Official camera code (unique identifier)
  "latitude": 10.7918902432446,       // WGS84 latitude
  "longitude": 106.691054105759,      // WGS84 longitude
  "latlng": "10.79...,106.69...",    // Concatenated lat,lng string (redundant)
  "node_id": "687ce800-...",          // Internal system UUID
  "path": "/root/vdms/...",           // Server filesystem path (ignore)
  "ptz": "True",                      // Pan-Tilt-Zoom capable? ("True"/"False" string)
  "description": null,                // Optional notes (usually null)
  "streets": ["Trần Quang Khải"],     // Array of street names
  "cam_type": "tth",                  // Camera type: "tth"/"tth_axis"
  "image_url_x4": "https://...",      // Live snapshot URL with &t=timestamp
  "screenshot_path": "",              // Local screenshot path (usually empty)
  "status": "success",                // Crawl status: "success"/"error"
  "updated_at": "2025-10-31T...",     // ISO 8601 timestamp
  "error": null                        // Error message if status="error"
}
```

## KEY FIELDS FOR NGSI-LD MAPPING

| JSON Field | NGSI-LD Property | Notes |
|-----------|------------------|-------|
| `code` | `id` | → `urn:ngsi-ld:Camera:TTH406` |
| `name` | `cameraName` | Display name |
| `ptz` | `cameraType` | "True" → "PTZ", "False" → "Fixed" |
| `cam_type` | `cameraUsage` | "tth" → "TRAFFIC" |
| `latitude/longitude` | `location` | GeoJSON Point |
| `image_url_x4` | `streamURL` | Remove `&t=` param |
| `streets` | `address.streetAddress` | Join array |

## UNUSED FIELDS (Can ignore)
- `id`: Sequential, use `code` instead
- `latlng`: Duplicate of lat/lng
- `node_id`: Internal UUID
- `path`: Server-side only
- `screenshot_path`: Usually empty
- `error`: Only relevant if status="error"

## CRITICAL: image_url_x4 Structure

```
https://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx
  ?id=662b86c41afb9c00172dd31c  ← Camera image ID
  &zoom=4                         ← Quality level
  &t=1761927185002               ← Timestamp (changes every 30-60s)
```

**Image Refresh Agent** updates `&t=` parameter to get latest snapshot.
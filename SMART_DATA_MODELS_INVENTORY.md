# Smart Data Models Inventory

> **Comprehensive documentation of all Smart Data Models used in Builder Layer End LOD Pipeline**  
> Version: 2.0.0  
> Last Updated: 2025-11-10

---

## Overview

This document catalogs all **Smart Data Models** used in the Builder Layer End project for the Ho Chi Minh City Traffic Monitoring System. The pipeline transforms raw traffic camera data into NGSI-LD entities, enriches them with external weather and air quality data, and adds SOSA/SSN semantic annotations for the Linked Open Data (LOD) cloud.

### Pipeline Architecture
- **Data Source**: 40 traffic cameras (Ho Chi Minh City) + External APIs (OpenWeatherMap, OpenAQ)
- **Context Broker**: Stellio v2.26.1 (NGSI-LD API)
- **Triple Store**: Apache Jena Fuseki (SPARQL endpoint)
- **Graph Database**: Neo4j 5.12.0 (relationship mapping)
- **Data Format**: NGSI-LD JSON-LD

### Total Models: 8
1. **Camera** - Traffic monitoring sensor devices (sosa:Sensor)
2. **WeatherObserved** - Real-time weather observations (sosa:Observation)
3. **AirQualityObserved** - Real-time air quality observations (sosa:Observation)
4. **ItemFlowObserved** - Real-time traffic flow observations
5. **RoadAccident** - Detected accident incidents
6. **TrafficPattern** - Historical traffic patterns and forecasts
7. **ObservableProperty** - SOSA/SSN semantic properties
8. **Platform** - Hosting infrastructure system

---

## 1. Camera

### Description
Traffic monitoring camera sensor with SOSA/SSN semantic annotations. Represents physical camera devices deployed across Ho Chi Minh City for real-time traffic surveillance. Enhanced with external weather and air quality data.

### Entity Type
- **Type**: `["Camera", "sosa:Sensor"]`
- **URI Pattern**: `urn:ngsi-ld:Camera:{cameraCode}`
- **Source**: Smart Data Models - dataModel.Device
- **SOSA/SSN Enhancement**: Added in Phase 2 (Transformation)

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `cameraName` | Property | Intersection or location name | "Trần Quang Khải - Trần Khắc Chân" |
| `cameraNum` | Property | Official camera code/number | "TTH 406" |
| `cameraType` | Property | Camera type (PTZ/Fixed) | "PTZ" or "Fixed" |
| `cameraUsage` | Property | Usage category | "TTH" (traffic) |
| `streamUrl` | Property | Live video stream URL | "rtsp://..." |
| `imageUrl` | Property | Standard resolution snapshot URL | "https://..." |
| `imageSnapshot` | Property | High resolution snapshot URL (x4 zoom) | "https://giaothong.hochiminhcity.gov.vn/..." |
| `address` | Property | Street address/intersection | "Trần Quang Khải - Trần Khắc Chân" |
| `description` | Property | Additional description | "Camera at major intersection" |
| `status` | Property | Operational status | "success", "failed", "offline" |
| `dateLastValueReported` | Property | Last data update timestamp (ISO 8601) | "2025-11-10T23:13:05.002234Z" |
| `dateModified` | Property | Last modification timestamp (ISO 8601) | "2025-11-10T23:13:05.002234Z" |
| `location` | GeoProperty | Geographic coordinates (WGS84) | `{"type": "Point", "coordinates": [106.691, 10.791]}` |

### SOSA/SSN Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `sosa:observes` | Relationship | `urn:ngsi-ld:ObservableProperty:TrafficFlow` | What the sensor observes |
| `sosa:isHostedBy` | Relationship | `urn:ngsi-ld:Platform:HCMCTrafficSystem` | Hosting platform |
| `sosa:madeObservation` | Relationship | Array of `ItemFlowObserved` IDs | **Dynamic array** - All observations created by this camera |

**CRITICAL NOTE**: The `sosa:madeObservation` relationship is initialized as an empty array `[]` during Phase 2 (SOSA/SSN Mapping), then **dynamically populated** during Phase 7 (Analytics Data Loop) when `ItemFlowObserved` entities are created and published to Stellio.

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld",
  "https://www.w3.org/ns/sosa/",
  "https://www.w3.org/ns/ssn/"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:Camera:TTH%20406",
  "type": ["Camera", "sosa:Sensor"],
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld",
    "https://www.w3.org/ns/sosa/",
    "https://www.w3.org/ns/ssn/"
  ],
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
    "value": "TTH"
  },
  "imageSnapshot": {
    "type": "Property",
    "value": "https://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id=662b86c41afb9c00172dd31c&zoom=4&t=1762276164754"
  },
  "status": {
    "type": "Property",
    "value": "success"
  },
  "dateLastValueReported": {
    "type": "Property",
    "value": "2025-11-10T23:13:05.002234Z"
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054105759, 10.7918902432446]
    }
  },
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
    "object": []
  }
}
```

### Configuration Files
- **Mapping**: `config/ngsi_ld_mappings.yaml` (entity_type: Camera)
- **SOSA/SSN**: `config/sosa_mappings.yaml` (sensor_mappings)
- **Transformer**: `agents/transformation/ngsi_ld_transformer_agent.py`
- **SOSA Mapper**: `agents/transformation/sosa_ssn_mapper_agent.py`

### Data Source
- **Raw Data**: `data/cameras_raw.json` (40 cameras from HCMC API)
- **After Phase 1**: `data/cameras_enriched.json` (with weather + air quality)
- **After Phase 2**: `data/ngsi_ld_entities.json` (~120 entities: Camera + Weather + AirQuality)

---

## 2. WeatherObserved

### Description
Real-time weather observation data linked to camera locations. Retrieved from OpenWeatherMap API during Phase 1 (External Data Collector) and transformed to NGSI-LD format in Phase 2.

### Entity Type
- **Type**: `["WeatherObserved", "sosa:Observation"]`
- **URI Pattern**: `urn:ngsi-ld:WeatherObserved:{cameraCode}`
- **Source**: Smart Data Models - dataModel.Weather
- **SOSA/SSN Enhancement**: Added in Phase 2 (Transformation)

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `temperature` | Property | Ambient temperature in Celsius | 28.5 (°C) |
| `relativeHumidity` | Property | Relative humidity percentage | 75.0 (%) |
| `windSpeed` | Property | Wind speed in meters/second | 3.5 (m/s) |
| `precipitation` | Property | Rainfall in last hour (mm) | 0.0 (mm) |
| `weatherType` | Property | Weather condition description | "clear sky", "light rain", "overcast clouds" |
| `atmosphericPressure` | Property | Atmospheric pressure (hPa) | 1013.0 (hPa) |
| `cloudiness` | Property | Cloud cover percentage | 20.0 (%) |
| `dateObserved` | Property | Observation timestamp (ISO 8601) | "2025-11-10T23:13:05Z" |
| `location` | GeoProperty | Geographic coordinates (same as Camera) | `{"type": "Point", "coordinates": [106.691, 10.791]}` |

### Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `refDevice` | Relationship | `urn:ngsi-ld:Camera:{cameraId}` | Link to source camera |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://smart-data-models.github.io/dataModel.Weather/context.jsonld",
  "https://www.w3.org/ns/sosa/",
  "https://www.w3.org/ns/ssn/"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:WeatherObserved:TTH%20406",
  "type": ["WeatherObserved", "sosa:Observation"],
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://smart-data-models.github.io/dataModel.Weather/context.jsonld",
    "https://www.w3.org/ns/sosa/",
    "https://www.w3.org/ns/ssn/"
  ],
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH%20406"
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054105759, 10.7918902432446]
    }
  },
  "temperature": {
    "type": "Property",
    "value": 28.5,
    "unitCode": "CEL",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "relativeHumidity": {
    "type": "Property",
    "value": 75.0,
    "unitCode": "P1",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "windSpeed": {
    "type": "Property",
    "value": 3.5,
    "unitCode": "MTS",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "precipitation": {
    "type": "Property",
    "value": 0.0,
    "unitCode": "MMT",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "weatherType": {
    "type": "Property",
    "value": "clear sky"
  },
  "atmosphericPressure": {
    "type": "Property",
    "value": 1013.0,
    "unitCode": "A97",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "cloudiness": {
    "type": "Property",
    "value": 20.0,
    "unitCode": "P1"
  },
  "dateObserved": {
    "type": "Property",
    "value": "2025-11-10T23:13:05Z"
  }
}
```

### Configuration Files
- **Mapping**: `config/ngsi_ld_mappings.yaml` (weather_mappings section)
- **Data Source Config**: `config/data_sources.yaml` (OpenWeatherMap API)
- **External Collector**: `agents/data_collection/external_data_collector_agent.py`
- **Transformer**: `agents/transformation/ngsi_ld_transformer_agent.py`

### Data Flow
1. **Phase 1**: OpenWeatherMap API → `data/cameras_enriched.json` (weather key)
2. **Phase 2**: NGSI-LD Transformer → `data/ngsi_ld_entities.json` (WeatherObserved entities)
3. **Phase 3**: Validation → `data/validated_entities.json`
4. **Phase 4**: Publishing → Stellio + RDF files

---

## 3. AirQualityObserved

### Description
Real-time air quality observation data linked to camera locations. Retrieved from OpenAQ API v3 during Phase 1 (External Data Collector) and transformed to NGSI-LD format in Phase 2.

### Entity Type
- **Type**: `["AirQualityObserved", "sosa:Observation"]`
- **URI Pattern**: `urn:ngsi-ld:AirQualityObserved:{cameraCode}`
- **Source**: Smart Data Models - dataModel.Environment
- **SOSA/SSN Enhancement**: Added in Phase 2 (Transformation)

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `airQualityIndex` | Property | Overall AQI value (0-500) | 85 |
| `pm25` | Property | PM2.5 concentration (μg/m³) | 25.3 |
| `pm10` | Property | PM10 concentration (μg/m³) | 42.7 |
| `co` | Property | Carbon monoxide (ppm) | 0.8 |
| `o3` | Property | Ozone concentration (μg/m³) | 65.2 |
| `no2` | Property | Nitrogen dioxide (μg/m³) | 38.5 |
| `so2` | Property | Sulfur dioxide (μg/m³) | 12.3 |
| `stationName` | Property | OpenAQ monitoring station name | "US Embassy - Ho Chi Minh City" |
| `distanceFromDevice` | Property | Distance from camera (km) | 3.5 |
| `dateObserved` | Property | Observation timestamp (ISO 8601) | "2025-11-10T23:13:05Z" |
| `location` | GeoProperty | Geographic coordinates (same as Camera) | `{"type": "Point", "coordinates": [106.691, 10.791]}` |

### Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `refDevice` | Relationship | `urn:ngsi-ld:Camera:{cameraId}` | Link to source camera |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://smart-data-models.github.io/dataModel.Environment/context.jsonld",
  "https://www.w3.org/ns/sosa/",
  "https://www.w3.org/ns/ssn/"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:AirQualityObserved:TTH%20406",
  "type": ["AirQualityObserved", "sosa:Observation"],
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://smart-data-models.github.io/dataModel.Environment/context.jsonld",
    "https://www.w3.org/ns/sosa/",
    "https://www.w3.org/ns/ssn/"
  ],
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH%20406"
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054105759, 10.7918902432446]
    }
  },
  "airQualityIndex": {
    "type": "Property",
    "value": 85
  },
  "pm25": {
    "type": "Property",
    "value": 25.3,
    "unitCode": "GQ",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "pm10": {
    "type": "Property",
    "value": 42.7,
    "unitCode": "GQ",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "co": {
    "type": "Property",
    "value": 0.8,
    "unitCode": "GP",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "o3": {
    "type": "Property",
    "value": 65.2,
    "unitCode": "GQ",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "no2": {
    "type": "Property",
    "value": 38.5,
    "unitCode": "GQ",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "so2": {
    "type": "Property",
    "value": 12.3,
    "unitCode": "GQ",
    "observedAt": "2025-11-10T23:13:05Z"
  },
  "stationName": {
    "type": "Property",
    "value": "US Embassy - Ho Chi Minh City"
  },
  "distanceFromDevice": {
    "type": "Property",
    "value": 3.5,
    "unitCode": "KMT"
  },
  "dateObserved": {
    "type": "Property",
    "value": "2025-11-10T23:13:05Z"
  }
}
```

### Configuration Files
- **Mapping**: `config/ngsi_ld_mappings.yaml` (airquality_mappings section)
- **Data Source Config**: `config/data_sources.yaml` (OpenAQ API v3)
- **External Collector**: `agents/data_collection/external_data_collector_agent.py`
- **Transformer**: `agents/transformation/ngsi_ld_transformer_agent.py`

### Data Flow
1. **Phase 1**: OpenAQ API v3 → `data/cameras_enriched.json` (air_quality key)
2. **Phase 2**: NGSI-LD Transformer → `data/ngsi_ld_entities.json` (AirQualityObserved entities)
3. **Phase 3**: Validation → `data/validated_entities.json`
4. **Phase 4**: Publishing → Stellio + RDF files

### API Integration Details
- **API**: OpenAQ v3 (https://api.openaq.org/v3/)
- **Method**: 2-step process
  1. GET /locations?coordinates={lat},{lng}&radius=25000
  2. GET /locations/{id}/latest
- **Rate Limiting**: 60 requests/minute (token bucket)
- **Caching**: 10-minute TTL with async-lru
- **Retry**: 3 attempts with exponential backoff

---

## 4. ItemFlowObserved

### Description
Real-time traffic flow observation created from computer vision analysis of camera images. Contains vehicle count, traffic intensity, occupancy, average speed, and congestion level metrics.

### Entity Type
- **Type**: `"ItemFlowObserved"`
- **URI Pattern**: `urn:ngsi-ld:ItemFlowObserved:{cameraId}-{timestamp}`
- **Source**: Smart Data Models - dataModel.Transportation

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `intensity` | Property | Traffic intensity (0.0-1.0, normalized by max capacity) | 0.65 (65% capacity) |
| `occupancy` | Property | Road occupancy (0.0-1.0, same as intensity) | 0.65 (65% occupancy) |
| `averageSpeed` | Property | Estimated average vehicle speed | 45.0 (km/h) |
| `vehicleCount` | Property | Total number of vehicles detected | 23 |
| `congestionLevel` | Property | Traffic congestion state | "free", "moderate", "congested" |
| `detectionDetails` | Property | CV detection breakdown by vehicle class | `{"total_detections": 25, "classes": {"car": 18, "motorbike": 5, "truck": 2}}` |
| `location` | GeoProperty | Geographic coordinates (copied from Camera) | `{"type": "Point", "coordinates": [106.691, 10.791]}` |

### Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `refDevice` | Relationship | `urn:ngsi-ld:Camera:{cameraId}` | Link to source camera |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:ItemFlowObserved:TTH%20406-20251110T231305Z",
  "type": "ItemFlowObserved",
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
  ],
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH%20406"
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054105759, 10.7918902432446]
    }
  },
  "intensity": {
    "type": "Property",
    "value": 0.65,
    "observedAt": "2025-11-10T23:13:05.002234Z"
  },
  "occupancy": {
    "type": "Property",
    "value": 0.65,
    "observedAt": "2025-11-10T23:13:05.002234Z"
  },
  "averageSpeed": {
    "type": "Property",
    "value": 45.0,
    "unitCode": "KMH",
    "observedAt": "2025-11-10T23:13:05.002234Z"
  },
  "vehicleCount": {
    "type": "Property",
    "value": 23,
    "observedAt": "2025-11-10T23:13:05.002234Z"
  },
  "congestionLevel": {
    "type": "Property",
    "value": "moderate",
    "observedAt": "2025-11-10T23:13:05.002234Z"
  },
  "detectionDetails": {
    "type": "Property",
    "value": {
      "total_detections": 25,
      "classes": {
        "car": 18,
        "motorbike": 5,
        "truck": 2
      }
    }
  }
}
```

### Configuration Files
- **CV Analysis**: `config/cv_config.yaml`
- **Agent**: `agents/analytics/cv_analysis_agent.py`
- **Entity Builder**: `cv_analysis_agent.py` (lines 450-550) - `create_itemflowobserved_entity()`

### Metrics Calculation
- **Vehicle Count**: Direct count from YOLOv8 detections (car, motorbike, bus, truck)
- **Intensity**: `vehicle_count / max_vehicles_per_camera` (default max: 50)
- **Occupancy**: Same as intensity (0.0-1.0 scale)
- **Average Speed**: Estimated from vehicle size/spacing (30-70 km/h range)
- **Congestion Level**: 
  - `free`: intensity < 0.4
  - `moderate`: 0.4 ≤ intensity < 0.8
  - `congested`: intensity ≥ 0.8

---

## 3. RoadAccident

### Description
Detected traffic accident incident using multi-method anomaly detection (speed variance, occupancy spike, sudden stop, pattern anomaly). Generated when confidence threshold exceeds 40%.

### Entity Type
- **Type**: `"RoadAccident"`
- **URI Pattern**: `urn:ngsi-ld:RoadAccident:{cameraId}:{timestamp}`
- **Source**: Smart Data Models - dataModel.Transportation

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `accidentType` | Property | Type of accident detected | "collision", "sudden_stop", "anomaly" |
| `severity` | Property | Severity classification | "minor", "moderate", "severe" |
| `confidence` | Property | Detection confidence score (0.0-1.0) | 0.85 (85% confidence) |
| `detectionMethods` | Property | Methods that detected accident | `["speed_variance", "occupancy_spike"]` |
| `location` | GeoProperty | Geographic coordinates | `{"type": "Point", "coordinates": [106.691, 10.791]}` |
| `dateDetected` | Property | Detection timestamp (ISO 8601) | "2025-10-31T23:15:30.123456Z" |
| `description` | Property | Incident description | "Sudden speed drop detected at intersection" |
| `status` | Property | Incident status | "detected", "confirmed", "resolved" |
| `involvedVehicles` | Property | Estimated vehicle count | 3 |
| `trafficImpact` | Property | Impact assessment | "high", "medium", "low" |

### Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `refDevice` | Relationship | `urn:ngsi-ld:Camera:{cameraId}` | Link to camera |
| `refObservations` | Relationship | List of `ItemFlowObserved` IDs | Related observations |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:RoadAccident:TTH%20406:20251110T231530",
  "type": "RoadAccident",
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
  ],
  "accidentType": {
    "type": "Property",
    "value": "sudden_stop"
  },
  "severity": {
    "type": "Property",
    "value": "moderate"
  },
  "confidence": {
    "type": "Property",
    "value": 0.85
  },
  "detectionMethods": {
    "type": "Property",
    "value": ["speed_variance", "occupancy_spike", "sudden_stop"]
  },
  "location": {
    "type": "GeoProperty",
    "value": {
      "type": "Point",
      "coordinates": [106.691054105759, 10.7918902432446]
    }
  },
  "dateDetected": {
    "type": "Property",
    "value": "2025-11-10T23:15:30.123456Z"
  },
  "description": {
    "type": "Property",
    "value": "Sudden speed drop detected at intersection with occupancy spike"
  },
  "status": {
    "type": "Property",
    "value": "detected"
  },
  "involvedVehicles": {
    "type": "Property",
    "value": 3
  },
  "trafficImpact": {
    "type": "Property",
    "value": "high"
  },
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH%20406"
  }
}
```

### Configuration Files
- **Config**: `config/accident_config.yaml`
- **Agent**: `agents/analytics/accident_detection_agent.py`

### Detection Methods
1. **Speed Variance**: Z-score > 3.0 (3 standard deviations)
2. **Occupancy Spike**: 2x normal occupancy
3. **Sudden Stop**: 80% speed drop in 30 seconds
4. **Pattern Anomaly**: Intensity 2.5 standard deviations from historical mean

### Severity Thresholds
- **Minor**: 0.3 ≤ confidence < 0.6 (possible incident)
- **Moderate**: 0.6 ≤ confidence < 0.9 (likely accident)
- **Severe**: confidence ≥ 0.9 (confirmed accident)

---

## 4. TrafficPattern

### Description
Historical traffic pattern analysis with time-series statistics, anomaly detection, and forecasting. Generates hourly, daily, and weekly patterns with predictions for short/medium/long-term horizons.

### Entity Type
- **Type**: `"TrafficPattern"`
- **URI Pattern**: `urn:ngsi-ld:TrafficPattern:{cameraId}:{patternType}:{timestamp}`
- **Source**: Custom model for traffic analytics

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `patternType` | Property | Pattern category | "hourly", "daily", "weekly", "rush_hour", "anomaly" |
| `analysisWindow` | Property | Time window analyzed | `{"start": "2025-10-25T00:00:00Z", "end": "2025-10-31T23:59:59Z", "duration": 604800}` |
| `metrics` | Property | Analyzed metrics | `["vehicle_count", "average_speed", "occupancy", "intensity"]` |
| `statistics` | Property | Statistical aggregates | `{"mean": 35.2, "median": 32.0, "std": 12.5, "min": 5, "max": 78, "p25": 20, "p75": 48, "p95": 65}` |
| `anomalies` | Property | Detected anomalies | `[{"timestamp": "2025-10-30T18:45:00Z", "z_score": 3.2, "value": 85}]` |
| `predictions` | Property | Forecast values | `{"short_term": 42, "medium_term": 38, "long_term": 35, "confidence": 0.75}` |
| `confidence` | Property | Pattern confidence (0.0-1.0) | 0.85 |
| `detectedAt` | Property | Pattern detection timestamp | "2025-10-31T23:59:59.123456Z" |
| `validUntil` | Property | Pattern validity expiration | "2025-11-07T23:59:59.123456Z" |

### Relationships

| Relationship | Type | Target Entity | Description |
|--------------|------|---------------|-------------|
| `refDevice` | Relationship | `urn:ngsi-ld:Camera:{cameraId}` | Link to camera |
| `refObservations` | Relationship | List of `ItemFlowObserved` IDs | Source observations |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://raw.githubusercontent.com/smart-data-models/data-models/master/context.jsonld"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:TrafficPattern:TTH%20406:hourly:20251110T2300",
  "type": "TrafficPattern",
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/data-models/master/context.jsonld"
  ],
  "patternType": {
    "type": "Property",
    "value": "hourly"
  },
  "analysisWindow": {
    "type": "Property",
    "value": {
      "start": "2025-11-10T23:00:00Z",
      "end": "2025-11-10T23:59:59Z",
      "duration": 3600
    }
  },
  "metrics": {
    "type": "Property",
    "value": ["vehicle_count", "average_speed", "occupancy", "intensity"]
  },
  "statistics": {
    "type": "Property",
    "value": {
      "mean": 35.2,
      "median": 32.0,
      "std": 12.5,
      "min": 5,
      "max": 78,
      "percentile_25": 20,
      "percentile_75": 48,
      "percentile_95": 65
    }
  },
  "anomalies": {
    "type": "Property",
    "value": [
      {
        "timestamp": "2025-11-10T23:45:00Z",
        "z_score": 3.2,
        "value": 85,
        "metric": "vehicle_count"
      }
    ]
  },
  "predictions": {
    "type": "Property",
    "value": {
      "short_term": 42,
      "medium_term": 38,
      "long_term": 35,
      "confidence": 0.75,
      "method": "weighted_average"
    }
  },
  "confidence": {
    "type": "Property",
    "value": 0.85
  },
  "detectedAt": {
    "type": "Property",
    "value": "2025-11-10T23:59:59.123456Z"
  },
  "validUntil": {
    "type": "Property",
    "value": "2025-11-17T23:59:59.123456Z"
  },
  "refDevice": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Camera:TTH%20406"
  }
}
```

### Configuration Files
- **Config**: `config/pattern_recognition.yaml`
- **Agent**: `agents/analytics/pattern_recognition_agent.py`
- **Storage**: Neo4j graph database (bolt://localhost:7687)

### Analysis Windows
- **Hourly**: 3,600 seconds (1 hour), min 10 samples
- **Daily**: 86,400 seconds (24 hours), min 24 samples
- **Weekly**: 604,800 seconds (7 days), min 168 samples

### Forecasting Methods
1. **Moving Average**: Simple 7-observation window (weight: 0.25)
2. **Exponential Smoothing**: α=0.3 smoothing factor (weight: 0.30)
3. **Weighted Moving Average**: Recent data weighted more (weight: 0.20)
4. **ARIMA**: p=1, d=1, q=1 (weight: 0.25)

---

## 5. ObservableProperty

### Description
SOSA/SSN semantic annotation representing what sensors observe. In this traffic domain, represents "Traffic Flow" as the observable phenomenon. This is a domain-specific semantic entity.

### Entity Type
- **Type**: `"ObservableProperty"`
- **URI**: `urn:ngsi-ld:ObservableProperty:TrafficFlow` (singleton)
- **Source**: SOSA/SSN Ontology

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `name` | Property | Observable property name | "Traffic Flow Monitoring" |
| `description` | Property | Property description | "Observable property representing traffic flow characteristics" |
| `unitOfMeasurement` | Property | Measurement unit | "vehicles/hour" |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://www.w3.org/ns/sosa/",
  "https://www.w3.org/ns/ssn/"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:ObservableProperty:TrafficFlow",
  "type": "ObservableProperty",
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://www.w3.org/ns/sosa/",
    "https://www.w3.org/ns/ssn/"
  ],
  "name": {
    "type": "Property",
    "value": "Traffic Flow Monitoring"
  },
  "description": {
    "type": "Property",
    "value": "Observable property representing traffic flow characteristics"
  },
  "unitOfMeasurement": {
    "type": "Property",
    "value": "vehicles/hour"
  }
}
```

### Configuration Files
- **SOSA Mapping**: `config/sosa_mappings.yaml`
- **Agent**: `agents/transformation/sosa_ssn_mapper_agent.py`

### Domain Adaptation
To adapt to other domains (e.g., air quality, temperature), modify `config/sosa_mappings.yaml`:
```yaml
observable_property:
  domain_type: "AirQuality"  # Change from "TrafficFlow"
  properties:
    name: "Air Quality Monitoring"
    unit_of_measurement: "AQI"
```

---

## 6. Platform

### Description
SOSA/SSN platform entity representing the hosting infrastructure for all sensors. In this system, represents the "HCMC Traffic Monitoring System" that hosts all 40 cameras.

### Entity Type
- **Type**: `"Platform"`
- **URI**: `urn:ngsi-ld:Platform:HCMCTrafficSystem` (singleton)
- **Source**: SOSA/SSN Ontology

### Properties Used

| Property | Type | Description | Example Value |
|----------|------|-------------|---------------|
| `name` | Property | Platform name | "Ho Chi Minh City Traffic Monitoring System" |
| `description` | Property | Platform description | "City-wide traffic monitoring infrastructure" |
| `operator` | Property | Operating organization | "HCMC Department of Transportation" |
| `deploymentYear` | Property | Year deployed | 2020 |
| `coverageArea` | Property | Geographic coverage | "Ho Chi Minh City, Vietnam" |

### @context URLs
```json
[
  "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
  "https://www.w3.org/ns/sosa/",
  "https://www.w3.org/ns/ssn/"
]
```

### Example Entity
```json
{
  "id": "urn:ngsi-ld:Platform:HCMCTrafficSystem",
  "type": "Platform",
  "@context": [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://www.w3.org/ns/sosa/",
    "https://www.w3.org/ns/ssn/"
  ],
  "name": {
    "type": "Property",
    "value": "Ho Chi Minh City Traffic Monitoring System"
  },
  "description": {
    "type": "Property",
    "value": "City-wide traffic monitoring infrastructure"
  },
  "operator": {
    "type": "Property",
    "value": "HCMC Department of Transportation"
  },
  "deploymentYear": {
    "type": "Property",
    "value": 2020
  },
  "coverageArea": {
    "type": "Property",
    "value": "Ho Chi Minh City, Vietnam"
  }
}
```

### Configuration Files
- **SOSA Mapping**: `config/sosa_mappings.yaml`
- **Agent**: `agents/transformation/sosa_ssn_mapper_agent.py`

### Domain Adaptation
To adapt to other domains (e.g., healthcare), modify `config/sosa_mappings.yaml`:
```yaml
platform:
  id: "urn:ngsi-ld:Platform:HospitalMonitoringSystem"
  name: "Hospital Patient Monitoring System"
  description: "Hospital-wide patient vital signs monitoring infrastructure"
```

---

## Summary Statistics

### Models by Category
- **Physical Entities**: 1 (Camera)
- **Observation Data**: 1 (ItemFlowObserved)
- **Analytics Outputs**: 2 (RoadAccident, TrafficPattern)
- **Semantic Annotations**: 2 (ObservableProperty, Platform)

### Properties by Type
- **Property**: 41 properties across all models
- **GeoProperty**: 4 (location in Camera, ItemFlowObserved, RoadAccident, TrafficPattern)
- **Relationship**: 7 relationships (refDevice, sosa:observes, sosa:isHostedBy, etc.)

### Context URLs Used
1. **NGSI-LD Core**: `https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld`
2. **Smart Data Models - Device**: `https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld`
3. **Smart Data Models - Transportation**: `https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld`
4. **Smart Data Models - Generic**: `https://raw.githubusercontent.com/smart-data-models/data-models/master/context.jsonld`
5. **SOSA Ontology**: `https://www.w3.org/ns/sosa/`
6. **SSN Ontology**: `https://www.w3.org/ns/ssn/`

### Data Flow Overview
```
Raw Camera Data
    ↓
[Camera] entities → Stellio + Fuseki (8,880 triples)
    ↓
CV Analysis Agent
    ↓
[ItemFlowObserved] entities → Stellio + Fuseki (3,000+ triples)
    ↓
Analytics Agents
    ↓
[RoadAccident] + [TrafficPattern] entities → Stellio + Fuseki (3,000+ triples)
    ↓
SOSA/SSN Mapper
    ↓
[ObservableProperty] + [Platform] entities → Stellio + Fuseki (200 triples)
    ↓
Total: 15,000+ triples in LOD cloud
```

---

## Pipeline Integration

### Phase 1-6: Core Pipeline
1. **Data Collection**: Camera data → `data/cameras_raw.json`
2. **Transformation**: NGSI-LD → `data/ngsi_ld_entities.json`
3. **Validation**: Schema validation → `data/validated_entities.json`
4. **SOSA Enrichment**: Semantic annotation → `data/sosa_enhanced_entities.json`
5. **Publishing**: Stellio Context Broker
6. **RDF Conversion**: 4 formats (Turtle, JSON-LD, N-Triples, RDF/XML) → `data/rdf/`

### Phase 7: Analytics Data Loop (NEW)
7. **CV Analysis**: ItemFlowObserved generation → `data/observations.json`
   - Validation → Publishing → RDF conversion → Fuseki (`data/rdf_observations/`)

### Phase 8: State Update Sync (NEW)
8. **Congestion Updates**: Query Stellio for updated cameras
   - RDF conversion → Fuseki update (`data/rdf_updates/`)

### Agents Involved
- **Transformation**: 2 agents (ngsi_ld_transformer, sosa_ssn_mapper)
- **Analytics**: 4 agents (cv_analysis, congestion_detection, accident_detection, pattern_recognition)
- **Validation**: 1 agent (smart_data_models_validation_agent)
- **Publishing**: 2 agents (entity_publisher, stellio_state_query)
- **RDF**: 2 agents (ngsi_ld_to_rdf, triplestore_loader)

---

## SPARQL Query Examples

### Query 1: Get All Cameras with Locations
```sparql
PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

SELECT ?camera ?name ?lat ?lon WHERE {
  ?camera a ngsi-ld:Camera ;
          ngsi-ld:cameraName ?name ;
          ngsi-ld:location ?loc .
  
  ?loc geo:lat ?lat ;
       geo:long ?lon .
}
```

### Query 2: Get Observations for Congested Cameras
```sparql
PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>

SELECT ?camera ?observation ?intensity ?congested WHERE {
  ?camera a ngsi-ld:Camera ;
          ngsi-ld:congested ?congested .
  
  ?observation a ngsi-ld:ItemFlowObserved ;
               ngsi-ld:refDevice ?camera ;
               ngsi-ld:intensity ?intensity .
  
  FILTER(?congested = true)
}
```

### Query 3: Get SOSA Sensor Relationships
```sparql
PREFIX sosa: <https://www.w3.org/ns/sosa/>
PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>

SELECT ?sensor ?observes ?platform WHERE {
  ?sensor a sosa:Sensor ;
          sosa:observes ?observes ;
          sosa:isHostedBy ?platform .
}
```

### Query 4: Get Traffic Patterns with Anomalies
```sparql
PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>

SELECT ?pattern ?camera ?patternType ?anomalies WHERE {
  ?pattern a ngsi-ld:TrafficPattern ;
           ngsi-ld:refDevice ?camera ;
           ngsi-ld:patternType ?patternType ;
           ngsi-ld:anomalies ?anomalies .
  
  FILTER(bound(?anomalies))
}
```

---

## Domain Adaptation Guide

This pipeline is **100% domain-agnostic** and can be adapted to any LOD domain by modifying configuration files:

### Healthcare Domain Example
```yaml
# config/ngsi_ld_mappings.yaml
entity_type: "MedicalDevice"
uri_prefix: "urn:ngsi-ld:MedicalDevice:"

# config/sosa_mappings.yaml
observable_property:
  domain_type: "VitalSigns"
  properties:
    name: "Patient Vital Signs Monitoring"
    unit_of_measurement: "bpm, °C, mmHg"

platform:
  id: "urn:ngsi-ld:Platform:HospitalMonitoringSystem"
  name: "Hospital Patient Monitoring System"
```

### Smart Agriculture Example
```yaml
# config/ngsi_ld_mappings.yaml
entity_type: "AgriculturalSensor"
uri_prefix: "urn:ngsi-ld:AgriculturalSensor:"

# config/sosa_mappings.yaml
observable_property:
  domain_type: "SoilMoisture"
  properties:
    name: "Soil Moisture Monitoring"
    unit_of_measurement: "volumetric water content (%)"

platform:
  id: "urn:ngsi-ld:Platform:SmartFarmSystem"
  name: "Smart Farm Monitoring System"
```

---

## Related Documentation

- **Pipeline Architecture**: `.audit/COMPLETE_PIPELINE_DIAGRAM.md`
- **Analytics Data Loop**: `.audit/ANALYTICS_DATA_LOOP_SUMMARY.md`
- **Configuration Files**:
  - `config/workflow.yaml` - Complete pipeline workflow
  - `config/ngsi_ld_mappings.yaml` - Camera property mappings
  - `config/sosa_mappings.yaml` - SOSA/SSN semantic mappings
  - `config/cv_config.yaml` - ItemFlowObserved settings
  - `config/accident_config.yaml` - RoadAccident detection
  - `config/pattern_recognition.yaml` - TrafficPattern analysis

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-11-10  
**Total Models**: 6  
**Total Properties**: 41  
**Total Relationships**: 7  
**Context URLs**: 6  
**Pipeline Status**: ✅ 100% Complete (8 phases, 19 agents)

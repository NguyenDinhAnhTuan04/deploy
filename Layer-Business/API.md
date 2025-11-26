# API Documentation

## Base URL
```
http://localhost:5000
```

## Authentication
No authentication required for current version.

## Headers
```
Content-Type: application/json
Accept: application/json
```

---

## Health Check

### GET /health
Check server health and data source connection status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T10:30:00.000Z",
  "connections": {
    "stellio": {
      "healthy": true,
      "details": {
        "url": "http://localhost:8080/ngsi-ld/v1/entities",
        "status": 200,
        "contentType": "application/ld+json"
      }
    },
    "fuseki": {
      "healthy": true,
      "details": {
        "url": "http://localhost:3030/lod-dataset/sparql",
        "authenticated": true
      }
    },
    "neo4j": {
      "healthy": true,
      "details": {
        "uri": "bolt://localhost:7687",
        "authenticated": true,
        "databaseAvailable": true
      }
    },
    "postgresql": {
      "healthy": true,
      "details": {
        "host": "localhost",
        "port": 5432,
        "database": "stellio_search",
        "connected": true
      }
    }
  }
}
```

**Status Codes:**
- `200 OK` - All connections healthy
- `503 Service Unavailable` - One or more connections failed

---

## Cameras

### GET /api/cameras
Get all traffic cameras.

**Source:** Stellio Context Broker (NGSI-LD)

**Response:**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "id": "urn:ngsi-ld:Camera:001",
      "name": "District 1 - Le Loi Street",
      "location": {
        "latitude": 10.8231,
        "longitude": 106.6297,
        "address": "Le Loi Street, District 1, HCMC"
      },
      "status": "active",
      "streamUrl": "rtsp://camera01.example.com/stream",
      "lastUpdate": "2025-11-10T10:30:00.000Z"
    }
  ]
}
```

### GET /api/cameras/:id
Get single camera by ID.

**Parameters:**
- `id` (path) - Camera ID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "urn:ngsi-ld:Camera:001",
    "name": "District 1 - Le Loi Street",
    "location": {
      "latitude": 10.8231,
      "longitude": 106.6297,
      "address": "Le Loi Street, District 1, HCMC"
    },
    "status": "active",
    "streamUrl": "rtsp://camera01.example.com/stream",
    "lastUpdate": "2025-11-10T10:30:00.000Z"
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `404 Not Found` - Camera not found
- `500 Internal Server Error` - Server error

---

## Weather

### GET /api/weather
Get all weather observations.

**Source:** Stellio Context Broker (NGSI-LD)

**Response:**
```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "id": "urn:ngsi-ld:Weather:001",
      "location": {
        "latitude": 10.8231,
        "longitude": 106.6297,
        "district": "District 1"
      },
      "temperature": 32.5,
      "humidity": 75,
      "rainfall": 0.5,
      "windSpeed": 15,
      "windDirection": "NE",
      "condition": "Partly Cloudy",
      "timestamp": "2025-11-10T10:30:00.000Z"
    }
  ]
}
```

---

## Air Quality

### GET /api/air-quality
Get all air quality observations.

**Source:** Stellio Context Broker (NGSI-LD)

**Response:**
```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "id": "urn:ngsi-ld:AirQuality:001",
      "location": {
        "latitude": 10.8231,
        "longitude": 106.6297,
        "station": "District 1 Monitoring Station"
      },
      "aqi": 85,
      "pm25": 35.5,
      "pm10": 65.2,
      "co": 0.8,
      "no2": 25.3,
      "so2": 12.1,
      "o3": 45.6,
      "level": "moderate",
      "timestamp": "2025-11-10T10:30:00.000Z"
    }
  ]
}
```

**AQI Levels:**
- `good` (0-50)
- `moderate` (51-100)
- `unhealthy` (101-150)
- `very_unhealthy` (151-200)
- `hazardous` (201+)

---

## Accidents

### GET /api/accidents
Get all accidents or accidents within a specific area.

**Source:** Neo4j Graph Database

**Query Parameters:**
- `lat` (optional) - Latitude for area search
- `lon` (optional) - Longitude for area search
- `radius` (optional) - Radius in kilometers (default: 5)

**Response:**
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "id": "accident-001",
      "location": {
        "latitude": 10.8231,
        "longitude": 106.6297,
        "address": "Le Loi Street, District 1"
      },
      "type": "collision",
      "severity": "moderate",
      "description": "Two-vehicle collision, minor injuries",
      "timestamp": "2025-11-10T09:15:00.000Z",
      "resolved": false,
      "casualties": 2
    }
  ]
}
```

**Accident Types:**
- `collision` - Vehicle collision
- `pedestrian` - Pedestrian involved
- `motorcycle` - Motorcycle accident
- `vehicle` - Single vehicle
- `other` - Other types

**Severity Levels:**
- `minor` - Minor damage, no injuries
- `moderate` - Moderate damage, minor injuries
- `severe` - Severe damage, serious injuries
- `fatal` - Fatalities involved

### GET /api/accidents/:id
Get single accident by ID.

### GET /api/accidents/:id/relationships
Get accident relationships from graph database.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "relationship": "NEAR",
      "relatedType": "Camera",
      "related": {
        "id": "camera-001",
        "name": "District 1 Camera"
      }
    }
  ]
}
```

---

## Traffic Patterns

### GET /api/patterns
Get all traffic patterns with historical data and predictions.

**Sources:** 
- Fuseki (SPARQL) - Traffic patterns and historical data
- PostgreSQL - Traffic metrics and predictions

**Response:**
```json
{
  "success": true,
  "count": 15,
  "data": [
    {
      "id": "pattern-001",
      "roadSegment": "Le Loi - District 1",
      "location": {
        "startPoint": {
          "latitude": 10.8231,
          "longitude": 106.6297
        },
        "endPoint": {
          "latitude": 10.8241,
          "longitude": 106.6307
        }
      },
      "averageSpeed": 35.5,
      "vehicleCount": 450,
      "congestionLevel": "moderate",
      "timeOfDay": "10:30:00",
      "dayOfWeek": "Monday",
      "historicalData": [
        {
          "date": "2025-11-09T10:30:00.000Z",
          "averageSpeed": 38.2,
          "vehicleCount": 425
        }
      ],
      "predictions": {
        "nextHour": 32.5,
        "confidence": 0.85
      },
      "timestamp": "2025-11-10T10:30:00.000Z"
    }
  ]
}
```

**Congestion Levels:**
- `free_flow` - Speed ≥ 60 km/h
- `light` - Speed 40-59 km/h
- `moderate` - Speed 25-39 km/h
- `heavy` - Speed 15-24 km/h
- `severe` - Speed < 15 km/h

### GET /api/patterns/road-segments
Get all road segments.

**Source:** Fuseki (SPARQL)

**Response:**
```json
{
  "success": true,
  "count": 20,
  "data": [
    {
      "id": "segment-001",
      "name": "Le Loi Street",
      "startPoint": {
        "latitude": 10.8231,
        "longitude": 106.6297
      },
      "endPoint": {
        "latitude": 10.8241,
        "longitude": 106.6307
      }
    }
  ]
}
```

### GET /api/patterns/:roadSegment
Get traffic pattern for specific road segment.

**Parameters:**
- `roadSegment` (path) - Road segment identifier

**Response:**
```json
{
  "success": true,
  "data": {
    "roadSegment": "Le Loi - District 1",
    "currentMetrics": {
      "avg_speed": 35.5,
      "vehicle_count": 450,
      "congestion_level": "moderate"
    },
    "historicalData": [
      {
        "date": "2025-11-09",
        "averageSpeed": 38.2,
        "vehicleCount": 425
      }
    ]
  }
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error message (in development mode)"
}
```

**Common Error Codes:**
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Data source unavailable

---

## Rate Limiting

No rate limiting currently implemented.

## CORS

CORS is enabled for `http://localhost:3000` by default.

To change CORS origin, update `CORS_ORIGIN` in `.env`:
```env
CORS_ORIGIN=http://your-frontend-domain.com
```

---

## WebSocket API

### Connection
```
ws://localhost:5001
```

### Subscribe to Updates
```json
{
  "type": "subscribe",
  "topics": ["camera", "weather", "air_quality", "accident", "pattern"]
}
```

### Receive Updates
```json
{
  "type": "camera",
  "data": { /* Camera object */ },
  "timestamp": "2025-11-10T10:30:00.000Z"
}
```

**Message Types:**
- `connection` - Connection established
- `subscribed` - Subscription confirmed
- `camera` - Camera update
- `weather` - Weather update
- `air_quality` - Air quality update
- `accident` - Accident update
- `pattern` - Traffic pattern update

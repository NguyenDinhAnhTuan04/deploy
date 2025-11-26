# HCMC Traffic Monitoring System

A full-stack web application for real-time traffic monitoring in Ho Chi Minh City, Vietnam.

## Architecture

### Backend (Node.js/Express)
- **REST API** with endpoints for cameras, weather, air quality, accidents, and traffic patterns
- **WebSocket Server** for real-time data updates
- **Data Sources Integration**:
  - Stellio Context Broker (http://localhost:8080/ngsi-ld/v1) - NGSI-LD entities
  - Apache Jena Fuseki (http://localhost:3030/lod-dataset/sparql) - SPARQL queries with Basic Auth (admin:test_admin)
  - Neo4j Graph Database (bolt://localhost:7687) - Accident data with auth (neo4j:test12345)
  - PostgreSQL (localhost:5432/stellio_search) - Traffic metrics and predictions with auth (stellio_user:stellio_test)

### Frontend (React + TypeScript)
- **Interactive Map** using Leaflet
- **Real-time Updates** via WebSocket
- **State Management** with Zustand
- **Responsive UI** with Tailwind CSS

## Prerequisites

- Node.js 18+ 
- npm or yarn
- Running instances of:
  - **Stellio Context Broker** (port 8080)
    - NGSI-LD endpoint: `/ngsi-ld/v1`
  - **Apache Jena Fuseki** (port 3030)
    - Dataset: `lod-dataset`
    - Credentials: `admin` / `test_admin`
  - **Neo4j** (ports 7474, 7687)
    - Credentials: `neo4j` / `test12345`
  - **PostgreSQL** (port 5432)
    - Database: `stellio_search`
    - Credentials: `stellio_user` / `stellio_test`

## Installation

### Backend Setup

```bash
cd backend
npm install
npm run setup
# Edit .env with your database credentials if needed
npm run test:connections  # Test all data source connections
npm run dev
```

The backend will:
1. Check all data source connections on startup
2. Display connection status for each service
3. Run on `http://localhost:5000`
4. Start WebSocket on `ws://localhost:5001`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend will run on `http://localhost:3000`.

## Configuration

### Backend Environment Variables

```env
# Server Configuration
PORT=5000
NODE_ENV=development

# Data Sources
STELLIO_URL=http://localhost:8080
STELLIO_NGSI_LD_PATH=/ngsi-ld/v1
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=lod-dataset
FUSEKI_USER=admin
FUSEKI_PASSWORD=test_admin
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test12345
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=stellio_user
POSTGRES_PASSWORD=stellio_test
POSTGRES_DB=stellio_search

# CORS
CORS_ORIGIN=http://localhost:3000

# WebSocket
WS_PORT=5001

# Update Intervals (milliseconds)
DATA_UPDATE_INTERVAL=30000
```

### Frontend Environment Variables

```env
VITE_API_URL=http://localhost:5000
VITE_WS_URL=ws://localhost:5001
```

## API Endpoints

### Cameras
- `GET /api/cameras` - Get all cameras
- `GET /api/cameras/:id` - Get camera by ID

### Weather
- `GET /api/weather` - Get all weather observations

### Air Quality
- `GET /api/air-quality` - Get all air quality observations

### Accidents
- `GET /api/accidents` - Get all accidents
- `GET /api/accidents?lat=<lat>&lon=<lon>&radius=<km>` - Get accidents by area
- `GET /api/accidents/:id` - Get accident by ID
- `GET /api/accidents/:id/relationships` - Get accident relationships

### Traffic Patterns
- `GET /api/patterns` - Get all traffic patterns
- `GET /api/patterns/road-segments` - Get all road segments
- `GET /api/patterns/:roadSegment` - Get pattern for specific road segment

## WebSocket Events

### Client → Server
```json
{
  "type": "subscribe",
  "topics": ["camera", "weather", "air_quality", "accident", "pattern"]
}
```

### Server → Client
```json
{
  "type": "camera|weather|air_quality|accident|pattern|update",
  "data": { ... },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Data Models

### Camera
```typescript
{
  id: string;
  name: string;
  location: { latitude, longitude, address };
  status: 'active' | 'inactive' | 'maintenance';
  streamUrl?: string;
  lastUpdate: string;
}
```

### Weather
```typescript
{
  id: string;
  location: { latitude, longitude, district };
  temperature: number;
  humidity: number;
  rainfall: number;
  windSpeed: number;
  windDirection: string;
  condition: string;
  timestamp: string;
}
```

### Air Quality
```typescript
{
  id: string;
  location: { latitude, longitude, station };
  aqi: number;
  pm25: number;
  pm10: number;
  co: number;
  no2: number;
  so2: number;
  o3: number;
  level: 'good' | 'moderate' | 'unhealthy' | 'very_unhealthy' | 'hazardous';
  timestamp: string;
}
```

### Accident
```typescript
{
  id: string;
  location: { latitude, longitude, address };
  type: 'collision' | 'pedestrian' | 'motorcycle' | 'vehicle' | 'other';
  severity: 'minor' | 'moderate' | 'severe' | 'fatal';
  description: string;
  timestamp: string;
  resolved: boolean;
  casualties?: number;
}
```

### Traffic Pattern
```typescript
{
  id: string;
  roadSegment: string;
  location: {
    startPoint: { latitude, longitude };
    endPoint: { latitude, longitude };
  };
  averageSpeed: number;
  vehicleCount: number;
  congestionLevel: 'free_flow' | 'light' | 'moderate' | 'heavy' | 'severe';
  timeOfDay: string;
  dayOfWeek: string;
  historicalData: Array<{
    date: string;
    averageSpeed: number;
    vehicleCount: number;
  }>;
  predictions?: {
    nextHour: number;
    confidence: number;
  };
  timestamp: string;
}
```

## Features

- ✅ Real-time traffic monitoring via WebSocket
- ✅ Interactive map with multiple data layers
- ✅ Camera locations and status
- ✅ Weather observations
- ✅ Air quality monitoring
- ✅ Accident tracking and reporting
- ✅ Traffic pattern analysis with predictions
- ✅ Historical data visualization
- ✅ Responsive design for mobile and desktop
- ✅ Filter controls for different data types
- ✅ Statistics dashboard

## Development

### Backend Development
```bash
cd backend
npm run dev  # Hot reload with ts-node-dev
npm run build  # Compile TypeScript
npm start  # Run compiled JavaScript
```

### Frontend Development
```bash
cd frontend
npm run dev  # Vite dev server with hot reload
npm run build  # Production build
npm run preview  # Preview production build
```

## Production Deployment

### Backend
```bash
cd backend
npm run build
npm start
```

### Frontend
```bash
cd frontend
npm run build
# Deploy dist/ folder to static hosting
```

## Technologies

### Backend
- Node.js + Express.js
- TypeScript
- WebSocket (ws)
- Axios (HTTP client)
- Neo4j Driver
- PostgreSQL (pg)
- SPARQL HTTP Client
- Winston (logging)

### Frontend
- React 18
- TypeScript
- Vite
- Leaflet + React-Leaflet
- Zustand (state management)
- Axios (HTTP client)
- Tailwind CSS
- date-fns

## License

MIT

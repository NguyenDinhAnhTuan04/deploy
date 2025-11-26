# Project Structure

```
Layer-Business/
│
├── backend/                          # Node.js/Express Backend
│   ├── src/
│   │   ├── server.ts                # Main server entry point
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript type definitions
│   │   ├── services/
│   │   │   ├── stellioService.ts    # Stellio Context Broker integration
│   │   │   ├── fusekiService.ts     # Apache Jena Fuseki SPARQL queries
│   │   │   ├── neo4jService.ts      # Neo4j graph database service
│   │   │   ├── postgresService.ts   # PostgreSQL database service
│   │   │   ├── websocketService.ts  # WebSocket server management
│   │   │   └── dataAggregator.ts    # Data aggregation and broadcasting
│   │   ├── routes/
│   │   │   ├── cameraRoutes.ts      # Camera API endpoints
│   │   │   ├── weatherRoutes.ts     # Weather API endpoints
│   │   │   ├── airQualityRoutes.ts  # Air quality API endpoints
│   │   │   ├── accidentRoutes.ts    # Accident API endpoints
│   │   │   └── patternRoutes.ts     # Traffic pattern API endpoints
│   │   ├── middlewares/
│   │   │   └── errorHandler.ts      # Error handling middleware
│   │   └── utils/
│   │       └── logger.ts            # Winston logger configuration
│   ├── logs/                        # Application logs
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── .gitignore
│
├── frontend/                        # React/TypeScript Frontend
│   ├── src/
│   │   ├── main.tsx                # Application entry point
│   │   ├── App.tsx                 # Root component
│   │   ├── index.css               # Global styles (Tailwind)
│   │   ├── vite-env.d.ts           # Vite environment types
│   │   ├── types/
│   │   │   └── index.ts            # TypeScript type definitions
│   │   ├── store/
│   │   │   └── trafficStore.ts     # Zustand state management
│   │   ├── services/
│   │   │   ├── api.ts              # REST API client (Axios)
│   │   │   └── websocket.ts        # WebSocket client service
│   │   └── components/
│   │       ├── TrafficMap.tsx      # Leaflet map component
│   │       └── Sidebar.tsx         # Sidebar with filters and stats
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env.example
│   └── .gitignore
│
├── package.json                     # Root package.json for scripts
├── .gitignore                       # Root gitignore
├── README.md                        # Comprehensive documentation
└── QUICKSTART.md                    # Quick start guide
```

## Backend Architecture

### Services Layer
- **StellioService**: Fetches NGSI-LD entities (cameras, weather, air quality) from Stellio Context Broker
- **FusekiService**: Executes SPARQL queries against Fuseki triple store for traffic patterns and historical data
- **Neo4jService**: Queries Neo4j graph database for accident data and relationships
- **PostgresService**: Retrieves traffic metrics, predictions, and time-series data from PostgreSQL
- **WebSocketService**: Manages WebSocket connections and broadcasts real-time updates
- **DataAggregator**: Orchestrates data fetching from all sources and broadcasts via WebSocket

### Routes Layer
- RESTful API endpoints for each data type
- Request validation and error handling
- Response formatting with success/error status

### Data Flow
1. Client connects to WebSocket server
2. DataAggregator fetches data from all sources every 30 seconds (configurable)
3. Data is transformed to unified format
4. Updates broadcast to all connected clients via WebSocket
5. REST API provides on-demand data access

## Frontend Architecture

### Components
- **TrafficMap**: Main Leaflet map with markers, popups, and polylines
- **Sidebar**: Filter controls and statistics dashboard

### State Management (Zustand)
- Cameras, weather, air quality, accidents, patterns arrays
- Selected items for detail views
- Filter states for toggling data layers
- WebSocket connection status

### Services
- **API Client**: Axios-based REST API communication
- **WebSocket Client**: Real-time data subscription and handling

### Data Flow
1. App loads initial data via REST API
2. WebSocket connects and subscribes to updates
3. Incoming WebSocket messages update Zustand store
4. React components re-render with new data
5. Map markers and overlays update automatically

## Key Features

### Real-time Updates
- WebSocket connection with automatic reconnection
- 30-second data refresh interval (configurable)
- Live connection status indicator

### Interactive Map
- OpenStreetMap tiles
- Color-coded markers by data type
- Clickable markers with detailed popups
- Traffic pattern polylines with congestion colors
- Filter toggles for each data layer

### Data Integration
- Stellio: NGSI-LD entities for cameras and sensors
- Fuseki: SPARQL queries for semantic data
- Neo4j: Graph relationships for accident analysis
- PostgreSQL: Time-series metrics and predictions

### Responsive Design
- Tailwind CSS utility classes
- Mobile-friendly sidebar
- Flexible map container
- Custom scrollbar styling

## Configuration

### Environment Variables

**Backend (.env)**
- Database connection strings
- API endpoints
- CORS origins
- Update intervals

**Frontend (.env)**
- API URL
- WebSocket URL

### Customization Points

1. **Map Center**: Edit `TrafficMap.tsx` center coordinates
2. **Update Interval**: Modify `DATA_UPDATE_INTERVAL` in backend .env
3. **Marker Icons**: Replace icon URLs in `TrafficMap.tsx`
4. **Color Schemes**: Adjust Tailwind config or congestion/AQI color functions
5. **Data Transformations**: Modify service layer transformation logic

## Technology Stack

### Backend
- **Runtime**: Node.js 18+
- **Framework**: Express.js
- **Language**: TypeScript
- **WebSocket**: ws library
- **Databases**: Neo4j, PostgreSQL
- **Triple Store**: Apache Jena Fuseki
- **Context Broker**: Stellio
- **Logging**: Winston
- **HTTP Client**: Axios

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Mapping**: Leaflet + React-Leaflet
- **State**: Zustand
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Date Handling**: date-fns

## Development Workflow

1. Start all data sources (Stellio, Fuseki, Neo4j, PostgreSQL)
2. Configure backend .env with connection details
3. Run `npm install` in both backend and frontend
4. Start backend dev server: `cd backend && npm run dev`
5. Start frontend dev server: `cd frontend && npm run dev`
6. Access application at http://localhost:3000
7. Make changes and see hot reload in action

## Production Deployment

### Backend
- Build TypeScript: `npm run build`
- Set NODE_ENV=production
- Use process manager (PM2, systemd)
- Configure reverse proxy (nginx, Apache)
- Set up SSL/TLS
- Enable production logging

### Frontend
- Build production bundle: `npm run build`
- Deploy dist/ to CDN or static hosting
- Configure environment variables
- Enable caching headers
- Set up CDN for assets

### Database Setup
- Create PostgreSQL database and tables
- Load Neo4j with accident data
- Configure Fuseki with traffic ontology
- Set up Stellio with NGSI-LD entities
- Set up backups and monitoring

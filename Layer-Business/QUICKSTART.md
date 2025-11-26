# Quick Start Guide

## Prerequisites

Ensure the following services are running:

1. **Stellio Context Broker**
   - URL: `http://localhost:8080`
   - NGSI-LD endpoint: `/ngsi-ld/v1`

2. **Apache Jena Fuseki**
   - URL: `http://localhost:3030`
   - Dataset: `lod-dataset`
   - Credentials: `admin` / `test_admin`

3. **Neo4j Database**
   - URL: `bolt://localhost:7687`
   - Web UI: `http://localhost:7474`
   - Credentials: `neo4j` / `test12345`

4. **PostgreSQL**
   - Host: `localhost:5432`
   - Database: `stellio_search`
   - Credentials: `stellio_user` / `stellio_test`

## 1. Install Dependencies

### Backend
```bash
cd backend
npm install
```

### Frontend
```bash
cd frontend
npm install
```

## 2. Configure Environment

### Backend
```bash
cd backend
npm run setup
```

This will create a `.env` file from `.env.example` with the following configuration:

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

**⚠️ Important:** Update credentials in `.env` if your setup uses different values!

### Test Connections

Before starting the server, test all data source connections:

```bash
npm run test:connections
```

**Expected Output:**
```
══════════════════════════════════════════════════════════
HCMC Traffic Monitoring - Connection Tests
══════════════════════════════════════════════════════════

📡 Testing Stellio Context Broker...
   URL: http://localhost:8080/ngsi-ld/v1/entities
   ✓ Status: 200
   ✓ Content-Type: application/ld+json

📊 Testing Apache Jena Fuseki...
   URL: http://localhost:3030/lod-dataset/sparql
   User: admin
   ✓ Status: 200
   ✓ Authentication: Success
   ✓ Query executed successfully

🔗 Testing Neo4j Database...
   URI: bolt://localhost:7687
   User: neo4j
   ✓ Connection: Success
   ✓ Authentication: Success
   ✓ Query test: Passed

🐘 Testing PostgreSQL Database...
   Host: localhost:5432
   Database: stellio_search
   User: stellio_user
   ✓ Connection: Success
   ✓ Database: stellio_search
   ✓ Version: PostgreSQL 15.x

══════════════════════════════════════════════════════════
Summary
══════════════════════════════════════════════════════════
stellio             : ✓ PASSED
fuseki              : ✓ PASSED
neo4j               : ✓ PASSED
postgresql          : ✓ PASSED
══════════════════════════════════════════════════════════

🎉 All connections successful! You can start the server.
```

If any tests fail, the script will show specific error messages to help troubleshoot.

### Frontend
```bash
cd frontend
cp .env.example .env
```

No changes needed if using default ports.

## 3. Start Services

### Start Backend (Terminal 1)
```bash
cd backend
npm run dev
```

The server will:
1. Check all data source connections on startup
2. Display connection status for each service
3. Start HTTP API on `http://localhost:5000`
4. Start WebSocket server on `ws://localhost:5001`
5. Begin data aggregation

**Expected Output:**
```
Starting HCMC Traffic Monitoring Server...
Checking data source connections...
✓ stellio: Connected
✓ fuseki: Connected
✓ neo4j: Connected
✓ postgresql: Connected
✓ HTTP Server running on port 5000
✓ WebSocket Server running on port 5001
✓ CORS enabled for: http://localhost:3000
✓ Data aggregation service started
==================================================
Server initialization complete!
==================================================
```

### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

Frontend: http://localhost:3000

## 4. Verify Setup

### Test Health Endpoint
```bash
curl http://localhost:5000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T...",
  "connections": {
    "stellio": {
      "healthy": true,
      "details": {
        "url": "http://localhost:8080/ngsi-ld/v1/entities",
        "status": 200
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
        "authenticated": true
      }
    },
    "postgresql": {
      "healthy": true,
      "details": {
        "host": "localhost",
        "database": "stellio_search"
      }
    }
  }
}
```

### Test Other Endpoints
```bash
# Get cameras
curl http://localhost:5000/api/cameras

# Get weather
curl http://localhost:5000/api/weather

# Get accidents
curl http://localhost:5000/api/accidents

# Get traffic patterns
curl http://localhost:5000/api/patterns
```

## Troubleshooting

### Backend won't start

**Connection Errors:**
```bash
# Check if services are running
curl http://localhost:8080/ngsi-ld/v1/entities
curl http://localhost:3030/$/ping
curl http://localhost:7474
psql -h localhost -U stellio_user -d stellio_search -c "SELECT 1"
```

**Port Conflicts:**
- Backend uses ports 5000 (HTTP) and 5001 (WebSocket)
- Check if ports are available: `netstat -ano | findstr :5000`

**Database Credentials:**
- Verify credentials in `.env` match your actual setup
- Check logs in `backend/logs/` for specific errors

### Frontend won't connect
- Verify backend is running and healthy
- Check browser console for errors
- Ensure CORS is configured correctly

### No data showing
- Check health endpoint: `http://localhost:5000/health`
- Verify all connections show `"healthy": true`
- Check backend logs for data source errors
- Ensure data exists in source databases

### Authentication Errors

**Fuseki:**
- Default: `admin` / `test_admin`
- Update in `.env` if using different credentials

**Neo4j:**
- Default: `neo4j` / `test12345`
- Change password on first login if needed

**PostgreSQL:**
- Default: `stellio_user` / `stellio_test`
- Create user if not exists:
  ```sql
  CREATE USER stellio_user WITH PASSWORD 'stellio_test';
  CREATE DATABASE stellio_search OWNER stellio_user;
  ```

## Next Steps

- Configure your actual data sources
- Customize map center coordinates for your city
- Adjust update intervals in backend .env
- Add authentication if needed
- Set up production deployment

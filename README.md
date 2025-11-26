# HCMC Traffic Monitoring System

Hệ thống giám sát giao thông thành phố Hồ Chí Minh với kiến trúc đa tầng, bao gồm pipeline xử lý dữ liệu và ứng dụng business layer.

## 🏗️ Kiến Trúc Hệ Thống

### 1. Builder-Layer-End (Data Pipeline)
Data pipeline xử lý và lưu trữ dữ liệu giao thông thời gian thực:

**Công nghệ:**
- **Neo4j**: Property Graph Database - lưu trữ quan hệ đường, camera, sự kiện
- **Apache Jena Fuseki**: RDF Triplestore - Linked Open Data
- **Stellio Context Broker**: NGSI-LD Context Broker - IoT data management
- **PostgreSQL + TimescaleDB**: Time-series data storage
- **Redis**: Caching và message broker
- **Kafka**: Event streaming

**Agents:**
- External Data Collector
- NGSI-LD Transformer
- Entity Publisher
- Data Quality Validator
- Accident Detection
- Congestion Detection
- Pattern Recognition
- Alert Dispatcher
- Incident Report Generator
- Performance Monitor
- Health Check Agent

### 2. Layer-Business (Application Layer)
Ứng dụng web cung cấp giao diện người dùng và REST API:

**Backend (Node.js/TypeScript):**
- REST API endpoints
- Real-time data aggregation
- WebSocket support
- Route optimization
- Analytics và reporting

**Frontend (React/Vite):**
- Interactive map với Leaflet
- Real-time updates
- Analytics dashboards
- Traffic visualization
- Camera feeds
- Weather & Air Quality integration

## 🚀 Quick Start

### Yêu Cầu
- **Docker & Docker Compose**: Pipeline layer
- **Node.js v20+**: Business layer
- **PM2**: Process management
- **Git**: Version control

### Chạy Pipeline (Builder-Layer-End)

```bash
cd Builder-Layer-End
docker-compose -f docker-compose.test.yml up -d
```

### Chạy Backend

```bash
cd Layer-Business/backend
npm install
npm run build
npm start
# hoặc với PM2
pm2 start dist/server.js --name hcmc-backend
```

### Chạy Frontend

```bash
cd Layer-Business/frontend
npm install
npm run build
npm run preview
# hoặc với PM2
pm2 start npm --name hcmc-frontend -- run preview
```

## 📦 Deployment

Hệ thống sử dụng GitHub Actions cho CI/CD tự động.

### Setup GitHub Secrets:
- `SERVER_HOST`: IP server
- `SERVER_USER`: SSH username
- `SERVER_PASSWORD`: SSH password

### Workflow tự động:
1. Push code lên GitHub
2. GitHub Actions deploy lên server
3. Pipeline containers restart (Docker)
4. Backend & Frontend restart (PM2)

Chi tiết: [Builder-Layer-End/DEPLOYMENT_GUIDE.md](Builder-Layer-End/DEPLOYMENT_GUIDE.md)

## 📚 Documentation

- **Data Pipeline**: [Builder-Layer-End/README.md](Builder-Layer-End/README.md)
- **Backend API**: [Layer-Business/backend/README.md](Layer-Business/backend/README.md)
- **Frontend**: [Layer-Business/frontend/README.md](Layer-Business/frontend/README.md)
- **Deployment Guide**: [Builder-Layer-End/DEPLOYMENT_GUIDE.md](Builder-Layer-End/DEPLOYMENT_GUIDE.md)
- **API Documentation**: [Layer-Business/API.md](Layer-Business/API.md)

## 🔗 Services & Ports

### Pipeline Services:
- **Neo4j Browser**: http://localhost:7474
- **Fuseki**: http://localhost:3030
- **Stellio API Gateway**: http://localhost:8080
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432
- **Kafka**: localhost:9092

### Application Services:
- **Backend API**: http://localhost:3000
- **Frontend**: http://localhost:4173

## 🛠️ Development

### Pipeline Development

```bash
cd Builder-Layer-End

# Chạy tests
pytest tests/ -v

# Check data completeness
python check_data_completeness.py

# Monitor orchestrator
python monitor_progress.py
```

### Backend Development

```bash
cd Layer-Business/backend

# Development mode
npm run dev

# Run tests
npm test

# Type checking
npm run lint
```

### Frontend Development

```bash
cd Layer-Business/frontend

# Development mode
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📊 Data Models

Hệ thống tuân thủ các chuẩn:
- **NGSI-LD**: Context information management
- **SOSA/SSN**: Sensor, Observation, Sample, and Actuator ontology
- **Smart Data Models**: FIWARE/TM Forum standards

Chi tiết: [SMART_DATA_MODELS_INVENTORY.md](SMART_DATA_MODELS_INVENTORY.md)

## 🔐 Environment Variables

### Backend (.env)
```env
STELLIO_URL=http://localhost:8080
NEO4J_URI=bolt://localhost:7687
FUSEKI_URL=http://localhost:3030
REDIS_HOST=localhost
POSTGRES_HOST=localhost
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:3000
VITE_MAP_CENTER_LAT=10.8231
VITE_MAP_CENTER_LNG=106.6297
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📝 License

[MIT License](Builder-Layer-End/LICENSE)

## 👥 Authors

HCMC Traffic Monitoring Team

## 🙏 Acknowledgments

- FIWARE Foundation (Stellio Context Broker)
- Smart Data Models Initiative
- Apache Jena Project
- Neo4j Community
- React & Vite Communities

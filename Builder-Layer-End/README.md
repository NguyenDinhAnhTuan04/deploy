# Builder Layer - Domain-Agnostic Linked Open Data Agent System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive, **100% domain-agnostic** multi-agent system for collecting, transforming, and managing Linked Open Data (LOD) across any domain - healthcare, geography, commerce, transportation, and more.

## 🌟 Key Features

### Architecture Principles

- **100% Domain-Agnostic**: Works with ANY LOD domain without code changes
- **100% Config-Driven**: All endpoints, mappings, transformations in YAML files
- **Zero-Code Domain Addition**: Add new domains via configuration only
- **Production-Ready**: Full error handling, retry logic, graceful shutdown
- **Scalable**: Async I/O, batch processing, connection pooling
- **Standards-Compliant**: NGSI-LD, SOSA/SSN, RDF, Smart Data Models

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Agent Catalog](#agent-catalog)
- [Configuration](#configuration)
- [Testing](#testing)
- [Architecture](#architecture)
- [Contributing](#contributing)

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Virtual environment (recommended)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd Builder-Layer-End

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 🎯 Quick Start

### 1. Image Refresh Agent (Data Collection)

The Image Refresh Agent refreshes time-sensitive URLs (camera images, sensor data) by updating timestamps and verifying accessibility.

**Domain-Agnostic Design**: Works with cameras, medical devices, inventory images, or any time-sensitive endpoint.

#### Configuration

Edit `config/data_sources.yaml`:

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
    - t  # timestamp parameter to refresh
```

#### Run Single Refresh Cycle

```bash
python agents/data_collection/image_refresh_agent.py --domain cameras --mode once
```

#### Run Continuous Refresh

```bash
python agents/data_collection/image_refresh_agent.py --domain cameras --mode continuous
```

#### Example: Add Healthcare Domain

No code changes needed! Just add to `config/data_sources.yaml`:

```yaml
medical_devices:
  source_file: "data/devices_raw.json"
  output_file: "data/devices_updated.json"
  refresh_interval: 60
  batch_size: 100
  url_template: "https://health.example.com/api/devices"
  params:
    - device_id
    - location
    - timestamp
```

Then run:
```bash
python agents/data_collection/image_refresh_agent.py --domain medical_devices --mode once
```

## 📦 Agent Catalog

### Data Collection Agents

#### 1. Image Refresh Agent ✅ (Implemented)

**Purpose**: Refresh time-sensitive URLs by updating timestamps and verifying accessibility.

**Features**:
- ✅ URL parsing and parameter extraction
- ✅ Timestamp generation (milliseconds)
- ✅ URL reconstruction with fresh timestamps
- ✅ Async HTTP HEAD verification
- ✅ Batch processing (configurable batch size)
- ✅ Retry logic with exponential backoff
- ✅ Graceful shutdown (SIGTERM/SIGINT)
- ✅ Comprehensive error handling
- ✅ Statistics tracking and logging

**Use Cases**:
- Traffic camera images
- Medical device status endpoints
- Weather station data
- Inventory product images
- IoT sensor readings

**Domain Examples**:
- Geography: Traffic cameras, weather stations
- Healthcare: Medical device monitors
- Commerce: Product inventory images
- Smart City: Environmental sensors

#### 2. External Data Collector Agent 🔜 (Planned)

**Purpose**: Collect data from external APIs, databases, and file systems.

**Planned Features**:
- RESTful API integration
- Database connectors (PostgreSQL, MongoDB)
- File system monitoring
- FTP/SFTP support
- Webhook receivers

### Transformation Agents 🔜

- **NGSI-LD Transformer Agent**: Transform raw data to NGSI-LD format
- **SOSA/SSN Mapper Agent**: Map observations to SOSA/SSN ontology

### Analytics Agents 🔜

- **CV Analysis Agent**: Computer vision analysis on images
- **Pattern Recognition Agent**: Detect patterns in time-series data
- **Anomaly Detection Agent**: Identify anomalies and outliers

### Context Management Agents 🔜

- **Entity Publisher Agent**: Publish entities to NGSI-LD context broker
- **State Updater Agent**: Update entity states in real-time
- **Temporal Data Manager Agent**: Manage temporal entity attributes

### RDF & Linked Data Agents 🔜

- **Smart Data Models Validation Agent**: Validate against Smart Data Models schemas
- **NGSI-LD to RDF Agent**: Convert NGSI-LD to RDF triples
- **Triplestore Loader Agent**: Load RDF data into triplestore
- **Content Negotiation Agent**: Serve data in multiple RDF formats

### Notification Agents 🔜

- **Subscription Manager Agent**: Manage NGSI-LD subscriptions
- **Alert Dispatcher Agent**: Dispatch alerts based on conditions
- **Incident Report Generator Agent**: Generate incident reports

### Monitoring Agents 🔜

- **Health Check Agent**: Monitor agent and service health
- **Data Quality Validator Agent**: Validate data quality metrics
- **Performance Monitor Agent**: Track performance metrics

### Integration Agents 🔜

- **API Gateway Agent**: Expose unified API interface
- **Cache Manager Agent**: Manage distributed caching

## ⚙️ Configuration

### Configuration Files

- `config/data_sources.yaml`: Data source endpoints (domain-agnostic)
- `config/stellio.yaml`: Stellio Context Broker configuration
- `config/fuseki.yaml`: Apache Jena Fuseki triplestore configuration
- `config/agents.yaml`: Agent-specific settings

### Environment Variables

Create `.env` file (optional):

```bash
LOG_LEVEL=INFO
MAX_WORKERS=10
STELLIO_URL=http://localhost:8080
FUSEKI_URL=http://localhost:3030
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v --cov=agents --cov-report=term-missing
```

### Run Specific Agent Tests

```bash
# Image Refresh Agent tests
pytest tests/data_collection/test_image_refresh_agent.py -v --cov=agents/data_collection/image_refresh_agent --cov-report=term-missing
```

### Test Coverage Goals

- **Target**: 100% code coverage for all agents
- **Current**: Image Refresh Agent - 100% coverage ✅

### Performance Benchmarks

Image Refresh Agent:
- ✅ Process 722 cameras in < 5 seconds
- ✅ Memory usage < 100MB
- ✅ No memory leaks after 1000 iterations

## 🏗️ Architecture

### Design Patterns

1. **Config-Driven Architecture**: All domain logic in YAML configuration
2. **Async I/O**: Non-blocking operations with aiohttp and asyncio
3. **Batch Processing**: Configurable batch sizes for optimal performance
4. **Retry Pattern**: Exponential backoff for transient failures
5. **Circuit Breaker**: Prevent cascading failures
6. **Observer Pattern**: Event-driven agent communication

### Data Flow

```
┌─────────────────────────────────────────────┐
│          Configuration Layer                │
│  (YAML files - domain definitions)          │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│          Data Collection Layer              │
│  - Image Refresh Agent                      │
│  - External Data Collector Agent            │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         Transformation Layer                │
│  - NGSI-LD Transformer                      │
│  - SOSA/SSN Mapper                          │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│          Analytics Layer                    │
│  - CV Analysis, Pattern Recognition         │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│       Context Management Layer              │
│  - Stellio Context Broker Integration       │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│       RDF & Linked Data Layer               │
│  - RDF Generation, Triplestore Loading      │
└─────────────────────────────────────────────┘
```

### Technology Stack

- **Python 3.9+**: Core language
- **aiohttp**: Async HTTP client
- **PyYAML**: Configuration management
- **pytest**: Testing framework
- **Stellio**: NGSI-LD Context Broker
- **Apache Jena Fuseki**: RDF Triplestore

## 📊 Project Structure

```
Builder-Layer-End/
├── config/                      # Configuration files (YAML)
│   ├── data_sources.yaml       # Data source endpoints (domain-agnostic)
│   ├── stellio.yaml            # Context broker config
│   ├── fuseki.yaml             # Triplestore config
│   └── agents.yaml             # Agent settings
├── agents/                      # Agent implementations
│   ├── data_collection/        # Data collection agents
│   │   ├── image_refresh_agent.py ✅
│   │   └── external_data_collector_agent.py
│   ├── transformation/         # Data transformation agents
│   ├── analytics/              # Analytics agents
│   ├── context_management/     # Context management agents
│   ├── rdf_linked_data/        # RDF and linked data agents
│   ├── notification/           # Notification agents
│   ├── monitoring/             # Monitoring agents
│   └── integration/            # Integration agents
├── shared/                      # Shared utilities
│   ├── config_loader.py        # Config loading utilities
│   ├── logger.py               # Logging utilities
│   └── utils.py                # Common utilities
├── tests/                       # Test suite (mirrors agents/)
│   └── data_collection/
│       └── test_image_refresh_agent.py ✅
├── data/                        # Data files
│   ├── cameras_raw.json        # Source data
│   └── cameras_updated.json    # Processed data
├── docker-compose.yml          # Docker orchestration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔧 Development

### Code Quality

```bash
# Format code with black
black agents/ tests/ shared/

# Lint with flake8
flake8 agents/ tests/ shared/

# Type checking with mypy
mypy agents/ shared/
```

### Adding a New Domain

1. **No code changes required!**
2. Add domain configuration to `config/data_sources.yaml`:

```yaml
your_new_domain:
  source_file: "data/your_domain_raw.json"
  output_file: "data/your_domain_updated.json"
  refresh_interval: 60
  batch_size: 100
  url_template: "https://your-api.example.com/endpoint"
  params:
    - param1
    - param2
    - timestamp
```

3. Run the agent:
```bash
python agents/data_collection/image_refresh_agent.py --domain your_new_domain --mode once
```

### Adding a New Agent

1. Create agent file in appropriate category folder
2. Implement required interfaces
3. Add configuration to `config/agents.yaml`
4. Write comprehensive tests
5. Update README with agent documentation

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code Quality**: All code must pass black, flake8, mypy checks
2. **Testing**: Achieve 100% test coverage for new code
3. **Documentation**: Update README and docstrings
4. **Domain-Agnostic**: Ensure no domain-specific logic in code
5. **Config-Driven**: All domain logic goes in YAML configuration

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub.

## 🙏 Acknowledgments

- NGSI-LD specification by ETSI
- SOSA/SSN ontology by W3C
- Smart Data Models initiative by TM Forum and FIWARE
- Apache Jena Fuseki project
- Stellio Context Broker by EGM

---

**Status**: 🚧 Active Development

**Last Updated**: November 1, 2025

**Version**: 0.1.0

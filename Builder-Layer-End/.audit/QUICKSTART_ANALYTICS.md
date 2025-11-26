# 🚀 Quick Start Guide - Enable Analytics Agents

## ✅ Current Status

Phase 5 Analytics có **4 agents**, hiện tại **2 đang chạy**, **2 sẵn sàng kích hoạt**:

| Agent | Status | Config File | Action |
|-------|--------|-------------|---------|
| cv_analysis_agent | ✅ **RUNNING** | Built-in | No action needed |
| congestion_detection_agent | ✅ **RUNNING** | `congestion_detection.yaml` | No action needed |
| accident_detection_agent | ⚠️ **READY** | `accident_config.yaml` ✅ | Can enable now |
| pattern_recognition_agent | ⚠️ **READY** | `pattern_recognition.yaml` ✅ | Needs Neo4j data |

---

## 🔥 Option 1: Enable Accident Detection (Easy)

### Prerequisites: ✅ None (ready to use)

### Steps:

1. **Edit workflow.yaml:**
```bash
# Open config/workflow.yaml
# Find Phase 5, line ~155
```

2. **Change enabled: false → true:**
```yaml
- name: "accident_detection_agent"
  module: "agents.analytics.accident_detection_agent"
  enabled: true    # ← Change this from false to true
  required: false
  timeout: 60
  config:
    input_file: "data/observations.json"
    config_file: "config/accident_config.yaml"
```

3. **Run workflow:**
```bash
python orchestrator.py
```

4. **Check outputs:**
```bash
# Check if accident detection ran
cat data/accidents.json

# Check alerts
cat data/accident_alerts.json

# Check statistics
cat data/accident_statistics.json
```

### Expected Result:
```
PHASE: Analytics
  ✓ cv_analysis_agent completed
  ✓ congestion_detection_agent completed
  ✓ accident_detection_agent completed  ← NEW!
```

---

## 🔮 Option 2: Enable Pattern Recognition (Needs Neo4j)

### Prerequisites:
1. ✅ Neo4j running on `bolt://localhost:7687`
2. ✅ At least 7 days of historical data in Neo4j
3. ⚠️ Update Neo4j password in config

### Steps:

1. **Update Neo4j password:**
```bash
# Edit config/pattern_recognition.yaml, line 7
```

```yaml
neo4j:
  uri: "bolt://localhost:7687"
  database: "neo4j"
  auth:
    username: "neo4j"
    password: "your_actual_password"  # ← Change this
```

2. **Edit workflow.yaml:**
```bash
# Open config/workflow.yaml
# Find Phase 5, line ~165
```

3. **Change enabled: false → true:**
```yaml
- name: "pattern_recognition_agent"
  module: "agents.analytics.pattern_recognition_agent"
  enabled: true    # ← Change this from false to true
  required: false
  timeout: 120
  config:
    config_file: "config/pattern_recognition.yaml"
    time_window: "7_days"
```

4. **Run workflow:**
```bash
python orchestrator.py
```

5. **Check outputs:**
```bash
# Check patterns detected
cat data/patterns.json

# Check predictions/forecasts
cat data/predictions.json

# Check anomalies
cat data/anomalies.json
```

### Expected Result:
```
PHASE: Analytics
  ✓ cv_analysis_agent completed
  ✓ congestion_detection_agent completed
  ✓ accident_detection_agent completed (if enabled)
  ✓ pattern_recognition_agent completed  ← NEW!
```

---

## ⚡ Option 3: Enable Both Agents

### Steps:

1. **Edit workflow.yaml - enable both:**
```yaml
Phase 5: Analytics
  agents:
    - cv_analysis_agent (enabled: true) ✅
    - congestion_detection_agent (enabled: true) ✅
    - accident_detection_agent (enabled: true) ✅ NEW
    - pattern_recognition_agent (enabled: true) ✅ NEW
```

2. **Run workflow:**
```bash
python orchestrator.py
```

3. **Full Analytics Pipeline:**
```
cameras_updated.json (Phase 1)
  ↓
cv_analysis_agent (YOLOv8)
  ↓ observations.json
  ├→ congestion_detection_agent → congestion_report.json
  ├→ accident_detection_agent → accidents.json + alerts
  └→ pattern_recognition_agent → patterns.json + predictions.json
```

---

## 🧪 Quick Test

### Test Config Files:
```bash
python test_analytics_configs.py
```

Should output:
```
✅ AccidentConfig loaded successfully
✅ PatternConfig loaded successfully
✅ ALL CONFIGURATION TESTS PASSED!
```

### Test Workflow Config:
```bash
python -c "import yaml; config = yaml.safe_load(open('config/workflow.yaml')); phase5 = config['workflow']['phases'][4]; agents = [a['name'] for a in phase5['agents']]; print(f'Phase 5 has {len(agents)} agents:'); [print(f'  {i+1}. {a}') for i, a in enumerate(agents)]"
```

Should output:
```
Phase 5 has 4 agents:
  1. cv_analysis_agent
  2. congestion_detection_agent
  3. accident_detection_agent
  4. pattern_recognition_agent
```

---

## 📊 Output Files Reference

### Currently Generated (2 agents running):
- `data/cameras_updated.json` - Phase 1 output
- `data/observations.json` - CV Analysis output
- `data/congestion_report.json` - Congestion Detection output

### After Enabling Accident Detection:
- `data/accidents.json` - Detected accidents
- `data/accident_alerts.json` - High-severity alerts
- `data/accident_statistics.json` - Detection stats
- `data/accident_state.json` - Internal state
- `data/accident_history.json` - Historical detections

### After Enabling Pattern Recognition:
- `data/patterns.json` - Traffic patterns
- `data/predictions.json` - Forecasted traffic
- `data/anomalies.json` - Detected anomalies
- `data/pattern_statistics.json` - Analysis stats
- `data/pattern_state.json` - Internal state

---

## ⚙️ Configuration Files

All configuration is in YAML files (no code changes needed):

| File | Agent | Status | Sections |
|------|-------|--------|----------|
| `config/workflow.yaml` | All agents | ✅ Complete | 6 phases |
| `config/accident_config.yaml` | Accident detection | ✅ Complete | 10 sections |
| `config/pattern_recognition.yaml` | Pattern recognition | ✅ Complete | 11 sections |
| `config/congestion_detection.yaml` | Congestion detection | ✅ Existing | - |

---

## 🔧 Troubleshooting

### Accident Detection Issues:

**Error: "Config file not found"**
```bash
# Verify file exists
ls config/accident_config.yaml

# Should exist with 200+ lines
```

**Error: "Stellio connection failed"**
```bash
# Check Stellio is running
curl http://localhost:8080/health

# If not running, start Stellio first
```

### Pattern Recognition Issues:

**Error: "Neo4j connection failed"**
```bash
# Check Neo4j is running
curl http://localhost:7474

# Or check bolt connection
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')); driver.verify_connectivity(); print('✅ Connected')"
```

**Error: "Insufficient historical data"**
```bash
# Need at least 7 days of data
# Run the workflow for 7+ days first to collect data
# Then enable pattern_recognition_agent
```

---

## 📝 Next Steps

### Immediate (Can do now):
1. ✅ Enable `accident_detection_agent`
2. ✅ Run workflow: `python orchestrator.py`
3. ✅ Verify accident detection works

### Short-term (When ready):
4. ⏳ Set up Neo4j with historical data (7+ days)
5. ⏳ Update Neo4j password in `pattern_recognition.yaml`
6. ⏳ Enable `pattern_recognition_agent`
7. ⏳ Run workflow to test pattern analysis

### Long-term (Production):
8. ⏳ Monitor accident detection accuracy
9. ⏳ Tune thresholds in config files
10. ⏳ Set up alerting webhooks
11. ⏳ Analyze pattern forecasts

---

## 🎯 Success Criteria

### Accident Detection Working:
- ✅ `data/accidents.json` created with detected incidents
- ✅ `data/accident_alerts.json` has alerts for moderate/severe
- ✅ No errors in logs
- ✅ RoadAccident entities in Stellio

### Pattern Recognition Working:
- ✅ `data/patterns.json` has detected patterns
- ✅ `data/predictions.json` has traffic forecasts
- ✅ TrafficPattern entities in Stellio
- ✅ No Neo4j connection errors

---

**Quick Reference Complete** ✅

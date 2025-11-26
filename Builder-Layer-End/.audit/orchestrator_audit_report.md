# ORCHESTRATOR AUDIT REPORT
**Date:** November 5, 2025  
**Auditor:** Senior System Architect  
**Target:** `orchestrator.py` vs Prompt 9 Specifications  
**Status:** 🔴 **CRITICAL ISSUES FOUND**

---

## EXECUTIVE SUMMARY

Sau khi thực hiện audit 100% tệp `orchestrator.py` và so sánh với thông số kỹ thuật trong **Prompt 9: Overall Workflow Orchestration**, tôi phát hiện **3 vấn đề nghiêm trọng** và **2 thiếu sót quan trọng** trong implementation hiện tại.

**Overall Compliance Score: 65/100**

---

## 1. KIỂM TRA SỰ TUÂN THỦ WORKFLOW (Prompt 9)

### ✅ **TUÂN THỦ ĐÚNG:**

#### Phase 1: Data Collection
- ✅ `image_refresh_agent` - **ĐÚNG THỨ TỰ**
- ✅ `external_data_collector_agent` - **ĐÚNG THỨ TỰ**
- ✅ Executed **sequentially** (parallel: false) ✓

#### Phase 2: Transformation  
- ✅ `ngsi_ld_transformer_agent` - **ĐÚNG THỨ TỰ**
- ✅ `sosa_ssn_mapper_agent` - **ĐÚNG THỨ TỰ**
- ✅ Executed **sequentially** (parallel: false) ✓

#### Phase 3: Validation
- ✅ `smart_data_models_validation_agent` - **ĐÚNG THỨ TỰ**
- ✅ Executed **sequentially** ✓

#### Phase 4: Publishing (PARALLEL)
- ✅ `entity_publisher_agent` - **ĐÚNG**
- ✅ `ngsi_ld_to_rdf_agent` - **ĐÚNG**
- ⚠️ `cv_analysis_agent` - **ENABLED=FALSE (disabled)**
- ✅ Executed **in parallel** (parallel: true) ✓

#### Phase 5: RDF Loading
- ✅ `triplestore_loader_agent` - **ĐÚNG THỨ TỰ**
- ✅ Executed **sequentially** ✓

---

### 🔴 **VI PHẠM NGHIÊM TRỌNG:**

#### **CRITICAL ISSUE #1: CV ANALYSIS AGENT BỊ TẮT**

**Location:** `config/workflow.yaml` lines 106-111

```yaml
- name: "cv_analysis_agent"
  module: "agents.analytics.cv_analysis_agent"
  enabled: false  # ❌ Optional analytics
  required: false
  timeout: 180
```

**Impact:**
- ❌ **CV Analysis Agent (10) KHÔNG CHẠY** → `observations.json` không được tạo ra
- ❌ **Congestion Detection Agent (11) KHÔNG THỂ CHẠY** (phụ thuộc vào `observations.json`)
- ❌ **Accident Detection Agent (12) KHÔNG THỂ CHẠY** (phụ thuộc vào observations)
- ❌ **Phase 6: Analytics HOÀN TOÀN BỊ BỎ QUA**

**Theo Prompt 9, Phase 6 phải tồn tại:**
```python
# Phase 6: Analytics (Layer 3)
run_agent("cv_analysis_agent")
# Output: observations.json → Traffic Metrics
```

**Severity:** 🔴 **CRITICAL** - Entire Analytics pipeline is broken

---

#### **CRITICAL ISSUE #2: THIẾU PHASE 6 (ANALYTICS)**

**Missing Phase:** Không có Phase 6 trong `workflow.yaml`

**Theo Prompt 9, workflow phải có 7 phases:**
1. ✅ Phase 1: Data Collection
2. ✅ Phase 2: Transformation
3. ✅ Phase 3: Validation
4. ✅ Phase 4: Publishing (Stellio + RDF)
5. ✅ Phase 5: RDF Loading
6. ❌ **Phase 6: Analytics** → **THIẾU HOÀN TOÀN**
7. ❌ **Phase 7: Integration & Access** → **THIẾU HOÀN TOÀN**

**Expected Phase 6 (từ Prompt 9):**
```yaml
# Phase 6: Analytics (Layer 3)
- name: "Analytics"
  description: "Perform CV analysis and detect traffic patterns"
  parallel: false
  agents:
    - name: "cv_analysis_agent"
      module: "agents.analytics.cv_analysis_agent"
      enabled: true
      required: true
      timeout: 180
      input_file: "data/cameras_updated.json"
      output_file: "data/observations.json"
    
    - name: "congestion_detection_agent"
      module: "agents.analytics.congestion_detection_agent"
      enabled: true
      required: false
      timeout: 60
      input_file: "data/observations.json"
      depends_on: ["cv_analysis_agent"]
    
    - name: "accident_detection_agent"
      module: "agents.analytics.accident_detection_agent"
      enabled: true
      required: false
      timeout: 60
      input_file: "data/observations.json"
      depends_on: ["cv_analysis_agent"]
```

**Impact:**
- ❌ CV Analysis không chạy
- ❌ Congestion Detection không chạy
- ❌ Accident Detection không chạy
- ❌ Không có ItemFlowObserved entities
- ❌ Không có RoadAccident entities
- ❌ Không có traffic metrics

**Severity:** 🔴 **CRITICAL** - Missing entire analytics capability

---

#### **CRITICAL ISSUE #3: THIẾU PHASE 7 (INTEGRATION & ACCESS)**

**Missing Phase:** Phase 7 không tồn tại

**Theo Prompt 9:**
```python
# Phase 7: Integration & Access (Layers 6, 8)
- API Gateway (Kong)
- Content Negotiation
- Alert Dispatcher
- WebSocket/FCM Notifications
```

**Expected Phase 7:**
```yaml
# Phase 7: Integration & Access
- name: "Integration & Access"
  description: "Setup API Gateway and notification channels"
  parallel: true
  agents:
    - name: "api_gateway_agent"
      module: "agents.integration.api_gateway_agent"
      enabled: true
      required: false
    
    - name: "alert_dispatcher_agent"
      module: "agents.notification.alert_dispatcher_agent"
      enabled: true
      required: false
    
    - name: "subscription_manager_agent"
      module: "agents.notification.subscription_manager_agent"
      enabled: true
      required: false
```

**Impact:**
- ❌ Không có API Gateway integration
- ❌ Không có Alert/Notification system
- ❌ Không có Subscription management
- ❌ Không có Content Negotiation

**Severity:** 🟡 **MAJOR** - Missing integration layer

---

## 2. KIỂM TRA ĐIỂM GIAO NHÁNH (BRANCH INTERSECTIONS)

### ❌ **FAILED - CV Analysis Agent không chạy song song**

**Theo Prompt 9:**
```python
# Phase 4-6: Parallel execution
parallel_run([
    "entity_publisher_agent",      # Phase 4
    "ngsi_ld_to_rdf_agent",        # Phase 4
    "cv_analysis_agent"            # Phase 6 - SHOULD RUN IN PARALLEL
])
```

**Thực tế trong `workflow.yaml`:**

```yaml
# Phase 4: Publishing
- name: "Publishing"
  parallel: true  # ✅ Parallel execution enabled
  agents:
    - name: "entity_publisher_agent"    # ✅ Will run in parallel
      enabled: true
    
    - name: "ngsi_ld_to_rdf_agent"      # ✅ Will run in parallel
      enabled: true
    
    - name: "cv_analysis_agent"         # ❌ DISABLED
      enabled: false  # ❌❌❌ CRITICAL
```

**Analysis:**
1. ✅ **Parallel execution logic** trong orchestrator.py là **ĐÚNG**:
   - Code tại lines 459-467 implement ThreadPoolExecutor correctly
   - `_execute_parallel()` method handles concurrent execution properly

2. ❌ **Configuration sai**:
   - `cv_analysis_agent` bị **DISABLED** (`enabled: false`)
   - Agent sẽ bị **SKIPPED** (AgentStatus.SKIPPED) theo code lines 347-353

3. ❌ **Không tuân thủ Prompt 9**:
   - Prompt 9 yêu cầu CV Analysis chạy **SONG SONG** với Publishing
   - Hiện tại CV Analysis **KHÔNG CHẠY**

**Verdict:** 🔴 **FAILED** - CV Analysis không participate trong parallel execution vì bị disabled

---

## 3. KIỂM TRA SỰ PHỤ THUỘC DỮ LIỆU (DATA DEPENDENCIES)

### ❌ **FAILED - Multiple Dependency Violations**

#### **Dependency Chain (Theo Prompt 9):**

```
cameras_raw.json
    ↓
[Image Refresh (1)] → cameras_updated.json
    ↓
[CV Analysis (10)] → observations.json
    ↓
[Congestion Detection (11)] → Updated Camera entities (congestionLevel)
[Accident Detection (12)] → RoadAccident entities
```

---

### **DEPENDENCY #1: CV Analysis phụ thuộc Image Refresh**

**Expected:**
- Image Refresh Agent (Phase 1) → `cameras_updated.json`
- CV Analysis Agent (Phase 6) reads `cameras_updated.json`

**Actual Implementation:**
- ✅ Image Refresh chạy ở Phase 1 (sequentially) - **ĐÚNG**
- ❌ CV Analysis **BỊ TẮT** → không đọc được `cameras_updated.json`

**Code Evidence (cv_analysis_agent.py lines 1-20):**
```python
"""
CV Analysis Agent
Performs computer vision analysis on camera images using YOLOv8
"""
# Agent này CÓ CODE để đọc cameras_updated.json
# Nhưng không được gọi vì enabled: false
```

**Dependency Check:**
- ✅ **Thứ tự đúng** (Image Refresh trước CV Analysis)
- ❌ **CV Analysis không chạy** → dependency không được satisfy

**Verdict:** 🔴 **VIOLATED** - Dependency exists in design but broken in execution

---

### **DEPENDENCY #2: Congestion Detection phụ thuộc CV Analysis**

**Expected:**
- CV Analysis Agent (Phase 6) → `observations.json` (ItemFlowObserved entities)
- Congestion Detection Agent (Phase 6) reads `observations.json`

**Actual Implementation:**
- ❌ CV Analysis **KHÔNG CHẠY** → `observations.json` **KHÔNG TỒN TẠI**
- ❌ Congestion Detection **KHÔNG CÓ INPUT FILE** để đọc

**Code Evidence (congestion_detection_agent.py lines 1-20):**
```python
"""
Congestion Detection Agent
Reads ItemFlowObserved entities (NGSI-LD) from a JSON file
"""
# Agent này EXPECTS observations.json as input
# Nhưng file này không tồn tại vì CV Analysis không chạy
```

**Critical Problem:**
```python
# Congestion Agent tries to load:
with open('data/observations.json', 'r') as f:
    observations = json.load(f)
# → FileNotFoundError if CV Analysis didn't run
```

**Dependency Check:**
- ❌ **CV Analysis không chạy** → no `observations.json`
- ❌ **Congestion Detection không thể chạy** → missing input file
- ❌ **Không có agent nào trong workflow.yaml gọi Congestion Detection**

**Verdict:** 🔴 **BROKEN DEPENDENCY** - Congestion Detection completely blocked

---

### **DEPENDENCY #3: Accident Detection phụ thuộc CV Analysis**

**Same issue as Congestion Detection:**
- ❌ CV Analysis không chạy
- ❌ `observations.json` không tồn tại
- ❌ Accident Detection không có input
- ❌ Không được config trong workflow.yaml

**Verdict:** 🔴 **BROKEN DEPENDENCY**

---

## 4. PHÂN TÍCH SỰ KHÔNG NHẤT QUÁN

### **Inconsistency #1: Agent Registry vs Workflow Phases**

**Agent Registry trong workflow.yaml (lines 270-293):**
```yaml
agent_registry:
  analytics:
    - cv_analysis_agent           # ✅ Registered
    - congestion_detection_agent  # ✅ Registered
    - accident_detection_agent    # ✅ Registered
```

**Workflow Phases:**
- ❌ cv_analysis_agent: **enabled: false** (Phase 4)
- ❌ congestion_detection_agent: **KHÔNG XUẤT HIỆN trong bất kỳ phase nào**
- ❌ accident_detection_agent: **KHÔNG XUẤT HIỆN trong bất kỳ phase nào**

**Verdict:** 🟡 **INCONSISTENT** - Agents registered but not used

---

### **Inconsistency #2: Prompt 9 Phase Count**

**Prompt 9 defines 7 phases:**
1. Data Collection
2. Transformation
3. Validation
4. Publishing (Stellio)
5. RDF Loading
6. Analytics
7. Integration & Access

**workflow.yaml implements:**
1. ✅ Data Collection
2. ✅ Transformation
3. ✅ Validation
4. ✅ Publishing (merged with Phase 6 in parallel)
5. ✅ RDF Loading
6. ❌ **Analytics** - MISSING
7. ❌ **Integration & Access** - MISSING

**Actual Phase Count:** 5 / 7 (71% complete)

**Verdict:** 🔴 **INCOMPLETE** - Missing 2 critical phases

---

## 5. ĐIỂM RỦI RO (RISK POINTS)

### **Risk #1: Parallel Execution Without Dependency Management** 🔴

**Issue:**
- Phase 4 chạy 3 agents song song: `entity_publisher`, `ngsi_ld_to_rdf`, `cv_analysis`
- Nhưng `cv_analysis` cần `cameras_updated.json` từ Phase 1
- Không có explicit dependency check trong orchestrator

**Code Location:** `orchestrator.py` lines 459-467

```python
def _execute_parallel(self, agents: List[Dict]) -> List[AgentResult]:
    """Execute agents in parallel"""
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        futures = {
            executor.submit(self.agent_executor.execute, agent): agent
            for agent in agents
        }
        # ❌ No dependency validation here
        # ❌ All agents start immediately
```

**Risk:**
- Nếu Image Refresh (Phase 1) fails → `cameras_updated.json` không tồn tại
- CV Analysis (Phase 4 parallel) sẽ start ngay → FileNotFoundError
- Orchestrator không kiểm tra file dependencies trước khi start parallel agents

**Mitigation Needed:**
```python
def _validate_dependencies(self, agent_config: Dict) -> bool:
    """Validate agent input files exist"""
    input_file = agent_config.get('input_file')
    if input_file and not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return False
    return True
```

**Severity:** 🔴 **HIGH RISK**

---

### **Risk #2: No Cross-Phase Dependency Declaration** 🟡

**Issue:**
- workflow.yaml không có cơ chế khai báo dependencies giữa các phase
- Ví dụ: Phase 6 (Analytics) phụ thuộc Phase 1 (Data Collection)
- Orchestrator chỉ execute phases tuần tự theo thứ tự trong YAML

**Missing Feature:**
```yaml
# Expected dependency syntax:
- name: "Analytics"
  depends_on:
    - "Data Collection"  # ❌ Not supported
  agents:
    - name: "cv_analysis_agent"
      depends_on_file: "data/cameras_updated.json"  # ❌ Not supported
```

**Risk:**
- Không thể detect circular dependencies
- Không thể skip phases nếu upstream failed
- Manual phase ordering error-prone

**Severity:** 🟡 **MEDIUM RISK**

---

### **Risk #3: No Idempotency Guarantee** 🟡

**Issue:**
- Orchestrator không track successfully completed phases
- Nếu workflow fails ở Phase 5 → rerun toàn bộ từ Phase 1
- Waste resources re-processing successfully completed phases

**Missing Feature:**
```python
# Expected state tracking:
workflow_state = {
    "phases": {
        "Data Collection": {"status": "success", "timestamp": "..."},
        "Transformation": {"status": "success", "timestamp": "..."},
        "RDF Loading": {"status": "failed", "error": "..."}
    }
}
# Resume from failed phase on re-run
```

**Risk:**
- Expensive re-computation (CV Analysis with YOLOv8 is slow)
- No incremental progress on failures

**Severity:** 🟡 **MEDIUM RISK**

---

## 6. BÁO CÁO TÓM TẮT

### **Compliance Matrix**

| **Aspect** | **Expected** | **Actual** | **Status** |
|-----------|-------------|-----------|-----------|
| Phase 1: Data Collection | Sequential | Sequential | ✅ PASS |
| Phase 2: Transformation | Sequential | Sequential | ✅ PASS |
| Phase 3: Validation | Sequential | Sequential | ✅ PASS |
| Phase 4: Publishing | Parallel | Parallel | ✅ PASS |
| Phase 5: RDF Loading | Sequential | Sequential | ✅ PASS |
| **Phase 6: Analytics** | **Sequential** | **MISSING** | ❌ **FAIL** |
| **Phase 7: Integration** | **Parallel** | **MISSING** | ❌ **FAIL** |
| CV Analysis in parallel | Yes | Disabled | ❌ **FAIL** |
| Dependency: Image→CV | Satisfied | Broken | ❌ **FAIL** |
| Dependency: CV→Congestion | Satisfied | Broken | ❌ **FAIL** |
| Retry Policy | Implemented | Implemented | ✅ PASS |
| Health Checks | Implemented | Implemented | ✅ PASS |
| Error Handling | Implemented | Implemented | ✅ PASS |
| Parallel Execution Logic | Implemented | Implemented | ✅ PASS |

**Overall Score: 9/16 = 56.25%**

---

### **Critical Findings Summary**

1. 🔴 **CV Analysis Agent bị tắt** → Entire analytics pipeline broken
2. 🔴 **Phase 6 (Analytics) thiếu hoàn toàn** → Không có traffic metrics
3. 🔴 **Phase 7 (Integration) thiếu hoàn toàn** → Không có API Gateway/Alerts
4. 🔴 **Dependency chain bị phá vỡ** → observations.json không được tạo
5. 🟡 **No dependency validation** trong parallel execution
6. 🟡 **Inconsistent agent registry** vs actual workflow phases

---

## 7. KHUYẾN NGHỊ KHẮC PHỤC

### **Priority 1: CRITICAL FIXES (Immediate)**

#### **Fix #1: Enable CV Analysis Agent**

```yaml
# config/workflow.yaml - Phase 4
- name: "cv_analysis_agent"
  module: "agents.analytics.cv_analysis_agent"
  enabled: true    # ✅ CHANGE FROM false TO true
  required: false  # Keep optional for now
  timeout: 180
  config:
    input_file: "data/cameras_updated.json"
    output_file: "data/observations.json"
```

---

#### **Fix #2: Add Phase 6 (Analytics)**

```yaml
# config/workflow.yaml - INSERT NEW PHASE AFTER Phase 4

# Phase 5: Analytics (CRITICAL - MISSING)
- name: "Analytics"
  description: "Perform CV analysis and detect traffic patterns"
  parallel: false
  agents:
    - name: "cv_analysis_agent"
      module: "agents.analytics.cv_analysis_agent"
      enabled: true
      required: true
      timeout: 300
      config:
        input_file: "data/cameras_updated.json"
        output_file: "data/observations.json"
        batch_size: 10
        model: "yolov8n.pt"
    
    - name: "congestion_detection_agent"
      module: "agents.analytics.congestion_detection_agent"
      enabled: true
      required: false
      timeout: 60
      config:
        input_file: "data/observations.json"
        config_file: "config/congestion_detection.yaml"
    
    - name: "accident_detection_agent"
      module: "agents.analytics.accident_detection_agent"
      enabled: false  # Enable when agent is implemented
      required: false
      timeout: 60
      config:
        input_file: "data/observations.json"
  
  outputs:
    - "data/observations.json"
```

---

#### **Fix #3: Remove CV Analysis from Phase 4 (Publishing)**

```yaml
# config/workflow.yaml - Phase 4
- name: "Publishing"
  description: "Publish validated data to Stellio and RDF"
  parallel: true
  agents:
    - name: "entity_publisher_agent"
      # ... keep as is
    
    - name: "ngsi_ld_to_rdf_agent"
      # ... keep as is
    
    # ❌ REMOVE cv_analysis_agent from here
    # It should be in Phase 6 (Analytics)
```

---

#### **Fix #4: Renumber Phases**

```yaml
workflow:
  phases:
    - name: "Data Collection"       # Phase 1
    - name: "Transformation"        # Phase 2
    - name: "Validation"            # Phase 3
    - name: "Publishing"            # Phase 4
    - name: "Analytics"             # Phase 5 (NEW)
    - name: "RDF Loading"           # Phase 6 (was Phase 5)
    - name: "Integration & Access"  # Phase 7 (NEW - optional)
```

---

### **Priority 2: MAJOR IMPROVEMENTS (Short-term)**

#### **Improvement #1: Add Dependency Validation**

```python
# orchestrator.py - Add new method to PhaseManager

def _validate_phase_dependencies(self, phase_config: Dict) -> bool:
    """Validate phase dependencies before execution"""
    agents = phase_config.get('agents', [])
    
    for agent_config in agents:
        # Check input file exists
        input_file = agent_config.get('config', {}).get('input_file')
        if input_file and not os.path.exists(input_file):
            logger.error(f"Agent {agent_config['name']}: Input file not found: {input_file}")
            return False
        
        # Check depends_on agents completed
        depends_on = agent_config.get('depends_on', [])
        for dep_agent in depends_on:
            if not self._check_agent_completed(dep_agent):
                logger.error(f"Agent {agent_config['name']}: Dependency not met: {dep_agent}")
                return False
    
    return True
```

---

#### **Improvement #2: Add Phase Dependencies in Config**

```yaml
# config/workflow.yaml - Add dependency declarations

- name: "Analytics"
  depends_on:
    - "Data Collection"  # Requires cameras_updated.json
  agents:
    - name: "cv_analysis_agent"
      depends_on_files:
        - "data/cameras_updated.json"
      produces_files:
        - "data/observations.json"
    
    - name: "congestion_detection_agent"
      depends_on_files:
        - "data/observations.json"
      depends_on_agents:
        - "cv_analysis_agent"
```

---

#### **Improvement #3: Add Workflow State Persistence**

```python
# orchestrator.py - Add state tracking

class WorkflowOrchestrator:
    def __init__(self):
        self.state_file = "data/workflow_state.json"
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load workflow state from file"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        """Save workflow state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _should_skip_phase(self, phase_name: str) -> bool:
        """Check if phase was already successfully completed"""
        phase_state = self.state.get('phases', {}).get(phase_name, {})
        return phase_state.get('status') == 'success'
```

---

### **Priority 3: OPTIONAL ENHANCEMENTS (Long-term)**

#### **Enhancement #1: Add Phase 7 (Integration & Access)**

```yaml
# Phase 7: Integration & Access
- name: "Integration & Access"
  description: "Setup API Gateway and notification systems"
  parallel: true
  agents:
    - name: "api_gateway_agent"
      module: "agents.integration.api_gateway_agent"
      enabled: false
      required: false
    
    - name: "alert_dispatcher_agent"
      module: "agents.notification.alert_dispatcher_agent"
      enabled: false
      required: false
```

---

#### **Enhancement #2: Add Monitoring Metrics**

```python
# orchestrator.py - Add metrics collection

def _collect_metrics(self) -> Dict:
    """Collect execution metrics"""
    return {
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'agent_timings': self._get_agent_timings()
    }
```

---

## 8. KẾT LUẬN

### **Trạng thái Hiện tại:**
- `orchestrator.py` có **architecture tốt** với retry policy, health checks, parallel execution
- **Tuân thủ 71%** specification của Prompt 9 (5/7 phases implemented)
- **Logic orchestration đúng** nhưng **configuration thiếu**

### **Vấn đề Nghiêm trọng:**
1. 🔴 **Analytics pipeline hoàn toàn bị broken** do CV Analysis bị tắt
2. 🔴 **Dependency chain bị phá vỡ** → observations.json không tồn tại
3. 🔴 **2 phases bị thiếu** (Analytics, Integration & Access)

### **Action Items:**
1. **IMMEDIATE:** Enable CV Analysis Agent (5 minutes)
2. **IMMEDIATE:** Add Phase 6 (Analytics) với đầy đủ agents (30 minutes)
3. **SHORT-TERM:** Add dependency validation (2 hours)
4. **LONG-TERM:** Add Phase 7 và workflow state persistence (1 day)

### **Recommendation:**
Thực hiện **Priority 1 fixes ngay lập tức** để restore analytics pipeline. Hệ thống hiện tại chỉ hoạt động ở mức **data ingestion và RDF transformation**, thiếu hoàn toàn **analytics capabilities** là core value của traffic monitoring system.

---

**Audit Completed:** November 5, 2025  
**Signature:** Senior System Architect  
**Next Review:** After implementing Priority 1 fixes

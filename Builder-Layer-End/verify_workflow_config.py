"""
Test Updated Workflow Configuration

Verifies that:
1. external_data_collector_agent is enabled
2. Phase 1 runs sequentially (image_refresh -> external_data_collector)
3. Phase 2 reads from cameras_enriched.json
"""

import yaml
from pathlib import Path

# Load workflow config
workflow_path = Path('config/workflow.yaml')
with open(workflow_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

workflow = config['workflow']
phases = workflow['phases']

print("=" * 80)
print("WORKFLOW CONFIGURATION VERIFICATION")
print("=" * 80)

# Find Phase 1: Data Collection
phase1 = next(p for p in phases if p['name'] == 'Data Collection')
print(f"\n📦 PHASE 1: {phase1['name']}")
print(f"   Description: {phase1['description']}")
print(f"   Parallel: {phase1['parallel']} {'✅ SEQUENTIAL' if not phase1['parallel'] else '❌ SHOULD BE SEQUENTIAL'}")
print(f"   Agents: {len(phase1['agents'])}")

# Check agents
for i, agent in enumerate(phase1['agents'], 1):
    name = agent['name']
    enabled = agent['enabled']
    required = agent['required']
    
    print(f"\n   Agent {i}: {name}")
    print(f"      Enabled: {enabled} {'✅' if enabled else '❌'}")
    print(f"      Required: {required} {'✅' if required else '⚠️'}")
    
    if name == 'image_refresh_agent':
        print(f"      Input: {agent['input_file']}")
        print(f"      Output: {agent['output_file']}")
    
    elif name == 'external_data_collector_agent':
        config_data = agent.get('config', {})
        print(f"      Config Path: {config_data.get('config_path', 'N/A')}")
        print(f"      Source: {config_data.get('source_file', 'N/A')}")
        print(f"      Output: {config_data.get('output_file', 'N/A')}")
        print(f"      Mode: {config_data.get('mode', 'N/A')}")

# Check Phase 1 outputs
print(f"\n   Phase Outputs:")
for output in phase1['outputs']:
    print(f"      - {output}")

# Find Phase 2: Transformation
phase2 = next(p for p in phases if p['name'] == 'Transformation')
print(f"\n📦 PHASE 2: {phase2['name']}")
print(f"   Description: {phase2['description']}")
print(f"   Parallel: {phase2['parallel']} {'✅ SEQUENTIAL' if not phase2['parallel'] else '❌ SHOULD BE SEQUENTIAL'}")
print(f"   Agents: {len(phase2['agents'])}")

# Check NGSI-LD Transformer input
ngsi_ld_agent = next(a for a in phase2['agents'] if a['name'] == 'ngsi_ld_transformer_agent')
print(f"\n   Agent: ngsi_ld_transformer_agent")
print(f"      Input: {ngsi_ld_agent['input_file']} {'✅ cameras_enriched.json' if 'enriched' in ngsi_ld_agent['input_file'] else '❌ SHOULD BE cameras_enriched.json'}")
print(f"      Output: {ngsi_ld_agent['output_file']}")

# Check SOSA Mapper
sosa_agent = next(a for a in phase2['agents'] if a['name'] == 'sosa_ssn_mapper_agent')
print(f"\n   Agent: sosa_ssn_mapper_agent")
print(f"      Input: {sosa_agent['input_file']}")
print(f"      Output: {sosa_agent['output_file']}")

# Verify workflow logic
print("\n" + "=" * 80)
print("WORKFLOW LOGIC VERIFICATION")
print("=" * 80)

checks = []

# Check 1: Phase 1 sequential
checks.append({
    'name': 'Phase 1 runs sequentially',
    'passed': not phase1['parallel'],
    'value': f"parallel={phase1['parallel']}"
})

# Check 2: external_data_collector enabled
ext_agent = next(a for a in phase1['agents'] if a['name'] == 'external_data_collector_agent')
checks.append({
    'name': 'external_data_collector_agent enabled',
    'passed': ext_agent['enabled'],
    'value': f"enabled={ext_agent['enabled']}"
})

# Check 3: external_data_collector required
checks.append({
    'name': 'external_data_collector_agent required',
    'passed': ext_agent['required'],
    'value': f"required={ext_agent['required']}"
})

# Check 4: external_data_collector reads from cameras_updated.json
ext_config = ext_agent.get('config', {})
checks.append({
    'name': 'external_data_collector reads cameras_updated.json',
    'passed': 'cameras_updated.json' in ext_config.get('source_file', ''),
    'value': f"source_file={ext_config.get('source_file', 'N/A')}"
})

# Check 5: external_data_collector outputs to cameras_enriched.json
checks.append({
    'name': 'external_data_collector outputs cameras_enriched.json',
    'passed': 'cameras_enriched.json' in ext_config.get('output_file', ''),
    'value': f"output_file={ext_config.get('output_file', 'N/A')}"
})

# Check 6: NGSI-LD Transformer reads cameras_enriched.json
checks.append({
    'name': 'ngsi_ld_transformer reads cameras_enriched.json',
    'passed': 'cameras_enriched.json' in ngsi_ld_agent['input_file'],
    'value': f"input_file={ngsi_ld_agent['input_file']}"
})

# Print results
all_passed = True
for check in checks:
    status = '✅ PASS' if check['passed'] else '❌ FAIL'
    print(f"{status}: {check['name']}")
    print(f"         {check['value']}")
    if not check['passed']:
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✅ ALL CHECKS PASSED - WORKFLOW CONFIGURATION IS CORRECT!")
else:
    print("❌ SOME CHECKS FAILED - PLEASE REVIEW CONFIGURATION")
print("=" * 80)

# Print execution flow
print("\n" + "=" * 80)
print("EXECUTION FLOW")
print("=" * 80)
print("""
Phase 1: Data Collection (Sequential)
├── 1. image_refresh_agent
│   ├── Input:  data/cameras_raw.json
│   └── Output: data/cameras_updated.json
│
└── 2. external_data_collector_agent
    ├── Input:  data/cameras_updated.json
    └── Output: data/cameras_enriched.json (with weather + air quality)

Phase 2: Transformation (Sequential)
├── 1. ngsi_ld_transformer_agent
│   ├── Input:  data/cameras_enriched.json
│   └── Output: data/ngsi_ld_entities.json (~120 entities)
│
└── 2. sosa_ssn_mapper_agent
    ├── Input:  data/ngsi_ld_entities.json
    └── Output: data/sosa_enhanced_entities.json (~121 entities)
""")

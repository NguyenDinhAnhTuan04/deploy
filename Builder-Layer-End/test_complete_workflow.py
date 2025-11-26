"""
End-to-End Workflow Test

Tests the complete updated workflow:
Phase 1: image_refresh_agent -> external_data_collector_agent
Phase 2: ngsi_ld_transformer_agent -> sosa_ssn_mapper_agent

Verifies:
1. Data flows correctly between agents
2. Each agent produces expected output
3. Entity counts are correct at each stage
"""

import json
from pathlib import Path

def count_entities(file_path):
    """Count entities in JSON file"""
    if not Path(file_path).exists():
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return len(data) if isinstance(data, list) else 1

def check_enrichment(file_path):
    """Check if cameras are enriched with weather and air quality"""
    if not Path(file_path).exists():
        return {'with_weather': 0, 'with_air_quality': 0}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        cameras = json.load(f)
    
    with_weather = sum(1 for c in cameras if 'weather' in c)
    with_air_quality = sum(1 for c in cameras if 'air_quality' in c)
    
    return {
        'total': len(cameras),
        'with_weather': with_weather,
        'with_air_quality': with_air_quality
    }

def check_entity_types(file_path):
    """Count entities by type"""
    if not Path(file_path).exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    type_counts = {}
    for entity in entities:
        entity_type = entity.get('type')
        if isinstance(entity_type, list):
            for t in entity_type:
                if not t.startswith('sosa:'):
                    type_counts[t] = type_counts.get(t, 0) + 1
        else:
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
    
    return type_counts

def check_sosa_types(file_path):
    """Count SOSA types"""
    if not Path(file_path).exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    sosa_counts = {'sosa:Sensor': 0, 'sosa:Observation': 0}
    for entity in entities:
        entity_type = entity.get('type')
        if isinstance(entity_type, list):
            if 'sosa:Sensor' in entity_type:
                sosa_counts['sosa:Sensor'] += 1
            if 'sosa:Observation' in entity_type:
                sosa_counts['sosa:Observation'] += 1
    
    return sosa_counts

print("=" * 80)
print("END-TO-END WORKFLOW VERIFICATION")
print("=" * 80)

# Phase 1: Data Collection
print("\n📦 PHASE 1: Data Collection")
print("-" * 80)

# Input
cameras_raw_count = count_entities('data/cameras_raw.json')
print(f"\n✓ Input: cameras_raw.json")
print(f"  Cameras: {cameras_raw_count}")

# After image_refresh_agent
cameras_updated_count = count_entities('data/cameras_updated.json')
print(f"\n✓ After image_refresh_agent: cameras_updated.json")
print(f"  Cameras: {cameras_updated_count}")

# After external_data_collector_agent
enrichment_stats = check_enrichment('data/cameras_enriched.json')
print(f"\n✓ After external_data_collector_agent: cameras_enriched.json")
print(f"  Total cameras: {enrichment_stats.get('total', 0)}")
print(f"  With weather data: {enrichment_stats.get('with_weather', 0)}")
print(f"  With air quality data: {enrichment_stats.get('with_air_quality', 0)}")

# Phase 2: Transformation
print("\n📦 PHASE 2: Transformation")
print("-" * 80)

# After ngsi_ld_transformer_agent
ngsi_ld_types = check_entity_types('data/ngsi_ld_entities.json')
ngsi_ld_count = count_entities('data/ngsi_ld_entities.json')
print(f"\n✓ After ngsi_ld_transformer_agent: ngsi_ld_entities.json")
print(f"  Total entities: {ngsi_ld_count}")
for entity_type, count in sorted(ngsi_ld_types.items()):
    print(f"    - {entity_type}: {count}")

# After sosa_ssn_mapper_agent
sosa_types = check_entity_types('data/sosa_enhanced_entities.json')
sosa_sosa_types = check_sosa_types('data/sosa_enhanced_entities.json')
sosa_count = count_entities('data/sosa_enhanced_entities.json')
print(f"\n✓ After sosa_ssn_mapper_agent: sosa_enhanced_entities.json")
print(f"  Total entities: {sosa_count}")
print(f"\n  Original types:")
for entity_type, count in sorted(sosa_types.items()):
    print(f"    - {entity_type}: {count}")
print(f"\n  SOSA types:")
for sosa_type, count in sorted(sosa_sosa_types.items()):
    print(f"    - {sosa_type}: {count}")

# Verification Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

checks = []

# Expected values (based on current data)
EXPECTED_CAMERAS = 40
EXPECTED_NGSI_LD = 119  # 40 Camera + 40 WeatherObserved + 39 AirQualityObserved
EXPECTED_SOSA = 121     # 119 + 1 Platform + 1 ObservableProperty

checks.append({
    'name': 'cameras_raw.json exists',
    'passed': cameras_raw_count > 0,
    'expected': f'> 0',
    'actual': cameras_raw_count
})

checks.append({
    'name': 'cameras_updated.json has same count',
    'passed': cameras_updated_count == cameras_raw_count,
    'expected': cameras_raw_count,
    'actual': cameras_updated_count
})

checks.append({
    'name': 'cameras_enriched.json has same count',
    'passed': enrichment_stats.get('total', 0) == EXPECTED_CAMERAS,
    'expected': EXPECTED_CAMERAS,
    'actual': enrichment_stats.get('total', 0)
})

checks.append({
    'name': 'All cameras have weather data',
    'passed': enrichment_stats.get('with_weather', 0) == EXPECTED_CAMERAS,
    'expected': EXPECTED_CAMERAS,
    'actual': enrichment_stats.get('with_weather', 0)
})

checks.append({
    'name': 'Most cameras have air quality data',
    'passed': enrichment_stats.get('with_air_quality', 0) >= EXPECTED_CAMERAS - 5,  # Allow 5 missing
    'expected': f'>= {EXPECTED_CAMERAS - 5}',
    'actual': enrichment_stats.get('with_air_quality', 0)
})

checks.append({
    'name': 'ngsi_ld_entities.json has ~120 entities',
    'passed': 115 <= ngsi_ld_count <= 125,  # Allow some variance
    'expected': f'{EXPECTED_NGSI_LD} ± 6',
    'actual': ngsi_ld_count
})

checks.append({
    'name': 'NGSI-LD has Camera entities',
    'passed': ngsi_ld_types.get('Camera', 0) == EXPECTED_CAMERAS,
    'expected': EXPECTED_CAMERAS,
    'actual': ngsi_ld_types.get('Camera', 0)
})

checks.append({
    'name': 'NGSI-LD has WeatherObserved entities',
    'passed': ngsi_ld_types.get('WeatherObserved', 0) == EXPECTED_CAMERAS,
    'expected': EXPECTED_CAMERAS,
    'actual': ngsi_ld_types.get('WeatherObserved', 0)
})

checks.append({
    'name': 'NGSI-LD has AirQualityObserved entities',
    'passed': ngsi_ld_types.get('AirQualityObserved', 0) >= EXPECTED_CAMERAS - 5,
    'expected': f'>= {EXPECTED_CAMERAS - 5}',
    'actual': ngsi_ld_types.get('AirQualityObserved', 0)
})

checks.append({
    'name': 'sosa_enhanced_entities.json has ~121 entities',
    'passed': 115 <= sosa_count <= 125,
    'expected': f'{EXPECTED_SOSA} ± 6',
    'actual': sosa_count
})

checks.append({
    'name': 'SOSA has sosa:Sensor (Camera)',
    'passed': sosa_sosa_types.get('sosa:Sensor', 0) == EXPECTED_CAMERAS,
    'expected': EXPECTED_CAMERAS,
    'actual': sosa_sosa_types.get('sosa:Sensor', 0)
})

checks.append({
    'name': 'SOSA has sosa:Observation (Weather+AirQuality)',
    'passed': 75 <= sosa_sosa_types.get('sosa:Observation', 0) <= 85,
    'expected': '~79',
    'actual': sosa_sosa_types.get('sosa:Observation', 0)
})

# Print results
all_passed = True
for check in checks:
    status = '✅ PASS' if check['passed'] else '❌ FAIL'
    print(f"{status}: {check['name']}")
    print(f"         Expected: {check['expected']}, Actual: {check['actual']}")
    if not check['passed']:
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✅ ALL CHECKS PASSED - WORKFLOW IS WORKING CORRECTLY!")
    print("\nThe complete pipeline successfully processes:")
    print(f"  • {EXPECTED_CAMERAS} cameras with coordinates")
    print(f"  • Enriched with weather data (OpenWeatherMap)")
    print(f"  • Enriched with air quality data (OpenAQ)")
    print(f"  • Transformed to ~{EXPECTED_NGSI_LD} NGSI-LD entities")
    print(f"  • Enhanced with SOSA/SSN semantics (~{EXPECTED_SOSA} entities)")
else:
    print("❌ SOME CHECKS FAILED - PLEASE REVIEW WORKFLOW EXECUTION")
print("=" * 80)

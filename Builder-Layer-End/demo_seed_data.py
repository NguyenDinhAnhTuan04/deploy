"""
Demo Seed Data Feature
Shows how to enable/disable seed data in workflow
"""

import yaml
import json

print("\n" + "="*80)
print("SEED DATA FEATURE DEMONSTRATION")
print("="*80)

# Show current config
with open('config/workflow.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

seed_config = config.get('seed_data', {})
enabled = seed_config.get('enabled', False)
files = seed_config.get('files', [])

print(f"\nCurrent seed_data.enabled = {enabled}")
print(f"\nFiles to seed ({len(files)}):")
for file_info in files:
    print(f"  - {file_info['path']}: {file_info['count']} entities")

print("\n" + "-"*80)
print("HOW IT WORKS:")
print("-"*80)
print("""
1. Set seed_data.enabled = true in config/workflow.yaml
2. Run orchestrator.py
3. After Phase 5 (Analytics) completes, orchestrator will:
   - Generate mock accidents in data/accidents.json
   - Generate mock patterns in data/traffic_patterns.json
   - Generate mock camera updates in data/updated_cameras.json
4. Validation agents will process these mock entities
5. No more "Empty entity list" warnings!

WHEN TO USE:
- enabled: true  → Testing without real detections (mock data)
- enabled: false → Production with real CV analysis (real data)
""")

print("="*80)
print("CURRENT STATUS: " + ("MOCK DATA MODE ✓" if enabled else "REAL DATA MODE ✓"))
print("="*80 + "\n")

# Show example of what would be seeded
if enabled:
    from data_seeder import DataSeeder
    seeder = DataSeeder(seed_config)
    
    print("Example entities that will be generated:")
    print("\n1. Mock Accident:")
    accidents = seeder._generate_mock_accidents(1)
    print(json.dumps(accidents[0], indent=2)[:500] + "...")
    
    print("\n2. Mock Traffic Pattern:")
    patterns = seeder._generate_mock_patterns(1)
    print(json.dumps(patterns[0], indent=2)[:500] + "...")

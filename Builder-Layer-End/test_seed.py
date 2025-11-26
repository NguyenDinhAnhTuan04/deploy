"""Test seed data functionality"""
import yaml
from data_seeder import seed_data_if_enabled
import logging

logging.basicConfig(level=logging.INFO)

# Load config
with open('config/workflow.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Temporarily enable seeding for test
seed_config = config.get('seed_data', {})
seed_config['enabled'] = True  # Force enable for testing

print("\n" + "="*80)
print("TESTING SEED DATA WITH enabled=True")
print("="*80 + "\n")

seed_data_if_enabled(seed_config)

print("\n" + "="*80)
print("SEED TEST COMPLETED - Check generated files:")
print("  - data/validated_accidents.json")
print("  - data/validated_patterns.json")
print("  - data/updated_cameras.json")
print("="*80)

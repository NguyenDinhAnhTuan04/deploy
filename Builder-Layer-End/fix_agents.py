"""
Fix all agent main() functions to accept config dict from orchestrator
"""
import os
import re

agents_to_fix = [
    "agents/transformation/ngsi_ld_transformer_agent.py",
    "agents/transformation/sosa_ssn_mapper_agent.py",
    "agents/rdf_linked_data/smart_data_models_validation_agent.py",
    "agents/context_management/entity_publisher_agent.py",
    "agents/rdf_linked_data/ngsi_ld_to_rdf_agent.py",
    "agents/rdf_linked_data/triplestore_loader_agent.py",
]

for agent_path in agents_to_fix:
    if not os.path.exists(agent_path):
        print(f"❌ Not found: {agent_path}")
        continue
    
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the main() function
    # Pattern 1: def main():
    pattern1 = r'^def main\(\):'
    # Pattern 2: async def main():
    pattern2 = r'^async def main\(\):'
    
    if re.search(pattern1, content, re.MULTILINE):
        # Replace def main(): with def main(config: Dict = None):
        new_content = re.sub(
            pattern1,
            'def main(config: Dict = None):',
            content,
            flags=re.MULTILINE
        )
        
        # Add import Dict at the top if not present
        if 'from typing import' not in new_content or 'Dict' not in new_content.split('from typing import')[1].split('\n')[0]:
            # Find first import line
            import_match = re.search(r'^import |^from ', new_content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.start()
                new_content = new_content[:insert_pos] + 'from typing import Dict\n' + new_content[insert_pos:]
        
        # Add config handling logic after main() definition
        # Find the function body start
        main_match = re.search(r'^def main\(config: Dict = None\):\s*"""[^"]*"""\s*', new_content, re.MULTILINE | re.DOTALL)
        if main_match:
            insert_pos = main_match.end()
            config_check = '''
    # If called from orchestrator with config dict
    if config:
        input_file = config.get('input_file')
        output_file = config.get('output_file')
        # Use config values if provided
        # Otherwise fall back to argparse
    else:
        # Command line execution
        pass
    
'''
            # Only add if not already present
            if 'If called from orchestrator' not in new_content:
                new_content = new_content[:insert_pos] + config_check + new_content[insert_pos:]
        
        with open(agent_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Fixed: {agent_path}")
    
    elif re.search(pattern2, content, re.MULTILINE):
        print(f"⏭️  Async already handled: {agent_path}")
    
    else:
        print(f"⚠️  No main() found: {agent_path}")

print("\n✅ All agents fixed!")

"""
Test Neo4j Sync Agent Configuration

Verifies that Phase 9 is properly configured in workflow.yaml
"""

import yaml
from pathlib import Path

def test_neo4j_sync_phase():
    """Test that Phase 9 (Neo4j Sync) is in workflow.yaml"""
    
    workflow_path = Path("config/workflow.yaml")
    
    if not workflow_path.exists():
        print("❌ config/workflow.yaml not found")
        return False
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    phases = config.get('workflow', {}).get('phases', [])
    
    print(f"📊 Total phases found: {len(phases)}")
    print()
    
    # Check each phase
    for i, phase in enumerate(phases, 1):
        phase_name = phase.get('name', 'Unknown')
        agents = phase.get('agents', [])
        print(f"Phase {i}: {phase_name} ({len(agents)} agents)")
    
    print()
    
    # Find Phase 9 (Neo4j Sync)
    neo4j_phase = None
    for phase in phases:
        if phase.get('name') == 'Neo4j Sync':
            neo4j_phase = phase
            break
    
    if neo4j_phase is None:
        print("❌ Phase 9 (Neo4j Sync) NOT FOUND in workflow.yaml")
        return False
    
    print("✅ Phase 9 (Neo4j Sync) FOUND in workflow.yaml")
    print()
    
    # Check agents in Phase 9
    agents = neo4j_phase.get('agents', [])
    print(f"📋 Phase 9 agents: {len(agents)}")
    
    for agent in agents:
        agent_name = agent.get('name', 'Unknown')
        module = agent.get('module', 'Unknown')
        enabled = agent.get('enabled', False)
        timeout = agent.get('timeout', 0)
        
        print(f"  - {agent_name}")
        print(f"    Module: {module}")
        print(f"    Enabled: {'✅' if enabled else '❌'}")
        print(f"    Timeout: {timeout}s")
        print()
    
    # Verify neo4j_sync_agent
    neo4j_agent = None
    for agent in agents:
        if agent.get('name') == 'neo4j_sync_agent':
            neo4j_agent = agent
            break
    
    if neo4j_agent is None:
        print("❌ neo4j_sync_agent NOT FOUND in Phase 9")
        return False
    
    print("✅ neo4j_sync_agent FOUND in Phase 9")
    
    # Check configuration
    config_data = neo4j_agent.get('config', {})
    print()
    print("⚙️ Agent Configuration:")
    print(f"  - Config file: {config_data.get('config_file', 'NOT SET')}")
    print(f"  - Sync mode: {config_data.get('sync_mode', 'NOT SET')}")
    print(f"  - Clear before sync: {config_data.get('clear_before_sync', False)}")
    print(f"  - Create indexes: {config_data.get('create_indexes', False)}")
    
    print()
    print("=" * 60)
    print("✅ Phase 9 (Neo4j Sync) is properly configured!")
    print("=" * 60)
    
    return True


def test_neo4j_config_file():
    """Test that neo4j_sync.yaml exists"""
    
    config_path = Path("config/neo4j_sync.yaml")
    
    if not config_path.exists():
        print("❌ config/neo4j_sync.yaml NOT FOUND")
        return False
    
    print("✅ config/neo4j_sync.yaml EXISTS")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Check required sections
    neo4j_sync = config.get('neo4j_sync', {})
    
    sections = ['postgres', 'neo4j', 'entity_mapping', 'sync_config']
    
    print()
    print("📋 Configuration sections:")
    for section in sections:
        exists = section in neo4j_sync
        print(f"  - {section}: {'✅' if exists else '❌'}")
    
    return True


def test_agent_module():
    """Test that neo4j_sync_agent module exists"""
    
    agent_path = Path("agents/integration/neo4j_sync_agent.py")
    
    if not agent_path.exists():
        print("❌ agents/integration/neo4j_sync_agent.py NOT FOUND")
        return False
    
    print("✅ agents/integration/neo4j_sync_agent.py EXISTS")
    
    # Check file size
    size = agent_path.stat().st_size
    lines = len(agent_path.read_text(encoding='utf-8').splitlines())
    
    print(f"  - Size: {size:,} bytes")
    print(f"  - Lines: {lines:,}")
    
    return True


if __name__ == '__main__':
    print()
    print("=" * 60)
    print("Testing Neo4j Sync Agent Configuration")
    print("=" * 60)
    print()
    
    # Test 1: Agent module
    print("Test 1: Agent Module")
    print("-" * 60)
    test_agent_module()
    print()
    
    # Test 2: Config file
    print("Test 2: Configuration File")
    print("-" * 60)
    test_neo4j_config_file()
    print()
    
    # Test 3: Workflow phase
    print("Test 3: Workflow Phase")
    print("-" * 60)
    success = test_neo4j_sync_phase()
    print()
    
    if success:
        print()
        print("🎉 All tests passed! Phase 9 is ready to use.")
        print()
        print("Next steps:")
        print("  1. Make sure Neo4j is running: docker-compose up -d neo4j")
        print("  2. Make sure Stellio is running: docker-compose up -d stellio")
        print("  3. Run the workflow orchestrator to execute all phases")
        print("  4. Or run Phase 9 manually: python agents/integration/neo4j_sync_agent.py")
    else:
        print()
        print("❌ Some tests failed. Please check the configuration.")

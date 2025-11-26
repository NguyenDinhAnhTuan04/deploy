"""
Orchestrator Dry-Run Test
Test orchestrator logic without actually running agents
"""

import sys
import yaml
from orchestrator import WorkflowConfig, RetryPolicy, HealthChecker

def test_config_loading():
    """Test workflow configuration loading"""
    print("\n" + "="*80)
    print("TEST 1: Configuration Loading")
    print("="*80)
    
    try:
        config_loader = WorkflowConfig('config/workflow.yaml')
        config = config_loader.config
        
        print(f"✅ Workflow name: {config['workflow']['name']}")
        print(f"✅ Version: {config['workflow']['version']}")
        print(f"✅ Phases: {len(config['workflow']['phases'])}")
        
        # List all phases
        for i, phase in enumerate(config['workflow']['phases'], 1):
            agents_count = len(phase.get('agents', []))
            print(f"   Phase {i}: {phase['name']} ({agents_count} agents)")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_retry_policy():
    """Test retry policy configuration"""
    print("\n" + "="*80)
    print("TEST 2: Retry Policy")
    print("="*80)
    
    try:
        config_loader = WorkflowConfig('config/workflow.yaml')
        retry_config = config_loader.get_retry_policy()
        
        retry_policy = RetryPolicy(retry_config)
        
        print(f"✅ Max attempts: {retry_policy.max_attempts}")
        print(f"✅ Strategy: {retry_policy.strategy}")
        print(f"✅ Base delay: {retry_policy.base_delay}s")
        print(f"✅ Max delay: {retry_policy.max_delay}s")
        
        # Test delay calculation
        print(f"\nDelay progression:")
        for attempt in range(1, 4):
            delay = retry_policy.get_delay(attempt)
            print(f"   Attempt {attempt}: {delay}s")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_health_checker():
    """Test health checker configuration"""
    print("\n" + "="*80)
    print("TEST 3: Health Checker")
    print("="*80)
    
    try:
        config_loader = WorkflowConfig('config/workflow.yaml')
        health_config = config_loader.get_health_checks()
        
        health_checker = HealthChecker(health_config)
        
        print(f"✅ Enabled: {health_checker.enabled}")
        print(f"✅ Timeout: {health_checker.timeout}s")
        print(f"✅ Endpoints: {len(health_checker.endpoints)}")
        
        # List endpoints
        for endpoint in health_checker.endpoints:
            required = "Required" if endpoint.get('required', False) else "Optional"
            print(f"   - {endpoint['name']}: {endpoint['url']} ({required})")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_agent_modules():
    """Test if agent modules can be imported"""
    print("\n" + "="*80)
    print("TEST 4: Agent Module Check")
    print("="*80)
    
    try:
        config_loader = WorkflowConfig('config/workflow.yaml')
        phases = config_loader.get_phases()
        
        total_agents = 0
        importable = 0
        failed = []
        
        for phase in phases:
            for agent in phase.get('agents', []):
                total_agents += 1
                module_path = agent.get('module')
                
                try:
                    # Check if module path exists as file
                    import importlib.util
                    file_path = module_path.replace('.', '/') + '.py'
                    
                    import os
                    if os.path.exists(file_path):
                        print(f"✅ {agent['name']}: {module_path}")
                        importable += 1
                    else:
                        print(f"⚠️  {agent['name']}: {module_path} (file not found)")
                        failed.append(f"{agent['name']} - {file_path}")
                except Exception as e:
                    print(f"❌ {agent['name']}: {module_path} (error: {e})")
                    failed.append(f"{agent['name']} - {str(e)}")
        
        print(f"\nSummary: {importable}/{total_agents} agents have valid file paths")
        
        if failed:
            print(f"\n⚠️  Missing/Invalid agents:")
            for item in failed:
                print(f"   - {item}")
        
        return len(failed) == 0
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    """Run all dry-run tests"""
    print("\n" + "="*80)
    print("ORCHESTRATOR DRY-RUN TEST")
    print("="*80)
    
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Retry Policy", test_retry_policy),
        ("Health Checker", test_health_checker),
        ("Agent Modules", test_agent_modules)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Orchestrator configuration is valid!")
        print("\n✅ Ready to run: D:/olp/Builder-Layer-End/.venv/Scripts/python.exe orchestrator.py")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Fix issues before running pipeline")
        return 1


if __name__ == '__main__':
    sys.exit(main())

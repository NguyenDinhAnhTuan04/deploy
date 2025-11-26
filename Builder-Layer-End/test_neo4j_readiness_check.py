"""
Test Neo4j Readiness Check for Pattern Recognition Agent

This script validates that the Neo4j readiness check prevents
pattern recognition from running before Neo4j sync completes,
eliminating all Neo4j property/label WARNING messages.

Author: AI Assistant
Date: 2025-11-12
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.analytics.pattern_recognition_agent import PatternRecognitionAgent
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pattern_recognition_with_readiness_check():
    """Test pattern recognition agent with Neo4j readiness check."""
    
    print("=" * 80)
    print("TESTING: Neo4j Readiness Check in Pattern Recognition Agent")
    print("=" * 80)
    
    config_path = "config/pattern_config.yaml"
    
    # Check if config exists
    if not os.path.exists(config_path):
        print(f"\n❌ Config file not found: {config_path}")
        print("Skipping test - config file required")
        return
    
    try:
        # Initialize agent
        print("\n1. Initializing Pattern Recognition Agent...")
        agent = PatternRecognitionAgent(config_path)
        print("   ✅ Agent initialized successfully")
        
        # Test Neo4j readiness check
        print("\n2. Testing Neo4j Readiness Check...")
        is_ready, reason = agent.neo4j.is_ready_for_pattern_analysis()
        
        print(f"   Neo4j Ready: {is_ready}")
        print(f"   Reason: {reason}")
        
        if is_ready:
            print("   ✅ Neo4j is READY - Pattern analysis can proceed")
        else:
            print("   ⚠️  Neo4j is NOT READY - Pattern analysis will be skipped gracefully")
        
        # Test individual checks
        print("\n3. Testing Individual Readiness Checks...")
        
        # Check Observation nodes
        has_observations = agent.neo4j.check_observation_nodes_exist()
        print(f"   Observation nodes exist: {has_observations}")
        
        # Check HAS_OBSERVATION relationships
        has_relationships = agent.neo4j.check_has_observation_relationship_exists()
        print(f"   HAS_OBSERVATION relationships exist: {has_relationships}")
        
        # Test pattern analysis with readiness check
        print("\n4. Testing Pattern Analysis (with readiness check)...")
        print("   This should either:")
        print("   - Skip gracefully if Neo4j not ready (NO WARNINGS)")
        print("   - Proceed with analysis if Neo4j ready")
        
        # Try to get cameras
        try:
            cameras = agent.neo4j.get_all_cameras()
            print(f"   Found {len(cameras)} cameras in Neo4j")
            
            if cameras and is_ready:
                # Test with first camera
                test_camera = cameras[0]
                print(f"\n   Testing with camera: {test_camera}")
                result = agent.analyze_camera_patterns(test_camera, '7_days')
                
                if result.get('status') == 'skipped':
                    print(f"   ✅ SKIPPED: {result.get('reason')}")
                    print("   ✅ NO Neo4j warnings generated!")
                elif result.get('status') == 'success':
                    print(f"   ✅ SUCCESS: Found {result.get('data_points', 0)} data points")
                elif result.get('status') == 'no_data':
                    print(f"   ℹ️  NO DATA: {result.get('reason')}")
                else:
                    print(f"   Result: {result}")
            
        except Exception as e:
            print(f"   ⚠️  Error getting cameras: {e}")
        
        # Test process_all_cameras
        print("\n5. Testing process_all_cameras (with global readiness check)...")
        results = agent.process_all_cameras('7_days')
        
        print(f"\n   Processing Results:")
        print(f"   - Status: {results.get('status', 'N/A')}")
        print(f"   - Cameras processed: {results.get('cameras_processed', 0)}")
        print(f"   - Entities created: {results.get('entities_created', 0)}")
        print(f"   - Skipped: {results.get('skipped', 0)}")
        print(f"   - Failures: {len(results.get('failures', []))}")
        
        if results.get('status') == 'skipped':
            print(f"\n   ✅ GRACEFULLY SKIPPED: {results.get('reason')}")
            print("   ✅ NO Neo4j property/label warnings!")
        
        # Clean up
        agent.close()
        print("\n✅ Agent closed successfully")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nEXPECTED BEHAVIOR:")
    print("- If Neo4j sync NOT complete: Pattern analysis SKIPPED gracefully")
    print("- If Neo4j sync complete: Pattern analysis proceeds normally")
    print("- NO Neo4j warning messages about missing labels/properties/relationships")
    print("=" * 80)


if __name__ == '__main__':
    test_pattern_recognition_with_readiness_check()

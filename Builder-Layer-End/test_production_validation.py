"""
Production validation test for Entity Publisher Agent.

This script validates the agent with the validated_entities.json from PROMPT 5.
Since Stellio is not running locally, we use mocked responses to simulate the API.
"""

import sys
sys.path.insert(0, '.')

import responses
from agents.context_management.entity_publisher_agent import EntityPublisherAgent


@responses.activate
def test_production_validation():
    """Test agent with validated entities (42 entities from PROMPT 5)."""
    
    # Mock Stellio API batch upsert
    responses.add(
        responses.POST,
        'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
        status=200,
        json={'success': True}
    )
    
    # Initialize agent
    agent = EntityPublisherAgent()
    
    # Publish validated entities
    report = agent.publish('data/validated_entities.json')
    
    # Print results
    print("\n" + "=" * 80)
    print("ENTITY PUBLISHER AGENT - PRODUCTION VALIDATION")
    print("=" * 80)
    print(f"Total entities:    {report['total_entities']}")
    print(f"Successful:        {report['successful']}")
    print(f"Failed:            {report['failed']}")
    print(f"Success rate:      {report['success_rate']}%")
    print(f"Duration:          {report['duration_seconds']}s")
    if 'throughput' in report:
        print(f"Throughput:        {report['throughput']} entities/second")
    print(f"Report saved to:   {report.get('report_path', 'N/A')}")
    print("=" * 80)
    
    # Close agent
    agent.close()
    
    # Validate results
    assert report['total_entities'] == 42, f"Expected 42 entities, got {report['total_entities']}"
    assert report['successful'] == 42, f"Expected all successful, got {report['successful']}"
    assert report['failed'] == 0, f"Expected 0 failures, got {report['failed']}"
    assert report['success_rate'] == 100.0, f"Expected 100% success rate, got {report['success_rate']}%"
    
    print("\n✓ Production validation PASSED - All 42 entities published successfully!")
    return report


if __name__ == '__main__':
    try:
        report = test_production_validation()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Production validation FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

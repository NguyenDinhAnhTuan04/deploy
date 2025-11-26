"""
Simple script to run Kafka Entity Publisher
Designed to run inside Docker network where kafka:9092 is resolvable
"""

import sys
import json
from kafka_entity_publisher_agent import KafkaEntityPublisherAgent

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_kafka_publisher.py <entities_file>")
        sys.exit(1)
    
    entities_file = sys.argv[1]
    
    config = {
        "kafka_bootstrap_servers": "kafka:9092",  # Docker network hostname
        "kafka_topic": "cim.entity._CatchAll"
    }
    
    agent = KafkaEntityPublisherAgent(config)
    result = agent.run({"entities_file": entities_file})
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)

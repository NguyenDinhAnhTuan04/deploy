#!/usr/bin/env python3
"""
Test CV Analysis với ảnh local thay vì download từ server chậm.
Tạo fake observations để test validation pipeline.
"""

import json
from datetime import datetime

# Tạo fake observations dựa trên cameras_updated.json
with open('data/cameras_updated.json', 'r', encoding='utf-8') as f:
    cameras = json.load(f)

observations = []
for camera in cameras[:10]:  # Test với 10 cameras đầu
    obs = {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld"
        ],
        "id": f"urn:ngsi-ld:ItemFlowObserved:test-{camera['id']}-{int(datetime.now().timestamp())}",
        "type": "ItemFlowObserved",
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": [float(camera['longitude']), float(camera['latitude'])]
            }
        },
        "refDevice": {
            "type": "Relationship",
            "object": f"urn:ngsi-ld:Camera:{camera['code']}"
        },
        "intensity": {
            "type": "Property",
            "value": 0.45,
            "observedAt": datetime.now().isoformat() + 'Z'
        },
        "averageVehicleSpeed": {
            "type": "Property",
            "value": 35.0,
            "unitCode": "KMH",
            "observedAt": datetime.now().isoformat() + 'Z'
        },
        "vehicleCount": {
            "type": "Property",
            "value": {
                "car": 15,
                "motorbike": 8,
                "truck": 2,
                "bus": 1
            },
            "observedAt": datetime.now().isoformat() + 'Z'
        },
        "dateObserved": {
            "type": "Property",
            "value": datetime.now().isoformat() + 'Z'
        }
    }
    observations.append(obs)

# Save observations
with open('data/observations.json', 'w', encoding='utf-8') as f:
    json.dump(observations, f, ensure_ascii=False, indent=2)

print(f"✅ Created {len(observations)} test observations in data/observations.json")
print("Now run: python orchestrator.py --start-from Analytics")

"""
Deep dive test: Run actual detection on observations
"""
import json
import sys
sys.path.insert(0, '.')

from agents.analytics.accident_detection_agent import AccidentDetectionAgent

print("="*60)
print("🔬 RUNNING ACTUAL DETECTION TEST")
print("="*60)

# Initialize agent
agent = AccidentDetectionAgent('config/accident_config.yaml')

# Load observations
with open('data/observations.json') as f:
    observations = json.load(f)

print(f"\n📊 Loaded {len(observations)} observations")
print(f"   Detectors initialized: {len(agent.detectors)}")
for detector in agent.detectors:
    print(f"   - {detector.name} (enabled: {detector.enabled}, weight: {detector.weight})")

# Group by camera
from collections import defaultdict
camera_obs = defaultdict(list)
for obs in observations:
    cam_ref = obs.get('refDevice', {}).get('object', 'unknown')
    camera_obs[cam_ref].append(obs)

print(f"\n📷 Cameras found: {len(camera_obs)}")

# Test first camera in detail
test_camera = list(camera_obs.keys())[0]
test_obs = camera_obs[test_camera]

print(f"\n🎯 Testing camera: {test_camera}")
print(f"   Observations: {len(test_obs)}")

# Add to buffer
for obs in test_obs:
    agent.observations_buffer[test_camera].append(obs)

recent = list(agent.observations_buffer[test_camera])
print(f"   Buffer size: {len(recent)}")

# Run each detector
print(f"\n🔍 Detection Results:")
print("-" * 60)

total_weighted_confidence = 0.0
total_weight = 0.0
detections_found = []

for detector in agent.detectors:
    if not detector.enabled:
        continue
    
    detected, confidence, reason = detector.detect(recent, test_camera)
    
    print(f"\n{detector.name}:")
    print(f"   Detected: {detected}")
    print(f"   Raw Confidence: {confidence:.4f}")
    print(f"   Weight: {detector.weight}")
    print(f"   Weighted: {confidence * detector.weight:.4f}")
    print(f"   Reason: {reason}")
    
    if detected:
        detections_found.append({
            'method': detector.name,
            'confidence': confidence,
            'weight': detector.weight,
            'weighted': confidence * detector.weight
        })
        total_weighted_confidence += confidence * detector.weight
        total_weight += detector.weight

print("\n" + "="*60)
print("📊 AGGREGATE RESULTS")
print("="*60)

if detections_found:
    print(f"\n✅ {len(detections_found)} methods detected anomalies:")
    for d in detections_found:
        print(f"   - {d['method']}: {d['confidence']:.3f} × {d['weight']} = {d['weighted']:.3f}")
    
    # Current implementation (WRONG - no weights)
    simple_avg = sum(d['confidence'] for d in detections_found) / len(detections_found)
    
    # Correct implementation (SHOULD BE)
    weighted_avg = total_weighted_confidence / total_weight if total_weight > 0 else 0
    
    print(f"\n🔴 CURRENT CODE (simple average):")
    print(f"   Confidence: {simple_avg:.4f}")
    print(f"   Above min_confidence (0.4): {'YES ✅' if simple_avg >= 0.4 else 'NO ❌'}")
    
    print(f"\n🟢 CORRECT FORMULA (weighted average):")
    print(f"   Confidence: {weighted_avg:.4f}")
    print(f"   Above min_confidence (0.4): {'YES ✅' if weighted_avg >= 0.4 else 'NO ❌'}")
    
    print(f"\n⚠️ BUG IDENTIFIED:")
    print(f"   Code uses: sum(confidence) / count")
    print(f"   Should use: sum(confidence × weight) / sum(weight)")
    print(f"   Impact: {'Detection blocked by incorrect calculation' if simple_avg < 0.4 and weighted_avg >= 0.4 else 'N/A'}")
else:
    print(f"\n❌ No detections from any method")
    print(f"\n📋 Possible reasons:")
    print(f"   - Data too uniform (all speeds = 80 km/h)")
    print(f"   - Insufficient observations in buffer")
    print(f"   - Thresholds too high for current data")

print("\n" + "="*60)

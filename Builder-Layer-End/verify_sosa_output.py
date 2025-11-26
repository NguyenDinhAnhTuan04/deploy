import json

entities = json.load(open('data/sosa_enhanced_entities.json', encoding='utf-8'))

# Count by type
type_counts = {}
sosa_type_counts = {}

for e in entities:
    entity_type = e.get('type')
    
    # Count original types
    if isinstance(entity_type, list):
        for t in entity_type:
            if not t.startswith('sosa:'):
                type_counts[t] = type_counts.get(t, 0) + 1
            else:
                sosa_type_counts[t] = sosa_type_counts.get(t, 0) + 1
    else:
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

print("Entity Distribution:")
print("=" * 60)
for t, c in sorted(type_counts.items()):
    print(f"  {t}: {c}")

print("\nSOSA Type Distribution:")
print("=" * 60)
for t, c in sorted(sosa_type_counts.items()):
    print(f"  {t}: {c}")

# Check Camera with sosa:Sensor
cameras = [e for e in entities if 'Camera' in str(e.get('type'))]
camera_with_sensor = [e for e in cameras if 'sosa:Sensor' in e.get('type', [])]
print(f"\nCamera entities: {len(cameras)}")
print(f"Camera with sosa:Sensor: {len(camera_with_sensor)}")

# Check WeatherObserved with sosa:Observation
weather = [e for e in entities if 'WeatherObserved' in str(e.get('type'))]
weather_with_obs = [e for e in weather if 'sosa:Observation' in e.get('type', [])]
print(f"\nWeatherObserved entities: {len(weather)}")
print(f"WeatherObserved with sosa:Observation: {len(weather_with_obs)}")

# Check AirQualityObserved with sosa:Observation
airquality = [e for e in entities if 'AirQualityObserved' in str(e.get('type'))]
aq_with_obs = [e for e in airquality if 'sosa:Observation' in e.get('type', [])]
print(f"\nAirQualityObserved entities: {len(airquality)}")
print(f"AirQualityObserved with sosa:Observation: {len(aq_with_obs)}")

# Sample Camera
if camera_with_sensor:
    sample = camera_with_sensor[0]
    print(f"\n{'='*60}")
    print("Sample Camera Entity:")
    print(f"{'='*60}")
    print(f"ID: {sample.get('id')}")
    print(f"Type: {sample.get('type')}")
    print(f"Has sosa:observes: {'sosa:observes' in sample}")
    print(f"Has sosa:isHostedBy: {'sosa:isHostedBy' in sample}")
    print(f"@context includes SOSA: {any('sosa' in str(ctx) for ctx in sample.get('@context', []))}")

# Sample WeatherObserved
if weather_with_obs:
    sample = weather_with_obs[0]
    print(f"\n{'='*60}")
    print("Sample WeatherObserved Entity:")
    print(f"{'='*60}")
    print(f"ID: {sample.get('id')}")
    print(f"Type: {sample.get('type')}")
    print(f"Has sosa:observes: {'sosa:observes' in sample}")
    print(f"Has sosa:isHostedBy: {'sosa:isHostedBy' in sample}")
    print(f"@context includes SOSA: {any('sosa' in str(ctx) for ctx in sample.get('@context', []))}")

# Sample AirQualityObserved
if aq_with_obs:
    sample = aq_with_obs[0]
    print(f"\n{'='*60}")
    print("Sample AirQualityObserved Entity:")
    print(f"{'='*60}")
    print(f"ID: {sample.get('id')}")
    print(f"Type: {sample.get('type')}")
    print(f"Has sosa:observes: {'sosa:observes' in sample}")
    print(f"Has sosa:isHostedBy: {'sosa:isHostedBy' in sample}")
    print(f"@context includes SOSA: {any('sosa' in str(ctx) for ctx in sample.get('@context', []))}")

print(f"\n{'='*60}")
print(f"TOTAL ENTITIES: {len(entities)}")
print(f"{'='*60}")

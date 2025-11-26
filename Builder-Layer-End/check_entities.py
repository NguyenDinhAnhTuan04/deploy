import json

entities = json.load(open('data/ngsi_ld_entities.json', encoding='utf-8'))

# Count types
types = {}
for e in entities:
    types[e['type']] = types.get(e['type'], 0) + 1

print('Entity Type Distribution:')
for t, c in sorted(types.items()):
    print(f'  {t}: {c}')

# Find AirQualityObserved with PM2.5
aq_with_pm25 = [e for e in entities if e['type'] == 'AirQualityObserved' and 'pm25' in e]
print(f'\nAirQualityObserved with PM2.5: {len(aq_with_pm25)} entities')

# Sample
if aq_with_pm25:
    sample = aq_with_pm25[0]
    print(f'\nSample AirQualityObserved:')
    print(f'  ID: {sample.get("id")}')
    print(f'  refDevice: {sample.get("refDevice", {}).get("object")}')
    
    # Pollution properties
    for prop in ['pm25', 'pm10', 'co', 'o3', 'no2', 'so2']:
        if prop in sample:
            val = sample[prop].get('value')
            unit = sample[prop].get('unitCode', '')
            print(f'  {prop}: {val} {unit}')
    
    if 'aqiCategory' in sample:
        print(f'  aqiCategory: {sample["aqiCategory"].get("value")}')

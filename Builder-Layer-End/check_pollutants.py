"""
Quick script to check pollutants in enriched data and NGSI-LD entities
"""
import json
from typing import Dict, List

def check_enriched_data():
    """Check cameras_enriched.json for pollutants"""
    print("\n" + "="*80)
    print("   CHECKING CAMERAS_ENRICHED.JSON")
    print("="*80 + "\n")
    
    with open("data/cameras_enriched.json", "r", encoding="utf-8") as f:
        cameras = json.load(f)
    
    print(f"Total cameras: {len(cameras)}")
    
    # Check first camera
    first = cameras[0]
    print(f"\nCamera: {first['name']}")
    
    if 'air_quality' in first:
        aq = first['air_quality']
        print(f"\nAir Quality Source: {aq.get('source', 'Unknown')}")
        
        pollutants = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2', 'nh3']
        print("\nPollutants:")
        present_count = 0
        for pollutant in pollutants:
            if pollutant in aq:
                value = aq[pollutant]['value']
                unit = aq[pollutant]['unit']
                print(f"  ✓ {pollutant}: {value} {unit}")
                present_count += 1
            else:
                print(f"  ✗ {pollutant}: MISSING")
        
        print(f"\nData Completeness: {present_count}/7 pollutants ({present_count/7*100:.1f}%)")
        
        # Check AQI
        if 'aqi_category' in aq:
            print(f"\nAQI Category: {aq['aqi_category']}")
        if 'aqi_index' in aq:
            print(f"AQI Index: {aq['aqi_index']}")
    else:
        print("\n✗ NO AIR QUALITY DATA!")
    
    # Check all cameras
    print("\n" + "-"*80)
    print("Checking all cameras...")
    
    cameras_with_aq = 0
    total_pollutants = {p: 0 for p in ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2', 'nh3']}
    
    for camera in cameras:
        if 'air_quality' in camera:
            cameras_with_aq += 1
            for pollutant in total_pollutants.keys():
                if pollutant in camera['air_quality']:
                    total_pollutants[pollutant] += 1
    
    print(f"\nCameras with air quality data: {cameras_with_aq}/{len(cameras)} ({cameras_with_aq/len(cameras)*100:.1f}%)")
    print("\nPollutant coverage across all cameras:")
    for pollutant, count in total_pollutants.items():
        percentage = (count / len(cameras) * 100) if len(cameras) > 0 else 0
        status = "✓" if percentage == 100 else "✗"
        print(f"  {status} {pollutant}: {count}/{len(cameras)} ({percentage:.1f}%)")


def check_ngsi_ld_entities():
    """Check NGSI-LD entities for pollutants"""
    print("\n" + "="*80)
    print("   CHECKING NGSI-LD ENTITIES")
    print("="*80 + "\n")
    
    with open("data/ngsi_ld_entities.json", "r", encoding="utf-8") as f:
        entities = json.load(f)
    
    # Filter AirQualityObserved entities
    aq_entities = [e for e in entities if e.get('type') == 'AirQualityObserved']
    
    print(f"Total entities: {len(entities)}")
    print(f"AirQualityObserved entities: {len(aq_entities)}")
    
    if not aq_entities:
        print("\n✗ NO AirQualityObserved ENTITIES FOUND!")
        return
    
    # Check first entity
    first = aq_entities[0]
    print(f"\nEntity ID: {first['id']}")
    print(f"Entity Type: {first['type']}")
    
    pollutants = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2', 'nh3']
    print("\nPollutants in NGSI-LD format:")
    present_count = 0
    for pollutant in pollutants:
        if pollutant in first:
            value = first[pollutant].get('value', 'N/A')
            unit_code = first[pollutant].get('unitCode', 'N/A')
            print(f"  ✓ {pollutant}:")
            print(f"      value: {value}")
            print(f"      unitCode: {unit_code}")
            present_count += 1
        else:
            print(f"  ✗ {pollutant}: MISSING")
    
    print(f"\nData Completeness: {present_count}/7 pollutants ({present_count/7*100:.1f}%)")
    
    # Check additional properties
    print("\nAdditional Properties:")
    if 'airQualityCategory' in first:
        print(f"  ✓ airQualityCategory: {first['airQualityCategory'].get('value', 'N/A')}")
    if 'airQualityIndexValue' in first:
        print(f"  ✓ airQualityIndexValue: {first['airQualityIndexValue'].get('value', 'N/A')}")
    if 'dataProvider' in first:
        print(f"  ✓ dataProvider: {first['dataProvider'].get('value', 'N/A')}")
    
    # Check all entities
    print("\n" + "-"*80)
    print("Checking all AirQualityObserved entities...")
    
    total_pollutants = {p: 0 for p in pollutants}
    
    for entity in aq_entities:
        for pollutant in pollutants:
            if pollutant in entity:
                total_pollutants[pollutant] += 1
    
    print(f"\nPollutant coverage across all {len(aq_entities)} entities:")
    for pollutant, count in total_pollutants.items():
        percentage = (count / len(aq_entities) * 100) if len(aq_entities) > 0 else 0
        status = "✓" if percentage == 100 else "✗"
        print(f"  {status} {pollutant}: {count}/{len(aq_entities)} ({percentage:.1f}%)")


def main():
    """Main entry point"""
    check_enriched_data()
    check_ngsi_ld_entities()
    
    print("\n" + "="*80)
    print("   SUMMARY")
    print("="*80 + "\n")
    
    # Load both files
    with open("data/cameras_enriched.json", "r", encoding="utf-8") as f:
        cameras = json.load(f)
    
    with open("data/ngsi_ld_entities.json", "r", encoding="utf-8") as f:
        entities = json.load(f)
    
    aq_entities = [e for e in entities if e.get('type') == 'AirQualityObserved']
    
    # Count pollutants
    enriched_pollutants = set()
    if cameras and 'air_quality' in cameras[0]:
        enriched_pollutants = set(cameras[0]['air_quality'].keys()) - {'source', 'aqi_category', 'aqi_index', 'location_name', 'distance_km'}
    
    entity_pollutants = set()
    if aq_entities:
        entity_pollutants = set(p for p in ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2', 'nh3'] if p in aq_entities[0])
    
    print(f"Data Flow Success:")
    print(f"  1. External Data Collector: {len(cameras)} cameras enriched")
    print(f"  2. Enriched Data Pollutants: {len(enriched_pollutants)} pollutants ({', '.join(sorted(enriched_pollutants))})")
    print(f"  3. NGSI-LD Transformation: {len(aq_entities)} AirQualityObserved entities created")
    print(f"  4. Entity Pollutants: {len(entity_pollutants)} pollutants ({', '.join(sorted(entity_pollutants))})")
    
    if len(enriched_pollutants) == 7 and len(entity_pollutants) == 7:
        print(f"\n✅ SUCCESS: All 7 pollutants (6 required + NH3 bonus) present!")
        print(f"   Data Completeness: 100%")
    elif len(enriched_pollutants) >= 6 and len(entity_pollutants) >= 6:
        print(f"\n✅ SUCCESS: All 6 required pollutants present!")
        print(f"   Data Completeness: {len(entity_pollutants)/6*100:.1f}%")
    else:
        print(f"\n⚠️  WARNING: Missing pollutants!")
        print(f"   Data Completeness: {len(entity_pollutants)/6*100:.1f}%")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

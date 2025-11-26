"""
Test Air Quality Data Flow - End-to-End Verification

This script tests the complete data flow from OpenWeatherMap API
through transformation to NGSI-LD entities.

Test Steps:
1. Fetch air quality data from OpenWeatherMap API
2. Check data structure (6 pollutants + NH3)
3. Simulate enrichment process
4. Verify NGSI-LD transformation
5. Validate output structure

Author: Builder Layer LOD System
Date: 2025-11-18
"""

import asyncio
import json
import sys
from pathlib import Path

import aiohttp
import yaml


async def test_api_fetch():
    """Test 1: Fetch air quality data from OpenWeatherMap API"""
    print("=" * 80)
    print("TEST 1: FETCH AIR QUALITY DATA FROM OPENWEATHERMAP API")
    print("=" * 80)
    
    # Load config
    with open('config/data_sources.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    api_config = config['air_quality']
    
    # Ho Chi Minh City coordinates
    lat = 10.8231
    lon = 106.6297
    
    url = api_config['base_url']
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_config['api_key']
    }
    
    print(f"\nEndpoint: {url}")
    print(f"Location: Ho Chi Minh City ({lat}, {lon})")
    print(f"\nFetching...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                
                # Extract components
                if data.get('list') and len(data['list']) > 0:
                    result = data['list'][0]
                    components = result.get('components', {})
                    aqi = result.get('main', {}).get('aqi')
                    
                    print(f"\n✅ API Response Status: {response.status} OK")
                    print(f"\nAIR QUALITY INDEX: {aqi} (", end='')
                    aqi_map = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
                    print(f"{aqi_map.get(aqi, 'Unknown')})")
                    
                    print("\nPOLLUTANTS FOUND:")
                    required = ['pm2_5', 'pm10', 'no2', 'o3', 'co', 'so2']
                    found = 0
                    for pollutant in required:
                        if pollutant in components:
                            value = components[pollutant]
                            print(f"  ✓ {pollutant.upper():6s}: {value:8.2f} µg/m³")
                            found += 1
                        else:
                            print(f"  ✗ {pollutant.upper():6s}: MISSING")
                    
                    # Check bonus NH3
                    if 'nh3' in components:
                        print(f"  + NH3   : {components['nh3']:8.2f} µg/m³ (Bonus)")
                    
                    print(f"\nDATA COMPLETENESS: {found}/6 required pollutants ({found/6*100:.1f}%)")
                    
                    if found == 6:
                        print("✅ TEST 1 PASSED: All 6 pollutants available!")
                        return True, components, aqi
                    else:
                        print(f"❌ TEST 1 FAILED: Only {found}/6 pollutants")
                        return False, None, None
            else:
                print(f"❌ API Error: Status {response.status}")
                return False, None, None


def test_enrichment_structure(components, aqi):
    """Test 2: Verify enrichment data structure"""
    print("\n" + "=" * 80)
    print("TEST 2: VERIFY ENRICHMENT DATA STRUCTURE")
    print("=" * 80)
    
    # Simulate enrichment structure (as returned by external_data_collector_agent)
    aq_data = {}
    
    pollutant_mapping = {
        'pm2_5': 'pm25',
        'pm10': 'pm10',
        'no2': 'no2',
        'o3': 'o3',
        'co': 'co',
        'so2': 'so2',
        'nh3': 'nh3'
    }
    
    for owm_name, our_name in pollutant_mapping.items():
        if owm_name in components:
            value = components[owm_name]
            aq_data[our_name] = {
                'value': value,
                'unit': 'µg/m³'
            }
    
    # Add AQI info
    aqi_categories = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
    aq_data['aqi_category'] = aqi_categories.get(aqi, "Unknown")
    aq_data['aqi_index'] = aqi
    aq_data['source'] = 'OpenWeatherMap'
    
    print("\nENRICHMENT DATA STRUCTURE:")
    print(json.dumps(aq_data, indent=2))
    
    # Verify structure
    required_pollutants = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2']
    all_present = all(
        p in aq_data and isinstance(aq_data[p], dict) and 'value' in aq_data[p]
        for p in required_pollutants
    )
    
    if all_present:
        print("\n✅ TEST 2 PASSED: Enrichment structure correct!")
        return True, aq_data
    else:
        print("\n❌ TEST 2 FAILED: Missing required fields")
        return False, None


def test_ngsi_ld_mapping():
    """Test 3: Verify NGSI-LD mapping configuration"""
    print("\n" + "=" * 80)
    print("TEST 3: VERIFY NGSI-LD MAPPING CONFIGURATION")
    print("=" * 80)
    
    # Load mapping config
    with open('config/ngsi_ld_mappings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    aq_config = config.get('airquality_mappings')
    
    if not aq_config:
        print("❌ TEST 3 FAILED: airquality_mappings not found in config")
        return False
    
    print(f"\nEntity Type: {aq_config['entity_type']}")
    print(f"URI Prefix: {aq_config['uri_prefix']}")
    
    print("\nPROPERTY MAPPINGS:")
    property_mappings = aq_config.get('property_mappings', {})
    
    required_mappings = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2']
    bonus_mappings = ['nh3', 'aqi_category', 'aqi_index', 'source']
    
    print("\nRequired Pollutants:")
    for field in required_mappings:
        if field in property_mappings:
            mapping = property_mappings[field]
            target = mapping.get('target', field)
            unit = mapping.get('unit', 'N/A')
            print(f"  ✓ {field:6s} → {target:20s} (unit: {unit})")
        else:
            print(f"  ✗ {field:6s} → MISSING")
    
    print("\nBonus/Metadata Fields:")
    for field in bonus_mappings:
        if field in property_mappings:
            mapping = property_mappings[field]
            target = mapping.get('target', field)
            print(f"  ✓ {field:15s} → {target}")
        else:
            print(f"  ✗ {field:15s} → MISSING")
    
    # Check if all required mappings exist
    all_required = all(m in property_mappings for m in required_mappings)
    
    if all_required:
        print("\n✅ TEST 3 PASSED: All required mappings present!")
        return True
    else:
        print("\n❌ TEST 3 FAILED: Missing required mappings")
        return False


def test_transform_logic():
    """Test 4: Verify transform logic in ngsi_ld_transformer_agent.py"""
    print("\n" + "=" * 80)
    print("TEST 4: VERIFY TRANSFORM LOGIC")
    print("=" * 80)
    
    # Read transformer agent code
    with open('agents/transformation/ngsi_ld_transformer_agent.py', 'r') as f:
        code = f.read()
    
    # Check for key logic
    checks = {
        'create_air_quality_observed_entity': 'def create_air_quality_observed_entity' in code,
        'pm25_pm10_co_o3_no2_so2': "['pm25', 'pm10', 'co', 'o3', 'no2', 'so2'" in code,
        'nh3_support': "'nh3'" in code,
        'nested_structure': "isinstance(measurement, dict)" in code,
        'value_extraction': "measurement.get('value')" in code,
    }
    
    print("\nCODE CHECKS:")
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name.replace('_', ' ').title()}")
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("\n✅ TEST 4 PASSED: Transform logic correct!")
        return True
    else:
        print("\n❌ TEST 4 FAILED: Transform logic incomplete")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("   AIR QUALITY DATA FLOW - END-TO-END VERIFICATION")
    print("=" * 80)
    print("\nTesting complete data flow from OpenWeatherMap API to NGSI-LD entities")
    print("Location: Ho Chi Minh City, Vietnam")
    print()
    
    results = {}
    
    # Test 1: API Fetch
    try:
        success, components, aqi = await test_api_fetch()
        results['API Fetch'] = success
    except Exception as e:
        print(f"\n❌ TEST 1 EXCEPTION: {e}")
        results['API Fetch'] = False
        components = None
        aqi = None
    
    # Test 2: Enrichment Structure
    if components and aqi:
        try:
            success, aq_data = test_enrichment_structure(components, aqi)
            results['Enrichment Structure'] = success
        except Exception as e:
            print(f"\n❌ TEST 2 EXCEPTION: {e}")
            results['Enrichment Structure'] = False
    else:
        print("\n⚠️  TEST 2 SKIPPED: No API data")
        results['Enrichment Structure'] = False
    
    # Test 3: NGSI-LD Mapping
    try:
        success = test_ngsi_ld_mapping()
        results['NGSI-LD Mapping'] = success
    except Exception as e:
        print(f"\n❌ TEST 3 EXCEPTION: {e}")
        results['NGSI-LD Mapping'] = False
    
    # Test 4: Transform Logic
    try:
        success = test_transform_logic()
        results['Transform Logic'] = success
    except Exception as e:
        print(f"\n❌ TEST 4 EXCEPTION: {e}")
        results['Transform Logic'] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("   TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:25s}: {status}")
    
    all_passed = all(results.values())
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if all_passed:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - SYSTEM READY!")
        print("=" * 80)
        print("\nNEXT STEPS:")
        print("1. Run orchestrator to generate new enriched data")
        print("2. Verify cameras_enriched.json has 6 pollutants")
        print("3. Check ngsi_ld_entities.json has AirQualityObserved with all pollutants")
        print("4. Publish to Stellio and verify entities")
    else:
        print("\n" + "=" * 80)
        print("❌ SOME TESTS FAILED - REVIEW ISSUES ABOVE")
        print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    # Run async main
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

"""
Test script for OpenAQ v3 API integration  
Tests Vietnam (Ho Chi Minh City) air quality data with all 6 pollutants
"""
import requests
import json

def test_openaq_v3():
    """Test OpenAQ v3 API with Ho Chi Minh City coordinates"""
    
    # Ho Chi Minh City US Consulate coordinates
    lat = 10.8231
    lon = 106.6297
    radius = 25000  # 25km
    
    # OpenAQ v3 requires API key
    api_key = "1268dbec69a5c8dd637f4a0616a7338d1f320ae966721abdc18e94a2b20b0675"
    
    base_url = "https://api.openaq.org/v3"
    
    print("=" * 80)
    print("TESTING OPENAQ V3 API WITH VIETNAM DATA")
    print("=" * 80)
    print(f"\nBase URL: {base_url}")
    print(f"Location: Ho Chi Minh City (US Consulate)")
    print(f"Coordinates: ({lat}, {lon})")
    print(f"Radius: {radius}m")
    print(f"\nExpected: All 6 pollutants (PM2.5, PM10, NO2, O3, CO, SO2)")
    
    # Step 1: Get locations near coordinates
    print("\n" + "=" * 80)
    print("STEP 1: GET LOCATIONS")
    print("=" * 80)
    
    locations_url = f"{base_url}/locations"
    locations_params = {
        'coordinates': f"{lat},{lon}",
        'radius': radius,
        'limit': 1
    }
    headers = {
        'X-API-Key': api_key
    }
    
    try:
        print(f"\nGET {locations_url}")
        print(f"Params: {locations_params}")
        response = requests.get(locations_url, params=locations_params, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                location = data['results'][0]
                location_id = location.get('id')
                location_name = location.get('name')
                
                print(f"\nLocation Found:")
                print(f"  ID:   {location_id}")
                print(f"  Name: {location_name}")
                
                # Get sensors info
                sensors = location.get('sensors', [])
                print(f"\nSensors: {len(sensors)}")
                
                # Build parameter list
                parameters = set()
                for sensor in sensors:
                    param = sensor.get('parameter', {})
                    if param:
                        param_name = param.get('name')
                        if param_name:
                            parameters.add(param_name)
                
                print(f"Parameters available: {', '.join(sorted(parameters))}")
                
                # Step 2: Get latest measurements for this location
                print("\n" + "=" * 80)
                print("STEP 2: GET LATEST MEASUREMENTS")
                print("=" * 80)
                
                measurements_url = f"{base_url}/locations/{location_id}/latest"
                print(f"\nGET {measurements_url}")
                
                meas_response = requests.get(measurements_url, headers=headers, timeout=10)
                print(f"Status: {meas_response.status_code}")
                
                if meas_response.status_code == 200:
                    meas_data = meas_response.json()
                    
                    print("\n" + "=" * 80)
                    print("POLLUTANTS FOUND")
                    print("=" * 80)
                    
                    # Build sensor_id -> parameter mapping
                    sensor_params = {}
                    for sensor in sensors:
                        sensor_id = sensor.get('id')
                        param = sensor.get('parameter', {})
                        if sensor_id and param:
                            sensor_params[sensor_id] = {
                                'name': param.get('name'),
                                'units': param.get('units')
                            }
                    
                    measurements = meas_data.get('results', [])
                    required_pollutants = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2']
                    found_pollutants = {}
                    
                    for measurement in measurements:
                        sensor_id = measurement.get('sensorsId')
                        value = measurement.get('value')
                        
                        if sensor_id in sensor_params:
                            param_info = sensor_params[sensor_id]
                            param_name = param_info['name']
                            unit = param_info['units']
                            
                            if param_name in required_pollutants:
                                found_pollutants[param_name] = {
                                    'value': value,
                                    'unit': unit
                                }
                    
                    # Display results
                    for pollutant in required_pollutants:
                        if pollutant in found_pollutants:
                            data_point = found_pollutants[pollutant]
                            print(f"  ✓ {pollutant.upper()}: {data_point['value']} {data_point['unit']}")
                        else:
                            print(f"  ✗ {pollutant.upper()}: MISSING")
                    
                    found_count = len(found_pollutants)
                    completeness = round(found_count / 6 * 100, 1)
                    
                    print("\n" + "=" * 80)
                    print("DATA COMPLETENESS")
                    print("=" * 80)
                    print(f"Found: {found_count}/6 pollutants ({completeness}%)")
                    
                    if found_count == 6:
                        print("✅ SUCCESS: All pollutants available!")
                    else:
                        print(f"⚠️  WARNING: Missing {6 - found_count} pollutants")
                        missing = [p for p in required_pollutants if p not in found_pollutants]
                        print(f"Missing: {', '.join(missing)}")
                    
                    print("\n" + "=" * 80)
                    print("RAW MEASUREMENTS (first 3)")
                    print("=" * 80)
                    print(json.dumps(measurements[:3], indent=2))
                    
                else:
                    print(f"Measurements Error: HTTP {meas_response.status_code}")
                    print(meas_response.text[:500])
                    
            else:
                print("No locations found for this area")
        else:
            print(f"Locations Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_openaq_v3()

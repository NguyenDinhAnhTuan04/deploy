"""
Test script for OpenWeatherMap Air Pollution API integration
Tests Vietnam (Ho Chi Minh City) air quality data with all 6 pollutants
"""
import requests
import json

def test_openweathermap():
    """Test OpenWeatherMap Air Pollution API with Ho Chi Minh City coordinates"""
    
    # Ho Chi Minh City coordinates
    lat = 10.8231
    lon = 106.6297
    
    # OpenWeatherMap API key (from config)
    api_key = "5d43c8c74f6a4b9f3cfdc3aaf1e5a015"
    
    url = "https://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key
    }
    
    print("=" * 80)
    print("TESTING OPENWEATHERMAP AIR POLLUTION API")
    print("=" * 80)
    print(f"\nEndpoint: {url}")
    print(f"Location: Ho Chi Minh City")
    print(f"Coordinates: ({lat}, {lon})")
    print(f"\nExpected: All 6 pollutants (PM2.5, PM10, NO2, O3, CO, SO2)")
    
    try:
        print("\nSending request...")
        response = requests.get(url, params=params, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('list') and len(data['list']) > 0:
                result = data['list'][0]
                components = result.get('components', {})
                main_aqi = result.get('main', {})
                
                print("\n" + "=" * 80)
                print("AIR QUALITY INDEX")
                print("=" * 80)
                
                aqi_value = main_aqi.get('aqi')
                aqi_categories = {
                    1: "Good",
                    2: "Fair",
                    3: "Moderate",
                    4: "Poor",
                    5: "Very Poor"
                }
                aqi_category = aqi_categories.get(aqi_value, "Unknown")
                print(f"AQI: {aqi_value} ({aqi_category})")
                
                print("\n" + "=" * 80)
                print("POLLUTANTS FOUND")
                print("=" * 80)
                
                # Map OpenWeatherMap field names to standard names
                pollutant_mapping = {
                    'pm2_5': ('PM2.5', 'pm25'),
                    'pm10': ('PM10', 'pm10'),
                    'no2': ('NO2', 'no2'),
                    'o3': ('O3', 'o3'),
                    'co': ('CO', 'co'),
                    'so2': ('SO2', 'so2'),
                    'nh3': ('NH3', 'nh3')  # Bonus
                }
                
                required_pollutants = ['pm2_5', 'pm10', 'no2', 'o3', 'co', 'so2']
                found_pollutants = {}
                
                for owm_name, (display_name, our_name) in pollutant_mapping.items():
                    if owm_name in components:
                        value = components[owm_name]
                        found_pollutants[our_name] = {
                            'value': value,
                            'unit': 'µg/m³'
                        }
                        is_required = owm_name in required_pollutants
                        marker = "✓" if is_required else "+"
                        print(f"  {marker} {display_name}: {value} µg/m³")
                    elif owm_name in required_pollutants:
                        display_name = pollutant_mapping[owm_name][0]
                        print(f"  ✗ {display_name}: MISSING")
                
                found_count = sum(1 for p in required_pollutants if pollutant_mapping[p][1] in found_pollutants)
                completeness = round(found_count / 6 * 100, 1)
                
                print("\n" + "=" * 80)
                print("DATA COMPLETENESS")
                print("=" * 80)
                print(f"Found: {found_count}/6 required pollutants ({completeness}%)")
                
                if found_count == 6:
                    print("✅ SUCCESS: All required pollutants available!")
                else:
                    print(f"⚠️  WARNING: Missing {6 - found_count} pollutants")
                    missing = [pollutant_mapping[p][0] for p in required_pollutants if pollutant_mapping[p][1] not in found_pollutants]
                    print(f"Missing: {', '.join(missing)}")
                
                print("\n" + "=" * 80)
                print("RAW COMPONENTS")
                print("=" * 80)
                print(json.dumps(components, indent=2))
                
            else:
                print("No air quality data available for this location")
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_openweathermap()

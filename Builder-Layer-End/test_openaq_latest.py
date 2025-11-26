import aiohttp
import asyncio
import json

async def test_openaq_v3_latest():
    async with aiohttp.ClientSession() as session:
        # Test latest endpoint for a specific location
        url = 'https://api.openaq.org/v3/locations/2446/latest'
        headers = {
            'X-API-Key': '1268dbec69a5c8dd637f4a0616a7338d1f320ae966721abdc18e94a2b20b0675'
        }
        
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(json.dumps(data, indent=2)[:1000])
            else:
                text = await response.text()
                print(f"Error: {text}")

asyncio.run(test_openaq_v3_latest())

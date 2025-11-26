import aiohttp
import asyncio

async def test_openaq_v3():
    async with aiohttp.ClientSession() as session:
        # Test locations endpoint
        url = 'https://api.openaq.org/v3/locations'
        params = {
            'coordinates': '10.8,106.7',
            'radius': 5000,
            'limit': 1
        }
        headers = {
            'X-API-Key': '1268dbec69a5c8dd637f4a0616a7338d1f320ae966721abdc18e94a2b20b0675'
        }
        
        async with session.get(url, params=params, headers=headers) as response:
            print(f"Status: {response.status}")
            text = await response.text()
            print(f"Response: {text[:1000]}")

asyncio.run(test_openaq_v3())

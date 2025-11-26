import asyncio
import aiohttp
import json

async def test():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'https://api.openaq.org/v3/locations/2446/latest',
            headers={'X-API-Key': 'b076f3cb-7f39-4eb5-93f8-05cceccc6b81'}
        ) as r:
            data = await r.json()
            print(json.dumps(data, indent=2))

asyncio.run(test())

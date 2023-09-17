import hashlib
import hmac
import aiohttp

async def get_server_time():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.binance.com/api/v3/time") as response:
            response_data = await response.json()
            return response_data['serverTime']

def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

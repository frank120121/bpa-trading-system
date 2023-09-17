import asyncio
import aiohttp
from urllib.parse import urlencode
import hashlib
import hmac
import os
from dotenv import load_dotenv
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)



load_dotenv()


url = "https://api.binance.com/sapi/v1/c2c/orderMatch/getUserOrderDetail"
credentials_dict = {
    'account_2': {
        'KEY': os.environ.get('API_KEY_MGL'),
        'SECRET': os.environ.get('API_SECRET_MGL')
    }
}
account = 'account_2'
if account in credentials_dict:
    KEY = credentials_dict[account]['KEY']
    SECRET = credentials_dict[account]['SECRET']
else:
    print(f"Credentials not found for account: {account}")
    exit()
def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
async def get_server_time():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.binance.com/api/v3/time") as response:
            response_data = await response.json()
            return response_data['serverTime']
async def fetch_order_details(KEY, SECRET, order_no):
    server_time = await get_server_time()
    timestamp = server_time 
    payload = {"adOrderNo": order_no, "timestamp": timestamp}
    query_string = urlencode(payload)
    signature = hashing(query_string, SECRET)
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB",
    }
    query_string += f"&signature={signature}"
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{url}?{query_string}", json=payload, headers=headers) as response:
            if response.status == 200:
                response_data = await response.json()
                logger.debug("Fetched order details: success")
                return response_data

            else:
                print(f"Request failed with status code {response.status}: {await response.text()}")
if __name__ == "__main__":
    adOrderNo = "20536613332382937088"
    asyncio.run(fetch_order_details(KEY, SECRET, adOrderNo))


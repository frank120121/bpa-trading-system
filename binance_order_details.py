import asyncio
import aiohttp
from urllib.parse import urlencode
from common_utils import get_server_timestamp
import hashlib
import hmac
import os
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


load_dotenv()


url = "https://api.binance.com/sapi/v1/c2c/orderMatch/getUserOrderDetail"
credentials_dict = {
    'account_1': {
        'KEY': os.environ.get('API_KEY_MFMP'),
        'SECRET': os.environ.get('API_SECRET_MFMP')
    }
}
account = 'account_1'
if account in credentials_dict:
    KEY = credentials_dict[account]['KEY']
    SECRET = credentials_dict[account]['SECRET']
else:
    logger.error(f"Credentials not found for account: {account}")
    exit()
def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
async def fetch_order_details(KEY, SECRET, order_no):
    timestamp = await get_server_timestamp()
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
                # print("Headers from the response:")
                # for header, value in response.headers.items():
                #     print(f"{header}: {value}")

                response_data = await response.json()
                logger.debug("Fetched order details: success")
                return response_data

            else:
                logger.error(f"Request failed with status code {response.status}: {await response.text()}")
if __name__ == "__main__":
    adOrderNo = "20580430641041174528"
    result = asyncio.run(fetch_order_details(KEY, SECRET, adOrderNo))
    print(result)
    account_number = None
    for method in result['data']['payMethods']:
        for field in method['fields']:
            if field['fieldName'] == 'Account number':
                account_number = field['fieldValue']
                break

    if account_number:
        print(account_number)
    else:
        print("Account number not found.")

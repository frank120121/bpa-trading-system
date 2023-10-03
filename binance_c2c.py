import time
import asyncio
import random
import traceback
import hashlib
import hmac
import aiohttp
from urllib.parse import urlencode
import websockets
from credentials import credentials_dict, BASE_URL
from websocket_handlers import on_message
import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)
async def get_server_timestamp():
    url = "https://api.binance.com/api/v1/time"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['serverTime']
                else:
                    return None
    except Exception as e:
        logger.error(f"An error occurred while fetching server time: {e}")
        return None
async def get_adjusted_timestamp(offset=0):
    logger.info(f"Using offset: {offset}")
    server_time = await get_server_timestamp()
    if server_time:
        return server_time - offset
    else:
        logger.warning("Falling back to local time.")
        return int(time.time() * 1000) - offset
def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
async def send_signed_request(http_method, url_path, KEY, SECRET, payload={}, dataLoad={}, offset=0):
    query_string = urlencode(payload)
    query_string = f"{query_string}&timestamp={await get_adjusted_timestamp(offset)}"
    url = f"{BASE_URL}{url_path}?{query_string}&signature={hashing(query_string, SECRET)}"
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB"
    }
    async with aiohttp.ClientSession() as session:
        async with session.request(http_method, url, params={}, data=dataLoad, headers=headers) as response:
            response_data = await response.json()
            if 'data' not in response_data:
                logger.error("API Response does not contain 'data' field")
                return {'success': False}
            if response.status != 200:
                logger.error(f"Received status code {response.status}: {response_data}")
                return {'success': False}
            return {'success': True, 'data': response_data}
async def run_websocket(KEY, SECRET, merchant_account, max_retries=10, initial_backoff=5, max_backoff=60):
    retry_count = 0
    backoff = initial_backoff
    offset = 0
    while retry_count < max_retries or max_retries == -1:
        try:
            uri_path = "/sapi/v1/c2c/chat/retrieveChatCredential"
            response = await send_signed_request("GET", uri_path, KEY, SECRET, offset=offset)
            if response and 'new_offset' in response:
                offset = response['new_offset']
                logger.info(f"Updated offset to {offset}")
                continue
            wss_url = ''
            if 'data' in response and 'data' in response['data'] and 'chatWssUrl' in response['data']['data']:
                wss_url = f"{response['data']['data']['chatWssUrl']}/{response['data']['data']['listenKey']}?token={response['data']['data']['listenToken']}&clientType=web"
            else:
                logger.error(f"Key 'chatWssUrl' not found in API response. Full response: {response}")
                return
            logger.info(f"Attempting to connect to WebSocket with URL: {wss_url}")
            async with websockets.connect(wss_url) as ws:
                async for message in ws:
                    logger.info(message)
                    await on_message(ws, message, KEY, SECRET, merchant_account)
            logger.info("WebSocket connection closed gracefully.")
            break
        except websockets.exceptions.ConnectionClosedError:
            logger.error("c2c webSocket connection closed unexpectedly. Reconnecting...")
        except websockets.WebSocketException as e:
            if "timeout" in str(e).lower():  
                logger.error("WebSocket connection timed out. Reconnecting...")
            else:
                raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. Reconnecting...")
            traceback.print_exc()  
        sleep_time = min(max_backoff, backoff)
        sleep_time += random.uniform(0, 0.1 * sleep_time)
        await asyncio.sleep(sleep_time)
        backoff *= 2
        retry_count += 1
        if retry_count >= max_retries and max_retries != -1:
            logger.warning("Max retries reached. Exiting.")
async def main_binance_c2c(merchant_account):
    credentials = list(credentials_dict.values())
    tasks = []
    for cred in credentials:
        task = asyncio.create_task(
            run_websocket(cred['KEY'], cred['SECRET'], merchant_account, max_retries=20, initial_backoff=5, max_backoff=60)
        )
        tasks.append(task)
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting.")
# if __name__ == "__main__":
#     setup_logging()
#     logger = logging.getLogger(__name__)
#     merchant_account = MerchantAccount()
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())

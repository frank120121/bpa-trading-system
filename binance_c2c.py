
import asyncio
import aiohttp
from urllib.parse import urlencode
import websockets
from websockets.exceptions import ConnectionClosedError
import logging
from common_utils import get_server_timestamp, hashing
from binance_endpoints import GET_CHAT_CREDENTIALS
from credentials import credentials_dict
from binance_ws_c2c import on_message

logger = logging.getLogger(__name__)

async def send_http_request(method, url, api_key, secret_key, params=None, body=None):
    params = params or {}
    params['timestamp'] = await get_server_timestamp()
    query_string = urlencode(params)
    signature = hashing(query_string, secret_key)
    final_url = f"{url}?{query_string}&signature={signature}"
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": api_key,
        "clientType": "WEB"
    }

    async with aiohttp.ClientSession() as session:
        async with session.request(method, final_url, json=body, headers=headers) as response:
            response_data = await response.json()
            if response.status != 200 or 'data' not in response_data:
                logger.error(f"Error {response.status} from API: {response_data}")
                return None
            return response_data['data']

async def get_websocket_url(api_key, secret_key):
    response_data = await send_http_request("GET", GET_CHAT_CREDENTIALS, api_key, secret_key)
    if response_data and 'chatWssUrl' in response_data and 'listenKey' in response_data:
        return f"{response_data['chatWssUrl']}/{response_data['listenKey']}?token={response_data['listenToken']}&clientType=web"
    return None

async def websocket_listener(uri, api_key, secret_key):
    while True:  # Retry indefinitely
        try:
            async with websockets.connect(uri) as ws:
                logger.info(f"WebSocket connection established, listening for messages...")
                async for message in ws:
                    await on_message(ws, message, api_key, secret_key)
            # If the connection was closed normally, exit the loop
            break
        except ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed unexpectedly: {e}. Attempting to reconnect...")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during WebSocket communication: {e}. Attempting to reconnect..")
        finally:
            await asyncio.sleep(1)

async def establish_websocket_connection(account_name, api_key, secret_key):
    logger.info(f"Starting WebSocket connection for: {account_name}")  
    while True:
        try:
            wss_url = await get_websocket_url(api_key, secret_key)
            if wss_url:
                await websocket_listener(wss_url, api_key, secret_key)
                logger.info(f"WebSocket connection established successfully for: {account_name}") 
            else:
                logger.error(f"Failed to get WebSocket URL for {account_name}.")
        except Exception as e:
            logger.exception(f"An error occurred during WebSocket connection for {account_name}:", exc_info=e)
        await asyncio.sleep(1)
        
async def main_binance_c2c():
    logger.info("Starting WebSocket connections for Binance C2C.")
    tasks = [establish_websocket_connection(account_name, cred['KEY'], cred['SECRET']) for account_name, cred in credentials_dict.items()]
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("An unexpected error occurred: ", exc_info=e)
    finally:
        logger.info("Finished all WebSocket connections.")
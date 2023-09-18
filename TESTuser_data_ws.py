import asyncio
import aiohttp
import websockets
import threading
from credentials import credentials_dict, BASE_URL
from websocket_handlers import on_message
from logging_config import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)

async def send_signed_request(http_method, url_path, api_key, secret_key, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.request(http_method, f"{BASE_URL}{url_path}", headers={'X-MBX-APIKEY': api_key}) as response:
            return await response.json()

async def on_error(ws, error):
    print(f"Error: {error}")

async def run_websocket(api_key, api_secret, merchant_account):
    try:
        listen_key_response = await send_signed_request("POST", "/api/v3/userDataStream", api_key, api_secret, params=None)
        listen_key = listen_key_response.get("listenKey", "")
        if not listen_key:
            logger.error("Failed to get listenKey")
            return
        ws_url = f"wss://stream.binance.com:9443/ws/{listen_key}"
        async with websockets.connect(ws_url) as ws:
            async for message in ws:
                await on_message(ws, message, api_key, api_secret, merchant_account)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
def start_binance_user_stream():
    tasks = []
    for account, creds in credentials_dict.items():
        api_key = creds['KEY']
        api_secret = creds['SECRET']
        task_binance = asyncio.create_task(run_websocket(api_key, api_secret))
        task_chat = threading.Thread(
            target=run_chat_websocket, 
            args=(api_key, api_secret), 
            kwargs={'max_retries': 20, 'initial_backoff': 5, 'max_backoff': 60}, 
            daemon=True
        )
        tasks.append(task_binance)
        task_chat.start()

    asyncio.run(asyncio.gather(*tasks))

def run_chat_websocket(KEY, SECRET, max_retries=10, initial_backoff=5, max_backoff=60):
    logger.info("Chat WebSocket is running.")

async def main_user_data_ws(merchant_account):
    tasks = []
    for account, creds in credentials_dict.items():
        api_key = creds['KEY']
        api_secret = creds['SECRET']
        task_binance = asyncio.create_task(run_websocket(api_key, api_secret, merchant_account))
        task_chat = threading.Thread(
            target=run_chat_websocket, 
            args=(api_key, api_secret), 
            kwargs={'max_retries': 20, 'initial_backoff': 5, 'max_backoff': 60}, 
            daemon=True
        )
        tasks.append(task_binance)
        task_chat.start()

    await asyncio.gather(*tasks)

# Remove this if block
# if __name__ == "__main__":
#    asyncio.run(main())






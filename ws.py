import websocket
import threading
import time
import logging
import random
import traceback
from http_api import send_signed_request 
import websocket_handlers 
from credentials import credentials_dict 

logging.basicConfig(level=logging.DEBUG)


def run_websocket(KEY, SECRET, max_retries=10, initial_backoff=5, max_backoff=60):
    retry_count = 0
    backoff = initial_backoff
    offset = 0 
    
    while retry_count < max_retries or max_retries == -1:
        try:
            uri_path = "/sapi/v1/c2c/chat/retrieveChatCredential"
            response = send_signed_request("GET", uri_path, KEY, SECRET, offset=offset)
            
            if response and 'new_offset' in response:
                offset = response['new_offset']
                logging.info(f"Updated offset to {offset}")
                continue 

            wss_url = ''
            if 'data' in response and 'data' in response['data'] and 'chatWssUrl' in response['data']['data']:
                wss_url = f"{response['data']['data']['chatWssUrl']}/{response['data']['data']['listenKey']}?token={response['data']['data']['listenToken']}&clientType=web"
            else:
                logging.error(f"Key 'chatWssUrl' not found in API response. Full response: {response}")
                return

            logging.info(f"Attempting to connect to WebSocket with URL: {wss_url}")

            ws = websocket.WebSocketApp(
                wss_url,
                on_message=lambda ws, message: websocket_handlers.on_message(ws, message, KEY, SECRET),
                on_error=lambda ws, error: logging.error(f"ERROR: {error}"),
                on_close=lambda ws, close_status_code, close_msg: websocket_handlers.on_close(ws, close_status_code, close_msg, KEY, SECRET)
            )

            ws.run_forever()
            logging.info("WebSocket connection closed gracefully.")
            break  
        except websocket.WebSocketConnectionClosedException:
            logging.error("WebSocket connection closed unexpectedly. Reconnecting...")
        except websocket.WebSocketTimeoutException:
            logging.error("WebSocket connection timed out. Reconnecting...")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}. Reconnecting...")
            traceback.print_exc()

        sleep_time = min(max_backoff, backoff)
        sleep_time += random.uniform(0, 0.1 * sleep_time)
        time.sleep(sleep_time)
        
        backoff *= 2
        retry_count += 1

    if retry_count >= max_retries and max_retries != -1:
        logging.warning("Max retries reached. Exiting.")


def main():
    credentials = list(credentials_dict.values())

    for cred in credentials:
        websocket_thread = threading.Thread(
            target=run_websocket, 
            args=(cred['KEY'], cred['SECRET']), 
            kwargs={'max_retries': 20, 'initial_backoff': 5, 'max_backoff': 60}, 
            daemon=True
        )
        websocket_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting.")
        exit(0)


if __name__ == "__main__":
    main()

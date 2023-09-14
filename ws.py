import websocket
import threading
import time
import logging
from http_api import send_signed_request
import websocket_handlers
from credentials import credentials_dict
import traceback

logging.basicConfig(level=logging.DEBUG)


def run_websocket(KEY, SECRET):
    retry_count = 0  # To keep track of reconnection attempts
    max_retries = 10  # Maximum number of reconnection attempts

    while retry_count < max_retries:
        try:
            offset = 1000  # Example offset, you might want to adjust this dynamically

            uri_path = "/sapi/v1/c2c/chat/retrieveChatCredential"
            response = send_signed_request("GET", uri_path, KEY, SECRET, offset=offset)

            wss_url = ''
            if response and 'data' in response:
                wss_url = f"{response['data']['chatWssUrl']}/{response['data']['listenKey']}?token={response['data']['listenToken']}&clientType=web"

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
        
        time.sleep(5)
        retry_count += 1  # Increment retry counter

    logging.warning(f"Max retries reached. Exiting.")

def main():

    credentials = list(credentials_dict.values())

    for cred in credentials:
        websocket_thread = threading.Thread(target=run_websocket, args=(cred['KEY'], cred['SECRET']), daemon=True)
        websocket_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting.")
        exit(0)

if __name__ == "__main__":
    main()
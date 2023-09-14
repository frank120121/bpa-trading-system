import json
import time
import threading
import websocket
from websocket_handlers import on_message as ws_on_message, on_close as ws_on_close
from database import create_connection, insert_user, update_user_status, get_user_status, update_total_fiat_spent

# Global state
already_processed = set()

wss_url = "<WebSocket URL here>"

def on_message(ws, message):
    global already_processed
    
    print("Received a message")
    msg_json = json.loads(message)
    print("Received message:", msg_json)

    uuid = msg_json.get('uuid', '')

    if uuid in already_processed:
        print(f"Skipping already processed message with uuid {uuid}")
        return

    already_processed.add(uuid)
    ws_on_message(ws, msg_json)

def on_close(ws, close_status_code, close_msg):
    ws_on_close(ws, close_status_code, close_msg)

def run_websocket():
    try:
        ws = websocket.WebSocketApp(wss_url, on_message=on_message, on_close=on_close)
        print("WebSocket Thread started")
        ws.run_forever()
    except Exception as e:
        print("Error running WebSocket:", e)

def main():
    websocket_thread = threading.Thread(target=run_websocket, daemon=True)
    websocket_thread.start()

    print("Main thread is free!")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)

if __name__ == "__main__":
    main()

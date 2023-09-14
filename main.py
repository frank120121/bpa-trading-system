from dotenv import load_dotenv
import os
import requests
import json
import hashlib
import hmac
import time
import threading
import websocket
from http_api import send_signed_request
from websocket_handlers import on_message, on_close
from credentials import KEY, SECRET

def run_websocket(wss_url, already_processed):
    try:
        ws = websocket.WebSocketApp(wss_url, on_message=lambda ws, msg: on_message(ws, msg, already_processed), on_close=on_close)
        print("WebSocket Thread started")
        ws.run_forever()
    except Exception as e:
        print("Error running WebSocket:", e)


def fetch_user_order_detail(adOrderNo, api_key, api_secret, time_diff):
    timestamp = int(time.time() * 1000) + time_diff
    params = {
        'timestamp': timestamp
    }

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature

    url = f"https://api.binance.com/sapi/v1/c2c/orderMatch/getUserOrderDetail?{query_string}&signature={signature}"

    payload = json.dumps({
        "adOrderNo": adOrderNo
    })

    headers = {
        'X-MBX-APIKEY': api_key,
        'clientType': 'web',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    
    return response.json()

if __name__ == "__main__":
    try:
        load_dotenv()
        api_key = os.environ.get('API_KEY_MFMP')
        api_secret = os.environ.get('API_SECRET_MFMP')  # Adjust according to your .env file

        # Fetch server time for timestamp
        response = requests.get('https://api.binance.com/api/v3/time')
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            time_diff = server_time - int(time.time() * 1000)
        else:
            print("Couldn't fetch server time. Using local time.")
            time_diff = 0

        adOrderNo = "20533337797840920576"  # Replace with the actual order number you want to query
        user_order_detail = fetch_user_order_detail(adOrderNo, api_key, api_secret, time_diff)

        print("User Order Detail:", user_order_detail)
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

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

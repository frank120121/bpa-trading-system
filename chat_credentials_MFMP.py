from dotenv import load_dotenv
import os
from binance import ThreadedWebsocketManager
import requests
import time
import hashlib
import hmac
import threading
import signal
import sys
import asyncio  # Don't forget to import asyncio

# Global variables
api_key = None
api_secret = None
twm = None
messages_received = False

# Define a function to handle the termination signal
def handle_signal(sig, frame):
    print("Terminating the script...")
    global twm
    if twm:
        twm.stop()
    sys.exit(0)

# Function to handle errors
def handle_error(e):
    print(f"Error: {e}")

# Register the signal handler
signal.signal(signal.SIGINT, handle_signal)

# Handle WebSocket messages
def handle_message(msg):
    global messages_received
    print("Debug: handle_message function called.")
    print(f"Debug: Message received = {msg}")
    print(f"Debug: Event Loop in Message Handler: {asyncio.get_event_loop()}")
    print(f"Message: {msg}")
    print(f"Event Loop in Message Handler: {asyncio.get_event_loop()}")
    messages_received = True

# Function to stop the script after 2 minutes of inactivity
def stop_script():
    global messages_received
    time.sleep(120)
    if not messages_received:
        print("No messages received for 2 minutes. Terminating the script...")
        handle_signal(None, None)

def main():
    global api_key, api_secret, twm
    
    try:
        load_dotenv()
        api_key = os.environ.get('API_KEY_MFMP')
        api_secret = os.environ.get('API_SECRET_MFMP')

        timestamp = str(int(time.time() * 1000))
        params = {'timestamp': timestamp}
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature

        headers = {
            'X-MBX-APIKEY': api_key,
            'clientType': 'web'
        }

        response = requests.get(
            "https://api.binance.com/sapi/v1/c2c/chat/retrieveChatCredential",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            chat_data = response.json()
            chatWssUrl = chat_data['data']['chatWssUrl']
            listenToken = chat_data['data']['listenToken']

            print(f"Debug: chatWssUrl = {chatWssUrl}")
            print(f"Debug: listenToken = {listenToken}")

            print("Type 'start websocket' to initiate the WebSocket connection.")
            command = input()
            print(f"Event Loop in Main: {asyncio.get_event_loop()}")

            if command == "start websocket":
                print("Attempting to start the WebSocket Manager")
                twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
                twm.start()
                print("WebSocket Manager started")

                print("Attempting to start the user socket")
                twm.start_user_socket(callback=handle_message)
                print("User socket started")

                timer_thread = threading.Thread(target=stop_script)
                timer_thread.start()

                print("WebSocket started successfully")
                twm.join()

            else:
                print("Invalid command. Exiting.")
                sys.exit(0)

        else:
            print(f"Failed to get data: {response.content}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


from binance import ThreadedWebsocketManager
import threading
import signal
import sys
import asyncio
import time

api_key = None
api_secret = None
twm = None
messages_received = False

def handle_signal(sig, frame):
    print("Terminating the WebSocket...")
    global twm
    if twm:
        twm.stop()
    sys.exit(0)

def handle_message(msg):
    global messages_received
    print("Debug: Message received =", msg)
    print("Debug: Event Loop in Message Handler:", asyncio.get_event_loop())
    messages_received = True

def stop_script():
    global messages_received
    time.sleep(120)
    if not messages_received:
        print("No messages received for 2 minutes. Terminating...")
        handle_signal(None, None)

def start_websocket(api_key, api_secret):
    global twm

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

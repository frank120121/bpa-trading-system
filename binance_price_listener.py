import websocket
import json
import threading

class BinancePriceListener:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.last_price = None
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@aggTrade"
        self.ws = websocket.WebSocketApp(self.ws_url, on_message=self.process_msg_stream,
                                         on_open=self.on_open, on_error=self.on_error,
                                         on_close=self.on_close)
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.reconnect_timer = threading.Timer(24 * 60 * 60, self.reconnect)

    def start(self):
        print("Starting thread.")
        self.thread.start()
        self.reconnect_timer.start()

    def process_msg_stream(self, ws, message):
        #print("Received message.")
        msg = json.loads(message)
        self.last_price = float(msg['p'])
        #print(f"Last price of {self.symbol} = {self.last_price}")

    def get_current_price(self):
        return self.last_price

    def on_open(self, ws):
        print("WebSocket connection opened.")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws):
        print("WebSocket connection closed.")

    def reconnect(self):
        print("Reconnecting after 24 hours.")
        self.ws.close()
        self.ws.run_forever()
        self.reconnect_timer = threading.Timer(24 * 60 * 60, self.reconnect)
        self.reconnect_timer.start()

if __name__ == "__main__":
    try:
        price_listener = BinancePriceListener('BTCUSDT')
        price_listener.start()
    except KeyboardInterrupt:
        print("Stopping the listener.")
        price_listener.ws.close()

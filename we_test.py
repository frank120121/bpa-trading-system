import websocket
import json
import logging

logging.basicConfig(level=logging.INFO)

def on_message(ws, message):
    print("Received message:", message)
    message_dict = json.loads(message)
    if message_dict['type'] == 'text' and message_dict['self'] == False:
        reply_content = f"Echo: {message_dict['content']}"
        uuid = message_dict['uuid']
        order_no = message_dict['orderNo']
        send_text_message(ws, reply_content, uuid, order_no)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    logging.info("WebSocket closed")

def on_open(ws):
    print("WebSocket connection is open.")
    sample_message_content = "Your payment is under review, please wait."
    sample_uuid = "some-uuid"
    sample_order_no = "some-order-no"
    send_text_message(ws, sample_message_content, sample_uuid, sample_order_no)

def send_text_message(ws, message_content, uuid, order_no):
    try:
        if ws.sock.connected:
            payload = {
                "content": message_content,
                "uuid": uuid,
                "order_no": order_no
            }
            ws.send(json.dumps(payload))
            logging.info(f"Sent message: {payload}")
        else:
            logging.warning("WebSocket is not open.")
    except Exception as e:
        logging.error(f"An error occurred while sending the message: {e}")

# Simulated variables for API Response (replace this with your actual API response)
response = {
    'code': '000000', 
    'message': 'success', 
    'data': {
        'chatWssUrl': 'wss://im.binance.com:443/chat', 
        'listenKey': 'c2c_c49b83ef5a2d4ec192e34925c967a1fb_v2', 
        'listenToken': 'TOKENd81b3dc03533496e956b840a6f275625'
    }, 
    'success': True
}

wss_url = ''
if response and 'data' in response:
    wss_url = f"{response['data']['chatWssUrl']}/{response['data']['listenKey']}?token={response['data']['listenToken']}&clientType=web"
else:
    print("Failed to get the WebSocket URL.")

if __name__ == "__main__":
    if wss_url:  # Make sure wss_url is available
        ws = websocket.WebSocketApp(wss_url,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.on_open = on_open
        ws.run_forever()
    else:
        print("Could not initialize WebSocket due to missing URL.")

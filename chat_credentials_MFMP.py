import requests
import time
import hashlib
import hmac
from dotenv import load_dotenv
import os

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
        'clientType': 'YOUR_CLIENT_TYPE_HERE'  # Replace with your client type
        # Optionally add 'x-gray-env', 'x-trace-id', and 'x-user-id'
    }

    response = requests.get(
        "https://api.binance.com/sapi/v1/c2c/chat/retrieveChatCredential", 
        headers=headers, 
        params=params
    )
    
    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Failed to get data: {response.content}")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")



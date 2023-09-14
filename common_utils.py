import hashlib
import hmac
import time
import requests
import json

def get_server_timestamp():
    url = "https://api.binance.com/api/v1/time"
    payload = {}
    headers = {}
    try:
        response = requests.get(url, headers=headers, data=payload)
        if response.status_code == 200:
            server_time = json.loads(response.text)['serverTime']
            return server_time
        else:
            return None
    except Exception as e:
        print(f"An error occurred while fetching server time: {e}")
        return None

def get_adjusted_timestamp(offset=0):
    print(f"Using offset: {offset}")
    server_time = get_server_timestamp()
    if server_time:
        return server_time - offset
    else:
        print("Falling back to local time.")
        return int(time.time() * 1000) - offset  # Fall back to local time

def hashing(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

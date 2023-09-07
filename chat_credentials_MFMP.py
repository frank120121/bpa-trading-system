import requests
import time
import hashlib
import hmac
from dotenv import load_dotenv
import os

load_dotenv()
# Your API key and API secret
api_key = os.environ.get('API_KEY_MFMP')
api_secret = os.environ.get('API_SECRET_MFMP')

# Create a timestamp
timestamp = str(int(time.time() * 1000))

# Define your parameters and create a query string
params = {
    'timestamp': timestamp
}
query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

# Create the signature
signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

# Add the signature to your parameters
params['signature'] = signature

# Create headers
headers = {
    'X-MBX-APIKEY': api_key
}

# Make the GET request
response = requests.get("https://api.binance.com/sapi/v1/c2c/chat/retrieveChatCredential", headers=headers, params=params)

# Print the response (or process it)
print(response.json())

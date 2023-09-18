from credentials import credentials_dict
import requests
import hashlib
import hmac
import time
import logging
logging.basicConfig(level=logging.DEBUG)

# Function to create HMAC SHA256 signature
def create_signature(secret_key, query_string):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
# Get your API key and secret key for 'account_1'
api_key = credentials_dict['account_1']['KEY']
secret_key = credentials_dict['account_1']['SECRET']
# The API endpoint and payload (parameter)
api_endpoint = "https://api.binance.com/sapi/v1/c2c/ads/getDetailByNo"
adsNo = "11515582400296718336"
timestamp = str(int(time.time() * 1000))  # Current Unix time in milliseconds
# Create query string and signature
query_string = f"adsNo={adsNo}&timestamp={timestamp}"
signature = create_signature(secret_key, query_string)
# Prepare headers
# ... (rest of the code remains the same)
# Prepare headers
headers = {
    'X-MBX-APIKEY': api_key,
    'clientType': 'web',  # Update this based on your client type
    'x-gray-env': 'some_value',  # Optional: replace 'some_value' with actual value
    'x-trace-id': 'some_trace_id',  # Optional: replace 'some_trace_id' with actual value
    'x-user-id': 'your_user_id'  # Optional: replace 'your_user_id' with actual user ID
}
# ... (rest of the code remains the same)
# Prepare the data payload
data = {
    'adsNo': adsNo,
    'timestamp': timestamp,
    'signature': signature
}
# Send POST request
response = requests.post(api_endpoint, headers=headers, data=data)
# Process the response
if response.status_code == 200:
    print("Success:", response.json())
else:
    print("Failed:", response.content)

import requests
from urllib.parse import urlencode
from common_utils import hashing, get_timestamp
from credentials import BASE_URL, KEY, SECRET
import websocket
import json

def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json;charset=utf-8",
        "X-MBX-APIKEY": KEY,
        "clientType": "WEB"
    })
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")

def send_signed_request(http_method, url_path, payload={}, dataLoad={}):
    query_string = urlencode(payload)
    query_string = query_string.replace('%27', '%22')  # Replace single quote to double quote

    if query_string:
        query_string = f"{query_string}&timestamp={get_timestamp()}"
    else:
        query_string = f"timestamp={get_timestamp()}"

    url = f"{BASE_URL}{url_path}?{query_string}&signature={hashing(query_string, SECRET)}"
    params = {"url": url, "params": {}, "data": dataLoad}
    response = dispatch_request(http_method)(**params)
    return response

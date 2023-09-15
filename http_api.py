import requests
from urllib.parse import urlencode
from common_utils import hashing, get_adjusted_timestamp
from credentials import BASE_URL
import logging

logging.basicConfig(level=logging.DEBUG)

def send_signed_request(http_method, url_path, KEY, SECRET, payload={}, dataLoad={}, offset=0):
    try:
        query_string = urlencode(payload)
        query_string = f"{query_string}&timestamp={get_adjusted_timestamp(offset)}"
        url = f"{BASE_URL}{url_path}?{query_string}&signature={hashing(query_string, SECRET)}"
        
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": KEY,
            "clientType": "WEB"
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = getattr(session, http_method.lower())(url, params={}, data=dataLoad)

        response_data = response.json()
        #print("API response:", response_data)

        if 'data' not in response_data:
            logging.error("API Response does not contain 'data' field")
            return {'success': False}
        
        if response.status_code != 200:
            logging.error(f"Received status code {response.status_code}: {response.text}")
            
            try:
                if response_data['code'] == -1021:
                    server_delay = int(response_data['msg'].split(" ")[-2].replace("ms", ""))
                    new_offset = offset - server_delay  # Adjust offset
                    return {'new_offset': new_offset, 'success': False}
            
            except Exception as e:
                logging.error(f"An error occurred while parsing the error response: {e}")

            return {'success': False}

        return {'success': True, 'data': response_data}

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    return {'success': False}


def send_signed_request_gUOD(order_no, KEY, SECRET, offset=0):
    try:
        uri_path = "/sapi/v1/c2c/orderMatch/getUserOrderDetail"
        payload = {
            "timestamp": get_adjusted_timestamp(offset)
        }
        
        query_string = urlencode(payload)
        url = f"{BASE_URL}{uri_path}?{query_string}&signature={hashing(query_string, SECRET)}"
        
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": KEY,
            "clientType": "WEB"
        }
        
        data_load = {
            "adOrderNo": order_no
        }

        session = requests.Session()
        session.headers.update(headers)
        
        response = session.post(url, json=data_load)
        
        if response.status_code != 200:
            logging.error(f"Received status code {response.status_code}: {response.text}")
            return None

        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None


def send_signed_request_msg_rd(order_no, user_id, KEY, SECRET, offset=0):
    try:
        uri_path = "/sapi/v1/c2c/chat/markOrderMessagesAsRead"
        payload = {
            "timestamp": get_adjusted_timestamp(offset)  # use offset here
        }
        
        query_string = urlencode(payload)
        query_string = f"{query_string}&timestamp={get_adjusted_timestamp(offset)}"  # and here
        url = f"{BASE_URL}{uri_path}?{query_string}&signature={hashing(query_string, SECRET)}"
        
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": KEY,
            "clientType": "WEB"  # Changed to uppercase for consistency
        }
        
        data_load = {
            "orderNo": order_no,
            "userId": user_id
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.post(url, json=data_load)
        
        if response.status_code != 200:
            logging.error(f"Received status code {response.status_code}: {response.text}")
            return None

        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None
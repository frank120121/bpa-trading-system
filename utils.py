from typing import Dict, Any, Optional
from http_api import send_signed_request_gUOD, send_signed_request_msg_rd

def fetch_order_details(order_no: str, KEY: str, SECRET: str) -> Optional[Dict[str, Any]]:

    #print(f"passing KEY: {KEY[:4]}********, SECRET: {SECRET[:4]}********")
    #print("Attempting to fetch order details.")
    try:
        response: Optional[Dict[str, Any]] = send_signed_request_gUOD(order_no, KEY, SECRET)  # Pass KEY and SECRET here
        if response:
            data = response.get('data', {})
            return data
        else:
            print("Empty API response")
            return None
    except Exception as e:
        print("An error occurred while fetching order details:", e)
        return None

def fetch_buyer_name(order_no: str, KEY: str, SECRET: str) -> str:
    try:
        response: Optional[Dict[str, Any]] = send_signed_request_gUOD(order_no, KEY, SECRET)
        
        if response:
            data = response.get('data', {})
            if 'buyerName' in data:
                return data['buyerName']
            else:
                print("Failed to fetch buyer name")
                return None
        else:
            print("Empty API response")
            return None
    except Exception as e:
        print("An error occurred while fetching buyer name:", e)
        return None

def fetch_fiat_unit(order_no: str, KEY: str, SECRET: str) -> str:
    try:
        response: Optional[Dict[str, Any]] = send_signed_request_gUOD(order_no, KEY, SECRET)  # Pass KEY and SECRET here
        
        if response:
            data = response.get('data', {})
            if 'fiatUnit' in data:
                return data['fiatUnit']
            else:
                print("Failed to fetch fiat unit")
                return None
        else:
            print("Empty API response")
            return None
    except Exception as e:
        print("An error occurred while fetching fiat unit", e)
        return None
    

def mark_msg_as_read(order_no: str, user_id: int, KEY: str, SECRET: str) -> bool:
    try:
        response = send_signed_request_msg_rd(order_no, user_id, KEY, SECRET)
        if response:
            # Checking the 'success' field in the API response
            if 'success' in response and response['success'] == True:
                return True
            else:
                print("Failed to mark the message as read")
                return False
        else:
            print("Empty API response")
            return False
    except Exception as e:
        print("An error occurred while marking the message as read:", e)
        return False
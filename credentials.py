import os
from dotenv import load_dotenv

load_dotenv()


BITSO_BASE_URL = "https://api.bitso.com/"
BASE_URL = "https://api.binance.com"


credentials_dict = {
    'account_1': {
        'KEY': os.environ.get('API_KEY_MFMP'),
        'SECRET': os.environ.get('API_SECRET_MFMP')
    },
    'account_2': {
        'KEY': os.environ.get('API_KEY_MGL'),
        'SECRET': os.environ.get('API_SECRET_MGL')
    }
    # Add more accounts as needed
}

# Bitso credentials
bitso_credentials = {
    'bitso_account_MGL': {
        'KEY': os.environ.get('BITSO_KEY_MGL'),
        'SECRET': os.environ.get('BITSO_SECRET_MGL')
    },
    # Add more Bitso accounts as needed
}

# Other exchange credentials
# ...

# WebSocket URLs

bitso_ws_url = 'wss://bitso.com/trade/socket.io/?EIO=4&transport=websocket'

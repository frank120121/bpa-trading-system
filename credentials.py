import os
from dotenv import load_dotenv

load_dotenv()

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

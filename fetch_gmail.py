import asyncio
from googleapiclient.discovery import build
import base64
import re
import pickle
import os
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import logging
from logging_config import setup_logging
setup_logging(log_filename='fetch_emails.log')
logger = logging.getLogger(__name__)

load_dotenv('.env.email')
gmail_credentials_json_path = os.getenv('GMAIL_CREDENTIALS_JSON_PATH')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

async def get_gmail_service():
    creds = None
    token_path = 'C:/Users/p7016/Documents/bpa/token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print("Error refreshing credentials, re-authenticating...")
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                gmail_credentials_json_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

async def gmail_fetch_ip(last_four):
    logger.info(f"Searching ip for: {last_four}")
    service = await get_gmail_service()
    messages_request = await asyncio.to_thread(service.users().messages().list, userId='me', q=f'subject:[Binance] Tienes una nueva orden P2P {last_four}')
    messages_response = messages_request.execute()
    messages = messages_response.get('messages', [])

    # Check the first email in the search results
    for message in messages[:1]:
        msg_request = await asyncio.to_thread(service.users().messages().get, userId='me', id=message['id'], format='full')
        msg_response = msg_request.execute()
        msg_body = msg_response['payload']['body']['data']
        
        # Decode the email body, which is base64 encoded
        email_content = base64.urlsafe_b64decode(msg_body).decode('utf-8')

        # Find the "desde" keyword and extract the IP address that follows it
        desde_match = re.search(r'desde\s+(\d+\.\d+\.\d+\.\d+)', email_content, re.IGNORECASE)
        if desde_match:
            logger.info(f"Ip found: {desde_match.group(1)}")
            return desde_match.group(1)
        else:
            # Handle the case where no match was found, e.g., return a default value or raise an exception
            logger.warning("No IP address found in email content")
            return None

async def main():
    last_four_digits = '1920'
    ip_address = await gmail_fetch_ip(last_four_digits)
    print("Extracted IP Address:", ip_address)

if __name__ == "__main__":
    asyncio.run(main())


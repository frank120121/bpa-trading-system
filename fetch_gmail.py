import asyncio
from googleapiclient.discovery import build
import base64
import re
import pickle
import os.path

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

async def get_gmail_service():
    creds = None
    if os.path.exists('C:/Users/p7016/Documents/bpa/token.pickle'):
        with open('C:/Users/p7016/Documents/bpa/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        # Handle credential validation or obtain new credentials if needed
        pass

    return build('gmail', 'v1', credentials=creds)

async def gmail_fetch_ip(last_four):
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
            return desde_match.group(1)

async def main():
    last_four_digits = '1920'
    ip_address = await gmail_fetch_ip(last_four_digits)
    print("Extracted IP Address:", ip_address)

if __name__ == "__main__":
    asyncio.run(main())

